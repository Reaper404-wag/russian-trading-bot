"""
Unit tests for portfolio management service
"""

import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from russian_trading_bot.services.portfolio_manager import (
    PortfolioManager, PortfolioSnapshot, PerformanceMetrics, TaxCalculation
)
from russian_trading_bot.models.trading import (
    ExecutionResult, OrderStatus, OrderAction, Position
)
from russian_trading_bot.models.market_data import MarketData


class TestPortfolioManager(unittest.TestCase):
    """Test cases for PortfolioManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.initial_cash = Decimal('1000000')  # 1M RUB
        self.portfolio_manager = PortfolioManager(self.initial_cash)
    
    def test_initialization(self):
        """Test portfolio manager initialization"""
        self.assertEqual(self.portfolio_manager.portfolio.cash_balance, self.initial_cash)
        self.assertEqual(self.portfolio_manager.portfolio.currency, "RUB")
        self.assertEqual(len(self.portfolio_manager.portfolio.positions), 0)
        self.assertEqual(self.portfolio_manager.initial_value, self.initial_cash)
    
    def test_buy_order_new_position(self):
        """Test handling buy order for new position"""
        # Create execution result
        execution = ExecutionResult(
            order_id="TEST001",
            status=OrderStatus.FILLED,
            filled_quantity=100,
            average_price=Decimal('150.50'),
            commission=Decimal('15.05'),
            timestamp=datetime.now()
        )
        
        order_details = {
            'symbol': 'SBER',
            'action': OrderAction.BUY,
            'quantity': 100
        }
        
        # Update position
        self.portfolio_manager.update_position(execution, order_details)
        
        # Check position was created
        self.assertIn('SBER', self.portfolio_manager.portfolio.positions)
        position = self.portfolio_manager.portfolio.positions['SBER']
        
        self.assertEqual(position.symbol, 'SBER')
        self.assertEqual(position.quantity, 100)
        self.assertEqual(position.average_price, Decimal('150.50'))
        self.assertEqual(position.currency, 'RUB')
        
        # Check cash was deducted
        expected_cash = self.initial_cash - (Decimal('150.50') * 100 + Decimal('15.05'))
        self.assertEqual(self.portfolio_manager.portfolio.cash_balance, expected_cash)
        
        # Check trade history
        self.assertEqual(len(self.portfolio_manager.trade_history), 1)
        trade = self.portfolio_manager.trade_history[0]
        self.assertEqual(trade['symbol'], 'SBER')
        self.assertEqual(trade['action'], 'buy')
        self.assertEqual(trade['quantity'], 100)
    
    def test_buy_order_existing_position(self):
        """Test handling buy order for existing position"""
        # First buy
        execution1 = ExecutionResult(
            order_id="TEST001",
            status=OrderStatus.FILLED,
            filled_quantity=100,
            average_price=Decimal('150.00'),
            commission=Decimal('15.00')
        )
        
        order_details1 = {
            'symbol': 'SBER',
            'action': OrderAction.BUY,
            'quantity': 100
        }
        
        self.portfolio_manager.update_position(execution1, order_details1)
        
        # Second buy
        execution2 = ExecutionResult(
            order_id="TEST002",
            status=OrderStatus.FILLED,
            filled_quantity=50,
            average_price=Decimal('160.00'),
            commission=Decimal('8.00')
        )
        
        order_details2 = {
            'symbol': 'SBER',
            'action': OrderAction.BUY,
            'quantity': 50
        }
        
        self.portfolio_manager.update_position(execution2, order_details2)
        
        # Check position was updated correctly
        position = self.portfolio_manager.portfolio.positions['SBER']
        self.assertEqual(position.quantity, 150)
        
        # Check average price calculation
        # (100 * 150 + 50 * 160) / 150 = 153.33
        expected_avg_price = (Decimal('150.00') * 100 + Decimal('160.00') * 50) / 150
        self.assertEqual(position.average_price, expected_avg_price)
    
    def test_sell_order_partial(self):
        """Test handling partial sell order"""
        # First buy 100 shares
        execution_buy = ExecutionResult(
            order_id="BUY001",
            status=OrderStatus.FILLED,
            filled_quantity=100,
            average_price=Decimal('150.00'),
            commission=Decimal('15.00')
        )
        
        order_buy = {
            'symbol': 'SBER',
            'action': OrderAction.BUY,
            'quantity': 100
        }
        
        self.portfolio_manager.update_position(execution_buy, order_buy)
        
        # Then sell 30 shares
        execution_sell = ExecutionResult(
            order_id="SELL001",
            status=OrderStatus.FILLED,
            filled_quantity=30,
            average_price=Decimal('160.00'),
            commission=Decimal('4.80')
        )
        
        order_sell = {
            'symbol': 'SBER',
            'action': OrderAction.SELL,
            'quantity': 30
        }
        
        self.portfolio_manager.update_position(execution_sell, order_sell)
        
        # Check position quantity
        position = self.portfolio_manager.portfolio.positions['SBER']
        self.assertEqual(position.quantity, 70)
        
        # Check realized P&L
        # Proceeds: 30 * 160 - 4.80 = 4795.20
        # Cost basis: 30 * 150 = 4500
        # Realized P&L: 4795.20 - 4500 = 295.20
        expected_realized_pnl = Decimal('30') * Decimal('160.00') - Decimal('4.80') - Decimal('30') * Decimal('150.00')
        self.assertEqual(position.realized_pnl, expected_realized_pnl)
    
    def test_sell_order_full_position(self):
        """Test selling entire position"""
        # Buy 100 shares
        execution_buy = ExecutionResult(
            order_id="BUY001",
            status=OrderStatus.FILLED,
            filled_quantity=100,
            average_price=Decimal('150.00'),
            commission=Decimal('15.00')
        )
        
        order_buy = {
            'symbol': 'SBER',
            'action': OrderAction.BUY,
            'quantity': 100
        }
        
        self.portfolio_manager.update_position(execution_buy, order_buy)
        
        # Sell all 100 shares
        execution_sell = ExecutionResult(
            order_id="SELL001",
            status=OrderStatus.FILLED,
            filled_quantity=100,
            average_price=Decimal('160.00'),
            commission=Decimal('16.00')
        )
        
        order_sell = {
            'symbol': 'SBER',
            'action': OrderAction.SELL,
            'quantity': 100
        }
        
        self.portfolio_manager.update_position(execution_sell, order_sell)
        
        # Check position was removed
        self.assertNotIn('SBER', self.portfolio_manager.portfolio.positions)
        
        # Check cash balance
        # Initial: 1,000,000
        # Buy cost: 150 * 100 + 15 = 15,015
        # Sell proceeds: 160 * 100 - 16 = 15,984
        # Final cash: 1,000,000 - 15,015 + 15,984 = 1,000,969
        expected_cash = self.initial_cash - Decimal('15015') + Decimal('15984')
        self.assertEqual(self.portfolio_manager.portfolio.cash_balance, expected_cash)
    
    def test_sell_order_insufficient_shares(self):
        """Test selling more shares than available"""
        # Buy 50 shares
        execution_buy = ExecutionResult(
            order_id="BUY001",
            status=OrderStatus.FILLED,
            filled_quantity=50,
            average_price=Decimal('150.00'),
            commission=Decimal('7.50')
        )
        
        order_buy = {
            'symbol': 'SBER',
            'action': OrderAction.BUY,
            'quantity': 50
        }
        
        self.portfolio_manager.update_position(execution_buy, order_buy)
        
        # Try to sell 100 shares
        execution_sell = ExecutionResult(
            order_id="SELL001",
            status=OrderStatus.FILLED,
            filled_quantity=100,
            average_price=Decimal('160.00'),
            commission=Decimal('16.00')
        )
        
        order_sell = {
            'symbol': 'SBER',
            'action': OrderAction.SELL,
            'quantity': 100
        }
        
        # Should raise ValueError
        with self.assertRaises(ValueError):
            self.portfolio_manager.update_position(execution_sell, order_sell)
    
    def test_sell_order_no_position(self):
        """Test selling shares without existing position"""
        execution_sell = ExecutionResult(
            order_id="SELL001",
            status=OrderStatus.FILLED,
            filled_quantity=100,
            average_price=Decimal('160.00'),
            commission=Decimal('16.00')
        )
        
        order_sell = {
            'symbol': 'SBER',
            'action': OrderAction.SELL,
            'quantity': 100
        }
        
        # Should raise ValueError
        with self.assertRaises(ValueError):
            self.portfolio_manager.update_position(execution_sell, order_sell)
    
    def test_update_market_prices(self):
        """Test updating market prices"""
        # Create position
        execution = ExecutionResult(
            order_id="TEST001",
            status=OrderStatus.FILLED,
            filled_quantity=100,
            average_price=Decimal('150.00'),
            commission=Decimal('15.00')
        )
        
        order_details = {
            'symbol': 'SBER',
            'action': OrderAction.BUY,
            'quantity': 100
        }
        
        self.portfolio_manager.update_position(execution, order_details)
        
        # Update market prices
        market_data = {
            'SBER': MarketData(
                symbol='SBER',
                timestamp=datetime.now(),
                price=Decimal('160.00'),
                volume=1000
            )
        }
        
        self.portfolio_manager.update_market_prices(market_data)
        
        # Check position was updated
        position = self.portfolio_manager.portfolio.positions['SBER']
        self.assertEqual(position.current_price, Decimal('160.00'))
        self.assertEqual(position.market_value, Decimal('16000.00'))  # 100 * 160
        self.assertEqual(position.unrealized_pnl, Decimal('1000.00'))  # (160 - 150) * 100
    
    def test_calculate_pnl(self):
        """Test P&L calculation"""
        # Create positions with different P&L scenarios
        # Position 1: Unrealized gain
        execution1 = ExecutionResult(
            order_id="TEST001",
            status=OrderStatus.FILLED,
            filled_quantity=100,
            average_price=Decimal('150.00'),
            commission=Decimal('15.00')
        )
        
        order1 = {'symbol': 'SBER', 'action': OrderAction.BUY, 'quantity': 100}
        self.portfolio_manager.update_position(execution1, order1)
        
        # Position 2: Realized gain from partial sell
        execution2_buy = ExecutionResult(
            order_id="TEST002",
            status=OrderStatus.FILLED,
            filled_quantity=200,
            average_price=Decimal('100.00'),
            commission=Decimal('20.00')
        )
        
        order2_buy = {'symbol': 'GAZP', 'action': OrderAction.BUY, 'quantity': 200}
        self.portfolio_manager.update_position(execution2_buy, order2_buy)
        
        execution2_sell = ExecutionResult(
            order_id="TEST003",
            status=OrderStatus.FILLED,
            filled_quantity=50,
            average_price=Decimal('120.00'),
            commission=Decimal('6.00')
        )
        
        order2_sell = {'symbol': 'GAZP', 'action': OrderAction.SELL, 'quantity': 50}
        self.portfolio_manager.update_position(execution2_sell, order2_sell)
        
        # Update market prices
        market_data = {
            'SBER': MarketData(symbol='SBER', timestamp=datetime.now(), price=Decimal('160.00'), volume=1000),
            'GAZP': MarketData(symbol='GAZP', timestamp=datetime.now(), price=Decimal('110.00'), volume=1000)
        }
        
        self.portfolio_manager.update_market_prices(market_data)
        
        # Calculate P&L
        pnl_metrics = self.portfolio_manager.calculate_pnl()
        
        # Check unrealized P&L
        # SBER: (160 - 150) * 100 = 1000
        # GAZP: (110 - 100) * 150 = 1500
        # Total unrealized: 2500
        expected_unrealized = Decimal('1000') + Decimal('1500')
        self.assertEqual(pnl_metrics['unrealized_pnl'], expected_unrealized)
        
        # Check realized P&L
        # GAZP: (120 * 50 - 6) - (100 * 50) = 5994 - 5000 = 994
        expected_realized = Decimal('994')
        self.assertEqual(pnl_metrics['realized_pnl'], expected_realized)
        
        # Check total P&L
        expected_total = expected_unrealized + expected_realized
        self.assertEqual(pnl_metrics['total_pnl'], expected_total)
    
    def test_take_snapshot(self):
        """Test taking portfolio snapshot"""
        # Create position
        execution = ExecutionResult(
            order_id="TEST001",
            status=OrderStatus.FILLED,
            filled_quantity=100,
            average_price=Decimal('150.00'),
            commission=Decimal('15.00')
        )
        
        order_details = {
            'symbol': 'SBER',
            'action': OrderAction.BUY,
            'quantity': 100
        }
        
        self.portfolio_manager.update_position(execution, order_details)
        
        # Update market price
        market_data = {
            'SBER': MarketData(
                symbol='SBER',
                timestamp=datetime.now(),
                price=Decimal('160.00'),
                volume=1000
            )
        }
        
        self.portfolio_manager.update_market_prices(market_data)
        
        # Take snapshot
        snapshot = self.portfolio_manager.take_snapshot()
        
        # Check snapshot values
        expected_positions_value = Decimal('16000.00')  # 100 * 160
        expected_cash = self.initial_cash - Decimal('15015.00')  # Initial - (150*100 + 15)
        expected_total = expected_cash + expected_positions_value
        
        self.assertEqual(snapshot.positions_value, expected_positions_value)
        self.assertEqual(snapshot.cash_balance, expected_cash)
        self.assertEqual(snapshot.total_value, expected_total)
        self.assertEqual(snapshot.positions_count, 1)
        self.assertEqual(snapshot.currency, "RUB")
        
        # Check snapshot was added to history
        self.assertEqual(len(self.portfolio_manager.snapshots), 1)
        self.assertEqual(self.portfolio_manager.snapshots[0], snapshot)
    
    def test_get_portfolio_summary(self):
        """Test getting portfolio summary"""
        # Create position
        execution = ExecutionResult(
            order_id="TEST001",
            status=OrderStatus.FILLED,
            filled_quantity=100,
            average_price=Decimal('150.00'),
            commission=Decimal('15.00')
        )
        
        order_details = {
            'symbol': 'SBER',
            'action': OrderAction.BUY,
            'quantity': 100
        }
        
        self.portfolio_manager.update_position(execution, order_details)
        
        # Update market price
        market_data = {
            'SBER': MarketData(
                symbol='SBER',
                timestamp=datetime.now(),
                price=Decimal('160.00'),
                volume=1000
            )
        }
        
        self.portfolio_manager.update_market_prices(market_data)
        
        # Get summary
        summary = self.portfolio_manager.get_portfolio_summary()
        
        # Check summary structure
        self.assertIn('timestamp', summary)
        self.assertIn('total_value', summary)
        self.assertIn('cash_balance', summary)
        self.assertIn('positions_count', summary)
        self.assertIn('currency', summary)
        self.assertIn('pnl_metrics', summary)
        self.assertIn('positions', summary)
        
        # Check values
        self.assertEqual(summary['positions_count'], 1)
        self.assertEqual(summary['currency'], 'RUB')
        self.assertEqual(len(summary['positions']), 1)
        
        # Check position details
        position_summary = summary['positions'][0]
        self.assertEqual(position_summary['symbol'], 'SBER')
        self.assertEqual(position_summary['quantity'], 100)
        self.assertEqual(position_summary['average_price'], 150.0)
        self.assertEqual(position_summary['current_price'], 160.0)
        self.assertEqual(position_summary['market_value'], 16000.0)
        self.assertEqual(position_summary['unrealized_pnl'], 1000.0)
    
    def test_failed_execution_ignored(self):
        """Test that failed executions are ignored"""
        execution = ExecutionResult(
            order_id="FAILED001",
            status=OrderStatus.REJECTED,
            error_message="Insufficient funds"
        )
        
        order_details = {
            'symbol': 'SBER',
            'action': OrderAction.BUY,
            'quantity': 100
        }
        
        # Update position with failed execution
        self.portfolio_manager.update_position(execution, order_details)
        
        # Check no position was created
        self.assertEqual(len(self.portfolio_manager.portfolio.positions), 0)
        
        # Check cash balance unchanged
        self.assertEqual(self.portfolio_manager.portfolio.cash_balance, self.initial_cash)
        
        # Check no trade history
        self.assertEqual(len(self.portfolio_manager.trade_history), 0)
    
    def test_get_position(self):
        """Test getting specific position"""
        # Create position
        execution = ExecutionResult(
            order_id="TEST001",
            status=OrderStatus.FILLED,
            filled_quantity=100,
            average_price=Decimal('150.00'),
            commission=Decimal('15.00')
        )
        
        order_details = {
            'symbol': 'SBER',
            'action': OrderAction.BUY,
            'quantity': 100
        }
        
        self.portfolio_manager.update_position(execution, order_details)
        
        # Get position
        position = self.portfolio_manager.get_position('SBER')
        self.assertIsNotNone(position)
        self.assertEqual(position.symbol, 'SBER')
        self.assertEqual(position.quantity, 100)
        
        # Test case insensitive
        position_lower = self.portfolio_manager.get_position('sber')
        self.assertIsNotNone(position_lower)
        
        # Test non-existent position
        no_position = self.portfolio_manager.get_position('GAZP')
        self.assertIsNone(no_position)
    
    def test_get_available_cash(self):
        """Test getting available cash"""
        self.assertEqual(self.portfolio_manager.get_available_cash(), self.initial_cash)
        
        # After buying shares
        execution = ExecutionResult(
            order_id="TEST001",
            status=OrderStatus.FILLED,
            filled_quantity=100,
            average_price=Decimal('150.00'),
            commission=Decimal('15.00')
        )
        
        order_details = {
            'symbol': 'SBER',
            'action': OrderAction.BUY,
            'quantity': 100
        }
        
        self.portfolio_manager.update_position(execution, order_details)
        
        expected_cash = self.initial_cash - Decimal('15015.00')
        self.assertEqual(self.portfolio_manager.get_available_cash(), expected_cash)


if __name__ == '__main__':
    unittest.main()