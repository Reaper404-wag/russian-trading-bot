"""
Example usage of enhanced Russian market monitoring system
Demonstrates advanced market condition monitoring, sentiment analysis, and risk assessment
"""

import asyncio
import logging
from decimal import Decimal
from datetime import datetime, timedelta

from ..models.market_data import MOEXMarketData
from ..models.trading import Portfolio, Position
from ..models.notifications import NotificationPreferences, NotificationChannel
from ..services.enhanced_market_monitor import EnhancedMarketMonitor
from ..services.notification_service import NotificationService
from ..config.alert_config import AlertConfig


async def demonstrate_enhanced_monitoring():
    """Demonstrate enhanced market monitoring capabilities"""
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    logger.info("🚀 Демонстрация расширенного мониторинга российского рынка")
    
    # Create configuration
    config = AlertConfig(
        email_username="test@example.com",
        email_password="test_password",
        telegram_bot_token="test_token",
        sentiment_threshold=0.3,
        risk_escalation_threshold=0.7,
        regime_change_threshold=0.8
    )
    
    # Create notification service
    notification_service = NotificationService(config.to_dict())
    
    # Create enhanced market monitor
    monitor = EnhancedMarketMonitor(notification_service, config.to_dict())
    
    # Set up user preferences
    preferences = NotificationPreferences(
        user_id="demo_user",
        email="user@example.com",
        telegram_chat_id="123456789",
        market_alerts=[NotificationChannel.EMAIL, NotificationChannel.TELEGRAM]
    )
    
    logger.info("✅ Расширенный мониторинг инициализирован")
    
    # Create sample market data
    market_data = [
        MOEXMarketData(
            symbol="SBER",
            price=Decimal("245.50"),
            volume=2500000,  # High volume
            timestamp=datetime.now(),
            change_percent=0.08,  # 8% increase
            previous_close=Decimal("227.31")
        ),
        MOEXMarketData(
            symbol="GAZP",
            price=Decimal("175.25"),
            volume=1800000,
            timestamp=datetime.now(),
            change_percent=-0.06,  # 6% decrease
            previous_close=Decimal("186.44")
        ),
        MOEXMarketData(
            symbol="LKOH",
            price=Decimal("6420.00"),
            volume=800000,
            timestamp=datetime.now(),
            change_percent=0.03,  # 3% increase
            previous_close=Decimal("6233.01")
        ),
        MOEXMarketData(
            symbol="ROSN",
            price=Decimal("485.60"),
            volume=1200000,
            timestamp=datetime.now(),
            change_percent=-0.02,  # 2% decrease
            previous_close=Decimal("495.51")
        )
    ]
    
    # Sample news data
    news_data = [
        {
            'title': 'Сбербанк показал рекордную прибыль за квартал',
            'source': 'rbc.ru',
            'timestamp': datetime.now()
        },
        {
            'title': 'Новые санкции могут затронуть энергетический сектор',
            'source': 'vedomosti.ru',
            'timestamp': datetime.now()
        },
        {
            'title': 'ЦБ РФ сохранил ключевую ставку на уровне 16%',
            'source': 'kommersant.ru',
            'timestamp': datetime.now()
        }
    ]
    
    logger.info("\n📊 Анализ рыночного настроения...")
    
    # Monitor market sentiment
    sentiment = await monitor.monitor_market_sentiment(market_data, news_data)
    
    logger.info(f"  Общее настроение: {sentiment.overall_sentiment}")
    logger.info(f"  Оценка настроения: {sentiment.sentiment_score:.3f}")
    logger.info(f"  Уверенность: {sentiment.confidence:.1%}")
    logger.info(f"  Ключевые факторы: {', '.join(sentiment.key_factors)}")
    
    if sentiment.sector_sentiments:
        logger.info("  Настроение по секторам:")
        for sector, score in sentiment.sector_sentiments.items():
            direction = "📈" if score > 0 else "📉" if score < 0 else "➡️"
            logger.info(f"    {sector}: {direction} {score:.1%}")
    
    logger.info("\n⚠️ Комплексная оценка рисков...")
    
    # Create sample portfolio for risk assessment
    portfolio = Portfolio(
        positions={
            "SBER": Position(
                symbol="SBER",
                quantity=200,
                average_price=Decimal("230.00"),
                current_price=Decimal("245.50"),
                market_value=Decimal("49100.00"),
                unrealized_pnl=Decimal("3100.00")
            ),
            "GAZP": Position(
                symbol="GAZP",
                quantity=150,
                average_price=Decimal("185.00"),
                current_price=Decimal("175.25"),
                market_value=Decimal("26287.50"),
                unrealized_pnl=Decimal("-1462.50")
            )
        },
        cash_balance=Decimal("100000.00"),
        total_value=Decimal("175387.50"),
        total_pnl=Decimal("1637.50")
    )
    
    # Assess comprehensive risk
    risk_assessment = await monitor.assess_comprehensive_risk(market_data, portfolio)
    
    logger.info(f"  Общий уровень риска: {risk_assessment.overall_risk_level}")
    logger.info(f"  Оценка риска: {risk_assessment.risk_score:.1%}")
    logger.info(f"  Волатильность: {risk_assessment.volatility_risk:.1%}")
    logger.info(f"  Геополитика: {risk_assessment.geopolitical_risk:.1%}")
    logger.info(f"  Ликвидность: {risk_assessment.liquidity_risk:.1%}")
    logger.info(f"  Валютный риск: {risk_assessment.currency_risk:.1%}")
    
    if risk_assessment.recommendations:
        logger.info("  Рекомендации:")
        for rec in risk_assessment.recommendations:
            logger.info(f"    • {rec}")
    
    logger.info("\n🔄 Детекция смены режимов рынка...")
    
    # Detect market regime changes
    regime_change = await monitor.detect_market_regime_changes(market_data)
    
    if regime_change:
        logger.info(f"  Обнаружена смена режима!")
        logger.info(f"  Переход: {regime_change.previous_regime} → {regime_change.current_regime}")
        logger.info(f"  Уверенность: {regime_change.confidence:.1%}")
        logger.info(f"  Ключевые индикаторы: {', '.join(regime_change.key_indicators)}")
        if regime_change.expected_duration:
            logger.info(f"  Ожидаемая продолжительность: {regime_change.expected_duration}")
    else:
        logger.info("  Режим рынка стабилен")
    
    logger.info("\n🏛️ Мониторинг экономических индикаторов...")
    
    # Monitor Russian economic indicators
    economic_indicators = await monitor.monitor_russian_economic_indicators()
    
    if economic_indicators:
        logger.info(f"  Курс RUB/USD: {economic_indicators.get('rub_usd_rate', 'N/A')}")
        logger.info(f"  Волатильность рубля: {economic_indicators.get('rub_volatility', 0):.1%}")
        logger.info(f"  Цена нефти: ${economic_indicators.get('oil_price', 'N/A')}")
        logger.info(f"  Изменение цены нефти: {economic_indicators.get('oil_change', 0):.1%}")
        logger.info(f"  Ключевая ставка ЦБ: {economic_indicators.get('cbr_rate', 'N/A')}%")
        logger.info(f"  Тренд ставки: {economic_indicators.get('rate_trend', 'N/A')}")
        logger.info(f"  Индекс экономического стресса: {economic_indicators.get('economic_stress_index', 0):.1%}")
    
    logger.info("\n🔔 Отправка расширенных уведомлений...")
    
    # Send enhanced market alerts
    alerts = await monitor.send_enhanced_market_alerts(market_data, preferences)
    
    logger.info(f"  Отправлено уведомлений: {len(alerts)}")
    for alert in alerts:
        logger.info(f"    • {alert.alert_type}: {alert.market_condition}")
    
    logger.info("\n📋 Сводка по рынку...")
    
    # Get comprehensive market summary
    market_summary = monitor.get_enhanced_market_summary()
    
    logger.info(f"  Время анализа: {market_summary['timestamp']}")
    
    if market_summary['basic_condition']:
        condition = market_summary['basic_condition']
        logger.info(f"  Фаза рынка: {condition['market_phase']}")
        logger.info(f"  Индекс волатильности: {condition['volatility_index']:.1%}")
    
    if market_summary['sentiment']:
        sentiment_data = market_summary['sentiment']
        logger.info(f"  Настроение рынка: {sentiment_data['overall_sentiment']} ({sentiment_data['sentiment_score']:.3f})")
    
    if market_summary['risk_assessment']:
        risk_data = market_summary['risk_assessment']
        logger.info(f"  Уровень риска: {risk_data['overall_risk_level']} ({risk_data['risk_score']:.1%})")
    
    economic_data = market_summary['economic_indicators']
    if economic_data['economic_stress_index']:
        stress_level = "Высокий" if economic_data['economic_stress_index'] > 0.7 else "Средний" if economic_data['economic_stress_index'] > 0.3 else "Низкий"
        logger.info(f"  Экономический стресс: {stress_level} ({economic_data['economic_stress_index']:.1%})")
    
    logger.info("\n🎯 Демонстрация завершена!")


async def demonstrate_real_time_monitoring():
    """Demonstrate real-time monitoring capabilities"""
    
    logger = logging.getLogger(__name__)
    logger.info("🔄 Демонстрация мониторинга в реальном времени...")
    
    # Create enhanced monitor
    config = AlertConfig()
    notification_service = NotificationService(config.to_dict())
    monitor = EnhancedMarketMonitor(notification_service, config.to_dict())
    
    # Simulate real-time data updates
    for i in range(5):
        logger.info(f"\n📊 Обновление данных #{i+1}")
        
        # Generate sample market data with changing conditions
        volatility = 0.02 + (i * 0.01)  # Increasing volatility
        
        market_data = [
            MOEXMarketData(
                symbol="SBER",
                price=Decimal(str(250 + i * 5)),
                volume=1000000 + i * 200000,
                timestamp=datetime.now(),
                change_percent=volatility * (1 if i % 2 == 0 else -1),
                previous_close=Decimal(str(245 + i * 5))
            )
        ]
        
        # Update market data
        for data in market_data:
            monitor.update_market_data(data)
        
        # Monitor sentiment
        sentiment = await monitor.monitor_market_sentiment(market_data, [])
        logger.info(f"  Настроение: {sentiment.overall_sentiment} ({sentiment.sentiment_score:.3f})")
        
        # Assess risk
        risk = await monitor.assess_comprehensive_risk(market_data)
        logger.info(f"  Риск: {risk.overall_risk_level} ({risk.risk_score:.1%})")
        
        # Check for regime changes
        regime_change = await monitor.detect_market_regime_changes(market_data)
        if regime_change:
            logger.info(f"  🔄 Смена режима: {regime_change.previous_regime} → {regime_change.current_regime}")
        
        # Wait before next update
        await asyncio.sleep(2)
    
    logger.info("\n✅ Мониторинг в реальном времени завершен")


async def demonstrate_stress_testing():
    """Demonstrate stress testing scenarios"""
    
    logger = logging.getLogger(__name__)
    logger.info("🧪 Демонстрация стресс-тестирования...")
    
    config = AlertConfig()
    notification_service = NotificationService(config.to_dict())
    monitor = EnhancedMarketMonitor(notification_service, config.to_dict())
    
    # Scenario 1: Market crash
    logger.info("\n📉 Сценарий 1: Обвал рынка")
    
    crash_data = [
        MOEXMarketData(
            symbol="SBER",
            price=Decimal("180.00"),  # -25% crash
            volume=5000000,  # Very high volume
            timestamp=datetime.now(),
            change_percent=-0.25,
            previous_close=Decimal("240.00")
        ),
        MOEXMarketData(
            symbol="GAZP",
            price=Decimal("135.00"),  # -25% crash
            volume=4000000,
            timestamp=datetime.now(),
            change_percent=-0.25,
            previous_close=Decimal("180.00")
        )
    ]
    
    sentiment = await monitor.monitor_market_sentiment(crash_data, [])
    risk = await monitor.assess_comprehensive_risk(crash_data)
    
    logger.info(f"  Настроение: {sentiment.overall_sentiment} ({sentiment.sentiment_score:.3f})")
    logger.info(f"  Риск: {risk.overall_risk_level} ({risk.risk_score:.1%})")
    
    # Scenario 2: High volatility
    logger.info("\n⚡ Сценарий 2: Высокая волатильность")
    
    volatile_data = [
        MOEXMarketData(
            symbol="SBER",
            price=Decimal("260.00"),  # +8% swing
            volume=3000000,
            timestamp=datetime.now(),
            change_percent=0.08,
            previous_close=Decimal("240.00")
        )
    ]
    
    # Add historical volatility
    for j in range(20):
        price_change = 0.05 * (1 if j % 2 == 0 else -1)  # 5% swings
        monitor.price_history["SBER"] = monitor.price_history.get("SBER", [])
        monitor.price_history["SBER"].append((
            datetime.now() - timedelta(days=j),
            Decimal(str(240 + j * price_change * 10))
        ))
    
    sentiment = await monitor.monitor_market_sentiment(volatile_data, [])
    risk = await monitor.assess_comprehensive_risk(volatile_data)
    
    logger.info(f"  Настроение: {sentiment.overall_sentiment} ({sentiment.sentiment_score:.3f})")
    logger.info(f"  Риск: {risk.overall_risk_level} ({risk.risk_score:.1%})")
    
    # Scenario 3: Geopolitical crisis
    logger.info("\n🌍 Сценарий 3: Геополитический кризис")
    
    crisis_news = [
        {
            'title': 'Введены жесткие санкции против российских банков',
            'source': 'reuters.com',
            'timestamp': datetime.now()
        },
        {
            'title': 'Ограничения на экспорт российской нефти',
            'source': 'bloomberg.com',
            'timestamp': datetime.now()
        }
    ]
    
    # Simulate geopolitical events
    monitor.geopolitical_events.extend([
        {'type': 'SANCTIONS', 'severity': 'HIGH', 'timestamp': datetime.now()},
        {'type': 'TRADE_RESTRICTIONS', 'severity': 'HIGH', 'timestamp': datetime.now()}
    ])
    
    sentiment = await monitor.monitor_market_sentiment(crash_data, crisis_news)
    risk = await monitor.assess_comprehensive_risk(crash_data)
    
    logger.info(f"  Настроение: {sentiment.overall_sentiment} ({sentiment.sentiment_score:.3f})")
    logger.info(f"  Риск: {risk.overall_risk_level} ({risk.risk_score:.1%})")
    logger.info(f"  Геополитический риск: {risk.geopolitical_risk:.1%}")
    
    logger.info("\n✅ Стресс-тестирование завершено")


if __name__ == "__main__":
    # Run demonstrations
    asyncio.run(demonstrate_enhanced_monitoring())
    
    # Uncomment to run additional demonstrations
    # asyncio.run(demonstrate_real_time_monitoring())
    # asyncio.run(demonstrate_stress_testing())