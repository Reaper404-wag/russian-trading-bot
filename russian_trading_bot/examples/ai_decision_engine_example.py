"""
Example demonstrating the AI Decision Engine for Russian Stock Market

This example shows how to use the AI decision engine, trading strategies,
and reasoning engine together to generate comprehensive trading decisions
with Russian language explanations.
"""

import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from russian_trading_bot.models.trading import TradingSignal, OrderAction
from russian_trading_bot.models.market_data import RussianStock, MarketData
from russian_trading_bot.models.news_data import NewsSentiment
from russian_trading_bot.services.technical_analyzer import TechnicalIndicators
from russian_trading_bot.services.ai_decision_engine import (
    AIDecisionEngine, MarketConditions, DecisionWeights
)
from russian_trading_bot.services.trading_strategies import StrategyManager
from russian_trading_bot.services.reasoning_engine import (
    RussianReasoningEngine, ExplanationLevel
)


def create_sample_data():
    """Create sample data for demonstration"""
    
    # Sample Russian stock
    stock = RussianStock(
        symbol="SBER",
        name="Сбербанк",
        sector="BANKING",
        currency="RUB"
    )
    
    # Current market data
    market_data = MarketData(
        symbol="SBER",
        timestamp=datetime.now(),
        price=Decimal("250.50"),
        volume=1800000,  # High volume
        bid=Decimal("250.40"),
        ask=Decimal("250.60"),
        currency="RUB"
    )
    
    # Historical data (simulating upward trend)
    historical_data = []
    base_price = 200.0
    for i in range(60):
        price = base_price + (i * 0.8) + (i % 5 - 2)  # Trend with noise
        historical_data.append(MarketData(
            symbol="SBER",
            timestamp=datetime.now() - timedelta(days=60-i),
            price=Decimal(str(max(price, 100.0))),
            volume=1000000 + (i * 5000),
            currency="RUB"
        ))
    
    # Technical indicators
    technical_indicators = TechnicalIndicators(
        symbol="SBER",
        timestamp=datetime.now(),
        rsi=35.0,  # Slightly oversold
        macd=1.8,
        macd_signal=1.5,  # Bullish MACD
        sma_20=248.0,
        sma_50=240.0,     # SMA20 > SMA50 (bullish)
        ema_12=249.0,
        ema_26=242.0,
        bollinger_upper=260.0,
        bollinger_middle=250.0,
        bollinger_lower=240.0,
        bollinger_width=8.0,
        atr=5.2,
        stochastic_k=40.0,
        stochastic_d=38.0
    )
    
    # News sentiments
    sentiments = [
        NewsSentiment(
            article_id="sber_news_1",
            overall_sentiment="POSITIVE",
            sentiment_score=0.6,
            confidence=0.8,
            positive_keywords=["рост", "прибыль", "дивиденды", "Сбербанк"],
            negative_keywords=[],
            neutral_keywords=["банк", "отчет", "квартал"],
            timestamp=datetime.now() - timedelta(hours=3)
        ),
        NewsSentiment(
            article_id="market_news_1",
            overall_sentiment="NEUTRAL",
            sentiment_score=0.1,
            confidence=0.6,
            positive_keywords=[],
            negative_keywords=[],
            neutral_keywords=["рынок", "торги", "MOEX"],
            timestamp=datetime.now() - timedelta(hours=1)
        )
    ]
    
    # Market conditions
    market_conditions = MarketConditions(
        market_volatility=0.25,      # Low volatility
        ruble_volatility=0.35,       # Moderate ruble volatility
        geopolitical_risk=0.3,       # Moderate geopolitical risk
        market_trend="BULLISH",      # Bullish market
        trading_volume_ratio=1.4     # Above average volume
    )
    
    return stock, market_data, historical_data, technical_indicators, sentiments, market_conditions


def demonstrate_ai_decision_engine():
    """Demonstrate the AI decision engine"""
    print("=== AI Decision Engine для российского рынка ===\n")
    
    # Create sample data
    stock, market_data, historical_data, technical_indicators, sentiments, market_conditions = create_sample_data()
    
    # Initialize AI decision engine
    print("1. Инициализация AI Decision Engine...")
    decision_engine = AIDecisionEngine()
    
    # Generate trading signal
    print("2. Генерация торгового сигнала...")
    signal = decision_engine.generate_trading_signal(
        symbol=stock.symbol,
        stock=stock,
        market_data=market_data,
        technical_indicators=technical_indicators,
        sentiments=sentiments,
        market_conditions=market_conditions,
        historical_volume=[data.volume for data in historical_data]
    )
    
    print(f"   Сигнал: {signal.action.value.upper()}")
    print(f"   Уверенность: {signal.confidence:.1%}")
    print(f"   Ожидаемая доходность: {signal.expected_return:.1%}")
    print(f"   Оценка риска: {signal.risk_score:.1%}")
    if signal.target_price:
        print(f"   Целевая цена: {signal.target_price:.2f} руб.")
    if signal.stop_loss:
        print(f"   Стоп-лосс: {signal.stop_loss:.2f} руб.")
    print()


def demonstrate_trading_strategies():
    """Demonstrate trading strategies"""
    print("=== Торговые стратегии для российского рынка ===\n")
    
    # Create sample data
    stock, market_data, historical_data, technical_indicators, sentiments, market_conditions = create_sample_data()
    
    # Initialize strategy manager
    print("1. Инициализация менеджера стратегий...")
    strategy_manager = StrategyManager()
    
    # Show available strategies
    performance = strategy_manager.get_strategy_performance()
    print("   Доступные стратегии:")
    for name, info in performance.items():
        print(f"   - {info['name']} (вес: {info['weight']:.1%})")
    print()
    
    # Generate combined signal
    print("2. Генерация комбинированного сигнала...")
    combined_signal = strategy_manager.generate_combined_signal(
        symbol=stock.symbol,
        stock=stock,
        market_data=market_data,
        technical_indicators=technical_indicators,
        historical_data=historical_data,
        sentiments=sentiments,
        market_conditions=market_conditions
    )
    
    print(f"   Комбинированный сигнал: {combined_signal.action.value.upper()}")
    print(f"   Уверенность: {combined_signal.confidence:.1%}")
    print(f"   Краткое обоснование: {combined_signal.reasoning[:100]}...")
    print()


def demonstrate_reasoning_engine():
    """Demonstrate the Russian reasoning engine"""
    print("=== Система объяснений на русском языке ===\n")
    
    # Create sample data
    stock, market_data, historical_data, technical_indicators, sentiments, market_conditions = create_sample_data()
    
    # Create a sample trading signal
    signal = TradingSignal(
        symbol="SBER",
        action=OrderAction.BUY,
        confidence=0.75,
        target_price=280.0,
        stop_loss=230.0,
        reasoning="Комплексный анализ указывает на покупку",
        timestamp=datetime.now(),
        expected_return=0.12,
        risk_score=0.25
    )
    
    # Initialize reasoning engine
    print("1. Инициализация системы объяснений...")
    reasoning_engine = RussianReasoningEngine()
    
    # Generate brief explanation
    print("2. Краткое объяснение:")
    brief_explanation = reasoning_engine.generate_comprehensive_explanation(
        signal=signal,
        stock=stock,
        technical_indicators=technical_indicators,
        sentiments=sentiments,
        market_conditions=market_conditions,
        factors=[],
        level=ExplanationLevel.BRIEF
    )
    print(brief_explanation[:500] + "...\n")
    
    # Generate detailed explanation
    print("3. Подробное объяснение:")
    detailed_explanation = reasoning_engine.generate_comprehensive_explanation(
        signal=signal,
        stock=stock,
        technical_indicators=technical_indicators,
        sentiments=sentiments,
        market_conditions=market_conditions,
        factors=[],
        level=ExplanationLevel.DETAILED
    )
    
    # Show first part of detailed explanation
    lines = detailed_explanation.split('\n')
    for line in lines[:20]:  # Show first 20 lines
        print(line)
    print("... (сокращено для демонстрации)")
    print()


def demonstrate_complete_workflow():
    """Demonstrate complete workflow from data to explanation"""
    print("=== Полный рабочий процесс ===\n")
    
    # Create sample data
    stock, market_data, historical_data, technical_indicators, sentiments, market_conditions = create_sample_data()
    
    print(f"Анализ акции: {stock.name} ({stock.symbol})")
    print(f"Текущая цена: {market_data.price} руб.")
    print(f"Объем торгов: {market_data.volume:,}")
    print(f"Сектор: {stock.sector}")
    print()
    
    # Step 1: AI Decision Engine
    print("Шаг 1: Анализ с помощью AI Decision Engine")
    decision_engine = AIDecisionEngine()
    ai_signal = decision_engine.generate_trading_signal(
        symbol=stock.symbol,
        stock=stock,
        market_data=market_data,
        technical_indicators=technical_indicators,
        sentiments=sentiments,
        market_conditions=market_conditions,
        historical_volume=[data.volume for data in historical_data]
    )
    print(f"AI рекомендация: {ai_signal.action.value.upper()} (уверенность: {ai_signal.confidence:.1%})")
    
    # Step 2: Trading Strategies
    print("\nШаг 2: Анализ торговых стратегий")
    strategy_manager = StrategyManager()
    strategy_signal = strategy_manager.generate_combined_signal(
        symbol=stock.symbol,
        stock=stock,
        market_data=market_data,
        technical_indicators=technical_indicators,
        historical_data=historical_data,
        sentiments=sentiments,
        market_conditions=market_conditions
    )
    print(f"Стратегии рекомендуют: {strategy_signal.action.value.upper()} (уверенность: {strategy_signal.confidence:.1%})")
    
    # Step 3: Generate explanation
    print("\nШаг 3: Генерация объяснения")
    reasoning_engine = RussianReasoningEngine()
    
    # Use the AI signal for explanation (it has more detailed information)
    explanation = reasoning_engine.generate_comprehensive_explanation(
        signal=ai_signal,
        stock=stock,
        technical_indicators=technical_indicators,
        sentiments=sentiments,
        market_conditions=market_conditions,
        factors=[],
        level=ExplanationLevel.DETAILED
    )
    
    # Show summary section
    lines = explanation.split('\n')
    summary_end = 0
    for i, line in enumerate(lines):
        if line.startswith('ТЕХНИЧЕСКИЙ АНАЛИЗ'):
            summary_end = i
            break
    
    print("ИТОГОВОЕ РЕШЕНИЕ:")
    for line in lines[:summary_end]:
        if line.strip():
            print(line)
    
    print("\n... (полное объяснение содержит технический анализ, анализ новостей, рыночные условия и рекомендации)")


if __name__ == "__main__":
    try:
        print("Демонстрация AI Decision Engine для российского фондового рынка\n")
        print("=" * 60)
        
        # Run demonstrations
        demonstrate_ai_decision_engine()
        print("\n" + "=" * 60)
        
        demonstrate_trading_strategies()
        print("\n" + "=" * 60)
        
        demonstrate_reasoning_engine()
        print("\n" + "=" * 60)
        
        demonstrate_complete_workflow()
        
        print("\n" + "=" * 60)
        print("Демонстрация завершена успешно!")
        
    except Exception as e:
        print(f"Ошибка при выполнении демонстрации: {e}")
        import traceback
        traceback.print_exc()