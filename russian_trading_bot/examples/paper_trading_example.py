"""
Example usage of the paper trading engine for Russian stock market.

This example demonstrates how to:
1. Set up and configure paper trading
2. Connect to live market data
3. Run automated trading strategies
4. Monitor performance in real-time
5. Analyze results
"""

import sys
import os
import time
import threading
from datetime import datetime, timedelta
from decimal import Decimal
import logging

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.paper_trading_engine import PaperTradingEngine, PaperTradingConfig, PaperTradingStatus
from services.ai_decision_engine import AIDecisionEngine, DecisionWeights
from models.trading import TradingSignal, OrderAction
from models.market_data import MarketData

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MockMarketDataProvider:
    """Mock market data provider that simulates live MOEX data"""
    
    def __init__(self):
        self.base_prices = {
            'SBER': Decimal('250.0'),
            'GAZP': Decimal('180.0'),
            'LKOH': Decimal('6500.0'),
            'YNDX': Decimal('2800.0'),
            'MGNT': Decimal('5200.0'),
            'ROSN': Decimal('520.0'),
            'NVTK': Decimal('1100.0'),
            'TCSG': Decimal('3200.0')
        }
        self.price_history = {symbol: [] for symbol in self.base_prices}
        self.start_time = datetime.now()
    
    def get_market_data(self, symbols):
        """Simulate live market data with realistic price movements"""
        import random
        import numpy as np
        
        current_time = datetime.now()
        elapsed_minutes = (current_time - self.start_time).total_seconds() / 60
        
        market_data = {}
        
        for symbol in symbols:
            if symbol not in self.base_prices:
                continue
            
            base_price = self.base_prices[symbol]
            
            # Simulate intraday price movement with trend and noise
            trend = np.sin(elapsed_minutes * 0.1) * 0.02  # 2% trend component
            noise = random.gauss(0, 0.01)  # 1% random noise
            
            # Add some volatility spikes occasionally
            if random.random() < 0.05:  # 5% chance of volatility spike
                noise *= 3
            
            price_change = trend + noise
            current_price = base_price * (1 + price_change)
            
            # Ensure price doesn't go negative
            current_price = max(current_price, base_price * 0.5)
            
            # Update base price slowly to simulate longer-term trends
            self.base_prices[symbol] = self.base_prices[symbol] * (1 + price_change * 0.1)
            
            # Generate volume (higher volume during volatility)
            base_volume = 100000
            volume_multiplier = 1 + abs(price_change) * 10
            volume = int(base_volume * volume_multiplier * random.uniform(0.5, 2.0))
            
            market_data[symbol] = MarketData(
                symbol=symbol,
                timestamp=current_time,
                price=current_price,
                volume=volume,
                bid=current_price * Decimal('0.999'),
                ask=current_price * Decimal('1.001'),
                currency="RUB"
            )
            
            # Store price history
            self.price_history[symbol].append((current_time, current_price))
            
            # Keep only last 1000 price points
            if len(self.price_history[symbol]) > 1000:
                self.price_history[symbol] = self.price_history[symbol][-1000:]
        
        return market_data
    
    def get_price_history(self, symbol, minutes=60):
        """Get price history for a symbol"""
        if symbol not in self.price_history:
            return []
        
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        return [(t, p) for t, p in self.price_history[symbol] if t >= cutoff_time]


def create_ai_engine():
    """Create AI decision engine with Russian market configuration"""
    weights = DecisionWeights(
        technical_weight=0.4,
        sentiment_weight=0.2,  # Lower weight since we don't have real news
        fundamental_weight=0.2,
        volume_weight=0.1,
        market_conditions_weight=0.1
    )
    return AIDecisionEngine(weights)


def create_paper_trading_config():
    """Create paper trading configuration"""
    return PaperTradingConfig(
        initial_capital=Decimal('1000000'),  # 1M RUB
        commission_rate=0.0005,              # 0.05% commission (typical for Russian brokers)
        slippage_rate=0.001,                 # 0.1% slippage
        max_position_size=0.15,              # 15% max position size
        min_confidence=0.65,                 # 65% minimum confidence
        
        # Risk management
        stop_loss_pct=0.05,                  # 5% stop loss
        take_profit_pct=0.15,                # 15% take profit
        max_drawdown_limit=0.20,             # 20% max drawdown
        max_daily_trades=8,                  # Max 8 trades per day
        
        # Timing
        update_interval=10,                  # Update every 10 seconds
        market_hours_only=False,             # Allow trading anytime for demo
        
        # Strategy
        position_sizing_method="confidence_weighted",
        auto_execute=True,
        log_all_signals=True,
        daily_reports=True
    )


class PaperTradingMonitor:
    """Monitor and display paper trading performance"""
    
    def __init__(self, engine: PaperTradingEngine):
        self.engine = engine
        self.running = False
        self.monitor_thread = None
    
    def start_monitoring(self):
        """Start monitoring thread"""
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Performance monitoring started")
    
    def stop_monitoring(self):
        """Stop monitoring thread"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Performance monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        last_report_time = datetime.now()
        
        while self.running:
            try:
                current_time = datetime.now()
                
                # Generate report every 30 seconds
                if (current_time - last_report_time).total_seconds() >= 30:
                    self._generate_status_report()
                    last_report_time = current_time
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(10)
    
    def _generate_status_report(self):
        """Generate and display status report"""
        try:
            status = self.engine.get_current_status()
            
            print("\n" + "="*60)
            print("ОТЧЕТ О СОСТОЯНИИ PAPER TRADING")
            print("="*60)
            print(f"Статус: {status['status'].upper()}")
            print(f"Время работы: {status.get('duration_hours', 0):.1f} часов")
            print(f"Текущий капитал: {status.get('current_capital', 0):,.0f} ₽")
            print(f"Общая доходность: {status.get('total_return', 0):.2%}")
            print(f"P&L: {status.get('total_pnl', 0):,.0f} ₽")
            
            print(f"\nТорговая активность:")
            print(f"Всего сделок: {status.get('total_trades', 0)}")
            print(f"Сделок сегодня: {status.get('daily_trades', 0)}/{status.get('max_daily_trades', 0)}")
            print(f"Открытых позиций: {status.get('open_positions', 0)}")
            print(f"Процент прибыльных: {status.get('win_rate', 0):.1%}")
            
            # Show open positions
            positions = self.engine.get_open_positions()
            if positions:
                print(f"\nОткрытые позиции:")
                print(f"{'Символ':<8} {'Действие':<8} {'Кол-во':<8} {'Цена входа':<12} {'Текущая P&L':<12}")
                print("-" * 60)
                
                for pos in positions:
                    print(f"{pos['symbol']:<8} {pos['action']:<8} {pos['quantity']:<8} "
                          f"{pos['entry_price']:<12.2f} {pos['unrealized_pnl']:<12.0f}")
            
            # Show recent trades
            recent_trades = self.engine.get_trade_history(limit=5)
            if recent_trades:
                print(f"\nПоследние сделки:")
                print(f"{'Символ':<8} {'Действие':<8} {'P&L':<12} {'Причина закрытия':<15}")
                print("-" * 50)
                
                for trade in recent_trades[-5:]:
                    pnl = trade.get('realized_pnl', 0) or 0
                    exit_reason = trade.get('exit_reason', 'открыта')
                    print(f"{trade['symbol']:<8} {trade['action']:<8} {pnl:<12.0f} {exit_reason:<15}")
            
            print("="*60)
            
        except Exception as e:
            logger.error(f"Error generating status report: {e}")


def setup_callbacks(engine: PaperTradingEngine):
    """Set up event callbacks for the paper trading engine"""
    
    def on_trade_executed(trade):
        logger.info(f"🔄 СДЕЛКА ВЫПОЛНЕНА: {trade.action.value} {trade.quantity} {trade.symbol} "
                   f"по цене {trade.execution_price} ₽ (уверенность: {trade.signal_confidence:.1%})")
        print(f"💰 Новая позиция: {trade.symbol} - {trade.reasoning}")
    
    def on_position_closed(trade):
        pnl = trade.realized_pnl or 0
        pnl_emoji = "📈" if pnl > 0 else "📉"
        logger.info(f"{pnl_emoji} ПОЗИЦИЯ ЗАКРЫТА: {trade.symbol} P&L: {pnl:.0f} ₽ ({trade.exit_reason})")
        print(f"🔚 Закрыта позиция {trade.symbol}: {pnl:+.0f} ₽")
    
    def on_signal_generated(signal):
        logger.debug(f"📊 СИГНАЛ: {signal.action.value} {signal.symbol} "
                    f"(уверенность: {signal.confidence:.1%}) - {signal.reasoning[:50]}...")
    
    def on_error(error):
        logger.error(f"❌ ОШИБКА: {error}")
        print(f"⚠️  Ошибка в системе: {error}")
    
    engine.on_trade_executed = on_trade_executed
    engine.on_position_closed = on_position_closed
    engine.on_signal_generated = on_signal_generated
    engine.on_error = on_error


def run_basic_paper_trading():
    """Run basic paper trading example"""
    print("🚀 ЗАПУСК БАЗОВОГО PAPER TRADING")
    print("="*50)
    
    # Create components
    ai_engine = create_ai_engine()
    config = create_paper_trading_config()
    paper_engine = PaperTradingEngine(ai_engine, config)
    market_provider = MockMarketDataProvider()
    
    # Setup
    paper_engine.set_market_data_provider(market_provider.get_market_data)
    paper_engine.set_symbols(['SBER', 'GAZP', 'LKOH', 'YNDX', 'MGNT'])
    
    # Setup callbacks
    setup_callbacks(paper_engine)
    
    # Start monitoring
    monitor = PaperTradingMonitor(paper_engine)
    monitor.start_monitoring()
    
    try:
        # Start paper trading session
        session_id = paper_engine.start_session("Базовая стратегия")
        print(f"✅ Сессия запущена: {session_id}")
        print("📊 Мониторинг производительности активен")
        print("⏰ Система будет работать 2 минуты...")
        print("\nНажмите Ctrl+C для остановки\n")
        
        # Run for 2 minutes
        time.sleep(120)
        
    except KeyboardInterrupt:
        print("\n🛑 Получен сигнал остановки...")
    
    finally:
        # Stop everything
        monitor.stop_monitoring()
        paper_engine.stop_session()
        
        # Generate final report
        print("\n" + "="*60)
        print("ФИНАЛЬНЫЙ ОТЧЕТ")
        print("="*60)
        
        if paper_engine.current_session:
            summary = paper_engine.current_session.get_summary()
            
            print(f"Продолжительность: {summary['duration_hours']:.1f} часов")
            print(f"Начальный капитал: {summary['initial_capital']:,.0f} ₽")
            print(f"Конечный капитал: {summary['current_capital']:,.0f} ₽")
            print(f"Общая доходность: {summary['total_return']:.2%}")
            print(f"P&L: {summary['total_pnl']:+,.0f} ₽")
            print(f"Всего сделок: {summary['total_trades']}")
            print(f"Прибыльных сделок: {summary['winning_trades']}")
            print(f"Убыточных сделок: {summary['losing_trades']}")
            print(f"Процент прибыльных: {summary['win_rate']:.1%}")
            print(f"Сделок в час: {summary['trades_per_hour']:.1f}")
            
            # Export session data
            try:
                filename = paper_engine.export_session_data()
                print(f"\n💾 Данные сессии экспортированы: {filename}")
            except Exception as e:
                print(f"❌ Ошибка экспорта: {e}")
        
        print("\n🏁 Paper trading завершен!")


def run_strategy_comparison():
    """Compare different paper trading strategies"""
    print("🔬 СРАВНЕНИЕ СТРАТЕГИЙ PAPER TRADING")
    print("="*50)
    
    strategies = [
        {
            'name': 'Консервативная',
            'config': PaperTradingConfig(
                initial_capital=Decimal('1000000'),
                min_confidence=0.8,
                max_position_size=0.08,
                stop_loss_pct=0.03,
                take_profit_pct=0.10,
                max_daily_trades=5
            )
        },
        {
            'name': 'Агрессивная',
            'config': PaperTradingConfig(
                initial_capital=Decimal('1000000'),
                min_confidence=0.6,
                max_position_size=0.20,
                stop_loss_pct=0.08,
                take_profit_pct=0.25,
                max_daily_trades=15
            )
        },
        {
            'name': 'Сбалансированная',
            'config': PaperTradingConfig(
                initial_capital=Decimal('1000000'),
                min_confidence=0.7,
                max_position_size=0.12,
                stop_loss_pct=0.05,
                take_profit_pct=0.15,
                max_daily_trades=10
            )
        }
    ]
    
    results = []
    market_provider = MockMarketDataProvider()
    
    for strategy in strategies:
        print(f"\n🧪 Тестирование стратегии: {strategy['name']}")
        
        # Create engine for this strategy
        ai_engine = create_ai_engine()
        paper_engine = PaperTradingEngine(ai_engine, strategy['config'])
        
        # Setup
        paper_engine.set_market_data_provider(market_provider.get_market_data)
        paper_engine.set_symbols(['SBER', 'GAZP', 'LKOH', 'YNDX'])
        
        try:
            # Run strategy for 1 minute
            session_id = paper_engine.start_session(f"Стратегия {strategy['name']}")
            time.sleep(60)
            paper_engine.stop_session()
            
            # Collect results
            if paper_engine.current_session:
                summary = paper_engine.current_session.get_summary()
                results.append((strategy['name'], summary))
                
                print(f"✅ {strategy['name']}: {summary['total_return']:.2%} доходность, "
                      f"{summary['total_trades']} сделок")
            
        except Exception as e:
            print(f"❌ Ошибка в стратегии {strategy['name']}: {e}")
    
    # Display comparison
    print("\n" + "="*80)
    print("СРАВНЕНИЕ РЕЗУЛЬТАТОВ")
    print("="*80)
    print(f"{'Стратегия':<15} {'Доходность':<12} {'Сделок':<8} {'Прибыльных':<12} {'P&L (₽)':<12}")
    print("-"*80)
    
    for name, summary in results:
        print(f"{name:<15} {summary['total_return']:>10.2%} "
              f"{summary['total_trades']:>7} {summary['win_rate']:>10.1%} "
              f"{summary['total_pnl']:>10.0f}")
    
    print("="*80)


def run_risk_analysis():
    """Analyze risk management in paper trading"""
    print("⚠️  АНАЛИЗ УПРАВЛЕНИЯ РИСКАМИ")
    print("="*50)
    
    # Test different risk settings
    risk_configs = [
        ('Низкий риск', {'stop_loss_pct': 0.02, 'take_profit_pct': 0.06, 'max_position_size': 0.05}),
        ('Средний риск', {'stop_loss_pct': 0.05, 'take_profit_pct': 0.15, 'max_position_size': 0.10}),
        ('Высокий риск', {'stop_loss_pct': 0.10, 'take_profit_pct': 0.30, 'max_position_size': 0.25})
    ]
    
    market_provider = MockMarketDataProvider()
    results = []
    
    for risk_name, risk_params in risk_configs:
        print(f"\n🎯 Тестирование: {risk_name}")
        
        # Create config with risk parameters
        config = create_paper_trading_config()
        for param, value in risk_params.items():
            setattr(config, param, value)
        
        ai_engine = create_ai_engine()
        paper_engine = PaperTradingEngine(ai_engine, config)
        
        # Setup
        paper_engine.set_market_data_provider(market_provider.get_market_data)
        paper_engine.set_symbols(['SBER', 'GAZP', 'LKOH'])
        
        try:
            # Run for 1 minute
            session_id = paper_engine.start_session(f"Риск-тест {risk_name}")
            time.sleep(60)
            paper_engine.stop_session()
            
            if paper_engine.current_session:
                summary = paper_engine.current_session.get_summary()
                results.append((risk_name, summary))
                
                print(f"✅ {risk_name}: {summary['total_return']:.2%} доходность")
            
        except Exception as e:
            print(f"❌ Ошибка в {risk_name}: {e}")
    
    # Display risk analysis
    print("\n" + "="*70)
    print("АНАЛИЗ РИСКОВ")
    print("="*70)
    print(f"{'Профиль риска':<15} {'Доходность':<12} {'Сделок':<8} {'Прибыльных':<12}")
    print("-"*70)
    
    for name, summary in results:
        print(f"{name:<15} {summary['total_return']:>10.2%} "
              f"{summary['total_trades']:>7} {summary['win_rate']:>10.1%}")
    
    print("="*70)


def main():
    """Main function to run paper trading examples"""
    print("СИСТЕМА PAPER TRADING ДЛЯ РОССИЙСКОГО РЫНКА")
    print("="*60)
    
    try:
        # Ask user which example to run
        print("\nВыберите пример для запуска:")
        print("1. Базовый paper trading (2 минуты)")
        print("2. Сравнение стратегий")
        print("3. Анализ управления рисками")
        print("4. Все примеры")
        
        choice = input("\nВведите номер (1-4): ").strip()
        
        if choice == '1':
            run_basic_paper_trading()
        elif choice == '2':
            run_strategy_comparison()
        elif choice == '3':
            run_risk_analysis()
        elif choice == '4':
            run_basic_paper_trading()
            print("\n" + "="*60 + "\n")
            run_strategy_comparison()
            print("\n" + "="*60 + "\n")
            run_risk_analysis()
        else:
            print("❌ Неверный выбор. Запуск базового примера...")
            run_basic_paper_trading()
        
        print("\n🎉 ВСЕ ПРИМЕРЫ ЗАВЕРШЕНЫ УСПЕШНО!")
        print("\nРекомендации:")
        print("- Paper trading позволяет тестировать стратегии без риска")
        print("- Используйте разные настройки риска для разных рыночных условий")
        print("- Мониторьте производительность в реальном времени")
        print("- Анализируйте результаты для улучшения стратегий")
        
    except Exception as e:
        logger.error(f"Ошибка в главной функции: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)