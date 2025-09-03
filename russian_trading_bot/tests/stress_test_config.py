"""
Configuration for stress testing Russian market trading system
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from decimal import Decimal


@dataclass
class StressTestConfig:
    """Configuration for stress testing scenarios"""
    
    # Market volatility settings
    volatility_multiplier: float = 1.0
    max_price_change: float = 0.10  # 10% max price change
    volume_multiplier: float = 1.0
    
    # Geopolitical risk settings
    geopolitical_risk_level: float = 0.0  # 0.0 to 1.0
    sanctions_impact: bool = False
    currency_volatility: float = 0.0
    
    # Broker stress settings
    broker_failure_rate: float = 0.0  # 0.0 to 1.0
    broker_latency_ms: int = 100
    connection_timeout_rate: float = 0.0
    
    # System load settings
    concurrent_users: int = 1
    requests_per_second: int = 10
    data_volume_multiplier: float = 1.0
    
    # Test duration
    test_duration_seconds: int = 60
    
    # Portfolio settings
    initial_capital: Decimal = Decimal('1000000')
    max_position_size: float = 0.1  # 10%
    
    # Risk management settings
    stop_loss_percentage: float = 0.05  # 5%
    max_daily_loss: float = 0.02  # 2%


# Predefined stress test scenarios
STRESS_TEST_SCENARIOS = {
    'normal_market': StressTestConfig(
        volatility_multiplier=1.0,
        geopolitical_risk_level=0.2,
        broker_failure_rate=0.01,
        broker_latency_ms=100
    ),
    
    'high_volatility': StressTestConfig(
        volatility_multiplier=3.0,
        max_price_change=0.15,
        volume_multiplier=5.0,
        geopolitical_risk_level=0.4,
        broker_latency_ms=200
    ),
    
    'geopolitical_crisis': StressTestConfig(
        volatility_multiplier=5.0,
        max_price_change=0.25,
        geopolitical_risk_level=1.0,
        sanctions_impact=True,
        currency_volatility=0.8,
        broker_failure_rate=0.1,
        broker_latency_ms=500
    ),
    
    'broker_overload': StressTestConfig(
        broker_failure_rate=0.3,
        broker_latency_ms=2000,
        connection_timeout_rate=0.2,
        concurrent_users=50,
        requests_per_second=100
    ),
    
    'system_overload': StressTestConfig(
        concurrent_users=100,
        requests_per_second=500,
        data_volume_multiplier=10.0,
        broker_latency_ms=1000,
        test_duration_seconds=300
    ),
    
    'market_crash': StressTestConfig(
        volatility_multiplier=10.0,
        max_price_change=0.50,  # 50% price swings
        volume_multiplier=20.0,
        geopolitical_risk_level=1.0,
        sanctions_impact=True,
        currency_volatility=1.0,
        broker_failure_rate=0.5,
        broker_latency_ms=5000
    )
}


@dataclass
class TestMetrics:
    """Metrics collected during stress testing"""
    
    # Performance metrics
    avg_response_time: float = 0.0
    max_response_time: float = 0.0
    min_response_time: float = 0.0
    requests_per_second: float = 0.0
    
    # Error metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    timeout_requests: int = 0
    error_rate: float = 0.0
    
    # Trading metrics
    total_trades: int = 0
    successful_trades: int = 0
    failed_trades: int = 0
    trade_success_rate: float = 0.0
    
    # Portfolio metrics
    initial_portfolio_value: Decimal = Decimal('0')
    final_portfolio_value: Decimal = Decimal('0')
    max_drawdown: float = 0.0
    total_return: float = 0.0
    
    # System metrics
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    
    def calculate_derived_metrics(self):
        """Calculate derived metrics from raw data"""
        if self.total_requests > 0:
            self.error_rate = (self.failed_requests / self.total_requests) * 100
        
        if self.total_trades > 0:
            self.trade_success_rate = (self.successful_trades / self.total_trades) * 100
        
        if self.initial_portfolio_value > 0:
            self.total_return = float((self.final_portfolio_value - self.initial_portfolio_value) / self.initial_portfolio_value * 100)


class StressTestReporter:
    """Generate stress test reports"""
    
    def __init__(self):
        self.test_results = {}
    
    def add_test_result(self, scenario_name: str, config: StressTestConfig, metrics: TestMetrics):
        """Add test result for reporting"""
        self.test_results[scenario_name] = {
            'config': config,
            'metrics': metrics,
            'timestamp': datetime.now()
        }
    
    def generate_report(self) -> str:
        """Generate comprehensive stress test report"""
        report = "ОТЧЕТ ПО СТРЕСС-ТЕСТИРОВАНИЮ СИСТЕМЫ ТОРГОВЛИ\n"
        report += "=" * 60 + "\n\n"
        
        for scenario_name, result in self.test_results.items():
            config = result['config']
            metrics = result['metrics']
            
            report += f"СЦЕНАРИЙ: {scenario_name.upper()}\n"
            report += "-" * 40 + "\n"
            
            # Configuration
            report += "Конфигурация:\n"
            report += f"  Множитель волатильности: {config.volatility_multiplier}x\n"
            report += f"  Геополитический риск: {config.geopolitical_risk_level:.1%}\n"
            report += f"  Частота отказов брокера: {config.broker_failure_rate:.1%}\n"
            report += f"  Задержка брокера: {config.broker_latency_ms}мс\n"
            report += f"  Одновременных пользователей: {config.concurrent_users}\n"
            
            # Performance metrics
            report += "\nПроизводительность:\n"
            report += f"  Среднее время отклика: {metrics.avg_response_time:.3f}с\n"
            report += f"  Максимальное время отклика: {metrics.max_response_time:.3f}с\n"
            report += f"  Запросов в секунду: {metrics.requests_per_second:.1f}\n"
            report += f"  Частота ошибок: {metrics.error_rate:.1f}%\n"
            
            # Trading metrics
            report += "\nТорговля:\n"
            report += f"  Всего сделок: {metrics.total_trades}\n"
            report += f"  Успешных сделок: {metrics.successful_trades}\n"
            report += f"  Успешность торговли: {metrics.trade_success_rate:.1f}%\n"
            
            # Portfolio metrics
            report += "\nПортфель:\n"
            report += f"  Начальная стоимость: {metrics.initial_portfolio_value:,.0f} ₽\n"
            report += f"  Конечная стоимость: {metrics.final_portfolio_value:,.0f} ₽\n"
            report += f"  Общая доходность: {metrics.total_return:.2f}%\n"
            report += f"  Максимальная просадка: {metrics.max_drawdown:.2f}%\n"
            
            # System metrics
            report += "\nСистема:\n"
            report += f"  Использование памяти: {metrics.memory_usage_mb:.1f} МБ\n"
            report += f"  Загрузка CPU: {metrics.cpu_usage_percent:.1f}%\n"
            
            report += "\n" + "=" * 60 + "\n\n"
        
        return report
    
    def generate_summary(self) -> str:
        """Generate summary of all stress tests"""
        if not self.test_results:
            return "Нет результатов стресс-тестирования для отчета.\n"
        
        summary = "СВОДКА СТРЕСС-ТЕСТИРОВАНИЯ\n"
        summary += "=" * 30 + "\n\n"
        
        # Overall statistics
        total_scenarios = len(self.test_results)
        passed_scenarios = sum(1 for result in self.test_results.values() 
                             if result['metrics'].error_rate < 10)  # Less than 10% error rate
        
        summary += f"Всего сценариев: {total_scenarios}\n"
        summary += f"Пройдено успешно: {passed_scenarios}\n"
        summary += f"Процент успеха: {(passed_scenarios / total_scenarios) * 100:.1f}%\n\n"
        
        # Best and worst performing scenarios
        if self.test_results:
            best_scenario = min(self.test_results.items(), 
                              key=lambda x: x[1]['metrics'].error_rate)
            worst_scenario = max(self.test_results.items(), 
                               key=lambda x: x[1]['metrics'].error_rate)
            
            summary += f"Лучший сценарий: {best_scenario[0]} ({best_scenario[1]['metrics'].error_rate:.1f}% ошибок)\n"
            summary += f"Худший сценарий: {worst_scenario[0]} ({worst_scenario[1]['metrics'].error_rate:.1f}% ошибок)\n\n"
        
        # Recommendations
        summary += "РЕКОМЕНДАЦИИ:\n"
        
        high_error_scenarios = [name for name, result in self.test_results.items() 
                              if result['metrics'].error_rate > 20]
        
        if high_error_scenarios:
            summary += f"- Требуется улучшение для сценариев: {', '.join(high_error_scenarios)}\n"
        
        high_latency_scenarios = [name for name, result in self.test_results.items() 
                                if result['metrics'].avg_response_time > 1.0]
        
        if high_latency_scenarios:
            summary += f"- Оптимизация производительности для: {', '.join(high_latency_scenarios)}\n"
        
        if not high_error_scenarios and not high_latency_scenarios:
            summary += "- Система показывает хорошую производительность во всех сценариях\n"
        
        return summary


if __name__ == "__main__":
    # Example usage
    from datetime import datetime
    
    reporter = StressTestReporter()
    
    # Add sample test results
    for scenario_name, config in STRESS_TEST_SCENARIOS.items():
        metrics = TestMetrics()
        metrics.total_requests = 1000
        metrics.successful_requests = 950
        metrics.failed_requests = 50
        metrics.avg_response_time = 0.2
        metrics.max_response_time = 1.5
        metrics.calculate_derived_metrics()
        
        reporter.add_test_result(scenario_name, config, metrics)
    
    # Generate reports
    print(reporter.generate_summary())
    print(reporter.generate_report())