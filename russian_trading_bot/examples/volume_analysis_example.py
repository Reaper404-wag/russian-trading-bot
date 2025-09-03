"""
Пример использования сервиса анализа объемов для российского рынка.
Демонстрирует различные возможности анализа объемов торгов на MOEX.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

from services.volume_analyzer import VolumeAnalyzer, VolumeProfile


def generate_sample_data():
    """Генерация примерных данных для демонстрации"""
    np.random.seed(42)
    
    # Генерируем 30 дней торговых данных
    days = 30
    base_price = 100.0
    base_volume = 1000000
    
    prices = []
    volumes = []
    high_prices = []
    low_prices = []
    
    current_price = base_price
    
    for day in range(days):
        # Симулируем дневные изменения цены
        price_change = np.random.normal(0, 2)  # Волатильность 2%
        current_price = max(current_price + price_change, 50)  # Минимальная цена 50
        
        # Генерируем high/low для дня
        daily_volatility = np.random.uniform(1, 3)
        high_price = current_price + daily_volatility
        low_price = current_price - daily_volatility
        
        # Генерируем объем с корреляцией к волатильности
        volume_multiplier = 1 + abs(price_change) / 10  # Больше объем при больших движениях
        daily_volume = int(base_volume * volume_multiplier * np.random.uniform(0.5, 2.0))
        
        prices.append(round(current_price, 2))
        high_prices.append(round(high_price, 2))
        low_prices.append(round(low_price, 2))
        volumes.append(daily_volume)
    
    return {
        'close': prices,
        'high': high_prices,
        'low': low_prices,
        'volume': volumes
    }


def demonstrate_volume_indicators():
    """Демонстрация расчета индикаторов объема"""
    print("=== ДЕМОНСТРАЦИЯ АНАЛИЗА ОБЪЕМОВ РОССИЙСКОГО РЫНКА ===\n")
    
    # Создаем анализатор
    analyzer = VolumeAnalyzer()
    
    # Генерируем тестовые данные
    market_data = generate_sample_data()
    
    print("1. БАЗОВЫЕ ИНДИКАТОРЫ ОБЪЕМА")
    print("-" * 40)
    
    # Рассчитываем все индикаторы объема
    indicators = analyzer.calculate_all_volume_indicators("SBER", market_data)
    
    print(f"Тикер: {indicators.symbol}")
    print(f"Время расчета: {indicators.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Средний объем (20 дней): {indicators.volume_sma_20:,.0f}")
    print(f"Отношение текущего объема к среднему: {indicators.volume_ratio:.2f}")
    print(f"VWAP: {indicators.vwap:.2f} ₽")
    print(f"On-Balance Volume: {indicators.obv:,.0f}")
    print(f"A/D Line: {indicators.ad_line:,.0f}")
    print(f"Chaikin Money Flow: {indicators.cmf:.4f}")
    print(f"Тренд объемов: {indicators.volume_trend}")
    print(f"Необычный объем обнаружен: {'Да' if indicators.unusual_volume_detected else 'Нет'}")
    
    if indicators.volume_profile:
        print(f"\nПрофиль объемов:")
        print(f"  Point of Control: {indicators.volume_profile['poc']:.2f} ₽")
        print(f"  Область стоимости: {indicators.volume_profile['value_area_low']:.2f} - {indicators.volume_profile['value_area_high']:.2f} ₽")
        print(f"  Общий объем: {indicators.volume_profile['total_volume']:,.0f}")
    
    print("\n2. ТОРГОВЫЕ СИГНАЛЫ НА ОСНОВЕ ОБЪЕМОВ")
    print("-" * 40)
    
    # Получаем торговые сигналы
    signals = analyzer.get_volume_signals(indicators)
    
    for signal_type, signal_value in signals.items():
        print(f"{signal_type.upper()}: {signal_value}")
    
    return analyzer, market_data, indicators


def demonstrate_volume_profile():
    """Демонстрация профиля объемов"""
    print("\n3. ДЕТАЛЬНЫЙ АНАЛИЗ ПРОФИЛЯ ОБЪЕМОВ")
    print("-" * 40)
    
    analyzer = VolumeAnalyzer()
    
    # Генерируем внутридневные данные
    np.random.seed(123)
    
    # Симулируем торговый день с почасовыми данными
    base_price = 150.0
    hourly_prices = []
    hourly_volumes = []
    
    # Основная сессия MOEX (10:00 - 18:45)
    for hour in range(10, 19):
        # Симулируем движение цены в течение дня
        if hour < 14:  # Утренняя активность
            price_change = np.random.normal(0, 1)
            volume_multiplier = np.random.uniform(1.2, 2.0)
        else:  # Дневная активность
            price_change = np.random.normal(0, 0.5)
            volume_multiplier = np.random.uniform(0.8, 1.5)
        
        base_price += price_change
        hourly_prices.append(round(base_price, 2))
        hourly_volumes.append(int(100000 * volume_multiplier))
    
    # Рассчитываем профиль объемов
    volume_profile = analyzer.calculate_volume_profile(hourly_prices, hourly_volumes)
    
    print(f"Анализ торгового дня:")
    print(f"Диапазон цен: {min(hourly_prices):.2f} - {max(hourly_prices):.2f} ₽")
    print(f"Общий объем: {volume_profile.total_volume:,.0f}")
    print(f"Point of Control (POC): {volume_profile.poc:.2f} ₽")
    print(f"Область стоимости: {volume_profile.value_area_low:.2f} - {volume_profile.value_area_high:.2f} ₽")
    
    # Находим уровни с наибольшим объемом
    max_volume_idx = volume_profile.volume_at_price.index(max(volume_profile.volume_at_price))
    print(f"Максимальный объем на уровне: {volume_profile.price_levels[max_volume_idx]:.2f} ₽")
    print(f"Объем на этом уровне: {max(volume_profile.volume_at_price):,.0f}")


def demonstrate_session_analysis():
    """Демонстрация анализа торговых сессий MOEX"""
    print("\n4. АНАЛИЗ ТОРГОВЫХ СЕССИЙ MOEX")
    print("-" * 40)
    
    analyzer = VolumeAnalyzer()
    
    # Симулируем полный торговый день MOEX
    # Основная сессия: 10:00-18:45, Вечерняя: 19:05-23:50
    session_hours = list(range(10, 19)) + list(range(19, 24))
    
    # Генерируем объемы с реалистичными паттернами
    np.random.seed(456)
    
    # Основная сессия - высокие объемы утром и в конце дня
    main_session_volumes = []
    for hour in range(10, 19):
        if hour in [10, 11, 17, 18]:  # Пики активности
            volume = np.random.randint(800000, 1200000)
        else:  # Обычная активность
            volume = np.random.randint(400000, 800000)
        main_session_volumes.append(volume)
    
    # Вечерняя сессия - более низкие объемы
    evening_session_volumes = []
    for hour in range(19, 24):
        volume = np.random.randint(100000, 300000)
        evening_session_volumes.append(volume)
    
    hourly_volumes = main_session_volumes + evening_session_volumes
    
    # Анализируем паттерны сессий
    session_analysis = analyzer.analyze_session_volume_pattern(hourly_volumes, session_hours)
    
    print("Анализ основной сессии (10:00-18:45):")
    main_session = session_analysis['main_session']
    print(f"  Общий объем: {main_session['total_volume']:,.0f}")
    print(f"  Средний часовой объем: {main_session['avg_volume']:,.0f}")
    print(f"  Пиковый часовой объем: {main_session['peak_hour_volume']:,.0f}")
    print(f"  Объем на открытии: {main_session['opening_volume']:,.0f}")
    print(f"  Объем на закрытии: {main_session['closing_volume']:,.0f}")
    
    print("\nАнализ вечерней сессии (19:05-23:50):")
    evening_session = session_analysis['evening_session']
    print(f"  Общий объем: {evening_session['total_volume']:,.0f}")
    print(f"  Средний часовой объем: {evening_session['avg_volume']:,.0f}")
    print(f"  Пиковый часовой объем: {evening_session['peak_hour_volume']:,.0f}")
    
    print("\nСравнение сессий:")
    comparison = session_analysis['session_comparison']
    print(f"  Соотношение основная/вечерняя: {comparison['main_to_evening_ratio']:.2f}")
    print(f"  Доминирующая сессия: {comparison['dominant_session']}")


def demonstrate_unusual_volume_detection():
    """Демонстрация обнаружения необычного объема"""
    print("\n5. ОБНАРУЖЕНИЕ НЕОБЫЧНОГО ОБЪЕМА")
    print("-" * 40)
    
    analyzer = VolumeAnalyzer()
    
    # Создаем исторические данные с нормальными объемами
    normal_volumes = [np.random.randint(800000, 1200000) for _ in range(20)]
    
    print("Исторические объемы (последние 5 дней):")
    for i, volume in enumerate(normal_volumes[-5:], 1):
        print(f"  День {i}: {volume:,.0f}")
    
    print(f"\nСредний объем: {np.mean(normal_volumes):,.0f}")
    
    # Тестируем различные объемы
    test_volumes = [
        (1000000, "Нормальный объем"),
        (2000000, "Повышенный объем (2x)"),
        (3000000, "Высокий объем (3x)"),
        (5000000, "Экстремальный объем (5x)")
    ]
    
    print("\nТестирование обнаружения необычного объема:")
    for volume, description in test_volumes:
        is_unusual = analyzer.detect_unusual_volume(volume, normal_volumes)
        volume_ratio = analyzer.calculate_volume_ratio(volume, normal_volumes)
        
        status = "🔴 НЕОБЫЧНЫЙ" if is_unusual else "🟢 НОРМАЛЬНЫЙ"
        print(f"  {description}: {volume:,.0f} (x{volume_ratio:.1f}) - {status}")
    
    print(f"\nПорог необычного объема для российского рынка: x{analyzer.unusual_volume_threshold * analyzer.russian_market_multiplier:.1f}")


def demonstrate_volume_trend_analysis():
    """Демонстрация анализа трендов объема"""
    print("\n6. АНАЛИЗ ТРЕНДОВ ОБЪЕМА")
    print("-" * 40)
    
    analyzer = VolumeAnalyzer()
    
    # Создаем различные паттерны объемов
    patterns = {
        "Растущий интерес": list(range(500000, 1500000, 50000)),
        "Снижающийся интерес": list(range(1500000, 500000, -50000)),
        "Стабильный интерес": [1000000 + np.random.randint(-50000, 50000) for _ in range(20)]
    }
    
    for pattern_name, volumes in patterns.items():
        trend = analyzer.analyze_volume_trend(volumes)
        avg_volume = np.mean(volumes)
        
        print(f"{pattern_name}:")
        print(f"  Средний объем: {avg_volume:,.0f}")
        print(f"  Определенный тренд: {trend}")
        print(f"  Последние 3 дня: {volumes[-3:]}")
        print()


def main():
    """Главная функция демонстрации"""
    try:
        # Основная демонстрация
        analyzer, market_data, indicators = demonstrate_volume_indicators()
        
        # Дополнительные демонстрации
        demonstrate_volume_profile()
        demonstrate_session_analysis()
        demonstrate_unusual_volume_detection()
        demonstrate_volume_trend_analysis()
        
        print("\n" + "="*60)
        print("ЗАКЛЮЧЕНИЕ")
        print("="*60)
        print("Сервис анализа объемов предоставляет комплексный анализ")
        print("торговой активности на российском рынке MOEX, включая:")
        print("• Технические индикаторы на основе объемов")
        print("• Профиль объемов и области стоимости")
        print("• Анализ торговых сессий MOEX")
        print("• Обнаружение необычной торговой активности")
        print("• Анализ трендов интереса к акциям")
        print("\nВсе алгоритмы адаптированы для особенностей российского рынка.")
        
    except Exception as e:
        print(f"Ошибка при выполнении демонстрации: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()