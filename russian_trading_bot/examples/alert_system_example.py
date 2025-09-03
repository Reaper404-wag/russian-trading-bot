"""
Example usage of Russian market alert system
Demonstrates email, Telegram, and SMS notifications
"""

import asyncio
import logging
from decimal import Decimal
from datetime import datetime

from ..models.notifications import (
    NotificationPreferences, NotificationChannel, 
    TradingSignalAlert, PortfolioAlert, MarketAlert, GeopoliticalAlert
)
from ..models.trading import TradingSignal, Portfolio, Position
from ..models.market_data import MOEXMarketData
from ..services.alert_manager import AlertManager, create_alert_manager, send_test_alerts
from ..config.alert_config import AlertConfig


async def demonstrate_alert_system():
    """Demonstrate the Russian market alert system"""
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 Демонстрация системы оповещений российского торгового бота")
    
    # Create alert configuration
    config = AlertConfig(
        # Email configuration (replace with real credentials)
        email_smtp_server="smtp.gmail.com",
        email_smtp_port=587,
        email_username="your_email@gmail.com",
        email_password="your_app_password",
        email_from_address="russian_trading_bot@example.com",
        
        # Telegram configuration (replace with real bot token)
        telegram_bot_token="YOUR_TELEGRAM_BOT_TOKEN",
        
        # SMS configuration (replace with real API key)
        sms_api_key="YOUR_SMS_API_KEY",
        
        # Alert thresholds
        trading_signal_confidence_threshold=0.7,
        portfolio_loss_threshold=0.05,
        portfolio_gain_threshold=0.10,
        market_volatility_threshold=0.03
    )
    
    # Create alert manager
    alert_manager = AlertManager(config)
    
    # Set up user preferences
    user_preferences = NotificationPreferences(
        user_id="demo_user",
        email="user@example.com",
        telegram_chat_id="123456789",  # Replace with real chat ID
        phone_number="+79001234567",   # Replace with real phone number
        
        # Configure notification channels for different alert types
        trading_signals=[NotificationChannel.EMAIL, NotificationChannel.TELEGRAM],
        portfolio_alerts=[NotificationChannel.EMAIL, NotificationChannel.TELEGRAM, NotificationChannel.SMS],
        market_alerts=[NotificationChannel.EMAIL, NotificationChannel.TELEGRAM],
        geopolitical_alerts=[NotificationChannel.EMAIL, NotificationChannel.TELEGRAM],
        
        # Set thresholds
        min_trading_signal_confidence=0.75,
        portfolio_loss_threshold=0.05,
        portfolio_gain_threshold=0.10,
        market_volatility_threshold=0.03
    )
    
    # Register user preferences
    alert_manager.register_user_preferences("demo_user", user_preferences)
    
    logger.info("✅ Система оповещений инициализирована")
    
    # Demonstrate trading signal alerts
    logger.info("\n📈 Демонстрация торговых сигналов...")
    
    # Create sample trading signals
    buy_signal = TradingSignal(
        symbol="SBER",
        action="BUY",
        current_price=Decimal("250.50"),
        target_price=Decimal("280.00"),
        stop_loss=Decimal("230.00")
    )
    
    sell_signal = TradingSignal(
        symbol="GAZP",
        action="SELL",
        current_price=Decimal("180.75"),
        target_price=Decimal("160.00"),
        stop_loss=Decimal("190.00")
    )
    
    # Send trading signal alerts
    await alert_manager.send_trading_signal_alert(
        "demo_user", buy_signal, 0.85,
        "Технический анализ показывает восходящий тренд. RSI в зоне перепроданности, MACD дает сигнал на покупку."
    )
    
    await alert_manager.send_trading_signal_alert(
        "demo_user", sell_signal, 0.78,
        "Фундаментальный анализ указывает на переоцененность акций. Снижение цен на газ может негативно повлиять на прибыль."
    )
    
    logger.info("✅ Торговые сигналы отправлены")
    
    # Demonstrate portfolio alerts
    logger.info("\n💼 Демонстрация уведомлений по портфелю...")
    
    # Create sample portfolio
    portfolio = Portfolio(
        positions={
            "SBER": Position(
                symbol="SBER",
                quantity=100,
                average_price=Decimal("240.00"),
                current_price=Decimal("250.50"),
                market_value=Decimal("25050.00"),
                unrealized_pnl=Decimal("1050.00")
            ),
            "GAZP": Position(
                symbol="GAZP",
                quantity=50,
                average_price=Decimal("190.00"),
                current_price=Decimal("180.75"),
                market_value=Decimal("9037.50"),
                unrealized_pnl=Decimal("-462.50")
            )
        },
        cash_balance=Decimal("50000.00"),
        total_value=Decimal("84087.50"),
        total_pnl=Decimal("587.50")
    )
    
    # Send portfolio alerts
    await alert_manager.send_portfolio_alert(
        "demo_user", portfolio, "ОБНОВЛЕНИЕ_ПОРТФЕЛЯ"
    )
    
    # Simulate portfolio loss alert
    portfolio.total_pnl = Decimal("-5000.00")
    portfolio.total_value = Decimal("79087.50")
    
    await alert_manager.send_portfolio_alert(
        "demo_user", portfolio, "ПРЕВЫШЕН_ПОРОГ_УБЫТКОВ", Decimal("84000.00")
    )
    
    logger.info("✅ Уведомления по портфелю отправлены")
    
    # Demonstrate market alerts
    logger.info("\n📊 Демонстрация рыночных уведомлений...")
    
    # Create sample market data
    market_data = [
        MOEXMarketData(
            symbol="SBER",
            price=Decimal("250.50"),
            volume=1500000,
            timestamp=datetime.now(),
            change_percent=0.08,  # 8% increase
            previous_close=Decimal("232.00")
        ),
        MOEXMarketData(
            symbol="GAZP",
            price=Decimal("180.75"),
            volume=2000000,
            timestamp=datetime.now(),
            change_percent=-0.06,  # 6% decrease
            previous_close=Decimal("192.00")
        )
    ]
    
    # Monitor market conditions
    market_alerts = await alert_manager.monitor_and_alert_market_conditions(
        market_data, ["demo_user"]
    )
    
    logger.info(f"✅ Рыночные уведомления: {len(market_alerts.get('demo_user', []))} алертов")
    
    # Demonstrate geopolitical alerts
    logger.info("\n🌍 Демонстрация геополитических уведомлений...")
    
    geo_alerts = await alert_manager.monitor_and_alert_geopolitical_events(["demo_user"])
    
    logger.info(f"✅ Геополитические уведомления: {len(geo_alerts.get('demo_user', []))} алертов")
    
    # Demonstrate custom alerts
    logger.info("\n🔔 Демонстрация пользовательских уведомлений...")
    
    await alert_manager.send_custom_alert(
        "demo_user",
        "СИСТЕМА_ЗАПУЩЕНА",
        "Торговый бот запущен",
        "Система автоматической торговли успешно запущена и готова к работе. Мониторинг рынка активен."
    )
    
    await alert_manager.send_custom_alert(
        "demo_user",
        "ТЕХНИЧЕСКОЕ_ОБСЛУЖИВАНИЕ",
        "Плановое обслуживание",
        "Запланировано техническое обслуживание системы с 02:00 до 04:00 МСК. Торговля будет приостановлена."
    )
    
    logger.info("✅ Пользовательские уведомления отправлены")
    
    # Show alert statistics
    logger.info("\n📈 Статистика оповещений:")
    stats = alert_manager.get_alert_statistics()
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")
    
    # Perform health check
    logger.info("\n🏥 Проверка состояния системы:")
    health = await alert_manager.health_check()
    logger.info(f"  Статус: {health['status']}")
    logger.info(f"  Время: {health['timestamp']}")
    
    for service, status in health.get('services', {}).items():
        logger.info(f"  {service}: {status['status']}")
    
    logger.info("\n🎉 Демонстрация завершена!")


async def test_individual_notifications():
    """Test individual notification channels"""
    
    logger = logging.getLogger(__name__)
    logger.info("🧪 Тестирование отдельных каналов уведомлений...")
    
    # Create alert manager
    alert_manager = await create_alert_manager()
    
    # Set up test user
    test_preferences = NotificationPreferences(
        user_id="test_user",
        email="test@example.com",
        telegram_chat_id="123456789",
        phone_number="+79001234567"
    )
    
    alert_manager.register_user_preferences("test_user", test_preferences)
    
    # Send test alerts
    test_results = await send_test_alerts(alert_manager, "test_user")
    
    logger.info("📊 Результаты тестирования:")
    for alert_type, success in test_results.items():
        status = "✅ Успешно" if success else "❌ Ошибка"
        logger.info(f"  {alert_type}: {status}")


async def demonstrate_telegram_bot():
    """Demonstrate Telegram bot functionality"""
    
    logger = logging.getLogger(__name__)
    logger.info("🤖 Демонстрация Telegram бота...")
    
    from ..services.notification_service import TelegramBot
    from ..models.notifications import TradingSignalAlert, PortfolioAlert
    
    # Create Telegram bot (replace with real token)
    bot = TelegramBot("YOUR_TELEGRAM_BOT_TOKEN")
    
    # Test chat ID (replace with real chat ID)
    test_chat_id = "123456789"
    
    # Send simple message
    await bot.send_message(test_chat_id, "🔔 Тест системы уведомлений российского торгового бота")
    
    # Send formatted trading signal
    signal_data = TradingSignalAlert(
        symbol="SBER",
        action="BUY",
        confidence=0.85,
        current_price=Decimal("250.50"),
        target_price=Decimal("280.00"),
        stop_loss=Decimal("230.00"),
        reasoning="Технический анализ показывает сильный восходящий тренд"
    )
    
    await bot.send_trading_signal(test_chat_id, signal_data)
    
    # Send portfolio update
    portfolio_data = PortfolioAlert(
        alert_type="ОБНОВЛЕНИЕ_ПОРТФЕЛЯ",
        current_value=Decimal("1250000.00"),
        change_amount=Decimal("25000.00"),
        change_percent=0.02
    )
    
    await bot.send_portfolio_update(test_chat_id, portfolio_data)
    
    logger.info("✅ Telegram уведомления отправлены")


if __name__ == "__main__":
    # Run the demonstration
    asyncio.run(demonstrate_alert_system())
    
    # Uncomment to test individual components
    # asyncio.run(test_individual_notifications())
    # asyncio.run(demonstrate_telegram_bot())