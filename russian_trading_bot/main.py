#!/usr/bin/env python3
"""
Russian Trading Bot - Main Application Entry Point
Главная точка входа для системы торговли на российском рынке
"""

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from russian_trading_bot.config.settings import load_settings
from russian_trading_bot.database.migrations import run_migrations
from russian_trading_bot.services.market_monitor import MarketMonitor
from russian_trading_bot.services.news_aggregator import NewsAggregator
from russian_trading_bot.services.ai_decision_engine import AIDecisionEngine
from russian_trading_bot.services.risk_manager import RiskManager
from russian_trading_bot.services.portfolio_manager import PortfolioManager
from russian_trading_bot.services.notification_service import NotificationService
from russian_trading_bot.infrastructure.maintenance.maintenance_orchestrator import RussianTradingMaintenanceOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/trading_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RussianTradingBot:
    """Главный класс торгового бота для российского рынка"""
    
    def __init__(self):
        self.settings = None
        self.market_monitor = None
        self.news_aggregator = None
        self.ai_engine = None
        self.risk_manager = None
        self.portfolio_manager = None
        self.notification_service = None
        self.maintenance_orchestrator = None
        self.running = False
        
    async def initialize(self):
        """Инициализация всех компонентов системы"""
        logger.info("🚀 Инициализация Russian Trading Bot...")
        
        try:
            # Load settings
            self.settings = load_settings()
            logger.info("✅ Настройки загружены")
            
            # Run database migrations
            await run_migrations()
            logger.info("✅ Миграции базы данных выполнены")
            
            # Initialize core services
            self.market_monitor = MarketMonitor(self.settings)
            self.news_aggregator = NewsAggregator(self.settings)
            self.ai_engine = AIDecisionEngine(self.settings)
            self.risk_manager = RiskManager(self.settings)
            self.portfolio_manager = PortfolioManager(self.settings)
            self.notification_service = NotificationService(self.settings)
            
            # Initialize maintenance system
            self.maintenance_orchestrator = RussianTradingMaintenanceOrchestrator()
            await self.maintenance_orchestrator.__aenter__()
            
            logger.info("✅ Все компоненты инициализированы")
            
            # Send startup notification
            await self.notification_service.send_notification(
                "🇷🇺 Russian Trading Bot запущен",
                f"Система торговли на российском рынке успешно запущена в {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
                "info"
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации: {e}")
            raise
            
    async def start_trading(self):
        """Запуск основного торгового цикла"""
        logger.info("📈 Запуск торгового цикла...")
        self.running = True
        
        # Start maintenance monitoring
        maintenance_task = asyncio.create_task(
            self.maintenance_orchestrator.start_monitoring()
        )
        
        # Main trading loop
        while self.running:
            try:
                # 1. Monitor market conditions
                market_data = await self.market_monitor.get_market_snapshot()
                
                # 2. Analyze news sentiment
                news_sentiment = await self.news_aggregator.get_sentiment_analysis()
                
                # 3. Make AI-powered trading decisions
                trading_signals = await self.ai_engine.generate_signals(
                    market_data, news_sentiment
                )
                
                # 4. Apply risk management
                filtered_signals = await self.risk_manager.filter_signals(trading_signals)
                
                # 5. Execute trades through portfolio manager
                if filtered_signals:
                    await self.portfolio_manager.execute_trades(filtered_signals)
                
                # 6. Log activity
                logger.info(f"Торговый цикл завершен: {len(filtered_signals)} сигналов обработано")
                
                # Wait before next cycle (5 minutes)
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"Ошибка в торговом цикле: {e}")
                await self.notification_service.send_notification(
                    "⚠️ Ошибка в торговом цикле",
                    f"Произошла ошибка: {str(e)}",
                    "error"
                )
                await asyncio.sleep(60)  # Wait 1 minute before retry
                
        # Cleanup
        maintenance_task.cancel()
        
    async def stop(self):
        """Остановка торгового бота"""
        logger.info("🛑 Остановка Russian Trading Bot...")
        self.running = False
        
        # Send shutdown notification
        if self.notification_service:
            await self.notification_service.send_notification(
                "🔴 Russian Trading Bot остановлен",
                f"Система торговли остановлена в {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
                "warning"
            )
        
        # Cleanup maintenance orchestrator
        if self.maintenance_orchestrator:
            await self.maintenance_orchestrator.__aexit__(None, None, None)
            
        logger.info("✅ Russian Trading Bot остановлен")
        
    async def run_health_check(self):
        """Проверка состояния системы"""
        logger.info("🏥 Проверка состояния системы...")
        
        health_status = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'components': {}
        }
        
        # Check each component
        components = [
            ('market_monitor', self.market_monitor),
            ('news_aggregator', self.news_aggregator),
            ('ai_engine', self.ai_engine),
            ('risk_manager', self.risk_manager),
            ('portfolio_manager', self.portfolio_manager),
            ('notification_service', self.notification_service)
        ]
        
        for name, component in components:
            try:
                if hasattr(component, 'health_check'):
                    status = await component.health_check()
                else:
                    status = 'healthy' if component else 'unhealthy'
                health_status['components'][name] = status
                logger.info(f"  {name}: {status}")
            except Exception as e:
                health_status['components'][name] = f'error: {e}'
                logger.error(f"  {name}: error - {e}")
                
        # Overall status
        unhealthy_count = sum(1 for status in health_status['components'].values() 
                            if 'error' in str(status) or status == 'unhealthy')
        
        if unhealthy_count == 0:
            health_status['overall'] = 'healthy'
        elif unhealthy_count < len(components) / 2:
            health_status['overall'] = 'degraded'
        else:
            health_status['overall'] = 'unhealthy'
            
        logger.info(f"Общее состояние системы: {health_status['overall']}")
        return health_status

async def main():
    """Главная функция приложения"""
    bot = RussianTradingBot()
    
    try:
        # Initialize the bot
        await bot.initialize()
        
        # Run health check
        health_status = await bot.run_health_check()
        
        if health_status['overall'] in ['healthy', 'degraded']:
            # Start trading
            await bot.start_trading()
        else:
            logger.error("❌ Система не готова к торговле. Проверьте состояние компонентов.")
            
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки...")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        await bot.stop()

if __name__ == "__main__":
    # Set up Russian locale
    os.environ.setdefault('LANG', 'ru_RU.UTF-8')
    os.environ.setdefault('TZ', 'Europe/Moscow')
    
    # Run the bot
    asyncio.run(main())