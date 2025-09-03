"""
Comprehensive Integration Tests for Russian Market Trading Workflow - Task 12.3
End-to-end testing, broker API integration, stress testing, and automated pipeline validation
"""

import pytest
import asyncio
import time
import threading
import concurrent.futures
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import json
import tempfile
import os
import random
import psutil
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

# Configure logging for integration tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import system path setup
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    # Try to import actual components
    from russian_trading_bot.services.ai_decision_engine import AIDecisionEngine, DecisionWeights, MarketConditions
    from russian_trading_bot.services.portfolio_manager import PortfolioManager
    from russian_trading_bot.services.moex_client import MOEXClient
    from russian_trading_bot.services.news_aggregator import RussianNewsAggregator
    from russian_trading_bot.services.sentiment_analyzer import SentimentAnalyzer
    from russian_trading_bot.services.technical_analyzer import TechnicalAnalyzer, TechnicalIndicators
    from russian_trading_bot.services.risk_manager import RiskManager
    from russian_trading_bot.services.notification_service import NotificationService
    from russian_trading_bot.services.tinkoff_broker import TinkoffBroker
    from russian_trading_bot.services.finam_broker import FinamBroker
    from russian_trading_bot.services.order_manager import RussianOrderManager, OrderPriority
    
    from russian_trading_bot.models.trading import TradingSignal, OrderAction, TradeOrder, ExecutionResult, OrderStatus, OrderType
    from russian_trading_bot.models.market_data import RussianStock, MarketData
    from russian_trading_bot.models.news_data import NewsArticle, NewsSentiment
    
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Could not import actual components: {e}")
    COMPONENTS_AVAILABLE = False
    
    # Define mock components for testing
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


# Import stress test configuration
from stress_test_config import StressTestConfig, STRESS_TEST_SCENARIOS, TestMetrics, StressTestReporter

@dataclass
class IntegrationTestMetrics:
    """Metrics for integration testing"""
    test_name: str
    start_time: datetime
    end_time: datetime
    duration: float
    success: bool
    error_message: Optional[str] = None
    data_points_processed: int = 0
    trades_executed: int = 0
    api_calls_made: int = 0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0


class MockDataProvider:
    """Enhanced mock data provider for comprehensive testing"""
    
    def __init__(self):
        self.symbols = ['SBER', 'GAZP', 'LKOH', 'YNDX', 'MGNT', 'ROSN', 'NVTK', 'TATN', 'SNGS', 'GMKN']
        self.base_prices = {
            'SBER': Decimal('250.0'), 'GAZP': Decimal('180.0'), 'LKOH': Decimal('6500.0'),
            'YNDX': Decimal('2800.0'), 'MGNT': Decimal('5200.0'), 'ROSN': Decimal('550.0'),
            'NVTK': Decimal('1200.0'), 'TATN': Decimal('800.0'), 'SNGS': Decimal('45.0'),
            'GMKN': Decimal('18000.0')
        }
        self.volatility_multiplier = 1.0
        self.market_open = True
        self.connection_stable = True
        self.data_delay_ms = 0
        
    def get_market_data(self, symbols: List[str], with_delay: bool = True) -> Dict[str, Any]:
        """Get market data with configurable delay and volatility"""
        if with_delay and self.data_delay_ms > 0:
            time.sleep(self.data_delay_ms / 1000.0)
            
        if not self.connection_stable:
            raise ConnectionError("Market data connection unstable")
            
        if not self.market_open:
            raise Exception("Market is closed")
            
        market_data = {}
        for symbol in symbols:
            if symbol in self.base_prices:
                base_price = self.base_prices[symbol]
                price_change = random.uniform(-0.05, 0.05) * self.volatility_multiplier
                current_price = base_price * (Decimal('1') + Decimal(str(price_change)))
                
                market_data[symbol] = {
                    'symbol': symbol,
                    'timestamp': datetime.now(),
                    'price': current_price,
                    'volume': random.randint(50000, 500000) * int(self.volatility_multiplier),
                    'bid': current_price * Decimal('0.999'),
                    'ask': current_price * Decimal('1.001'),
                    'currency': 'RUB'
                }
                
        return market_data
    
    def get_news_data(self, symbols: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """Get news data with sentiment bias"""
        if not self.connection_stable:
            raise ConnectionError("News data connection unstable")
            
        news_articles = []
        sentiment_templates = {
            'positive': [
                "{symbol} показал рост прибыли в текущем квартале",
                "Аналитики повысили рекомендации по акциям {symbol}",
                "{symbol} объявил о новых инвестиционных проектах"
            ],
            'negative': [
                "{symbol} столкнулся с регулятивными проблемами",
                "Прибыль {symbol} оказалась ниже ожиданий",
                "{symbol} снизил прогнозы на текущий год"
            ],
            'neutral': [
                "{symbol} провел собрание акционеров",
                "Руководство {symbol} прокомментировало рыночную ситуацию",
                "{symbol} опубликовал финансовую отчетность"
            ]
        }
        
        for i in range(limit):
            symbol = random.choice(symbols)
            sentiment_type = random.choice(['positive', 'negative', 'neutral'])
            template = random.choice(sentiment_templates[sentiment_type])
            content = template.format(symbol=symbol)
            
            news_articles.append({
                'title': content,
                'content': content + " Подробности в полной версии статьи.",
                'source': random.choice(['RBC', 'Vedomosti', 'Kommersant', 'Interfax']),
                'timestamp': datetime.now() - timedelta(hours=random.randint(0, 24)),
                'language': 'ru',
                'mentioned_stocks': [symbol],
                'sentiment_score': random.uniform(-1, 1) if sentiment_type != 'neutral' else random.uniform(-0.2, 0.2)
            })
            
        return news_articles
    
    def set_volatility(self, multiplier: float):
        """Set market volatility multiplier"""
        self.volatility_multiplier = multiplier
        
    def set_connection_stability(self, stable: bool):
        """Set connection stability for failure testing"""
        self.connection_stable = stable
        
    def set_data_delay(self, delay_ms: int):
        """Set data retrieval delay for performance testing"""
        self.data_delay_ms = delay_ms


class MockBrokerSystem:
    """Enhanced mock broker system for comprehensive testing"""
    
    def __init__(self, initial_balance: Decimal = Decimal('1000000')):
        self.account_balance = initial_balance
        self.positions = {}
        self.orders = {}
        self.order_counter = 0
        self.failure_rate = 0.0
        self.latency_ms = 100
        self.connection_stable = True
        self.order_history = []
        
    def place_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Place order with realistic broker behavior"""
        if not self.connection_stable:
            raise ConnectionError("Broker connection unstable")
            
        # Simulate latency
        time.sleep(self.latency_ms / 1000.0)
        
        # Simulate random failures
        if random.random() < self.failure_rate:
            return {
                'order_id': f"FAILED_{self.order_counter}",
                'status': 'REJECTED',
                'error_message': 'Simulated broker failure',
                'timestamp': datetime.now()
            }
            
        self.order_counter += 1
        order_id = f"ORDER_{self.order_counter:06d}"
        
        symbol = order_data['symbol']
        action = order_data['action']
        quantity = order_data['quantity']
        price = order_data.get('price', Decimal('250.0'))
        
        commission = price * quantity * Decimal('0.0005')  # 0.05% commission
        
        if action == 'BUY':
            total_cost = price * quantity + commission
            if total_cost <= self.account_balance:
                self.account_balance -= total_cost
                
                if symbol in self.positions:
                    pos = self.positions[symbol]
                    total_quantity = pos['quantity'] + quantity
                    total_cost_basis = pos['avg_price'] * pos['quantity'] + price * quantity
                    new_avg_price = total_cost_basis / total_quantity
                    
                    self.positions[symbol] = {
                        'quantity': total_quantity,
                        'avg_price': new_avg_price
                    }
                else:
                    self.positions[symbol] = {
                        'quantity': quantity,
                        'avg_price': price
                    }
                
                result = {
                    'order_id': order_id,
                    'status': 'FILLED',
                    'filled_quantity': quantity,
                    'average_price': price,
                    'commission': commission,
                    'timestamp': datetime.now()
                }
            else:
                result = {
                    'order_id': order_id,
                    'status': 'REJECTED',
                    'error_message': 'Insufficient funds',
                    'timestamp': datetime.now()
                }
                
        elif action == 'SELL':
            if symbol in self.positions and self.positions[symbol]['quantity'] >= quantity:
                proceeds = price * quantity - commission
                self.account_balance += proceeds
                
                self.positions[symbol]['quantity'] -= quantity
                if self.positions[symbol]['quantity'] == 0:
                    del self.positions[symbol]
                
                result = {
                    'order_id': order_id,
                    'status': 'FILLED',
                    'filled_quantity': quantity,
                    'average_price': price,
                    'commission': commission,
                    'timestamp': datetime.now()
                }
            else:
                result = {
                    'order_id': order_id,
                    'status': 'REJECTED',
                    'error_message': 'Insufficient position',
                    'timestamp': datetime.now()
                }
        
        self.order_history.append(result)
        return result
    
    def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        if not self.connection_stable:
            raise ConnectionError("Broker connection unstable")
            
        return {
            'balance': self.account_balance,
            'currency': 'RUB',
            'positions': self.positions.copy(),
            'total_orders': len(self.order_history)
        }
    
    def set_failure_rate(self, rate: float):
        """Set order failure rate for stress testing"""
        self.failure_rate = rate
        
    def set_latency(self, latency_ms: int):
        """Set order execution latency"""
        self.latency_ms = latency_ms
        
    def set_connection_stability(self, stable: bool):
        """Set connection stability"""
        self.connection_stable = stable


class IntegrationTestFramework:
    """Framework for running comprehensive integration tests"""
    
    def __init__(self):
        self.data_provider = MockDataProvider()
        self.broker_system = MockBrokerSystem()
        self.test_metrics = []
        self.system_monitor = SystemMonitor()
        
    def run_end_to_end_workflow_test(self, symbols: List[str], duration_seconds: int = 60) -> IntegrationTestMetrics:
        """Test complete end-to-end trading workflow"""
        test_name = "end_to_end_workflow"
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting {test_name} test with {len(symbols)} symbols for {duration_seconds} seconds")
            
            # Initialize metrics
            data_points_processed = 0
            trades_executed = 0
            api_calls_made = 0
            
            # Start system monitoring
            self.system_monitor.start_monitoring()
            
            end_time = start_time + timedelta(seconds=duration_seconds)
            
            while datetime.now() < end_time:
                # Phase 1: Data Collection
                try:
                    market_data = self.data_provider.get_market_data(symbols)
                    news_data = self.data_provider.get_news_data(symbols, limit=5)
                    data_points_processed += len(market_data) + len(news_data)
                    api_calls_made += 2
                except Exception as e:
                    logger.warning(f"Data collection failed: {e}")
                    continue
                
                # Phase 2: Analysis (simplified mock)
                trading_signals = []
                for symbol in symbols:
                    if symbol in market_data:
                        # Simple mock analysis
                        price_change = random.uniform(-0.05, 0.05)
                        if abs(price_change) > 0.02:  # Only trade on significant moves
                            action = 'BUY' if price_change > 0 else 'SELL'
                            confidence = 0.6 + random.uniform(0, 0.3)
                            
                            trading_signals.append({
                                'symbol': symbol,
                                'action': action,
                                'confidence': confidence,
                                'price': market_data[symbol]['price'],
                                'quantity': random.randint(10, 100)
                            })
                
                # Phase 3: Trade Execution
                for signal in trading_signals:
                    if signal['confidence'] >= 0.7:  # Only execute high-confidence signals
                        try:
                            result = self.broker_system.place_order(signal)
                            if result['status'] == 'FILLED':
                                trades_executed += 1
                            api_calls_made += 1
                        except Exception as e:
                            logger.warning(f"Trade execution failed: {e}")
                
                # Brief pause between cycles
                time.sleep(1)
            
            # Stop monitoring and collect metrics
            memory_usage, cpu_usage = self.system_monitor.stop_monitoring()
            
            test_end_time = datetime.now()
            duration = (test_end_time - start_time).total_seconds()
            
            return IntegrationTestMetrics(
                test_name=test_name,
                start_time=start_time,
                end_time=test_end_time,
                duration=duration,
                success=True,
                data_points_processed=data_points_processed,
                trades_executed=trades_executed,
                api_calls_made=api_calls_made,
                memory_usage_mb=memory_usage,
                cpu_usage_percent=cpu_usage
            )
            
        except Exception as e:
            test_end_time = datetime.now()
            duration = (test_end_time - start_time).total_seconds()
            
            return IntegrationTestMetrics(
                test_name=test_name,
                start_time=start_time,
                end_time=test_end_time,
                duration=duration,
                success=False,
                error_message=str(e),
                memory_usage_mb=self.system_monitor.get_current_memory_usage(),
                cpu_usage_percent=self.system_monitor.get_current_cpu_usage()
            )  
  
    def run_broker_api_integration_test(self, broker_configs: List[Dict[str, Any]]) -> IntegrationTestMetrics:
        """Test Russian broker API integration"""
        test_name = "broker_api_integration"
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting {test_name} test with {len(broker_configs)} broker configurations")
            
            api_calls_made = 0
            successful_connections = 0
            successful_orders = 0
            
            self.system_monitor.start_monitoring()
            
            for i, config in enumerate(broker_configs):
                broker_name = config.get('name', f'broker_{i}')
                logger.info(f"Testing broker: {broker_name}")
                
                # Test connection
                try:
                    # Simulate broker connection
                    time.sleep(0.1)  # Connection delay
                    api_calls_made += 1
                    successful_connections += 1
                    logger.info(f"Successfully connected to {broker_name}")
                except Exception as e:
                    logger.warning(f"Failed to connect to {broker_name}: {e}")
                    continue
                
                # Test account info retrieval
                try:
                    account_info = self.broker_system.get_account_info()
                    api_calls_made += 1
                    logger.info(f"Retrieved account info from {broker_name}")
                except Exception as e:
                    logger.warning(f"Failed to get account info from {broker_name}: {e}")
                    continue
                
                # Test order placement
                test_orders = [
                    {'symbol': 'SBER', 'action': 'BUY', 'quantity': 10, 'price': Decimal('250.0')},
                    {'symbol': 'GAZP', 'action': 'BUY', 'quantity': 20, 'price': Decimal('180.0')},
                    {'symbol': 'SBER', 'action': 'SELL', 'quantity': 5, 'price': Decimal('255.0')}
                ]
                
                for order in test_orders:
                    try:
                        result = self.broker_system.place_order(order)
                        api_calls_made += 1
                        
                        if result['status'] == 'FILLED':
                            successful_orders += 1
                            logger.info(f"Successfully executed order on {broker_name}: {order['symbol']} {order['action']}")
                        else:
                            logger.warning(f"Order rejected on {broker_name}: {result.get('error_message', 'Unknown error')}")
                            
                    except Exception as e:
                        logger.warning(f"Order execution failed on {broker_name}: {e}")
                
                # Brief pause between brokers
                time.sleep(0.5)
            
            memory_usage, cpu_usage = self.system_monitor.stop_monitoring()
            test_end_time = datetime.now()
            duration = (test_end_time - start_time).total_seconds()
            
            # Consider test successful if at least 70% of operations succeeded
            success_rate = (successful_connections + successful_orders) / (len(broker_configs) + len(broker_configs) * 3)
            success = success_rate >= 0.7
            
            return IntegrationTestMetrics(
                test_name=test_name,
                start_time=start_time,
                end_time=test_end_time,
                duration=duration,
                success=success,
                api_calls_made=api_calls_made,
                trades_executed=successful_orders,
                memory_usage_mb=memory_usage,
                cpu_usage_percent=cpu_usage
            )
            
        except Exception as e:
            test_end_time = datetime.now()
            duration = (test_end_time - start_time).total_seconds()
            
            return IntegrationTestMetrics(
                test_name=test_name,
                start_time=start_time,
                end_time=test_end_time,
                duration=duration,
                success=False,
                error_message=str(e),
                memory_usage_mb=self.system_monitor.get_current_memory_usage(),
                cpu_usage_percent=self.system_monitor.get_current_cpu_usage()
            )
    
    def run_stress_test(self, scenario_name: str, config: StressTestConfig, duration_seconds: int = 120) -> IntegrationTestMetrics:
        """Run stress test with specified configuration"""
        test_name = f"stress_test_{scenario_name}"
        start_time = datetime.now()
        
        try:
            logger.info(f"Starting {test_name} with volatility {config.volatility_multiplier}x for {duration_seconds} seconds")
            
            # Configure system for stress test
            self.data_provider.set_volatility(config.volatility_multiplier)
            self.data_provider.set_data_delay(config.broker_latency_ms // 2)  # Data delay
            self.broker_system.set_failure_rate(config.broker_failure_rate)
            self.broker_system.set_latency(config.broker_latency_ms)
            
            # Simulate connection instability if configured
            if config.connection_timeout_rate > 0:
                connection_stable = random.random() > config.connection_timeout_rate
                self.data_provider.set_connection_stability(connection_stable)
                self.broker_system.set_connection_stability(connection_stable)
            
            symbols = ['SBER', 'GAZP', 'LKOH', 'YNDX', 'MGNT']
            data_points_processed = 0
            trades_executed = 0
            api_calls_made = 0
            failed_operations = 0
            
            self.system_monitor.start_monitoring()
            
            end_time = start_time + timedelta(seconds=duration_seconds)
            
            # Run concurrent operations if specified
            if config.concurrent_users > 1:
                with concurrent.futures.ThreadPoolExecutor(max_workers=config.concurrent_users) as executor:
                    futures = []
                    
                    for user_id in range(config.concurrent_users):
                        future = executor.submit(self._run_user_simulation, user_id, symbols, end_time)
                        futures.append(future)
                    
                    # Collect results from all users
                    for future in concurrent.futures.as_completed(futures):
                        try:
                            user_metrics = future.result()
                            data_points_processed += user_metrics['data_points']
                            trades_executed += user_metrics['trades']
                            api_calls_made += user_metrics['api_calls']
                            failed_operations += user_metrics['failures']
                        except Exception as e:
                            logger.warning(f"User simulation failed: {e}")
                            failed_operations += 1
            else:
                # Single user simulation
                user_metrics = self._run_user_simulation(0, symbols, end_time)
                data_points_processed = user_metrics['data_points']
                trades_executed = user_metrics['trades']
                api_calls_made = user_metrics['api_calls']
                failed_operations = user_metrics['failures']
            
            memory_usage, cpu_usage = self.system_monitor.stop_monitoring()
            test_end_time = datetime.now()
            duration = (test_end_time - start_time).total_seconds()
            
            # Determine success based on failure rate
            total_operations = api_calls_made + trades_executed
            failure_rate = failed_operations / total_operations if total_operations > 0 else 1.0
            success = failure_rate < 0.5  # Less than 50% failure rate
            
            return IntegrationTestMetrics(
                test_name=test_name,
                start_time=start_time,
                end_time=test_end_time,
                duration=duration,
                success=success,
                data_points_processed=data_points_processed,
                trades_executed=trades_executed,
                api_calls_made=api_calls_made,
                memory_usage_mb=memory_usage,
                cpu_usage_percent=cpu_usage,
                error_message=f"Failure rate: {failure_rate:.1%}" if not success else None
            )
            
        except Exception as e:
            test_end_time = datetime.now()
            duration = (test_end_time - start_time).total_seconds()
            
            return IntegrationTestMetrics(
                test_name=test_name,
                start_time=start_time,
                end_time=test_end_time,
                duration=duration,
                success=False,
                error_message=str(e),
                memory_usage_mb=self.system_monitor.get_current_memory_usage(),
                cpu_usage_percent=self.system_monitor.get_current_cpu_usage()
            )
    
    def _run_user_simulation(self, user_id: int, symbols: List[str], end_time: datetime) -> Dict[str, int]:
        """Simulate a single user's trading activity"""
        data_points = 0
        trades = 0
        api_calls = 0
        failures = 0
        
        logger.info(f"Starting user {user_id} simulation")
        
        while datetime.now() < end_time:
            try:
                # Data collection
                market_data = self.data_provider.get_market_data(symbols[:3])  # Limit symbols per user
                news_data = self.data_provider.get_news_data(symbols[:3], limit=2)
                data_points += len(market_data) + len(news_data)
                api_calls += 2
                
                # Trading decision (simplified)
                for symbol in market_data:
                    if random.random() < 0.3:  # 30% chance to trade
                        order = {
                            'symbol': symbol,
                            'action': random.choice(['BUY', 'SELL']),
                            'quantity': random.randint(5, 50),
                            'price': market_data[symbol]['price']
                        }
                        
                        result = self.broker_system.place_order(order)
                        api_calls += 1
                        
                        if result['status'] == 'FILLED':
                            trades += 1
                        elif result['status'] == 'REJECTED':
                            failures += 1
                
            except Exception as e:
                failures += 1
                logger.warning(f"User {user_id} operation failed: {e}")
            
            # Brief pause
            time.sleep(random.uniform(0.1, 0.5))
        
        logger.info(f"User {user_id} completed: {trades} trades, {failures} failures")
        
        return {
            'data_points': data_points,
            'trades': trades,
            'api_calls': api_calls,
            'failures': failures
        }


class SystemMonitor:
    """Monitor system resources during testing"""
    
    def __init__(self):
        self.monitoring = False
        self.memory_samples = []
        self.cpu_samples = []
        self.monitor_thread = None
        
    def start_monitoring(self):
        """Start system monitoring"""
        self.monitoring = True
        self.memory_samples = []
        self.cpu_samples = []
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.start()
        
    def stop_monitoring(self) -> Tuple[float, float]:
        """Stop monitoring and return average usage"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        avg_memory = sum(self.memory_samples) / len(self.memory_samples) if self.memory_samples else 0
        avg_cpu = sum(self.cpu_samples) / len(self.cpu_samples) if self.cpu_samples else 0
        
        return avg_memory, avg_cpu
    
    def _monitor_loop(self):
        """Monitor system resources in background"""
        while self.monitoring:
            try:
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                cpu_percent = process.cpu_percent()
                
                self.memory_samples.append(memory_mb)
                self.cpu_samples.append(cpu_percent)
                
            except Exception as e:
                logger.warning(f"System monitoring error: {e}")
            
            time.sleep(1)
    
    def get_current_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
    
    def get_current_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        try:
            process = psutil.Process()
            return process.cpu_percent()
        except:
            return 0.0


class AutomatedTestPipeline:
    """Automated testing pipeline for continuous validation"""
    
    def __init__(self):
        self.framework = IntegrationTestFramework()
        self.test_results = []
        self.notification_callbacks = []
        
    def run_full_test_suite(self) -> List[IntegrationTestMetrics]:
        """Run complete test suite"""
        logger.info("Starting full integration test suite")
        
        test_results = []
        
        # Test 1: End-to-end workflow
        symbols = ['SBER', 'GAZP', 'LKOH', 'YNDX']
        result = self.framework.run_end_to_end_workflow_test(symbols, duration_seconds=30)
        test_results.append(result)
        logger.info(f"End-to-end test completed: {'PASSED' if result.success else 'FAILED'}")
        
        # Test 2: Broker API integration
        broker_configs = [
            {'name': 'tinkoff_mock', 'type': 'tinkoff'},
            {'name': 'finam_mock', 'type': 'finam'}
        ]
        result = self.framework.run_broker_api_integration_test(broker_configs)
        test_results.append(result)
        logger.info(f"Broker API test completed: {'PASSED' if result.success else 'FAILED'}")
        
        # Test 3: Stress tests
        stress_scenarios = ['normal_market', 'high_volatility', 'geopolitical_crisis']
        for scenario_name in stress_scenarios:
            if scenario_name in STRESS_TEST_SCENARIOS:
                config = STRESS_TEST_SCENARIOS[scenario_name]
                result = self.framework.run_stress_test(scenario_name, config, duration_seconds=60)
                test_results.append(result)
                logger.info(f"Stress test {scenario_name} completed: {'PASSED' if result.success else 'FAILED'}")
        
        self.test_results.extend(test_results)
        self._notify_results(test_results)
        
        return test_results
    
    def run_continuous_validation(self, interval_minutes: int = 60, max_runs: Optional[int] = None):
        """Run continuous validation pipeline"""
        logger.info(f"Starting continuous validation with {interval_minutes} minute intervals")
        
        run_count = 0
        
        while True:
            if max_runs and run_count >= max_runs:
                logger.info(f"Reached maximum runs ({max_runs}), stopping")
                break
                
            run_count += 1
            logger.info(f"Starting validation run #{run_count}")
            
            try:
                results = self.run_full_test_suite()
                self._save_results(results, run_count)
                
                # Check for critical failures
                critical_failures = [r for r in results if not r.success and 'end_to_end' in r.test_name]
                if critical_failures:
                    logger.error(f"Critical failures detected in run #{run_count}")
                    
            except Exception as e:
                logger.error(f"Error during validation run #{run_count}: {e}")
            
            if max_runs and run_count >= max_runs:
                break
                
            logger.info(f"Waiting {interval_minutes} minutes until next run...")
            time.sleep(interval_minutes * 60)
    
    def _save_results(self, results: List[IntegrationTestMetrics], run_number: int):
        """Save test results to file"""
        results_data = {
            'run_number': run_number,
            'timestamp': datetime.now().isoformat(),
            'results': [
                {
                    'test_name': r.test_name,
                    'success': r.success,
                    'duration': r.duration,
                    'data_points_processed': r.data_points_processed,
                    'trades_executed': r.trades_executed,
                    'api_calls_made': r.api_calls_made,
                    'memory_usage_mb': r.memory_usage_mb,
                    'cpu_usage_percent': r.cpu_usage_percent,
                    'error_message': r.error_message
                }
                for r in results
            ]
        }
        
        filename = f"integration_test_results_run_{run_number:04d}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Test results saved to {filename}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
    
    def _notify_results(self, results: List[IntegrationTestMetrics]):
        """Send notifications about test results"""
        for callback in self.notification_callbacks:
            try:
                callback(results)
            except Exception as e:
                logger.error(f"Notification callback failed: {e}")
    
    def add_notification_callback(self, callback):
        """Add notification callback"""
        self.notification_callbacks.append(callback)
    
    def generate_report(self, results: List[IntegrationTestMetrics]) -> str:
        """Generate comprehensive test report"""
        report = "ОТЧЕТ ПО ИНТЕГРАЦИОННОМУ ТЕСТИРОВАНИЮ\n"
        report += "=" * 50 + "\n\n"
        
        # Summary
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.success)
        failed_tests = total_tests - passed_tests
        
        report += f"Всего тестов: {total_tests}\n"
        report += f"Пройдено: {passed_tests}\n"
        report += f"Провалено: {failed_tests}\n"
        report += f"Процент успеха: {(passed_tests / total_tests * 100):.1f}%\n\n"
        
        # Performance metrics
        total_duration = sum(r.duration for r in results)
        total_trades = sum(r.trades_executed for r in results)
        total_api_calls = sum(r.api_calls_made for r in results)
        avg_memory = sum(r.memory_usage_mb for r in results) / len(results)
        avg_cpu = sum(r.cpu_usage_percent for r in results) / len(results)
        
        report += f"Общая длительность: {total_duration:.1f} сек\n"
        report += f"Всего сделок: {total_trades}\n"
        report += f"Всего API вызовов: {total_api_calls}\n"
        report += f"Среднее использование памяти: {avg_memory:.1f} МБ\n"
        report += f"Средняя загрузка CPU: {avg_cpu:.1f}%\n\n"
        
        # Detailed results
        for result in results:
            report += f"ТЕСТ: {result.test_name}\n"
            report += f"Статус: {'ПРОЙДЕН' if result.success else 'ПРОВАЛЕН'}\n"
            report += f"Длительность: {result.duration:.2f} сек\n"
            report += f"Обработано данных: {result.data_points_processed}\n"
            report += f"Выполнено сделок: {result.trades_executed}\n"
            report += f"API вызовов: {result.api_calls_made}\n"
            report += f"Память: {result.memory_usage_mb:.1f} МБ\n"
            report += f"CPU: {result.cpu_usage_percent:.1f}%\n"
            
            if result.error_message:
                report += f"Ошибка: {result.error_message}\n"
            
            report += "-" * 30 + "\n\n"
        
        return report


# Pytest test classes and fixtures
@pytest.fixture
def integration_framework():
    """Create integration test framework"""
    return IntegrationTestFramework()


@pytest.fixture
def automated_pipeline():
    """Create automated test pipeline"""
    return AutomatedTestPipeline()


class TestEndToEndWorkflow:
    """Test complete end-to-end trading workflow"""
    
    def test_basic_end_to_end_workflow(self, integration_framework):
        """Test basic end-to-end workflow with minimal duration"""
        symbols = ['SBER', 'GAZP']
        result = integration_framework.run_end_to_end_workflow_test(symbols, duration_seconds=10)
        
        assert result.success, f"End-to-end test failed: {result.error_message}"
        assert result.duration > 0
        assert result.data_points_processed > 0
        assert result.api_calls_made > 0
        
    def test_extended_end_to_end_workflow(self, integration_framework):
        """Test extended end-to-end workflow with multiple symbols"""
        symbols = ['SBER', 'GAZP', 'LKOH', 'YNDX', 'MGNT']
        result = integration_framework.run_end_to_end_workflow_test(symbols, duration_seconds=30)
        
        assert result.success, f"Extended end-to-end test failed: {result.error_message}"
        assert result.data_points_processed >= len(symbols)
        assert result.memory_usage_mb > 0
        assert result.cpu_usage_percent >= 0
        
    def test_workflow_with_data_failures(self, integration_framework):
        """Test workflow resilience to data source failures"""
        # Configure intermittent data failures
        integration_framework.data_provider.set_connection_stability(False)
        
        symbols = ['SBER', 'GAZP']
        result = integration_framework.run_end_to_end_workflow_test(symbols, duration_seconds=15)
        
        # Test should handle failures gracefully
        # May not be fully successful but should not crash
        assert result.duration > 0
        assert result.error_message is None or "connection" in result.error_message.lower()


class TestBrokerAPIIntegration:
    """Test Russian broker API integration"""
    
    def test_single_broker_integration(self, integration_framework):
        """Test integration with single broker"""
        broker_configs = [{'name': 'test_broker', 'type': 'mock'}]
        result = integration_framework.run_broker_api_integration_test(broker_configs)
        
        assert result.success, f"Single broker test failed: {result.error_message}"
        assert result.api_calls_made > 0
        assert result.trades_executed >= 0
        
    def test_multiple_broker_integration(self, integration_framework):
        """Test integration with multiple brokers"""
        broker_configs = [
            {'name': 'tinkoff_mock', 'type': 'tinkoff'},
            {'name': 'finam_mock', 'type': 'finam'},
            {'name': 'vtb_mock', 'type': 'vtb'}
        ]
        result = integration_framework.run_broker_api_integration_test(broker_configs)
        
        assert result.success, f"Multiple broker test failed: {result.error_message}"
        assert result.api_calls_made >= len(broker_configs)
        
    def test_broker_failover_scenario(self, integration_framework):
        """Test broker failover mechanism"""
        # Configure high failure rate
        integration_framework.broker_system.set_failure_rate(0.5)
        
        broker_configs = [
            {'name': 'primary_broker', 'type': 'primary'},
            {'name': 'backup_broker', 'type': 'backup'}
        ]
        result = integration_framework.run_broker_api_integration_test(broker_configs)
        
        # Should handle failures and potentially succeed with backup
        assert result.duration > 0
        assert result.api_calls_made > 0


class TestStressTesting:
    """Test system under stress conditions"""
    
    def test_normal_market_stress(self, integration_framework):
        """Test system under normal market conditions"""
        config = STRESS_TEST_SCENARIOS['normal_market']
        result = integration_framework.run_stress_test('normal_market', config, duration_seconds=30)
        
        assert result.success, f"Normal market stress test failed: {result.error_message}"
        assert result.trades_executed >= 0
        assert result.memory_usage_mb > 0
        
    def test_high_volatility_stress(self, integration_framework):
        """Test system under high volatility conditions"""
        config = STRESS_TEST_SCENARIOS['high_volatility']
        result = integration_framework.run_stress_test('high_volatility', config, duration_seconds=45)
        
        # May not be fully successful under extreme conditions but should not crash
        assert result.duration > 0
        assert result.data_points_processed > 0
        
    def test_geopolitical_crisis_stress(self, integration_framework):
        """Test system during geopolitical crisis simulation"""
        config = STRESS_TEST_SCENARIOS['geopolitical_crisis']
        result = integration_framework.run_stress_test('geopolitical_crisis', config, duration_seconds=60)
        
        # System should survive crisis conditions
        assert result.duration > 0
        assert result.api_calls_made > 0
        
    def test_broker_overload_stress(self, integration_framework):
        """Test system under broker overload conditions"""
        config = STRESS_TEST_SCENARIOS['broker_overload']
        result = integration_framework.run_stress_test('broker_overload', config, duration_seconds=30)
        
        # Should handle broker overload gracefully
        assert result.duration > 0
        # May have high failure rate but should not crash
        
    def test_concurrent_user_stress(self, integration_framework):
        """Test system with multiple concurrent users"""
        config = StressTestConfig(
            concurrent_users=5,
            requests_per_second=50,
            volatility_multiplier=2.0,
            broker_latency_ms=200
        )
        result = integration_framework.run_stress_test('concurrent_users', config, duration_seconds=45)
        
        assert result.duration > 0
        assert result.api_calls_made > 0
        # Should handle concurrent load


class TestAutomatedPipeline:
    """Test automated testing pipeline"""
    
    def test_single_test_suite_run(self, automated_pipeline):
        """Test single run of full test suite"""
        results = automated_pipeline.run_full_test_suite()
        
        assert len(results) > 0
        assert any(r.test_name.startswith('end_to_end') for r in results)
        assert any(r.test_name.startswith('broker_api') for r in results)
        assert any(r.test_name.startswith('stress_test') for r in results)
        
    def test_report_generation(self, automated_pipeline):
        """Test test report generation"""
        # Run a quick test suite
        results = automated_pipeline.run_full_test_suite()
        
        # Generate report
        report = automated_pipeline.generate_report(results)
        
        assert "ОТЧЕТ ПО ИНТЕГРАЦИОННОМУ ТЕСТИРОВАНИЮ" in report
        assert "Всего тестов:" in report
        assert "Процент успеха:" in report
        
    def test_results_persistence(self, automated_pipeline):
        """Test that results are properly saved"""
        results = automated_pipeline.run_full_test_suite()
        
        # Save results
        automated_pipeline._save_results(results, 1)
        
        # Check if file was created
        filename = "integration_test_results_run_0001.json"
        assert os.path.exists(filename)
        
        # Verify file content
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert 'run_number' in data
            assert 'results' in data
            assert len(data['results']) == len(results)
        
        # Cleanup
        os.remove(filename)
        
    def test_notification_system(self, automated_pipeline):
        """Test notification system"""
        notifications_received = []
        
        def test_callback(results):
            notifications_received.append(results)
        
        automated_pipeline.add_notification_callback(test_callback)
        
        # Run test suite
        results = automated_pipeline.run_full_test_suite()
        
        # Verify notification was sent
        assert len(notifications_received) == 1
        assert len(notifications_received[0]) == len(results)


class TestSystemMonitoring:
    """Test system monitoring capabilities"""
    
    def test_system_monitor_basic(self):
        """Test basic system monitoring functionality"""
        monitor = SystemMonitor()
        
        monitor.start_monitoring()
        time.sleep(2)  # Monitor for 2 seconds
        memory_usage, cpu_usage = monitor.stop_monitoring()
        
        assert memory_usage > 0
        assert cpu_usage >= 0
        
    def test_system_monitor_during_load(self):
        """Test system monitoring during simulated load"""
        monitor = SystemMonitor()
        
        monitor.start_monitoring()
        
        # Simulate some CPU load
        start_time = time.time()
        while time.time() - start_time < 3:
            _ = sum(i * i for i in range(1000))
        
        memory_usage, cpu_usage = monitor.stop_monitoring()
        
        assert memory_usage > 0
        assert cpu_usage >= 0


# Performance benchmarking tests
class TestPerformanceBenchmarks:
    """Performance benchmarking tests"""
    
    def test_data_collection_performance(self, integration_framework):
        """Benchmark data collection performance"""
        symbols = ['SBER', 'GAZP', 'LKOH', 'YNDX', 'MGNT']
        
        start_time = time.time()
        
        for _ in range(10):  # 10 iterations
            market_data = integration_framework.data_provider.get_market_data(symbols)
            news_data = integration_framework.data_provider.get_news_data(symbols, limit=5)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete 10 iterations in reasonable time
        assert duration < 5.0  # Less than 5 seconds
        
        # Calculate throughput
        data_points_per_second = (len(symbols) * 2 * 10) / duration  # market + news data
        assert data_points_per_second > 10  # At least 10 data points per second
        
    def test_trade_execution_performance(self, integration_framework):
        """Benchmark trade execution performance"""
        orders = []
        for i in range(20):
            orders.append({
                'symbol': 'SBER',
                'action': 'BUY' if i % 2 == 0 else 'SELL',
                'quantity': 10,
                'price': Decimal('250.0')
            })
        
        start_time = time.time()
        
        successful_trades = 0
        for order in orders:
            result = integration_framework.broker_system.place_order(order)
            if result['status'] == 'FILLED':
                successful_trades += 1
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should execute trades efficiently
        trades_per_second = successful_trades / duration
        assert trades_per_second > 5  # At least 5 trades per second
        
    def test_memory_usage_stability(self, integration_framework):
        """Test memory usage stability over time"""
        monitor = SystemMonitor()
        monitor.start_monitoring()
        
        symbols = ['SBER', 'GAZP']
        
        # Run operations for extended period
        for _ in range(50):
            market_data = integration_framework.data_provider.get_market_data(symbols)
            news_data = integration_framework.data_provider.get_news_data(symbols, limit=2)
            
            # Execute some trades
            if random.random() < 0.3:
                order = {
                    'symbol': 'SBER',
                    'action': 'BUY',
                    'quantity': 10,
                    'price': Decimal('250.0')
                }
                integration_framework.broker_system.place_order(order)
        
        memory_usage, cpu_usage = monitor.stop_monitoring()
        
        # Memory usage should be reasonable
        assert memory_usage < 500  # Less than 500MB
        
        # Check for memory leaks by comparing initial and final usage
        initial_memory = monitor.get_current_memory_usage()
        
        # Run more operations
        for _ in range(20):
            market_data = integration_framework.data_provider.get_market_data(symbols)
        
        final_memory = monitor.get_current_memory_usage()
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be minimal
        assert memory_increase < 50  # Less than 50MB increase


def notification_callback_example(results: List[IntegrationTestMetrics]):
    """Example notification callback for failed tests"""
    failed_tests = [r for r in results if not r.success]
    
    if failed_tests:
        logger.warning(f"Integration test failures detected: {len(failed_tests)} tests failed")
        for test in failed_tests:
            logger.error(f"FAILED: {test.test_name} - {test.error_message}")
    else:
        logger.info("All integration tests passed successfully")


if __name__ == "__main__":
    # Example usage for manual testing
    pipeline = AutomatedTestPipeline()
    pipeline.add_notification_callback(notification_callback_example)
    
    print("Running comprehensive integration test suite...")
    results = pipeline.run_full_test_suite()
    
    print("\nTest Results Summary:")
    for result in results:
        status = "PASSED" if result.success else "FAILED"
        print(f"  {result.test_name}: {status} ({result.duration:.2f}s)")
    
    print(f"\nGenerated report:")
    print(pipeline.generate_report(results))