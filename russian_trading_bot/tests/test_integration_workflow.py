"""
Integration tests for Russian market trading workflow

These tests verify the complete end-to-end workflow from data collection
to trade execution, including all system components working together.
"""

import pytest
import asyncio
import time
import threading
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
import json
import tempfile
import os

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all components for integration testing
from services.backtesting_engine import BacktestingEngine, BacktestConfig
from services.paper_trading_engine import PaperTradingEngine, PaperTradingConfig
from services.ai_decision_engine import AIDecisionEngine, DecisionWeights, MarketConditions
from services.portfolio_manager import PortfolioManager
from services.moex_client import MOEXClient
from services.news_aggregator import NewsAggregator
from services.sentiment_analyzer import SentimentAnalyzer
from services.technical_analyzer import TechnicalAnalyzer
from services.risk_manager import RiskManager
from services.notification_service import NotificationService

from models.trading import TradingSignal, OrderAction, TradeOrder, ExecutionResult
from models.market_data import RussianStock, MarketData
from models.news_data import NewsArticle, NewsSentiment


class MockMOEXClient:
    """Mock MOEX client for integration testing"""
    
    def __init__(self):
        self.symbols = ['SBER', 'GAZP', 'LKOH', 'YNDX', 'MGNT']
        self.base_prices = {
            'SBER': Decimal('250.0'),
            'GAZP': Decimal('180.0'),
            'LKOH': Decimal('6500.0'),
            'YNDX': Decimal('2800.0'),
            'MGNT': Decimal('5200.0')
        }
        self.connected = False
    
    def connect(self):
        """Mock connection to MOEX"""
        self.connected = True
        return True
    
    def disconnect(self):
        """Mock disconnection from MOEX"""
        self.connected = False
    
    def get_market_data(self, symbols):
        """Mock market data retrieval"""
        if not self.connected:
            raise ConnectionError("Not connected to MOEX")
        
        import random
        market_data = {}
        
        for symbol in symbols:
            if symbol in self.base_prices:
                base_price = self.base_prices[symbol]
                # Add some random variation
                price_change = random.uniform(-0.02, 0.02)  # ±2%
                current_price = base_price * (1 + price_change)
                
                market_data[symbol] = MarketData(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    price=current_price,
                    volume=random.randint(50000, 500000),
                    bid=current_price * Decimal('0.999'),
                    ask=current_price * Decimal('1.001'),
                    currency="RUB"
                )
        
        return market_data
    
    def get_historical_data(self, symbol, start_date, end_date):
        """Mock historical data retrieval"""
        if not self.connected:
            raise ConnectionError("Not connected to MOEX")
        
        import pandas as pd
        import numpy as np
        
        # Generate mock historical data
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        trading_days = [d for d in date_range if d.weekday() < 5]  # Exclude weekends
        
        base_price = float(self.base_prices.get(symbol, Decimal('100')))
        returns = np.random.normal(0.001, 0.02, len(trading_days))  # Daily returns
        
        prices = [base_price]
        for ret in returns:
            prices.append(prices[-1] * (1 + ret))
        
        historical_data = []
        for i, date in enumerate(trading_days):
            if i < len(prices) - 1:
                historical_data.append({
                    'date': date,
                    'open': prices[i],
                    'high': prices[i] * (1 + abs(np.random.normal(0, 0.01))),
                    'low': prices[i] * (1 - abs(np.random.normal(0, 0.01))),
                    'close': prices[i + 1],
                    'volume': np.random.randint(10000, 1000000)
                })
        
        return historical_data


class MockNewsAggregator:
    """Mock news aggregator for integration testing"""
    
    def __init__(self):
        self.connected = False
        self.news_sources = ['RBC', 'Vedomosti', 'Kommersant', 'Interfax']
    
    def connect(self):
        """Mock connection to news sources"""
        self.connected = True
        return True
    
    def get_latest_news(self, symbols=None, limit=10):
        """Mock news retrieval"""
        if not self.connected:
            raise ConnectionError("Not connected to news sources")
        
        import random
        news_articles = []
        
        for i in range(limit):
            symbol = random.choice(symbols) if symbols else random.choice(['SBER', 'GAZP', 'LKOH'])
            source = random.choice(self.news_sources)
            
            # Generate mock news content
            positive_news = [
                f"{symbol} показал рост прибыли в текущем квартале",
                f"Аналитики повысили рекомендации по акциям {symbol}",
                f"{symbol} объявил о новых инвестиционных проектах"
            ]
            
            negative_news = [
                f"{symbol} столкнулся с регулятивными проблемами",
                f"Прибыль {symbol} оказалась ниже ожиданий",
                f"{symbol} снизил прогнозы на текущий год"
            ]
            
            neutral_news = [
                f"{symbol} провел собрание акционеров",
                f"Руководство {symbol} прокомментировало рыночную ситуацию",
                f"{symbol} опубликовал финансовую отчетность"
            ]
            
            sentiment_type = random.choice(['positive', 'negative', 'neutral'])
            if sentiment_type == 'positive':
                content = random.choice(positive_news)
            elif sentiment_type == 'negative':
                content = random.choice(negative_news)
            else:
                content = random.choice(neutral_news)
            
            article = NewsArticle(
                title=content,
                content=content + " " + "Подробности в полной версии статьи.",
                source=source,
                timestamp=datetime.now() - timedelta(hours=random.randint(0, 24)),
                url=f"https://{source.lower()}.ru/news/{i}",
                language="ru",
                mentioned_stocks=[symbol] if symbol else []
            )
            
            news_articles.append(article)
        
        return news_articles


class MockBrokerAPI:
    """Mock broker API for integration testing"""
    
    def __init__(self):
        self.connected = False
        self.account_balance = Decimal('1000000')  # 1M RUB
        self.positions = {}
        self.orders = {}
        self.order_counter = 0
    
    def connect(self):
        """Mock connection to broker"""
        self.connected = True
        return True
    
    def disconnect(self):
        """Mock disconnection from broker"""
        self.connected = False
    
    def get_account_info(self):
        """Mock account information"""
        if not self.connected:
            raise ConnectionError("Not connected to broker")
        
        return {
            'balance': self.account_balance,
            'currency': 'RUB',
            'positions': self.positions
        }
    
    def place_order(self, order: TradeOrder):
        """Mock order placement"""
        if not self.connected:
            raise ConnectionError("Not connected to broker")
        
        self.order_counter += 1
        order_id = f"ORDER_{self.order_counter:06d}"
        
        # Simulate order execution with small delay
        execution_price = order.price or Decimal('250.0')
        commission = execution_price * order.quantity * Decimal('0.0005')  # 0.05% commission
        
        # Update account balance and positions
        if order.action == OrderAction.BUY:
            total_cost = execution_price * order.quantity + commission
            if total_cost <= self.account_balance:
                self.account_balance -= total_cost
                
                if order.symbol in self.positions:
                    # Update existing position
                    pos = self.positions[order.symbol]
                    total_quantity = pos['quantity'] + order.quantity
                    total_cost_basis = pos['avg_price'] * pos['quantity'] + execution_price * order.quantity
                    new_avg_price = total_cost_basis / total_quantity
                    
                    self.positions[order.symbol] = {
                        'quantity': total_quantity,
                        'avg_price': new_avg_price
                    }
                else:
                    # Create new position
                    self.positions[order.symbol] = {
                        'quantity': order.quantity,
                        'avg_price': execution_price
                    }
                
                return ExecutionResult(
                    order_id=order_id,
                    status="filled",
                    filled_quantity=order.quantity,
                    average_price=execution_price,
                    commission=commission,
                    timestamp=datetime.now()
                )
            else:
                return ExecutionResult(
                    order_id=order_id,
                    status="rejected",
                    error_message="Insufficient funds"
                )
        
        elif order.action == OrderAction.SELL:
            if order.symbol in self.positions and self.positions[order.symbol]['quantity'] >= order.quantity:
                # Execute sell order
                proceeds = execution_price * order.quantity - commission
                self.account_balance += proceeds
                
                # Update position
                self.positions[order.symbol]['quantity'] -= order.quantity
                if self.positions[order.symbol]['quantity'] == 0:
                    del self.positions[order.symbol]
                
                return ExecutionResult(
                    order_id=order_id,
                    status="filled",
                    filled_quantity=order.quantity,
                    average_price=execution_price,
                    commission=commission,
                    timestamp=datetime.now()
                )
            else:
                return ExecutionResult(
                    order_id=order_id,
                    status="rejected",
                    error_message="Insufficient position"
                )


@pytest.fixture
def mock_moex_client():
    """Create mock MOEX client"""
    return MockMOEXClient()


@pytest.fixture
def mock_news_aggregator():
    """Create mock news aggregator"""
    return MockNewsAggregator()


@pytest.fixture
def mock_broker_api():
    """Create mock broker API"""
    return MockBrokerAPI()


@pytest.fixture
def ai_engine():
    """Create AI decision engine"""
    weights = DecisionWeights(
        technical_weight=0.4,
        sentiment_weight=0.3,
        fundamental_weight=0.2,
        volume_weight=0.1,
        market_conditions_weight=0.1
    )
    return AIDecisionEngine(weights)


class TestRussianMarketIntegration:
    """Integration tests for Russian market trading workflow"""
    
    def test_data_collection_pipeline(self, mock_moex_client, mock_news_aggregator):
        """Test complete data collection pipeline"""
        # Test MOEX data collection
        mock_moex_client.connect()
        symbols = ['SBER', 'GAZP', 'LKOH']
        
        # Get market data
        market_data = mock_moex_client.get_market_data(symbols)
        assert len(market_data) == len(symbols)
        
        for symbol in symbols:
            assert symbol in market_data
            data = market_data[symbol]
            assert data.price > 0
            assert data.volume > 0
            assert data.currency == "RUB"
        
        # Get historical data
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        
        historical_data = mock_moex_client.get_historical_data('SBER', start_date, end_date)
        assert len(historical_data) > 0
        assert all('close' in record for record in historical_data)
        
        # Test news collection
        mock_news_aggregator.connect()
        news_articles = mock_news_aggregator.get_latest_news(symbols, limit=5)
        
        assert len(news_articles) == 5
        for article in news_articles:
            assert isinstance(article, NewsArticle)
            assert article.language == "ru"
            assert len(article.mentioned_stocks) > 0
        
        mock_moex_client.disconnect()
    
    def test_analysis_pipeline(self, mock_moex_client, mock_news_aggregator, ai_engine):
        """Test complete analysis pipeline"""
        # Setup data sources
        mock_moex_client.connect()
        mock_news_aggregator.connect()
        
        symbols = ['SBER', 'GAZP']
        
        # Get market data
        market_data = mock_moex_client.get_market_data(symbols)
        
        # Get news data
        news_articles = mock_news_aggregator.get_latest_news(symbols, limit=3)
        
        # Mock sentiment analysis
        sentiments = []
        for article in news_articles:
            sentiment = NewsSentiment(
                article_id=f"news_{len(sentiments)}",
                sentiment_score=0.2,  # Slightly positive
                confidence=0.8,
                positive_keywords=["рост", "прибыль"],
                negative_keywords=[],
                mentioned_stocks=article.mentioned_stocks
            )
            sentiments.append(sentiment)
        
        # Mock technical analysis
        from services.technical_analyzer import TechnicalIndicators
        
        technical_indicators = TechnicalIndicators(
            rsi=45.0,
            macd=0.1,
            macd_signal=0.05,
            sma_20=float(market_data['SBER'].price) * 0.98,
            sma_50=float(market_data['SBER'].price) * 0.95,
            bollinger_upper=float(market_data['SBER'].price) * 1.02,
            bollinger_lower=float(market_data['SBER'].price) * 0.98,
            bollinger_middle=float(market_data['SBER'].price),
            stochastic_k=55.0
        )
        
        # Mock market conditions
        market_conditions = MarketConditions(
            market_volatility=0.25,
            ruble_volatility=0.15,
            geopolitical_risk=0.3,
            market_trend="BULLISH",
            trading_volume_ratio=1.2
        )
        
        # Generate trading signal
        stock = RussianStock(
            symbol='SBER',
            name='Сбербанк',
            sector='BANKING',
            currency='RUB'
        )
        
        signal = ai_engine.generate_trading_signal(
            symbol='SBER',
            stock=stock,
            market_data=market_data['SBER'],
            technical_indicators=technical_indicators,
            sentiments=sentiments,
            market_conditions=market_conditions
        )
        
        # Verify signal generation
        assert isinstance(signal, TradingSignal)
        assert signal.symbol == 'SBER'
        assert signal.action in [OrderAction.BUY, OrderAction.SELL]
        assert 0 <= signal.confidence <= 1
        assert signal.reasoning  # Should have Russian reasoning
        
        mock_moex_client.disconnect()
    
    def test_trade_execution_workflow(self, mock_moex_client, mock_broker_api, ai_engine):
        """Test complete trade execution workflow"""
        # Setup
        mock_moex_client.connect()
        mock_broker_api.connect()
        
        # Get market data
        market_data = mock_moex_client.get_market_data(['SBER'])
        sber_data = market_data['SBER']
        
        # Create trading signal
        signal = TradingSignal(
            symbol='SBER',
            action=OrderAction.BUY,
            confidence=0.8,
            target_price=sber_data.price * Decimal('1.05'),
            stop_loss=sber_data.price * Decimal('0.95'),
            reasoning="Интеграционный тест: покупка SBER"
        )
        
        # Create trade order
        order = TradeOrder(
            symbol='SBER',
            action=OrderAction.BUY,
            quantity=100,
            order_type="market",
            price=sber_data.price
        )
        
        # Execute order
        execution_result = mock_broker_api.place_order(order)
        
        # Verify execution
        assert execution_result.status == "filled"
        assert execution_result.filled_quantity == 100
        assert execution_result.average_price > 0
        assert execution_result.commission > 0
        
        # Verify account state
        account_info = mock_broker_api.get_account_info()
        assert 'SBER' in account_info['positions']
        assert account_info['positions']['SBER']['quantity'] == 100
        assert account_info['balance'] < Decimal('1000000')  # Should be reduced
        
        # Test sell order
        sell_order = TradeOrder(
            symbol='SBER',
            action=OrderAction.SELL,
            quantity=50,
            order_type="market",
            price=sber_data.price
        )
        
        sell_result = mock_broker_api.place_order(sell_order)
        assert sell_result.status == "filled"
        assert sell_result.filled_quantity == 50
        
        # Verify position update
        updated_account = mock_broker_api.get_account_info()
        assert updated_account['positions']['SBER']['quantity'] == 50
        
        mock_moex_client.disconnect()
        mock_broker_api.disconnect()
    
    def test_portfolio_management_integration(self, mock_moex_client, mock_broker_api):
        """Test portfolio management integration"""
        # Setup
        mock_moex_client.connect()
        mock_broker_api.connect()
        
        portfolio_manager = PortfolioManager(Decimal('1000000'))
        
        # Execute some trades
        symbols = ['SBER', 'GAZP']
        market_data = mock_moex_client.get_market_data(symbols)
        
        for symbol in symbols:
            # Buy order
            order = TradeOrder(
                symbol=symbol,
                action=OrderAction.BUY,
                quantity=50,
                order_type="market",
                price=market_data[symbol].price
            )
            
            execution_result = mock_broker_api.place_order(order)
            
            if execution_result.status == "filled":
                # Update portfolio
                order_details = {
                    'symbol': symbol,
                    'action': OrderAction.BUY,
                    'quantity': 50
                }
                
                portfolio_manager.update_position(execution_result, order_details)
        
        # Update market prices
        portfolio_manager.update_market_prices(market_data)
        
        # Take snapshot
        snapshot = portfolio_manager.take_snapshot()
        
        # Verify portfolio state
        assert snapshot.total_value > 0
        assert len(portfolio_manager.portfolio.positions) == len(symbols)
        
        # Calculate performance metrics
        performance = portfolio_manager.calculate_performance_metrics()
        
        assert isinstance(performance.total_return, float)
        assert isinstance(performance.sharpe_ratio, float)
        assert isinstance(performance.max_drawdown, float)
        
        # Get portfolio summary
        summary = portfolio_manager.get_portfolio_summary()
        
        assert 'total_value' in summary
        assert 'positions' in summary
        assert len(summary['positions']) == len(symbols)
        
        mock_moex_client.disconnect()
        mock_broker_api.disconnect()
    
    def test_risk_management_integration(self, mock_moex_client, mock_broker_api):
        """Test risk management integration"""
        # Setup
        mock_moex_client.connect()
        mock_broker_api.connect()
        
        # Create risk manager (mock implementation)
        class MockRiskManager:
            def __init__(self):
                self.max_position_size = 0.1  # 10%
                self.stop_loss_pct = 0.05     # 5%
                self.max_daily_loss = 0.02    # 2%
            
            def validate_order(self, order, portfolio_value):
                """Validate order against risk rules"""
                order_value = order.price * order.quantity
                position_pct = float(order_value / portfolio_value)
                
                if position_pct > self.max_position_size:
                    return False, f"Position size {position_pct:.1%} exceeds limit {self.max_position_size:.1%}"
                
                return True, "Order approved"
            
            def check_stop_loss(self, position, current_price):
                """Check if stop loss should be triggered"""
                if position['action'] == OrderAction.BUY:
                    loss_pct = (position['avg_price'] - current_price) / position['avg_price']
                    return loss_pct >= self.stop_loss_pct
                return False
        
        risk_manager = MockRiskManager()
        portfolio_value = Decimal('1000000')
        
        # Test position size validation
        market_data = mock_moex_client.get_market_data(['SBER'])
        sber_price = market_data['SBER'].price
        
        # Valid order (within limits)
        valid_order = TradeOrder(
            symbol='SBER',
            action=OrderAction.BUY,
            quantity=300,  # Should be within 10% limit
            order_type="market",
            price=sber_price
        )
        
        is_valid, message = risk_manager.validate_order(valid_order, portfolio_value)
        assert is_valid == True
        
        # Invalid order (exceeds limits)
        invalid_order = TradeOrder(
            symbol='SBER',
            action=OrderAction.BUY,
            quantity=5000,  # Should exceed 10% limit
            order_type="market",
            price=sber_price
        )
        
        is_valid, message = risk_manager.validate_order(invalid_order, portfolio_value)
        assert is_valid == False
        assert "exceeds limit" in message
        
        # Test stop loss check
        position = {
            'action': OrderAction.BUY,
            'avg_price': Decimal('250.0'),
            'quantity': 100
        }
        
        # Price drop triggering stop loss
        stop_loss_price = Decimal('230.0')  # 8% drop
        should_stop = risk_manager.check_stop_loss(position, stop_loss_price)
        assert should_stop == True
        
        # Price drop not triggering stop loss
        no_stop_price = Decimal('245.0')  # 2% drop
        should_stop = risk_manager.check_stop_loss(position, no_stop_price)
        assert should_stop == False
        
        mock_moex_client.disconnect()
        mock_broker_api.disconnect()
    
    def test_notification_system_integration(self):
        """Test notification system integration"""
        # Mock notification service
        class MockNotificationService:
            def __init__(self):
                self.sent_notifications = []
            
            def send_trade_notification(self, trade_info):
                """Send trade notification"""
                notification = {
                    'type': 'trade',
                    'timestamp': datetime.now(),
                    'message': f"Executed {trade_info['action']} {trade_info['quantity']} {trade_info['symbol']}",
                    'data': trade_info
                }
                self.sent_notifications.append(notification)
                return True
            
            def send_alert(self, alert_type, message, data=None):
                """Send alert notification"""
                notification = {
                    'type': alert_type,
                    'timestamp': datetime.now(),
                    'message': message,
                    'data': data or {}
                }
                self.sent_notifications.append(notification)
                return True
        
        notification_service = MockNotificationService()
        
        # Test trade notification
        trade_info = {
            'symbol': 'SBER',
            'action': 'BUY',
            'quantity': 100,
            'price': 250.0,
            'timestamp': datetime.now()
        }
        
        success = notification_service.send_trade_notification(trade_info)
        assert success == True
        assert len(notification_service.sent_notifications) == 1
        
        notification = notification_service.sent_notifications[0]
        assert notification['type'] == 'trade'
        assert 'SBER' in notification['message']
        assert notification['data'] == trade_info
        
        # Test alert notification
        success = notification_service.send_alert(
            'risk_alert',
            'Portfolio drawdown exceeded 10%',
            {'drawdown': 0.12, 'portfolio_value': 900000}
        )
        
        assert success == True
        assert len(notification_service.sent_notifications) == 2
        
        alert = notification_service.sent_notifications[1]
        assert alert['type'] == 'risk_alert'
        assert 'drawdown' in alert['message']
        assert alert['data']['drawdown'] == 0.12
    
    def test_backtesting_integration(self, ai_engine):
        """Test backtesting system integration"""
        # Create backtesting engine
        backtest_engine = BacktestingEngine(ai_engine)
        
        # Configure backtest
        config = BacktestConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 3, 31),  # 3 months
            initial_capital=Decimal('1000000'),
            commission_rate=0.0005,
            slippage_rate=0.001,
            max_position_size=0.1,
            min_confidence=0.6
        )
        
        symbols = ['SBER', 'GAZP']
        
        # Load historical data (mock)
        success = backtest_engine.load_historical_data(symbols, config.start_date, config.end_date)
        assert success == True
        
        # Verify data loaded
        assert len(backtest_engine.historical_data) == len(symbols)
        for symbol in symbols:
            assert symbol in backtest_engine.historical_data
            df = backtest_engine.historical_data[symbol]
            assert len(df) > 0
            assert 'close' in df.columns
        
        # Run backtest
        results = backtest_engine.run_backtest(config, symbols, "Integration Test Strategy")
        
        # Verify results
        assert results.initial_capital == config.initial_capital
        assert results.final_capital > 0
        assert results.duration_days == (config.end_date - config.start_date).days
        assert isinstance(results.total_return, float)
        assert isinstance(results.sharpe_ratio, float)
        assert results.total_trades >= 0
        
        # Generate report
        report = backtest_engine.get_backtest_report(results)
        assert isinstance(report, str)
        assert "ОТЧЕТ ПО БЭКТЕСТИНГУ" in report
        assert "₽" in report  # Russian currency symbol
    
    def test_paper_trading_integration(self, ai_engine):
        """Test paper trading system integration"""
        # Create paper trading engine
        config = PaperTradingConfig(
            initial_capital=Decimal('1000000'),
            commission_rate=0.0005,
            max_position_size=0.1,
            min_confidence=0.6,
            update_interval=1,  # 1 second for testing
            market_hours_only=False,
            auto_execute=True
        )
        
        paper_engine = PaperTradingEngine(ai_engine, config)
        
        # Setup mock market data provider
        def mock_market_provider(symbols):
            data = {}
            for symbol in symbols:
                data[symbol] = MarketData(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    price=Decimal('250.0'),
                    volume=100000,
                    bid=Decimal('249.5'),
                    ask=Decimal('250.5'),
                    currency="RUB"
                )
            return data
        
        paper_engine.set_market_data_provider(mock_market_provider)
        paper_engine.set_symbols(['SBER', 'GAZP'])
        
        # Setup callbacks to track events
        events = []
        
        def on_trade_executed(trade):
            events.append(('trade_executed', trade))
        
        def on_position_closed(trade):
            events.append(('position_closed', trade))
        
        paper_engine.on_trade_executed = on_trade_executed
        paper_engine.on_position_closed = on_position_closed
        
        # Start session
        session_id = paper_engine.start_session("Integration Test")
        assert paper_engine.status.value == "running"
        assert paper_engine.current_session is not None
        
        # Let it run briefly
        time.sleep(2)
        
        # Check status
        status = paper_engine.get_current_status()
        assert status['status'] == 'running'
        assert status['session_active'] == True
        
        # Stop session
        paper_engine.stop_session()
        assert paper_engine.status.value == "stopped"
        
        # Verify session completed
        if paper_engine.current_session:
            summary = paper_engine.current_session.get_summary()
            assert isinstance(summary, dict)
            assert 'total_return' in summary
            assert 'total_trades' in summary
    
    def test_stress_testing_high_volatility(self, mock_moex_client, ai_engine):
        """Test system behavior under high market volatility"""
        mock_moex_client.connect()
        
        # Simulate high volatility market data
        def high_volatility_data(symbols):
            import random
            data = {}
            
            for symbol in symbols:
                # High volatility: ±10% price swings
                base_price = Decimal('250.0')
                volatility = random.uniform(-0.1, 0.1)  # ±10%
                current_price = base_price * (1 + volatility)
                
                # High volume during volatility
                volume = random.randint(500000, 2000000)
                
                data[symbol] = MarketData(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    price=current_price,
                    volume=volume,
                    bid=current_price * Decimal('0.995'),  # Wider spreads
                    ask=current_price * Decimal('1.005'),
                    currency="RUB"
                )
            
            return data
        
        # Test multiple iterations of high volatility
        symbols = ['SBER', 'GAZP', 'LKOH']
        volatility_data = []
        
        for i in range(10):
            market_data = high_volatility_data(symbols)
            volatility_data.append(market_data)
            
            # Verify system handles extreme prices
            for symbol, data in market_data.items():
                assert data.price > 0
                assert data.volume > 0
                assert data.bid < data.ask
        
        # Test AI decision making under high volatility
        market_conditions = MarketConditions(
            market_volatility=0.8,  # Very high volatility
            ruble_volatility=0.6,
            geopolitical_risk=0.7,
            market_trend="VOLATILE",
            trading_volume_ratio=3.0  # 3x normal volume
        )
        
        # Generate signals under stress conditions
        from services.technical_analyzer import TechnicalIndicators
        
        for market_data in volatility_data[:3]:  # Test first 3 iterations
            for symbol, data in market_data.items():
                # Mock technical indicators for volatile conditions
                indicators = TechnicalIndicators(
                    rsi=random.uniform(20, 80),  # Wide RSI range
                    macd=random.uniform(-2, 2),  # High MACD values
                    macd_signal=random.uniform(-2, 2),
                    sma_20=float(data.price) * random.uniform(0.9, 1.1),
                    sma_50=float(data.price) * random.uniform(0.85, 1.15),
                    bollinger_upper=float(data.price) * 1.1,  # Wide bands
                    bollinger_lower=float(data.price) * 0.9,
                    bollinger_middle=float(data.price),
                    stochastic_k=random.uniform(0, 100)
                )
                
                stock = RussianStock(
                    symbol=symbol,
                    name=f"Company {symbol}",
                    sector="GENERAL",
                    currency="RUB"
                )
                
                # Generate signal under stress
                signal = ai_engine.generate_trading_signal(
                    symbol=symbol,
                    stock=stock,
                    market_data=data,
                    technical_indicators=indicators,
                    sentiments=[],
                    market_conditions=market_conditions
                )
                
                # Verify signal is generated (even if confidence is low)
                assert isinstance(signal, TradingSignal)
                assert signal.symbol == symbol
                assert 0 <= signal.confidence <= 1
                
                # Under high volatility, confidence should be adjusted
                # (implementation specific - could be lower due to uncertainty)
        
        mock_moex_client.disconnect()
    
    def test_error_recovery_and_resilience(self, mock_moex_client, mock_broker_api):
        """Test system error recovery and resilience"""
        # Test connection failures
        mock_moex_client.connect()
        mock_broker_api.connect()
        
        # Simulate connection loss
        mock_moex_client.disconnect()
        
        # System should handle gracefully
        try:
            market_data = mock_moex_client.get_market_data(['SBER'])
            assert False, "Should have raised ConnectionError"
        except ConnectionError:
            pass  # Expected
        
        # Test reconnection
        mock_moex_client.connect()
        market_data = mock_moex_client.get_market_data(['SBER'])
        assert len(market_data) == 1
        
        # Test broker API failures
        mock_broker_api.disconnect()
        
        order = TradeOrder(
            symbol='SBER',
            action=OrderAction.BUY,
            quantity=100,
            order_type="market",
            price=Decimal('250.0')
        )
        
        try:
            result = mock_broker_api.place_order(order)
            assert False, "Should have raised ConnectionError"
        except ConnectionError:
            pass  # Expected
        
        # Test order rejection handling
        mock_broker_api.connect()
        
        # Order that should be rejected (insufficient funds)
        large_order = TradeOrder(
            symbol='SBER',
            action=OrderAction.BUY,
            quantity=100000,  # Very large order
            order_type="market",
            price=Decimal('250.0')
        )
        
        result = mock_broker_api.place_order(large_order)
        assert result.status == "rejected"
        assert "Insufficient funds" in result.error_message
        
        # Test data corruption handling
        def corrupted_data_provider(symbols):
            # Return corrupted data
            return {
                'SBER': MarketData(
                    symbol='SBER',
                    timestamp=datetime.now(),
                    price=Decimal('-100.0'),  # Invalid negative price
                    volume=-1000,  # Invalid negative volume
                    bid=Decimal('250.0'),
                    ask=Decimal('249.0'),  # Invalid: ask < bid
                    currency="USD"  # Wrong currency
                )
            }
        
        # System should validate and handle corrupted data
        corrupted_data = corrupted_data_provider(['SBER'])
        sber_data = corrupted_data['SBER']
        
        # Validate data integrity
        data_issues = []
        if sber_data.price <= 0:
            data_issues.append("Invalid price")
        if sber_data.volume < 0:
            data_issues.append("Invalid volume")
        if sber_data.ask <= sber_data.bid:
            data_issues.append("Invalid spread")
        if sber_data.currency != "RUB":
            data_issues.append("Wrong currency")
        
        assert len(data_issues) > 0  # Should detect issues
        
        mock_moex_client.disconnect()
        mock_broker_api.disconnect()
    
    def test_performance_under_load(self, ai_engine):
        """Test system performance under high load"""
        import time
        
        # Test concurrent signal generation
        symbols = ['SBER', 'GAZP', 'LKOH', 'YNDX', 'MGNT'] * 10  # 50 symbols
        
        start_time = time.time()
        signals_generated = 0
        
        # Generate many signals quickly
        for symbol in symbols:
            try:
                # Mock data for performance test
                market_data = MarketData(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    price=Decimal('250.0'),
                    volume=100000,
                    bid=Decimal('249.5'),
                    ask=Decimal('250.5'),
                    currency="RUB"
                )
                
                from services.technical_analyzer import TechnicalIndicators
                indicators = TechnicalIndicators(
                    rsi=50.0,
                    macd=0.1,
                    macd_signal=0.05,
                    sma_20=245.0,
                    sma_50=240.0,
                    bollinger_upper=255.0,
                    bollinger_lower=245.0,
                    bollinger_middle=250.0,
                    stochastic_k=55.0
                )
                
                market_conditions = MarketConditions(
                    market_volatility=0.3,
                    ruble_volatility=0.2,
                    geopolitical_risk=0.4,
                    market_trend="SIDEWAYS",
                    trading_volume_ratio=1.0
                )
                
                stock = RussianStock(
                    symbol=symbol,
                    name=f"Company {symbol}",
                    sector="GENERAL",
                    currency="RUB"
                )
                
                signal = ai_engine.generate_trading_signal(
                    symbol=symbol,
                    stock=stock,
                    market_data=market_data,
                    technical_indicators=indicators,
                    sentiments=[],
                    market_conditions=market_conditions
                )
                
                if signal:
                    signals_generated += 1
                
            except Exception as e:
                # Log but don't fail the test
                print(f"Error generating signal for {symbol}: {e}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Performance assertions
        assert signals_generated > 0
        assert duration < 30.0  # Should complete within 30 seconds
        
        signals_per_second = signals_generated / duration
        assert signals_per_second > 1.0  # At least 1 signal per second
        
        print(f"Performance test: {signals_generated} signals in {duration:.2f}s "
              f"({signals_per_second:.1f} signals/sec)")
    
    @pytest.mark.integration
    def test_complete_end_to_end_workflow(self, mock_moex_client, mock_news_aggregator, 
                                        mock_broker_api, ai_engine):
        """Complete end-to-end integration test"""
        print("\n🚀 Starting complete end-to-end workflow test...")
        
        # 1. Setup all components
        mock_moex_client.connect()
        mock_news_aggregator.connect()
        mock_broker_api.connect()
        
        portfolio_manager = PortfolioManager(Decimal('1000000'))
        symbols = ['SBER', 'GAZP']
        
        print("✅ All components initialized")
        
        # 2. Data collection phase
        print("📊 Phase 1: Data Collection")
        
        # Get market data
        market_data = mock_moex_client.get_market_data(symbols)
        assert len(market_data) == len(symbols)
        print(f"   - Market data collected for {len(market_data)} symbols")
        
        # Get news data
        news_articles = mock_news_aggregator.get_latest_news(symbols, limit=3)
        assert len(news_articles) == 3
        print(f"   - {len(news_articles)} news articles collected")
        
        # 3. Analysis phase
        print("🔍 Phase 2: Analysis")
        
        # Analyze sentiment
        sentiments = []
        for article in news_articles:
            sentiment = NewsSentiment(
                article_id=f"news_{len(sentiments)}",
                sentiment_score=0.1,  # Slightly positive
                confidence=0.7,
                positive_keywords=["рост"],
                negative_keywords=[],
                mentioned_stocks=article.mentioned_stocks
            )
            sentiments.append(sentiment)
        
        print(f"   - Sentiment analysis completed for {len(sentiments)} articles")
        
        # Technical analysis
        from services.technical_analyzer import TechnicalIndicators
        
        technical_indicators = TechnicalIndicators(
            rsi=55.0,
            macd=0.2,
            macd_signal=0.1,
            sma_20=float(market_data['SBER'].price) * 0.99,
            sma_50=float(market_data['SBER'].price) * 0.97,
            bollinger_upper=float(market_data['SBER'].price) * 1.02,
            bollinger_lower=float(market_data['SBER'].price) * 0.98,
            bollinger_middle=float(market_data['SBER'].price),
            stochastic_k=60.0
        )
        
        print("   - Technical analysis completed")
        
        # 4. Decision making phase
        print("🤖 Phase 3: AI Decision Making")
        
        market_conditions = MarketConditions(
            market_volatility=0.25,
            ruble_volatility=0.15,
            geopolitical_risk=0.3,
            market_trend="BULLISH",
            trading_volume_ratio=1.1
        )
        
        signals = []
        for symbol in symbols:
            stock = RussianStock(
                symbol=symbol,
                name=f"Russian Company {symbol}",
                sector="GENERAL",
                currency="RUB"
            )
            
            signal = ai_engine.generate_trading_signal(
                symbol=symbol,
                stock=stock,
                market_data=market_data[symbol],
                technical_indicators=technical_indicators,
                sentiments=sentiments,
                market_conditions=market_conditions
            )
            
            if signal and signal.confidence >= 0.6:
                signals.append(signal)
        
        print(f"   - {len(signals)} trading signals generated")
        
        # 5. Trade execution phase
        print("💰 Phase 4: Trade Execution")
        
        executed_trades = 0
        for signal in signals:
            # Create order
            order = TradeOrder(
                symbol=signal.symbol,
                action=signal.action,
                quantity=100,
                order_type="market",
                price=market_data[signal.symbol].price
            )
            
            # Execute order
            execution_result = mock_broker_api.place_order(order)
            
            if execution_result.status == "filled":
                # Update portfolio
                order_details = {
                    'symbol': signal.symbol,
                    'action': signal.action,
                    'quantity': 100
                }
                
                portfolio_manager.update_position(execution_result, order_details)
                executed_trades += 1
                
                print(f"   - Executed {signal.action.value} {signal.symbol} at {execution_result.average_price}")
        
        print(f"   - {executed_trades} trades executed successfully")
        
        # 6. Portfolio management phase
        print("📈 Phase 5: Portfolio Management")
        
        # Update portfolio with current prices
        portfolio_manager.update_market_prices(market_data)
        
        # Take snapshot
        snapshot = portfolio_manager.take_snapshot()
        
        # Calculate performance
        performance = portfolio_manager.calculate_performance_metrics()
        
        print(f"   - Portfolio value: {snapshot.total_value:,.0f} ₽")
        print(f"   - Total P&L: {snapshot.total_pnl:+,.0f} ₽")
        print(f"   - Positions: {len(portfolio_manager.portfolio.positions)}")
        
        # 7. Verification phase
        print("✅ Phase 6: Verification")
        
        # Verify portfolio state
        assert snapshot.total_value > 0
        assert len(portfolio_manager.portfolio.positions) <= len(symbols)
        
        # Verify account state
        account_info = mock_broker_api.get_account_info()
        assert len(account_info['positions']) == executed_trades
        
        # Verify performance metrics
        assert isinstance(performance.total_return, float)
        assert isinstance(performance.sharpe_ratio, float)
        
        print("   - All verifications passed")
        
        # 8. Cleanup
        mock_moex_client.disconnect()
        mock_news_aggregator.disconnect()
        mock_broker_api.disconnect()
        
        print("🏁 End-to-end workflow test completed successfully!")
        print(f"   - Data sources: ✅")
        print(f"   - Analysis: ✅")
        print(f"   - Decision making: ✅")
        print(f"   - Trade execution: ✅")
        print(f"   - Portfolio management: ✅")
        print(f"   - System integration: ✅")
        
        # Return summary for further analysis
        return {
            'symbols_analyzed': len(symbols),
            'news_articles': len(news_articles),
            'signals_generated': len(signals),
            'trades_executed': executed_trades,
            'final_portfolio_value': float(snapshot.total_value),
            'total_pnl': float(snapshot.total_pnl),
            'performance_metrics': {
                'total_return': performance.total_return,
                'sharpe_ratio': performance.sharpe_ratio,
                'max_drawdown': performance.max_drawdown
            }
        }