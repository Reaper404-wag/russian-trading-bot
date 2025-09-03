"""
Unit tests for Russian market portfolio diversification rules
Tests sector diversification, correlation analysis, and position size limits
"""

import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List

from ..services.risk_manager import (
    RussianMarketRiskManager, 
    Portfolio, 
    Position, 
    RiskParameters
)


class TestDiversificationRules(unittest.TestCase):
    """Test cases for Russian market diversification rules"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.risk_manager = RussianMarketRiskManager()
        
        # Sample Russian stock sectors
        self.stock_sectors = {
            'SBER': 'BANKING',
            'GAZP': 'OIL_GAS', 
            'LKOH': 'OIL_GAS',
            'ROSN': 'OIL_GAS',
            'NVTK': 'OIL_GAS',
            'YNDX': 'INFORMATION_TECHNOLOGY',
            'GMKN': 'METALS_MINING',
            'MGNT': 'CONSUMER_STAPLES',
            'MTSS': 'COMMUNICATION_SERVICES',
            'VTBR': 'BANKING',
            'ALRS': 'METALS_MINING',
            'SNGS': 'OIL_GAS',
            'TATN': 'OIL_GAS',
            'NLMK': 'METALS_MINING',
            'MAGN': 'METALS_MINING'
        }
        
        # Sample price histories for correlation testing
        self.price_histories = {
            'SBER': [Decimal('250'), Decimal('255'), Decimal('248'), Decimal('252'), Decimal('260')],
            'GAZP': [Decimal('180'), Decimal('185'), Decimal('175'), Decimal('182'), Decimal('190')],
            'LKOH': [Decimal('6500'), Decimal('6600'), Decimal('6400'), Decimal('6550'), Decimal('6700')],
            'YNDX': [Decimal('2800'), Decimal('2750'), Decimal('2900'), Decimal('2850'), Decimal('2800')]
        }
    
    def create_test_portfolio(self, positions_data: Dict[str, Dict]) -> Portfolio:
        """Create a test portfolio with given positions"""
        positions = {}
        for symbol, data in positions_data.items():
            positions[symbol] = Position(
                symbol=symbol,
                quantity=data['quantity'],
                entry_price=data['entry_price'],
                current_price=data['current_price'],
                market_value=data['current_price'] * data['quantity'],
                unrealized_pnl=(data['current_price'] - data['entry_price']) * data['quantity'],
                entry_date=datetime.now(),
                sector=self.stock_sectors.get(symbol, 'UNKNOWN')
            )
        
        return Portfolio(
            positions=positions,
            cash_balance=Decimal('100000')  # 100k RUB cash
        )
    
    def test_sector_diversification_compliant_portfolio(self):
        """Test sector diversification with compliant portfolio"""
        # Create well-diversified portfolio
        positions_data = {
            'SBER': {'quantity': 100, 'entry_price': Decimal('250'), 'current_price': Decimal('260')},  # Banking 13%
            'GAZP': {'quantity': 50, 'entry_price': Decimal('180'), 'current_price': Decimal('190')},   # Oil/Gas 9.5%
            'YNDX': {'quantity': 10, 'entry_price': Decimal('2800'), 'current_price': Decimal('2850')}, # IT 14.25%
            'MGNT': {'quantity': 20, 'entry_price': Decimal('5000'), 'current_price': Decimal('5200')}, # Consumer 10.4%
            'MTSS': {'quantity': 300, 'entry_price': Decimal('300'), 'current_price': Decimal('320')}   # Telecom 9.6%
        }
        
        portfolio = self.create_test_portfolio(positions_data)
        result = self.risk_manager.check_sector_diversification_rules(portfolio, self.stock_sectors)
        
        self.assertTrue(result['is_compliant'])
        self.assertEqual(len(result['violations']), 0)
        self.assertIn('BANKING', result['sector_allocations'])
        self.assertIn('OIL_GAS', result['sector_allocations'])
        
    def test_sector_diversification_oil_gas_concentration(self):
        """Test sector diversification with oil/gas over-concentration"""
        # Create portfolio with too much oil/gas exposure
        positions_data = {
            'GAZP': {'quantity': 200, 'entry_price': Decimal('180'), 'current_price': Decimal('190')},  # 38k
            'LKOH': {'quantity': 8, 'entry_price': Decimal('6500'), 'current_price': Decimal('6700')},  # 53.6k
            'ROSN': {'quantity': 100, 'entry_price': Decimal('500'), 'current_price': Decimal('520')},  # 52k
            'SBER': {'quantity': 50, 'entry_price': Decimal('250'), 'current_price': Decimal('260')}    # 13k
        }
        
        portfolio = self.create_test_portfolio(positions_data)
        result = self.risk_manager.check_sector_diversification_rules(portfolio, self.stock_sectors)
        
        self.assertFalse(result['is_compliant'])
        self.assertGreater(len(result['violations']), 0)
        
        # Check for oil/gas concentration violation
        oil_gas_violation = next(
            (v for v in result['violations'] if v['sector'] == 'OIL_GAS'), None
        )
        self.assertIsNotNone(oil_gas_violation)
        self.assertGreater(oil_gas_violation['current_allocation'], 25.0)
        
    def test_sector_diversification_high_risk_sectors(self):
        """Test high-risk sector concentration limits"""
        # Create portfolio with too much exposure to high-risk sectors
        positions_data = {
            'GAZP': {'quantity': 150, 'entry_price': Decimal('180'), 'current_price': Decimal('190')},  # Oil/Gas
            'SBER': {'quantity': 120, 'entry_price': Decimal('250'), 'current_price': Decimal('260')},  # Banking
            'GMKN': {'quantity': 5, 'entry_price': Decimal('20000'), 'current_price': Decimal('21000')}, # Metals
            'YNDX': {'quantity': 5, 'entry_price': Decimal('2800'), 'current_price': Decimal('2850')}   # IT (low risk)
        }
        
        portfolio = self.create_test_portfolio(positions_data)
        result = self.risk_manager.check_sector_diversification_rules(portfolio, self.stock_sectors)
        
        # Should have high-risk sector concentration violation
        high_risk_violation = next(
            (v for v in result['violations'] if v['type'] == 'HIGH_RISK_SECTOR_CONCENTRATION'), None
        )
        self.assertIsNotNone(high_risk_violation)
        self.assertGreater(result['high_risk_sectors_total'], 50.0)
        
    def test_position_size_limits_compliant(self):
        """Test position size limits with compliant portfolio"""
        positions_data = {
            'SBER': {'quantity': 50, 'entry_price': Decimal('250'), 'current_price': Decimal('260')},   # ~6.5%
            'GAZP': {'quantity': 80, 'entry_price': Decimal('180'), 'current_price': Decimal('190')},   # ~7.6%
            'YNDX': {'quantity': 5, 'entry_price': Decimal('2800'), 'current_price': Decimal('2850')},  # ~7.1%
            'MGNT': {'quantity': 25, 'entry_price': Decimal('5000'), 'current_price': Decimal('5200')}, # ~6.5%
        }
        
        portfolio = self.create_test_portfolio(positions_data)
        result = self.risk_manager.check_position_size_limits(portfolio)
        
        self.assertTrue(result['is_compliant'])
        self.assertEqual(len(result['violations']), 0)
        
        # Check that all positions are within limits
        for symbol, allocation in result['position_allocations'].items():
            if symbol in result['blue_chip_symbols']:
                self.assertLessEqual(allocation, result['limits']['blue_chip_stock'])
            else:
                self.assertLessEqual(allocation, result['limits']['individual_stock'])
    
    def test_position_size_limits_violation(self):
        """Test position size limits with violations"""
        positions_data = {
            'SBER': {'quantity': 200, 'entry_price': Decimal('250'), 'current_price': Decimal('260')},  # ~26% (blue-chip)
            'YNDX': {'quantity': 20, 'entry_price': Decimal('2800'), 'current_price': Decimal('2850')}, # ~28.5% (blue-chip)
            'MGNT': {'quantity': 30, 'entry_price': Decimal('5000'), 'current_price': Decimal('5200')}, # ~7.8% (non-blue-chip, OK)
        }
        
        portfolio = self.create_test_portfolio(positions_data)
        result = self.risk_manager.check_position_size_limits(portfolio)
        
        self.assertFalse(result['is_compliant'])
        self.assertGreaterEqual(len(result['violations']), 2)  # SBER and YNDX should violate
        
        # Check specific violations
        sber_violation = next((v for v in result['violations'] if v['symbol'] == 'SBER'), None)
        yndx_violation = next((v for v in result['violations'] if v['symbol'] == 'YNDX'), None)
        
        self.assertIsNotNone(sber_violation)
        self.assertIsNotNone(yndx_violation)
        self.assertEqual(sber_violation['stock_type'], 'blue-chip')
        self.assertEqual(yndx_violation['stock_type'], 'blue-chip')
    
    def test_stock_correlation_calculation(self):
        """Test stock correlation calculation"""
        # Test correlation between SBER and GAZP
        correlation = self.risk_manager.calculate_stock_correlation(
            'SBER', 'GAZP',
            self.price_histories['SBER'],
            self.price_histories['GAZP']
        )
        
        self.assertIsNotNone(correlation)
        self.assertGreaterEqual(correlation, -1.0)
        self.assertLessEqual(correlation, 1.0)
        
        # Test self-correlation (should be close to 1)
        self_correlation = self.risk_manager.calculate_stock_correlation(
            'SBER', 'SBER',
            self.price_histories['SBER'],
            self.price_histories['SBER']
        )
        self.assertAlmostEqual(self_correlation, 1.0, places=2)
        
        # Test with insufficient data
        short_history = [Decimal('100')]
        correlation_insufficient = self.risk_manager.calculate_stock_correlation(
            'SBER', 'GAZP',
            short_history,
            self.price_histories['GAZP']
        )
        self.assertIsNone(correlation_insufficient)
    
    def test_correlation_matrix_building(self):
        """Test correlation matrix building"""
        symbols = ['SBER', 'GAZP', 'LKOH', 'YNDX']
        correlation_matrix = self.risk_manager.build_correlation_matrix(symbols, self.price_histories)
        
        # Check diagonal elements (should be 1.0)
        for symbol in symbols:
            self.assertEqual(correlation_matrix.get((symbol, symbol)), 1.0)
        
        # Check symmetry
        for i, symbol1 in enumerate(symbols):
            for j, symbol2 in enumerate(symbols):
                if i != j:
                    corr_12 = correlation_matrix.get((symbol1, symbol2))
                    corr_21 = correlation_matrix.get((symbol2, symbol1))
                    if corr_12 is not None and corr_21 is not None:
                        self.assertEqual(corr_12, corr_21)
    
    def test_correlation_limits_compliant(self):
        """Test correlation limits with compliant portfolio"""
        positions_data = {
            'SBER': {'quantity': 100, 'entry_price': Decimal('250'), 'current_price': Decimal('260')},
            'YNDX': {'quantity': 10, 'entry_price': Decimal('2800'), 'current_price': Decimal('2850')},
        }
        
        portfolio = self.create_test_portfolio(positions_data)
        
        # Create correlation matrix with low correlations
        correlation_matrix = {
            ('SBER', 'YNDX'): 0.3,  # Low correlation
            ('YNDX', 'SBER'): 0.3,
            ('SBER', 'SBER'): 1.0,
            ('YNDX', 'YNDX'): 1.0
        }
        
        result = self.risk_manager.check_correlation_limits(portfolio, correlation_matrix)
        
        self.assertTrue(result['is_compliant'])
        self.assertEqual(len(result['violations']), 0)
        self.assertEqual(len(result['high_correlation_pairs']), 0)
    
    def test_correlation_limits_violation(self):
        """Test correlation limits with violations"""
        positions_data = {
            'GAZP': {'quantity': 100, 'entry_price': Decimal('180'), 'current_price': Decimal('190')},  # 19k
            'LKOH': {'quantity': 3, 'entry_price': Decimal('6500'), 'current_price': Decimal('6700')},  # 20.1k
            'ROSN': {'quantity': 80, 'entry_price': Decimal('500'), 'current_price': Decimal('520')},   # 41.6k
        }
        
        portfolio = self.create_test_portfolio(positions_data)
        
        # Create correlation matrix with high correlations (oil companies)
        correlation_matrix = {
            ('GAZP', 'LKOH'): 0.85,  # High correlation
            ('GAZP', 'ROSN'): 0.80,  # High correlation
            ('LKOH', 'ROSN'): 0.75,  # High correlation
            ('LKOH', 'GAZP'): 0.85,
            ('ROSN', 'GAZP'): 0.80,
            ('ROSN', 'LKOH'): 0.75,
            ('GAZP', 'GAZP'): 1.0,
            ('LKOH', 'LKOH'): 1.0,
            ('ROSN', 'ROSN'): 1.0
        }
        
        result = self.risk_manager.check_correlation_limits(portfolio, correlation_matrix)
        
        self.assertFalse(result['is_compliant'])
        self.assertGreater(len(result['violations']), 0)
        self.assertGreater(len(result['high_correlation_pairs']), 0)
        
        # Should have excessive correlation violation
        excessive_corr_violation = next(
            (v for v in result['violations'] if v['type'] == 'EXCESSIVE_CORRELATION'), None
        )
        self.assertIsNotNone(excessive_corr_violation)
    
    def test_comprehensive_diversification_enforcement(self):
        """Test comprehensive diversification rule enforcement"""
        # Create portfolio with multiple violations
        positions_data = {
            'GAZP': {'quantity': 200, 'entry_price': Decimal('180'), 'current_price': Decimal('190')},  # Oil/Gas
            'LKOH': {'quantity': 10, 'entry_price': Decimal('6500'), 'current_price': Decimal('6700')}, # Oil/Gas
            'ROSN': {'quantity': 100, 'entry_price': Decimal('500'), 'current_price': Decimal('520')},  # Oil/Gas
            'SBER': {'quantity': 200, 'entry_price': Decimal('250'), 'current_price': Decimal('260')},  # Banking (large position)
        }
        
        portfolio = self.create_test_portfolio(positions_data)
        
        result = self.risk_manager.enforce_diversification_rules(
            portfolio, self.stock_sectors, self.price_histories
        )
        
        self.assertFalse(result['is_fully_compliant'])
        self.assertGreater(result['total_violations'], 0)
        self.assertLess(result['diversification_score'], 1.0)
        
        # Should have sector, position, and potentially correlation violations
        self.assertFalse(result['sector_analysis']['is_compliant'])
        self.assertFalse(result['position_analysis']['is_compliant'])
        
        # Check that recommendations are provided
        self.assertGreater(len(result['all_recommendations']), 0)
    
    def test_diversification_score_calculation(self):
        """Test diversification score calculation"""
        # Create well-diversified portfolio
        positions_data = {
            'SBER': {'quantity': 50, 'entry_price': Decimal('250'), 'current_price': Decimal('260')},   # Banking
            'YNDX': {'quantity': 5, 'entry_price': Decimal('2800'), 'current_price': Decimal('2850')},  # IT
            'MGNT': {'quantity': 25, 'entry_price': Decimal('5000'), 'current_price': Decimal('5200')}, # Consumer
            'MTSS': {'quantity': 150, 'entry_price': Decimal('300'), 'current_price': Decimal('320')},  # Telecom
        }
        
        portfolio = self.create_test_portfolio(positions_data)
        
        result = self.risk_manager.enforce_diversification_rules(
            portfolio, self.stock_sectors, self.price_histories
        )
        
        # Well-diversified portfolio should have high score
        self.assertGreaterEqual(result['diversification_score'], 0.8)
        
        # Create poorly diversified portfolio
        poor_positions_data = {
            'GAZP': {'quantity': 300, 'entry_price': Decimal('180'), 'current_price': Decimal('190')},  # 57k - huge position
            'LKOH': {'quantity': 8, 'entry_price': Decimal('6500'), 'current_price': Decimal('6700')},  # 53.6k - huge position
        }
        
        poor_portfolio = self.create_test_portfolio(poor_positions_data)
        
        poor_result = self.risk_manager.enforce_diversification_rules(
            poor_portfolio, self.stock_sectors, self.price_histories
        )
        
        # Poorly diversified portfolio should have low score
        self.assertLess(poor_result['diversification_score'], 0.5)
    
    def test_empty_portfolio_handling(self):
        """Test handling of empty portfolio"""
        empty_portfolio = Portfolio(positions={}, cash_balance=Decimal('100000'))
        
        sector_result = self.risk_manager.check_sector_diversification_rules(
            empty_portfolio, self.stock_sectors
        )
        position_result = self.risk_manager.check_position_size_limits(empty_portfolio)
        correlation_result = self.risk_manager.check_correlation_limits(empty_portfolio, {})
        
        # Empty portfolio should be compliant
        self.assertTrue(sector_result['is_compliant'])
        self.assertTrue(position_result['is_compliant'])
        self.assertTrue(correlation_result['is_compliant'])
        
        # Should have no violations
        self.assertEqual(len(sector_result['violations']), 0)
        self.assertEqual(len(position_result['violations']), 0)
        self.assertEqual(len(correlation_result['violations']), 0)


if __name__ == '__main__':
    unittest.main()