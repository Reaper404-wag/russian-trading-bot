"""
Example usage of the backtesting engine for Russian stock market strategies.

This example demonstrates how to:
1. Configure and run backtests
2. Analyze results
3. Compare different strategies
4. Generate reports
"""

import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal
import logging

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.backtesting_engine import BacktestingEngine, BacktestConfig
from services.ai_decision_engine import AIDecisionEngine, DecisionWeights
from models.trading import TradingSignal, OrderAction

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_sample_ai_engine():
    """Create a sample AI decision engine for backtesting"""
    weights = DecisionWeights(
        technical_weight=0.4,
        sentiment_weight=0.3,
        fundamental_weight=0.2,
        volume_weight=0.1,
        market_conditions_weight=0.1
    )
    return AIDecisionEngine(weights)


def run_basic_backtest():
    """Run a basic backtest example"""
    logger.info("=== Запуск базового бэктестинга ===")
    
    # Create AI engine
    ai_engine = create_sample_ai_engine()
    
    # Create backtesting engine
    backtest_engine = BacktestingEngine(ai_engine)
    
    # Configure backtest
    config = BacktestConfig(
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        initial_capital=Decimal('1000000'),  # 1M RUB
        commission_rate=0.0005,              # 0.05% commission
        slippage_rate=0.001,                 # 0.1% slippage
        max_position_size=0.1,               # 10% max position
        min_confidence=0.6,                  # 60% minimum confidence
        stop_loss_pct=0.05,                  # 5% stop loss
        take_profit_pct=0.15,                # 15% take profit
        benchmark_symbol="IMOEX"             # MOEX Russia Index
    )
    
    # Russian blue-chip stocks
    symbols = ['SBER', 'GAZP', 'LKOH', 'YNDX', 'MGNT', 'ROSN', 'NVTK', 'TCSG']
    
    try:
        # Run backtest
        logger.info(f"Запуск бэктестинга для {len(symbols)} акций...")
        results = backtest_engine.run_backtest(config, symbols, "Базовая стратегия")
        
        # Display results
        logger.info("Бэктестинг завершен!")
        print(backtest_engine.get_backtest_report(results))
        
        # Export results
        filename = backtest_engine.export_results(results)
        logger.info(f"Результаты экспортированы в файл: {filename}")
        
        return results
        
    except Exception as e:
        logger.error(f"Ошибка при выполнении бэктестинга: {e}")
        return None


def run_strategy_comparison():
    """Compare different trading strategies"""
    logger.info("=== Сравнение торговых стратегий ===")
    
    # Strategy 1: Conservative (high confidence threshold)
    conservative_config = BacktestConfig(
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        initial_capital=Decimal('1000000'),
        min_confidence=0.8,                  # High confidence threshold
        max_position_size=0.05,              # Small positions
        stop_loss_pct=0.03,                  # Tight stop loss
        take_profit_pct=0.10,                # Conservative take profit
        position_sizing_method="equal_weight"
    )
    
    # Strategy 2: Aggressive (lower confidence, larger positions)
    aggressive_config = BacktestConfig(
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        initial_capital=Decimal('1000000'),
        min_confidence=0.6,                  # Lower confidence threshold
        max_position_size=0.15,              # Larger positions
        stop_loss_pct=0.08,                  # Wider stop loss
        take_profit_pct=0.20,                # Higher take profit
        position_sizing_method="confidence_weighted"
    )
    
    # Strategy 3: Balanced
    balanced_config = BacktestConfig(
        start_date=datetime(2023, 1, 1),
        end_date=datetime(2023, 12, 31),
        initial_capital=Decimal('1000000'),
        min_confidence=0.7,                  # Medium confidence
        max_position_size=0.1,               # Medium positions
        stop_loss_pct=0.05,                  # Standard stop loss
        take_profit_pct=0.15,                # Standard take profit
        position_sizing_method="equal_weight"
    )
    
    symbols = ['SBER', 'GAZP', 'LKOH', 'YNDX', 'MGNT']
    strategies = [
        (conservative_config, "Консервативная стратегия"),
        (aggressive_config, "Агрессивная стратегия"),
        (balanced_config, "Сбалансированная стратегия")
    ]
    
    results_comparison = []
    
    for config, strategy_name in strategies:
        logger.info(f"Тестирование стратегии: {strategy_name}")
        
        # Create fresh AI engine for each strategy
        ai_engine = create_sample_ai_engine()
        backtest_engine = BacktestingEngine(ai_engine)
        
        try:
            results = backtest_engine.run_backtest(config, symbols, strategy_name)
            results_comparison.append((strategy_name, results))
            
            logger.info(f"{strategy_name} - Доходность: {results.total_return:.2%}, "
                       f"Шарп: {results.sharpe_ratio:.2f}, "
                       f"Макс. просадка: {results.max_drawdown:.2%}")
            
        except Exception as e:
            logger.error(f"Ошибка в стратегии {strategy_name}: {e}")
    
    # Print comparison summary
    print("\n" + "="*80)
    print("СРАВНЕНИЕ СТРАТЕГИЙ")
    print("="*80)
    print(f"{'Стратегия':<25} {'Доходность':<12} {'Шарп':<8} {'Макс.просадка':<15} {'Сделок':<8}")
    print("-"*80)
    
    for strategy_name, results in results_comparison:
        print(f"{strategy_name:<25} {results.total_return:>10.2%} "
              f"{results.sharpe_ratio:>7.2f} {results.max_drawdown:>13.2%} "
              f"{results.total_trades:>7}")
    
    return results_comparison


def run_sector_analysis():
    """Analyze performance by Russian market sectors"""
    logger.info("=== Анализ по секторам российского рынка ===")
    
    # Define sector groups
    sectors = {
        'Нефтегаз': ['GAZP', 'LKOH', 'ROSN', 'NVTK', 'SNGS'],
        'Банки': ['SBER', 'VTBR', 'TCSG'],
        'Металлы': ['GMKN', 'NLMK', 'MAGN', 'ALRS'],
        'Технологии': ['YNDX', 'OZON', 'VKCO'],
        'Ритейл': ['MGNT', 'FIVE', 'LNTA']
    }
    
    ai_engine = create_sample_ai_engine()
    
    sector_results = {}
    
    for sector_name, sector_symbols in sectors.items():
        logger.info(f"Анализ сектора: {sector_name}")
        
        config = BacktestConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            initial_capital=Decimal('1000000'),
            min_confidence=0.65,
            max_position_size=0.2,  # Higher concentration for sector focus
            stop_loss_pct=0.06,
            take_profit_pct=0.18
        )
        
        backtest_engine = BacktestingEngine(ai_engine)
        
        try:
            results = backtest_engine.run_backtest(config, sector_symbols, f"Стратегия {sector_name}")
            sector_results[sector_name] = results
            
            logger.info(f"{sector_name} - Доходность: {results.total_return:.2%}, "
                       f"Волатильность: {results.volatility:.2%}")
            
        except Exception as e:
            logger.error(f"Ошибка в секторе {sector_name}: {e}")
    
    # Print sector analysis
    print("\n" + "="*70)
    print("АНАЛИЗ ПО СЕКТОРАМ")
    print("="*70)
    print(f"{'Сектор':<15} {'Доходность':<12} {'Волатильность':<15} {'Шарп':<8} {'Сделок':<8}")
    print("-"*70)
    
    for sector_name, results in sector_results.items():
        print(f"{sector_name:<15} {results.total_return:>10.2%} "
              f"{results.volatility:>13.2%} {results.sharpe_ratio:>7.2f} "
              f"{results.total_trades:>7}")
    
    return sector_results


def run_risk_analysis():
    """Analyze risk management effectiveness"""
    logger.info("=== Анализ управления рисками ===")
    
    # Test different risk management settings
    risk_configs = [
        {
            'name': 'Низкий риск',
            'stop_loss_pct': 0.03,
            'take_profit_pct': 0.08,
            'max_position_size': 0.05,
            'max_drawdown_limit': 0.10
        },
        {
            'name': 'Средний риск',
            'stop_loss_pct': 0.05,
            'take_profit_pct': 0.15,
            'max_position_size': 0.10,
            'max_drawdown_limit': 0.15
        },
        {
            'name': 'Высокий риск',
            'stop_loss_pct': 0.08,
            'take_profit_pct': 0.25,
            'max_position_size': 0.20,
            'max_drawdown_limit': 0.25
        }
    ]
    
    symbols = ['SBER', 'GAZP', 'LKOH', 'YNDX']
    risk_results = []
    
    for risk_config in risk_configs:
        logger.info(f"Тестирование: {risk_config['name']}")
        
        config = BacktestConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            initial_capital=Decimal('1000000'),
            min_confidence=0.65,
            stop_loss_pct=risk_config['stop_loss_pct'],
            take_profit_pct=risk_config['take_profit_pct'],
            max_position_size=risk_config['max_position_size'],
            max_drawdown_limit=risk_config['max_drawdown_limit']
        )
        
        ai_engine = create_sample_ai_engine()
        backtest_engine = BacktestingEngine(ai_engine)
        
        try:
            results = backtest_engine.run_backtest(config, symbols, risk_config['name'])
            risk_results.append((risk_config['name'], results))
            
        except Exception as e:
            logger.error(f"Ошибка в конфигурации {risk_config['name']}: {e}")
    
    # Print risk analysis
    print("\n" + "="*90)
    print("АНАЛИЗ УПРАВЛЕНИЯ РИСКАМИ")
    print("="*90)
    print(f"{'Профиль риска':<15} {'Доходность':<12} {'Макс.просадка':<15} {'Шарп':<8} {'Сортино':<8}")
    print("-"*90)
    
    for risk_name, results in risk_results:
        print(f"{risk_name:<15} {results.total_return:>10.2%} "
              f"{results.max_drawdown:>13.2%} {results.sharpe_ratio:>7.2f} "
              f"{results.sortino_ratio:>7.2f}")
    
    return risk_results


def run_time_period_analysis():
    """Analyze performance across different time periods"""
    logger.info("=== Анализ по временным периодам ===")
    
    # Define different time periods
    periods = [
        ('Q1 2023', datetime(2023, 1, 1), datetime(2023, 3, 31)),
        ('Q2 2023', datetime(2023, 4, 1), datetime(2023, 6, 30)),
        ('Q3 2023', datetime(2023, 7, 1), datetime(2023, 9, 30)),
        ('Q4 2023', datetime(2023, 10, 1), datetime(2023, 12, 31)),
        ('H1 2023', datetime(2023, 1, 1), datetime(2023, 6, 30)),
        ('H2 2023', datetime(2023, 7, 1), datetime(2023, 12, 31)),
        ('Полный год', datetime(2023, 1, 1), datetime(2023, 12, 31))
    ]
    
    symbols = ['SBER', 'GAZP', 'LKOH', 'YNDX', 'MGNT']
    period_results = []
    
    for period_name, start_date, end_date in periods:
        logger.info(f"Анализ периода: {period_name}")
        
        config = BacktestConfig(
            start_date=start_date,
            end_date=end_date,
            initial_capital=Decimal('1000000'),
            min_confidence=0.65,
            max_position_size=0.1,
            stop_loss_pct=0.05,
            take_profit_pct=0.15
        )
        
        ai_engine = create_sample_ai_engine()
        backtest_engine = BacktestingEngine(ai_engine)
        
        try:
            results = backtest_engine.run_backtest(config, symbols, f"Стратегия {period_name}")
            period_results.append((period_name, results))
            
        except Exception as e:
            logger.error(f"Ошибка в периоде {period_name}: {e}")
    
    # Print period analysis
    print("\n" + "="*80)
    print("АНАЛИЗ ПО ВРЕМЕННЫМ ПЕРИОДАМ")
    print("="*80)
    print(f"{'Период':<12} {'Доходность':<12} {'Годовая':<12} {'Волатильность':<15} {'Сделок':<8}")
    print("-"*80)
    
    for period_name, results in period_results:
        print(f"{period_name:<12} {results.total_return:>10.2%} "
              f"{results.annual_return:>10.2%} {results.volatility:>13.2%} "
              f"{results.total_trades:>7}")
    
    return period_results


def main():
    """Main function to run all backtesting examples"""
    print("СИСТЕМА БЭКТЕСТИНГА ДЛЯ РОССИЙСКОГО ФОНДОВОГО РЫНКА")
    print("="*60)
    
    try:
        # 1. Basic backtest
        basic_results = run_basic_backtest()
        
        # 2. Strategy comparison
        strategy_results = run_strategy_comparison()
        
        # 3. Sector analysis
        sector_results = run_sector_analysis()
        
        # 4. Risk analysis
        risk_results = run_risk_analysis()
        
        # 5. Time period analysis
        period_results = run_time_period_analysis()
        
        print("\n" + "="*60)
        print("ВСЕ АНАЛИЗЫ ЗАВЕРШЕНЫ УСПЕШНО!")
        print("="*60)
        
        # Summary recommendations
        print("\nРЕКОМЕНДации НА ОСНОВЕ АНАЛИЗА:")
        print("- Используйте сбалансированный подход к управлению рисками")
        print("- Диверсифицируйте портфель по секторам российского рынка")
        print("- Учитывайте сезонность и макроэкономические факторы")
        print("- Регулярно пересматривайте параметры стратегии")
        print("- Мониторьте геополитические риски для российского рынка")
        
    except Exception as e:
        logger.error(f"Ошибка в главной функции: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)