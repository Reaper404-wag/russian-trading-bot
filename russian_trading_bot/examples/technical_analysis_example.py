"""
Пример использования сервиса технического анализа для российского рынка.
Демонстрирует расчет технических индикаторов для российских акций.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from datetime import datetime, timedelta
from services.technical_analyzer import TechnicalAnalyzer, TechnicalIndicators


def generate_sample_market_data(symbol: str, days: int = 100) -> dict:
    """
    Генерирует примерные рыночные данные для демонстрации.
    
    Args:
        symbol: Тикер российской акции
        days: Количество дней данных
        
    Returns:
        Словарь с рыночными данными
    """
    print(f"📊 Генерация тестовых данных для {symbol}...")
    
    # Базовые цены для разных российских акций
    base_prices = {
        'SBER': 280.0,
        'GAZP': 180.0,
        'LKOH': 6500.0,
        'ROSN': 550.0,
        'NVTK': 1200.0,
        'YNDX': 2800.0,
        'MGNT': 6000.0,
        'GMKN': 18000.0
    }
    
    base_price = base_prices.get(symbol, 100.0)
    
    # Генерируем данные с учетом волатильности российского рынка
    closes = []
    highs = []
    lows = []
    
    current_price = base_price
    
    for i in range(days):
        # Имитируем волатильность российского рынка (обычно выше мирового)
        daily_change = np.random.normal(0, 0.03)  # 3% стандартное отклонение
        
        # Добавляем трендовую составляющую
        trend = 0.001 * np.sin(i / 20)  # Медленный тренд
        
        current_price *= (1 + daily_change + trend)
        current_price = max(current_price, base_price * 0.5)  # Минимальная цена
        
        # Генерируем high/low на основе внутридневной волатильности
        intraday_range = current_price * 0.02  # 2% внутридневной диапазон
        high = current_price + np.random.uniform(0, intraday_range)
        low = current_price - np.random.uniform(0, intraday_range)
        
        closes.append(round(current_price, 2))
        highs.append(round(high, 2))
        lows.append(round(low, 2))
    
    return {
        'close': closes,
        'high': highs,
        'low': lows,
        'symbol': symbol
    }


def demonstrate_technical_analysis():
    """Демонстрация технического анализа российских акций"""
    
    print("🇷🇺 Демонстрация технического анализа для российского рынка MOEX")
    print("=" * 70)
    
    # Создаем анализатор
    analyzer = TechnicalAnalyzer()
    
    # Список популярных российских акций
    russian_stocks = ['SBER', 'GAZP', 'LKOH', 'ROSN', 'NVTK']
    
    for stock in russian_stocks:
        print(f"\n📈 Анализ акции {stock}")
        print("-" * 40)
        
        # Генерируем тестовые данные
        market_data = generate_sample_market_data(stock, 60)
        
        # Рассчитываем все индикаторы
        indicators = analyzer.calculate_all_indicators(stock, market_data)
        
        # Выводим результаты
        print(f"Тикер: {indicators.symbol}")
        print(f"Время расчета: {indicators.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Основные индикаторы
        if indicators.rsi:
            print(f"RSI (14): {indicators.rsi:.2f}")
            if indicators.rsi < 25:
                print("  🟢 Сигнал: Перепроданность (возможна покупка)")
            elif indicators.rsi > 75:
                print("  🔴 Сигнал: Перекупленность (возможна продажа)")
            else:
                print("  🟡 Сигнал: Нейтральная зона")
        
        # MACD
        if indicators.macd and indicators.macd_signal:
            print(f"MACD: {indicators.macd:.4f}")
            print(f"MACD Signal: {indicators.macd_signal:.4f}")
            print(f"MACD Histogram: {indicators.macd_histogram:.4f}")
            
            if indicators.macd > indicators.macd_signal:
                print("  🟢 MACD: Бычий сигнал")
            else:
                print("  🔴 MACD: Медвежий сигнал")
        
        # Скользящие средние
        if indicators.sma_20 and indicators.sma_50:
            print(f"SMA(20): {indicators.sma_20:.2f} ₽")
            print(f"SMA(50): {indicators.sma_50:.2f} ₽")
            
            if indicators.sma_20 > indicators.sma_50:
                print("  🟢 Краткосрочный тренд: Восходящий")
            else:
                print("  🔴 Краткосрочный тренд: Нисходящий")
        
        # Полосы Боллинджера
        if all([indicators.bollinger_upper, indicators.bollinger_middle, indicators.bollinger_lower]):
            print(f"Bollinger Bands:")
            print(f"  Верхняя: {indicators.bollinger_upper:.2f} ₽")
            print(f"  Средняя: {indicators.bollinger_middle:.2f} ₽")
            print(f"  Нижняя: {indicators.bollinger_lower:.2f} ₽")
            print(f"  Ширина: {indicators.bollinger_width:.2f}%")
            
            current_price = market_data['close'][-1]
            if current_price <= indicators.bollinger_lower:
                print("  🟢 Цена у нижней полосы (возможна покупка)")
            elif current_price >= indicators.bollinger_upper:
                print("  🔴 Цена у верхней полосы (возможна продажа)")
            else:
                print("  🟡 Цена в нормальном диапазоне")
        
        # ATR (волатильность)
        if indicators.atr:
            print(f"ATR (14): {indicators.atr:.2f} ₽")
            current_price = market_data['close'][-1]
            volatility_percent = (indicators.atr / current_price) * 100
            print(f"Волатильность: {volatility_percent:.2f}%")
            
            if volatility_percent > 5:
                print("  ⚠️ Высокая волатильность")
            elif volatility_percent < 2:
                print("  😴 Низкая волатильность")
            else:
                print("  📊 Нормальная волатильность")
        
        # Стохастический осциллятор
        if indicators.stochastic_k and indicators.stochastic_d:
            print(f"Stochastic %K: {indicators.stochastic_k:.2f}")
            print(f"Stochastic %D: {indicators.stochastic_d:.2f}")
            
            if indicators.stochastic_k < 20:
                print("  🟢 Stochastic: Перепроданность")
            elif indicators.stochastic_k > 80:
                print("  🔴 Stochastic: Перекупленность")
            else:
                print("  🟡 Stochastic: Нормальная зона")
        
        # Общие торговые сигналы
        signals = analyzer.get_market_signal(indicators)
        print(f"\n🎯 Торговые сигналы:")
        for indicator_name, signal in signals.items():
            emoji = "🟢" if signal == "ПОКУПКА" else "🔴" if signal == "ПРОДАЖА" else "🟡"
            print(f"  {emoji} {indicator_name.upper()}: {signal}")
        
        # Подсчет общего настроения
        buy_signals = sum(1 for signal in signals.values() if signal == "ПОКУПКА")
        sell_signals = sum(1 for signal in signals.values() if signal == "ПРОДАЖА")
        
        print(f"\n📊 Общее настроение:")
        print(f"  Сигналы покупки: {buy_signals}")
        print(f"  Сигналы продажи: {sell_signals}")
        
        if buy_signals > sell_signals:
            print("  🟢 Общий сигнал: ПОКУПКА")
        elif sell_signals > buy_signals:
            print("  🔴 Общий сигнал: ПРОДАЖА")
        else:
            print("  🟡 Общий сигнал: НЕЙТРАЛЬНО")


def demonstrate_individual_indicators():
    """Демонстрация отдельных индикаторов"""
    
    print("\n\n🔍 Детальная демонстрация отдельных индикаторов")
    print("=" * 60)
    
    analyzer = TechnicalAnalyzer()
    
    # Генерируем тестовые данные для Сбербанка
    market_data = generate_sample_market_data('SBER', 100)
    prices = market_data['close']
    highs = market_data['high']
    lows = market_data['low']
    
    print(f"Тестовые данные: {len(prices)} дней торгов SBER")
    print(f"Диапазон цен: {min(prices):.2f} - {max(prices):.2f} ₽")
    print()
    
    # RSI
    print("📊 RSI (Relative Strength Index)")
    rsi = analyzer.calculate_rsi(prices)
    print(f"RSI(14): {rsi:.2f}")
    
    if rsi < 30:
        print("Интерпретация: Акция перепродана, возможен отскок")
    elif rsi > 70:
        print("Интерпретация: Акция перекуплена, возможна коррекция")
    else:
        print("Интерпретация: Нейтральная зона")
    print()
    
    # MACD
    print("📈 MACD (Moving Average Convergence Divergence)")
    macd, signal, histogram = analyzer.calculate_macd(prices)
    print(f"MACD Line: {macd:.4f}")
    print(f"Signal Line: {signal:.4f}")
    print(f"Histogram: {histogram:.4f}")
    
    if macd > signal:
        print("Интерпретация: Бычий сигнал, восходящий импульс")
    else:
        print("Интерпретация: Медвежий сигнал, нисходящий импульс")
    print()
    
    # Полосы Боллинджера
    print("📊 Bollinger Bands")
    bollinger = analyzer.calculate_bollinger_bands(prices)
    print(f"Верхняя полоса: {bollinger['bollinger_upper']:.2f} ₽")
    print(f"Средняя полоса: {bollinger['bollinger_middle']:.2f} ₽")
    print(f"Нижняя полоса: {bollinger['bollinger_lower']:.2f} ₽")
    print(f"Ширина полос: {bollinger['bollinger_width']:.2f}%")
    
    current_price = prices[-1]
    if current_price > bollinger['bollinger_upper']:
        print("Интерпретация: Цена выше верхней полосы, возможна коррекция")
    elif current_price < bollinger['bollinger_lower']:
        print("Интерпретация: Цена ниже нижней полосы, возможен отскок")
    else:
        print("Интерпретация: Цена в нормальном диапазоне")
    print()
    
    # ATR
    print("📊 ATR (Average True Range)")
    atr = analyzer.calculate_atr(highs, lows, prices)
    print(f"ATR(14): {atr:.2f} ₽")
    volatility_percent = (atr / current_price) * 100
    print(f"Волатильность: {volatility_percent:.2f}%")
    print("Интерпретация: Показывает среднюю волатильность за период")
    print()
    
    # Стохастический осциллятор
    print("📊 Stochastic Oscillator")
    stoch_k, stoch_d = analyzer.calculate_stochastic(highs, lows, prices)
    print(f"%K: {stoch_k:.2f}")
    print(f"%D: {stoch_d:.2f}")
    
    if stoch_k < 20:
        print("Интерпретация: Перепроданность, возможна покупка")
    elif stoch_k > 80:
        print("Интерпретация: Перекупленность, возможна продажа")
    else:
        print("Интерпретация: Нормальная зона")


def demonstrate_russian_market_adaptations():
    """Демонстрация адаптаций для российского рынка"""
    
    print("\n\n🇷🇺 Адаптации для российского рынка")
    print("=" * 50)
    
    analyzer = TechnicalAnalyzer()
    
    print("Особенности настроек для российского рынка:")
    print(f"• RSI пороги: 25/75 (вместо стандартных 30/70)")
    print(f"• Bollinger Bands: коэффициент волатильности {analyzer.volatility_adjustment}")
    print(f"• Адаптация к высокой волатильности российских акций")
    print(f"• Учет особенностей торговых сессий MOEX")
    print()
    
    # Демонстрация разных порогов RSI
    print("📊 Сравнение порогов RSI:")
    test_rsi_values = [20, 25, 30, 70, 75, 80]
    
    for rsi_val in test_rsi_values:
        indicators = TechnicalIndicators(
            symbol="TEST",
            timestamp=datetime.now(),
            rsi=rsi_val
        )
        
        signals = analyzer.get_market_signal(indicators)
        rsi_signal = signals.get('rsi', 'НЕТ ДАННЫХ')
        
        print(f"  RSI {rsi_val}: {rsi_signal}")
    
    print("\nВидно, что пороги 25/75 более подходят для волатильного российского рынка")


if __name__ == "__main__":
    try:
        demonstrate_technical_analysis()
        demonstrate_individual_indicators()
        demonstrate_russian_market_adaptations()
        
        print("\n\n✅ Демонстрация технического анализа завершена!")
        print("Все индикаторы адаптированы для российского рынка MOEX")
        
    except Exception as e:
        print(f"\n❌ Ошибка при выполнении демонстрации: {e}")
        import traceback
        traceback.print_exc()