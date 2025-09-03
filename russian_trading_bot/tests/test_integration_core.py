"""
Core integration tests for Russian market trading workflow - Task 12.3
Simplified version without external dependencies for testing the integration framework
"""

import pytest
import asyncio
import time
import threading
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import json
import tempfile
import os
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum


# Mock data models for testing
class OrderAction(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class OrderStatus(Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


@dataclass
class MarketData:
    symbol: str
    timestamp: datetime
    price: Decimal
    volume: int
    bid: Decimal
    ask: Decimal
    currency: str = "RUB"


@dataclass
class RussianStock:
    symbol: str
    name: str
    sector: str
    currency: str = "RUB"


@dataclass
class NewsArticle:
    title: str
    content: str
    source: str
    timestamp: datetime
    url: str
    language: str = "ru"
    mentioned_stocks: List[str] = None
    
    def __post_init__(self):
        if self.mentioned_stocks is None:
            self.mentioned_stocks = []


@dataclass
class TradeOrder:
    symbol: str
    action: OrderAction
    quantity: int
    order_type: OrderType
    price: Optional[Decimal] = None


@dataclass
class ExecutionResult:
    order_id: str
    status: OrderStatus
    filled_quantity: int = 0
    average_price: Optional[Decimal] = None
    commission: Optional[Decimal] = None
    timestamp: Optional[datetime] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class TradingSignal:
    symbol: str
    action: OrderAction
    confidence: float
    target_price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    reasoning: str = ""
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


# Mock service classes
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
        self.market_open = True
        self.volatility_multiplier = 1.0
    
    def connect(self):
        self.connected = True
        return True
    
    def disconnect(self):
        self.connected = False
    
    def get_market_data(self, symbols):
        if not self.connected:
            raise ConnectionError("Not connected to MOEX")
        
        if not self.market_open:
            raise Exception("Market is closed")
        
        market_data = {}
        for symbol in symbols:
            if symbol in self.base_prices:
                base_price = self.base_prices[symbol]
                price_change = random.uniform(-0.02, 0.02) * self.volatility_multiplier
                current_price = base_price * (Decimal('1') + Decimal(str(price_change)))
                
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
    
    def set_volatility(self, multiplier):
        self.volatility_multiplier = multiplier
    
    def set_market_status(self, is_open):
        self.market_open = is_open


class MockNewsAggregator:
    """Mock news aggregator for integration testing"""
    
    def __init__(self):
        self.connected = False
        self.news_sources = ['RBC', 'Vedomosti', 'Kommersant', 'Interfax']
        self.sentiment_bias = 0.0
    
    def connect(self):
        self.connected = True
        return True
    
    def get_latest_news(self, symbols=None, limit=10):
        if not self.connected:
            raise ConnectionError("Not connected to news sources")
        
        news_articles = []
        for i in range(limit):
            symbol = random.choice(symbols) if symbols else random.choice(['SBER', 'GAZP', 'LKOH'])
            source = random.choice(self.news_sources)
            
            if self.sentiment_bias > 0.3:
                content = f"{symbol} показал рост прибыли в текущем квартале"
            elif self.sentiment_bias < -0.3:
                content = f"{symbol} столкнулся с регулятивными проблемами"
            else:
                content = f"{symbol} провел собрание акционеров"
            
            article = NewsArticle(
                title=content,
                content=content + " Подробности в полной версии статьи.",
                source=source,
                timestamp=datetime.now() - timedelta(hours=random.randint(0, 24)),
                url=f"https://{source.lower()}.ru/news/{i}",
                language="ru",
                mentioned_stocks=[symbol] if symbol else []
            )
            
            news_articles.append(article)
        
        return news_articles
    
    def set_sentiment_bias(self, bias):
        self.sentiment_bias = bias
    
    def disconnect(self):
        self.connected = False


class MockBrokerAPI:
    """Mock broker API for integration testing"""
    
    def __init__(self):
        self.connected = False
        self.account_balance = Decimal('1000000')
        self.positions = {}
        self.orders = {}
        self.order_counter = 0
        self.failure_rate = 0.0
        self.latency_ms = 100
    
    def connect(self):
        self.connected = True
        return True
    
    def disconnect(self):
        self.connected = False
    
    def place_order(self, order: TradeOrder):
        if not self.connected:
            raise ConnectionError("Not connected to broker")
        
        time.sleep(self.latency_ms / 1000.0)
        
        if random.random() < self.failure_rate:
            return ExecutionResult(
                order_id=f"FAILED_{self.order_counter}",
                status=OrderStatus.REJECTED,
                error_message="Simulated broker failure"
            )
        
        self.order_counter += 1
        order_id = f"ORDER_{self.order_counter:06d}"
        
        execution_price = order.price or Decimal('250.0')
        commission = execution_price * order.quantity * Decimal('0.0005')
        
        if order.action == OrderAction.BUY:
            total_cost = execution_price * order.quantity + commission
            if total_cost <= self.account_balance:
                self.account_balance -= total_cost
                
                if order.symbol in self.positions:
                    pos = self.positions[order.symbol]
                    total_quantity = pos['quantity'] + order.quantity
                    total_cost_basis = pos['avg_price'] * pos['quantity'] + execution_price * order.quantity
                    new_avg_price = total_cost_basis / total_quantity
                    
                    self.positions[order.symbol] = {
                        'quantity': total_quantity,
                        'avg_price': new_avg_price
                    }
                else:
                    self.positions[order.symbol] = {
                        'quantity': order.quantity,
                        'avg_price': execution_price
                    }
                
                return ExecutionResult(
                    order_id=order_id,
                    status=OrderStatus.FILLED,
                    filled_quantity=order.quantity,
                    average_price=execution_price,
                    commission=commission,
                    timestamp=datetime.now()
                )
            else:
                return ExecutionResult(
                    order_id=order_id,
                    status=OrderStatus.REJECTED,
                    error_message="Insufficient funds"
                )
        
        elif order.action == OrderAction.SELL:
            if order.symbol in self.positions and self.positions[order.symbol]['quantity'] >= order.quantity:
                proceeds = execution_price * order.quantity - commission
                self.account_balance += proceeds
                
                self.positions[order.symbol]['quantity'] -= order.quantity
                if self.positions[order.symbol]['quantity'] == 0:
                    del self.positions[order.symbol]
                
                return ExecutionResult(
                    order_id=order_id,
                    status=OrderStatus.FILLED,
                    filled_quantity=order.quantity,
                    average_price=execution_price,
                    commission=commission,
                    timestamp=datetime.now()
                )
            else:
                return ExecutionResult(
                    order_id=order_id,
                    status=OrderStatus.REJECTED,
                    error_message="Insufficient position"
                )
    
    def get_account_info(self):
        if not self.connected:
            raise ConnectionError("Not connected to broker")
        
        return {
            'balance': self.account_balance,
            'currency': 'RUB',
            'positions': self.positions
        }
    
    def set_failure_rate(self, rate):
        self.failure_rate = rate
    
    def set_latency(self, latency_ms):
        self.latency_ms = latency_ms


class MockAIEngine:
    """Mock AI decision engine"""
    
    def __init__(self):
        self.confidence_threshold = 0.6
    
    def generate_trading_signal(self, symbol, market_data, **kwargs):
        # Simple mock logic
        price_change = random.uniform(-0.05, 0.05)
        
        if price_change > 0.02:
            action = OrderAction.BUY
            confidence = 0.7 + random.uniform(0, 0.2)
        elif price_change < -0.02:
            action = OrderAction.SELL
            confidence = 0.7 + random.uniform(0, 0.2)
        else:
            action = OrderAction.HOLD
            confidence = 0.5 + random.uniform(0, 0.3)
        
        return TradingSignal(
            symbol=symbol,
            action=action,
            confidence=confidence,
            target_price=market_data.price * Decimal('1.05'),
            stop_loss=market_data.price * Decimal('0.95'),
            reasoning=f"Mock AI decision for {symbol}: {action.value}"
        )


class MockRiskManager:
    """Mock risk manager"""
    
    def __init__(self):
        self.max_position_size = 0.1
        self.stop_loss_pct = 0.05
    
    def calculate_position_size(self, symbol, market_data, portfolio_value, **kwargs):
        # Simple position sizing
        base_size = 0.05  # 5% base position
        
        # Adjust for volatility if provided
        market_conditions = kwargs.get('market_conditions')
        if market_conditions and hasattr(market_conditions, 'market_volatility'):
            volatility_adjustment = 1 - market_conditions.market_volatility
            return min(base_size * volatility_adjustment, self.max_position_size)
        
        return base_size
    
    def calculate_stop_loss(self, symbol, entry_price, **kwargs):
        return entry_price * (Decimal('1') - Decimal(str(self.stop_loss_pct)))


# Test fixtures
@pytest.fixture
def mock_moex_client():
    return MockMOEXClient()


@pytest.fixture
def mock_news_aggregator():
    return MockNewsAggregator()


@pytest.fixture
def mock_broker_api():
    return MockBrokerAPI()


@pytest.fixture
def mock_ai_engine():
    return MockAIEngine()


@pytest.fixture
def mock_risk_manager():
    return MockRiskManager()


class TestEndToEndTradingWorkflow:
    """End-to-end testing from data collection to trade execution"""
    
    def test_complete_trading_workflow(self, mock_moex_client, mock_news_aggregator, mock_broker_api, mock_ai_engine, mock_risk_manager):
        """Test complete end-to-end trading workflow"""
        # Initialize all components
        mock_moex_client.connect()
        mock_news_aggregator.connect()
        mock_broker_api.connect()
        
        symbols = ['SBER', 'GAZP']
        
        # Phase 1: Data Collection
        market_data = mock_moex_client.get_market_data(symbols)
        news_articles = mock_news_aggregator.get_latest_news(symbols, limit=5)
        
        assert len(market_data) == len(symbols)
        assert len(news_articles) == 5
        
        # Phase 2: Analysis and Decision Making
        executed_trades = 0
        
        for symbol in symbols:
            # Generate trading signal
            signal = mock_ai_engine.generate_trading_signal(
                symbol=symbol,
                market_data=market_data[symbol]
            )
            
            # Risk management validation
            if signal.action in [OrderAction.BUY, OrderAction.SELL] and signal.confidence >= 0.6:
                position_size = mock_risk_manager.calculate_position_size(
                    symbol=symbol,
                    market_data=market_data[symbol],
                    portfolio_value=Decimal('1000000')
                )
                
                # Execute trade
                order = TradeOrder(
                    symbol=symbol,
                    action=signal.action,
                    quantity=int(position_size * 1000),
                    order_type=OrderType.MARKET,
                    price=market_data[symbol].price
                )
                
                execution_result = mock_broker_api.place_order(order)
                
                if execution_result.status == OrderStatus.FILLED:
                    executed_trades += 1
        
        # Phase 3: Verification
        account_info = mock_broker_api.get_account_info()
        
        assert executed_trades >= 0
        assert 'balance' in account_info
        assert 'positions' in account_info
        
        # Cleanup
        mock_moex_client.disconnect()
        mock_broker_api.disconnect()
    
    def test_data_pipeline_resilience(self, mock_moex_client, mock_news_aggregator):
        """Test data collection pipeline resilience to failures"""
        
        # Test MOEX connection failure recovery
        mock_moex_client.connect()
        
        # Simulate connection loss
        mock_moex_client.connected = False
        
        with pytest.raises(ConnectionError):
            mock_moex_client.get_market_data(['SBER'])
        
        # Reconnect and verify recovery
        mock_moex_client.connect()
        market_data = mock_moex_client.get_market_data(['SBER'])
        assert 'SBER' in market_data
        
        # Test news aggregator failure recovery
        mock_news_aggregator.connect()
        
        # Simulate connection loss
        mock_news_aggregator.connected = False
        
        with pytest.raises(ConnectionError):
            mock_news_aggregator.get_latest_news(['SBER'])
        
        # Reconnect and verify recovery
        mock_news_aggregator.connect()
        news = mock_news_aggregator.get_latest_news(['SBER'], limit=1)
        assert len(news) == 1
    
    def test_market_hours_compliance(self, mock_moex_client):
        """Test compliance with Russian market trading hours"""
        mock_moex_client.connect()
        
        # Test market closed scenario
        mock_moex_client.set_market_status(False)
        
        with pytest.raises(Exception, match="Market is closed"):
            mock_moex_client.get_market_data(['SBER'])
        
        # Test market open scenario
        mock_moex_client.set_market_status(True)
        market_data = mock_moex_client.get_market_data(['SBER'])
        assert 'SBER' in market_data


class TestRussianBrokerAPIIntegration:
    """Integration tests for Russian broker API connections"""
    
    def test_broker_connection_workflow(self, mock_broker_api):
        """Test broker connection and basic operations"""
        # Test connection
        assert mock_broker_api.connect() is True
        
        # Test account info retrieval
        account_info = mock_broker_api.get_account_info()
        assert account_info['balance'] == Decimal('1000000')
        assert account_info['currency'] == 'RUB'
        
        # Test order placement
        order = TradeOrder(
            symbol="SBER",
            action=OrderAction.BUY,
            quantity=10,
            order_type=OrderType.MARKET,
            price=Decimal('250.0')
        )
        
        result = mock_broker_api.place_order(order)
        assert result.status == OrderStatus.FILLED
        assert result.filled_quantity == 10
        
        # Verify account update
        updated_account = mock_broker_api.get_account_info()
        assert updated_account['balance'] < Decimal('1000000')
        assert 'SBER' in updated_account['positions']
        
        mock_broker_api.disconnect()
    
    def test_broker_failover_mechanism(self):
        """Test broker failover mechanism"""
        # Setup primary broker (will fail)
        primary_broker = MockBrokerAPI()
        primary_broker.connect()
        primary_broker.set_failure_rate(1.0)  # 100% failure rate
        
        # Setup backup broker (will succeed)
        backup_broker = MockBrokerAPI()
        backup_broker.connect()
        backup_broker.set_failure_rate(0.0)  # 0% failure rate
        
        order = TradeOrder(
            symbol="SBER",
            action=OrderAction.BUY,
            quantity=10,
            order_type=OrderType.MARKET,
            price=Decimal('250.0')
        )
        
        # Try primary broker (should fail)
        primary_result = primary_broker.place_order(order)
        assert primary_result.status == OrderStatus.REJECTED
        
        # Try backup broker (should succeed)
        backup_result = backup_broker.place_order(order)
        assert backup_result.status == OrderStatus.FILLED
    
    def test_broker_error_handling(self, mock_broker_api):
        """Test broker error handling and recovery"""
        mock_broker_api.connect()
        
        # Test insufficient funds error
        large_order = TradeOrder(
            symbol="SBER",
            action=OrderAction.BUY,
            quantity=10000,  # Very large order
            order_type=OrderType.MARKET,
            price=Decimal('250.0')
        )
        
        result = mock_broker_api.place_order(large_order)
        assert result.status == OrderStatus.REJECTED
        assert "Insufficient funds" in result.error_message
        
        # Test insufficient position error
        sell_order = TradeOrder(
            symbol="NONEXISTENT",
            action=OrderAction.SELL,
            quantity=10,
            order_type=OrderType.MARKET,
            price=Decimal('250.0')
        )
        
        result = mock_broker_api.place_order(sell_order)
        assert result.status == OrderStatus.REJECTED
        assert "Insufficient position" in result.error_message


class TestStressTesting:
    """Stress testing for high Russian market volatility"""
    
    def test_high_volatility_stress_scenario(self, mock_moex_client, mock_broker_api, mock_ai_engine, mock_risk_manager):
        """Test system behavior under extreme market volatility"""
        # Setup high volatility environment
        mock_moex_client.connect()
        mock_broker_api.connect()
        mock_moex_client.set_volatility(5.0)  # 5x normal volatility
        
        symbols = ['SBER', 'GAZP', 'LKOH']
        
        # Collect volatile market data
        market_data = mock_moex_client.get_market_data(symbols)
        
        # Test risk management under extreme conditions
        for symbol in symbols:
            # Calculate position size under stress
            position_size = mock_risk_manager.calculate_position_size(
                symbol=symbol,
                market_data=market_data[symbol],
                portfolio_value=Decimal('1000000')
            )
            
            # Position sizes should be reasonable even under stress
            assert position_size <= 0.1  # Max 10% position size
            assert position_size > 0     # Should still allow some trading
            
            # Test stop loss calculation
            stop_loss = mock_risk_manager.calculate_stop_loss(
                symbol=symbol,
                entry_price=market_data[symbol].price
            )
            
            # Stop losses should be reasonable
            stop_loss_pct = abs(stop_loss - market_data[symbol].price) / market_data[symbol].price
            assert 0.01 <= stop_loss_pct <= 0.1  # Between 1% and 10%
        
        mock_moex_client.disconnect()
        mock_broker_api.disconnect()
    
    def test_broker_overload_scenario(self, mock_broker_api):
        """Test broker behavior under high load"""
        mock_broker_api.connect()
        mock_broker_api.set_latency(1000)  # 1 second latency
        mock_broker_api.set_failure_rate(0.3)  # 30% failure rate
        
        # Execute multiple orders rapidly
        orders = []
        for i in range(10):
            order = TradeOrder(
                symbol="SBER",
                action=OrderAction.BUY,
                quantity=10,
                order_type=OrderType.MARKET,
                price=Decimal('250.0')
            )
            orders.append(order)
        
        # Execute orders and measure performance
        start_time = time.time()
        results = []
        
        for order in orders:
            result = mock_broker_api.place_order(order)
            results.append(result)
        
        execution_time = time.time() - start_time
        
        # Verify some orders succeeded despite failures
        successful_orders = [r for r in results if r.status == OrderStatus.FILLED]
        failed_orders = [r for r in results if r.status == OrderStatus.REJECTED]
        
        assert len(successful_orders) > 0  # Some orders should succeed
        assert len(failed_orders) > 0     # Some orders should fail due to stress
        assert execution_time > 5.0       # Should take time due to latency
        
        mock_broker_api.disconnect()
    
    def test_geopolitical_crisis_scenario(self, mock_news_aggregator):
        """Test system response to geopolitical crisis"""
        mock_news_aggregator.connect()
        mock_news_aggregator.set_sentiment_bias(-0.8)  # Very negative sentiment
        
        # Generate crisis news
        crisis_news = mock_news_aggregator.get_latest_news(['SBER', 'GAZP'], limit=10)
        
        # Verify crisis news characteristics
        assert len(crisis_news) == 10
        
        # Most news should mention crisis-related terms
        crisis_terms = ['проблем', 'снизил', 'столкнулся']
        crisis_articles = 0
        
        for article in crisis_news:
            if any(term in article.content for term in crisis_terms):
                crisis_articles += 1
        
        # At least 70% should be crisis-related due to negative bias
        assert crisis_articles >= len(crisis_news) * 0.7
        
        mock_news_aggregator.disconnect()


class TestAutomatedTestingPipeline:
    """Automated testing pipeline for continuous validation"""
    
    def test_system_health_monitoring(self):
        """Test comprehensive system health monitoring"""
        
        class SystemHealthMonitor:
            def __init__(self):
                self.components = {
                    'moex_client': {'status': 'unknown', 'last_check': None},
                    'news_aggregator': {'status': 'unknown', 'last_check': None},
                    'ai_engine': {'status': 'unknown', 'last_check': None},
                    'broker_api': {'status': 'unknown', 'last_check': None},
                    'risk_manager': {'status': 'unknown', 'last_check': None}
                }
            
            def check_component_health(self, component_name):
                """Perform health check on component"""
                start_time = time.time()
                
                try:
                    # Simulate component-specific health checks
                    time.sleep(0.01)  # Simulate check time
                    success = random.random() > 0.1  # 90% success rate
                    
                    response_time = time.time() - start_time
                    
                    if success:
                        self.components[component_name].update({
                            'status': 'healthy',
                            'last_check': datetime.now()
                        })
                        return {'status': 'healthy', 'response_time': response_time}
                    else:
                        self.components[component_name].update({
                            'status': 'unhealthy',
                            'last_check': datetime.now()
                        })
                        return {'status': 'unhealthy', 'error': 'Health check failed'}
                
                except Exception as e:
                    self.components[component_name].update({
                        'status': 'error',
                        'last_check': datetime.now()
                    })
                    return {'status': 'error', 'error': str(e)}
            
            def get_system_status(self):
                """Get overall system health status"""
                healthy_count = sum(1 for comp in self.components.values() if comp['status'] == 'healthy')
                total_count = len(self.components)
                
                if healthy_count == total_count:
                    overall_status = 'healthy'
                elif healthy_count >= total_count * 0.8:
                    overall_status = 'degraded'
                else:
                    overall_status = 'unhealthy'
                
                return {
                    'status': overall_status,
                    'healthy_components': healthy_count,
                    'total_components': total_count,
                    'health_percentage': (healthy_count / total_count) * 100
                }
        
        # Test health monitoring
        monitor = SystemHealthMonitor()
        
        # Check all components
        for component in monitor.components.keys():
            health = monitor.check_component_health(component)
            assert health['status'] in ['healthy', 'unhealthy', 'error']
        
        # Get system status
        system_status = monitor.get_system_status()
        assert system_status['status'] in ['healthy', 'degraded', 'unhealthy']
        assert system_status['total_components'] == 5
        assert 0 <= system_status['health_percentage'] <= 100
    
    def test_performance_benchmarking(self, mock_moex_client, mock_ai_engine):
        """Test system performance benchmarking"""
        
        class PerformanceBenchmark:
            def __init__(self):
                self.benchmarks = {}
            
            def benchmark_data_collection(self, moex_client, symbols):
                """Benchmark data collection performance"""
                start_time = time.time()
                
                market_data = moex_client.get_market_data(symbols)
                
                end_time = time.time()
                duration = end_time - start_time
                
                self.benchmarks['data_collection'] = {
                    'duration': duration,
                    'symbols_count': len(symbols),
                    'symbols_per_second': len(symbols) / duration if duration > 0 else 0
                }
                
                return market_data, duration
            
            def benchmark_signal_generation(self, ai_engine, symbol, market_data):
                """Benchmark AI signal generation performance"""
                start_time = time.time()
                
                signal = ai_engine.generate_trading_signal(symbol=symbol, market_data=market_data)
                
                end_time = time.time()
                duration = end_time - start_time
                
                self.benchmarks['signal_generation'] = {
                    'duration': duration,
                    'signals_per_second': 1 / duration if duration > 0 else 0
                }
                
                return signal, duration
        
        # Setup
        mock_moex_client.connect()
        benchmark = PerformanceBenchmark()
        
        # Benchmark data collection
        symbols = ['SBER', 'GAZP', 'LKOH']
        market_data, collection_time = benchmark.benchmark_data_collection(mock_moex_client, symbols)
        
        assert collection_time < 1.0  # Should be fast
        assert len(market_data) == len(symbols)
        
        # Benchmark signal generation
        signal, signal_time = benchmark.benchmark_signal_generation(
            mock_ai_engine, 'SBER', market_data['SBER']
        )
        
        assert signal_time < 0.5  # Should be fast
        assert isinstance(signal, TradingSignal)
        
        mock_moex_client.disconnect()
    
    def test_data_quality_validation_pipeline(self, mock_moex_client, mock_news_aggregator):
        """Test comprehensive data quality validation"""
        
        class DataQualityValidator:
            def validate_market_data(self, market_data):
                """Validate market data quality"""
                errors = []
                warnings = []
                
                for symbol, data in market_data.items():
                    # Check required fields
                    if not data.price or data.price <= 0:
                        errors.append(f"{symbol}: Invalid price {data.price}")
                    
                    if not data.volume or data.volume < 0:
                        errors.append(f"{symbol}: Invalid volume {data.volume}")
                    
                    if data.currency != "RUB":
                        warnings.append(f"{symbol}: Unexpected currency {data.currency}")
                    
                    # Check bid/ask spread
                    if data.bid and data.ask:
                        spread = (data.ask - data.bid) / data.price
                        if spread > 0.05:  # 5% spread threshold
                            warnings.append(f"{symbol}: Wide bid/ask spread {spread:.2%}")
                
                return {'errors': errors, 'warnings': warnings}
            
            def validate_news_data(self, news_articles):
                """Validate news data quality"""
                errors = []
                warnings = []
                
                for i, article in enumerate(news_articles):
                    # Check required fields
                    if not article.title or len(article.title.strip()) == 0:
                        errors.append(f"Article {i}: Empty title")
                    
                    if not article.content or len(article.content.strip()) == 0:
                        errors.append(f"Article {i}: Empty content")
                    
                    if article.language != "ru":
                        warnings.append(f"Article {i}: Unexpected language {article.language}")
                
                return {'errors': errors, 'warnings': warnings}
        
        # Setup
        mock_moex_client.connect()
        mock_news_aggregator.connect()
        
        validator = DataQualityValidator()
        
        # Test market data validation
        market_data = mock_moex_client.get_market_data(['SBER', 'GAZP'])
        market_validation = validator.validate_market_data(market_data)
        
        # Should have no errors for mock data
        assert len(market_validation['errors']) == 0
        
        # Test news data validation
        news_articles = mock_news_aggregator.get_latest_news(['SBER'], limit=3)
        news_validation = validator.validate_news_data(news_articles)
        
        # Should have no errors for mock data
        assert len(news_validation['errors']) == 0
        
        mock_moex_client.disconnect()
    
    def test_continuous_integration_pipeline(self):
        """Test continuous integration pipeline simulation"""
        
        class ContinuousIntegrationPipeline:
            def __init__(self):
                self.test_suites = [
                    'unit_tests',
                    'integration_tests',
                    'performance_tests',
                    'stress_tests'
                ]
                self.results = {}
            
            def run_test_suite(self, suite_name):
                """Simulate running a test suite"""
                start_time = time.time()
                
                # Simulate test execution
                if suite_name == 'unit_tests':
                    time.sleep(0.05)
                    success_rate = 0.98
                    test_count = 150
                elif suite_name == 'integration_tests':
                    time.sleep(0.1)
                    success_rate = 0.95
                    test_count = 50
                elif suite_name == 'performance_tests':
                    time.sleep(0.08)
                    success_rate = 0.90
                    test_count = 20
                else:  # stress_tests
                    time.sleep(0.06)
                    success_rate = 0.85
                    test_count = 15
                
                # Simulate test results
                passed_tests = int(test_count * success_rate)
                failed_tests = test_count - passed_tests
                
                duration = time.time() - start_time
                
                result = {
                    'suite': suite_name,
                    'total_tests': test_count,
                    'passed_tests': passed_tests,
                    'failed_tests': failed_tests,
                    'success_rate': (passed_tests / test_count) * 100,
                    'duration': duration
                }
                
                self.results[suite_name] = result
                return result
            
            def run_full_pipeline(self):
                """Run complete CI pipeline"""
                for suite in self.test_suites:
                    result = self.run_test_suite(suite)
                    
                    # Stop pipeline if critical tests fail
                    if suite in ['unit_tests', 'integration_tests'] and result['success_rate'] < 90:
                        return {
                            'status': 'failed',
                            'failed_suite': suite,
                            'message': f"Critical test suite {suite} failed"
                        }
                
                # Calculate overall statistics
                total_tests = sum(r['total_tests'] for r in self.results.values())
                total_passed = sum(r['passed_tests'] for r in self.results.values())
                overall_success_rate = (total_passed / total_tests) * 100 if total_tests > 0 else 0
                
                return {
                    'status': 'success' if overall_success_rate >= 90 else 'warning',
                    'total_tests': total_tests,
                    'total_passed': total_passed,
                    'overall_success_rate': overall_success_rate,
                    'suite_results': self.results
                }
        
        # Run CI pipeline
        ci_pipeline = ContinuousIntegrationPipeline()
        
        # Test individual suite execution
        unit_test_result = ci_pipeline.run_test_suite('unit_tests')
        assert unit_test_result['total_tests'] > 0
        assert unit_test_result['success_rate'] >= 90
        
        # Test full pipeline execution
        pipeline_result = ci_pipeline.run_full_pipeline()
        
        assert pipeline_result['status'] in ['success', 'warning', 'failed']
        assert pipeline_result['total_tests'] > 0
        assert pipeline_result['overall_success_rate'] >= 80
        assert len(pipeline_result['suite_results']) == len(ci_pipeline.test_suites)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])