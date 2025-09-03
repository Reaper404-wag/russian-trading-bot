"""
Тесты для сервиса технического анализа российского рынка.
"""

import pytest
import numpy as np
from datetime import datetime
from russian_trading_bot.services.technical_analyzer import TechnicalAnalyzer, TechnicalIndicators


class TestTechnicalAnalyzer:
    """Тесты для технического анализатора"""
    
    def setup_method(self):
        """Настройка для каждого теста"""
        self.analyzer = TechnicalAnalyzer()
        
        # Тестовые данные - имитация цен российской акции
        self.test_prices = [
            100.0, 102.0, 101.0, 103.0, 105.0, 104.0, 106.0, 108.0, 107.0, 109.0,
            111.0, 110.0, 112.0, 114.0, 113.0, 115.0, 117.0, 116.0, 118.0, 120.0,
            119.0, 121.0, 123.0, 122.0, 124.0, 126.0, 125.0, 127.0, 129.0, 128.0,
            130.0, 132.0, 131.0, 133.0, 135.0, 134.0, 136.0, 138.0, 137.0, 139.0,
            141.0, 140.0, 142.0, 144.0, 143.0, 145.0, 147.0, 146.0, 148.0, 150.0
        ]
        
        self.test_highs = [price + 2.0 for price in self.test_prices]
        self.test_lows = [price - 2.0 for price in self.test_prices]
    
    def test_calculate_rsi_basic(self):
        """Тест базового расчета RSI"""
        rsi = self.analyzer.calculate_rsi(self.test_prices)
        
        assert rsi is not None
        assert 0 <= rsi <= 100
        assert isinstance(rsi, float)
    
    def test_calculate_rsi_insufficient_data(self):
        """Тест RSI с недостаточным количеством данных"""
        short_prices = [100.0, 101.0, 102.0]
        rsi = self.analyzer.calculate_rsi(short_prices)
        
        assert rsi is None
    
    def test_calculate_rsi_trending_up(self):
        """Тест RSI для растущего тренда"""
        uptrend_prices = list(range(100, 150, 2))  # Постоянный рост
        rsi = self.analyzer.calculate_rsi(uptrend_prices)
        
        assert rsi > 50  # RSI должен быть выше 50 для растущего тренда
    
    def test_calculate_rsi_trending_down(self):
        """Тест RSI для падающего тренда"""
        downtrend_prices = list(range(150, 100, -2))  # Постоянное падение
        rsi = self.analyzer.calculate_rsi(downtrend_prices)
        
        assert rsi < 50  # RSI должен быть ниже 50 для падающего тренда
    
    def test_calculate_macd_basic(self):
        """Тест базового расчета MACD"""
        macd, signal, histogram = self.analyzer.calculate_macd(self.test_prices)
        
        assert macd is not None
        assert signal is not None
        assert histogram is not None
        assert isinstance(macd, float)
        assert isinstance(signal, float)
        assert isinstance(histogram, float)
    
    def test_calculate_macd_insufficient_data(self):
        """Тест MACD с недостаточным количеством данных"""
        short_prices = [100.0, 101.0, 102.0]
        macd, signal, histogram = self.analyzer.calculate_macd(short_prices)
        
        assert macd is None
        assert signal is None
        assert histogram is None
    
    def test_calculate_moving_averages(self):
        """Тест расчета скользящих средних"""
        ma_values = self.analyzer.calculate_moving_averages(self.test_prices)
        
        assert 'sma_20' in ma_values
        assert 'sma_50' in ma_values
        assert 'ema_12' in ma_values
        assert 'ema_26' in ma_values
        
        # SMA20 должна быть меньше последней цены в растущем тренде
        assert ma_values['sma_20'] < self.test_prices[-1]
        assert ma_values['sma_50'] < self.test_prices[-1]
    
    def test_calculate_moving_averages_insufficient_data(self):
        """Тест скользящих средних с недостаточными данными"""
        short_prices = [100.0, 101.0, 102.0]
        ma_values = self.analyzer.calculate_moving_averages(short_prices)
        
        assert ma_values == {}
    
    def test_calculate_bollinger_bands(self):
        """Тест расчета полос Боллинджера"""
        bollinger = self.analyzer.calculate_bollinger_bands(self.test_prices)
        
        assert 'bollinger_upper' in bollinger
        assert 'bollinger_middle' in bollinger
        assert 'bollinger_lower' in bollinger
        assert 'bollinger_width' in bollinger
        
        # Верхняя полоса должна быть выше средней, средняя выше нижней
        assert bollinger['bollinger_upper'] > bollinger['bollinger_middle']
        assert bollinger['bollinger_middle'] > bollinger['bollinger_lower']
        assert bollinger['bollinger_width'] > 0
    
    def test_calculate_bollinger_bands_custom_params(self):
        """Тест полос Боллинджера с кастомными параметрами"""
        bollinger = self.analyzer.calculate_bollinger_bands(
            self.test_prices, period=10, std_dev=1.5
        )
        
        assert bollinger is not None
        assert len(bollinger) == 4
    
    def test_calculate_atr(self):
        """Тест расчета Average True Range"""
        atr = self.analyzer.calculate_atr(
            self.test_highs, self.test_lows, self.test_prices
        )
        
        assert atr is not None
        assert atr > 0
        assert isinstance(atr, float)
    
    def test_calculate_atr_insufficient_data(self):
        """Тест ATR с недостаточными данными"""
        short_highs = [102.0, 103.0]
        short_lows = [98.0, 99.0]
        short_closes = [100.0, 101.0]
        
        atr = self.analyzer.calculate_atr(short_highs, short_lows, short_closes)
        assert atr is None
    
    def test_calculate_stochastic(self):
        """Тест расчета стохастического осциллятора"""
        k_percent, d_percent = self.analyzer.calculate_stochastic(
            self.test_highs, self.test_lows, self.test_prices
        )
        
        assert k_percent is not None
        assert d_percent is not None
        assert 0 <= k_percent <= 100
        assert 0 <= d_percent <= 100
    
    def test_calculate_stochastic_insufficient_data(self):
        """Тест стохастического осциллятора с недостаточными данными"""
        short_highs = [102.0, 103.0]
        short_lows = [98.0, 99.0]
        short_closes = [100.0, 101.0]
        
        k_percent, d_percent = self.analyzer.calculate_stochastic(
            short_highs, short_lows, short_closes
        )
        
        assert k_percent is None
        assert d_percent is None
    
    def test_calculate_all_indicators(self):
        """Тест расчета всех индикаторов"""
        market_data = {
            'close': self.test_prices,
            'high': self.test_highs,
            'low': self.test_lows
        }
        
        indicators = self.analyzer.calculate_all_indicators("SBER", market_data)
        
        assert isinstance(indicators, TechnicalIndicators)
        assert indicators.symbol == "SBER"
        assert indicators.rsi is not None
        assert indicators.macd is not None
        assert indicators.sma_20 is not None
        assert indicators.bollinger_upper is not None
        assert indicators.atr is not None
        assert indicators.stochastic_k is not None
    
    def test_calculate_all_indicators_empty_data(self):
        """Тест расчета индикаторов с пустыми данными"""
        market_data = {'close': [], 'high': [], 'low': []}
        
        indicators = self.analyzer.calculate_all_indicators("GAZP", market_data)
        
        assert isinstance(indicators, TechnicalIndicators)
        assert indicators.symbol == "GAZP"
        assert indicators.rsi is None
    
    def test_get_market_signal_buy_conditions(self):
        """Тест генерации сигналов покупки"""
        indicators = TechnicalIndicators(
            symbol="SBER",
            timestamp=datetime.now(),
            rsi=20.0,  # Перепроданность
            macd=1.0,
            macd_signal=0.5,  # MACD выше сигнальной линии
            bollinger_upper=150.0,
            bollinger_middle=125.0,
            bollinger_lower=100.0,  # Цена у нижней полосы
            stochastic_k=15.0  # Перепроданность
        )
        
        signals = self.analyzer.get_market_signal(indicators)
        
        assert signals['rsi'] == 'ПОКУПКА'
        assert signals['macd'] == 'ПОКУПКА'
        assert signals['stochastic'] == 'ПОКУПКА'
    
    def test_get_market_signal_sell_conditions(self):
        """Тест генерации сигналов продажи"""
        indicators = TechnicalIndicators(
            symbol="GAZP",
            timestamp=datetime.now(),
            rsi=80.0,  # Перекупленность
            macd=0.5,
            macd_signal=1.0,  # MACD ниже сигнальной линии
            bollinger_upper=150.0,  # Цена у верхней полосы
            bollinger_middle=150.0,
            bollinger_lower=100.0,
            stochastic_k=85.0  # Перекупленность
        )
        
        signals = self.analyzer.get_market_signal(indicators)
        
        assert signals['rsi'] == 'ПРОДАЖА'
        assert signals['macd'] == 'ПРОДАЖА'
        assert signals['stochastic'] == 'ПРОДАЖА'
    
    def test_get_market_signal_neutral_conditions(self):
        """Тест генерации нейтральных сигналов"""
        indicators = TechnicalIndicators(
            symbol="LKOH",
            timestamp=datetime.now(),
            rsi=50.0,  # Нейтральная зона
            macd=1.0,
            macd_signal=1.0,  # MACD равен сигнальной линии
            bollinger_upper=150.0,
            bollinger_middle=125.0,  # Цена в середине
            bollinger_lower=100.0,
            stochastic_k=50.0  # Нейтральная зона
        )
        
        signals = self.analyzer.get_market_signal(indicators)
        
        assert signals['rsi'] == 'НЕЙТРАЛЬНО'
        assert signals['bollinger'] == 'НЕЙТРАЛЬНО'
        assert signals['stochastic'] == 'НЕЙТРАЛЬНО'
    
    def test_russian_market_volatility_adjustment(self):
        """Тест адаптации для российской волатильности"""
        # Создаем данные с высокой волатильностью (типично для российского рынка)
        volatile_prices = []
        base_price = 100.0
        for i in range(50):
            # Имитируем высокую волатильность российского рынка
            change = np.random.normal(0, 5)  # Высокое стандартное отклонение
            base_price += change
            volatile_prices.append(max(base_price, 50))  # Минимальная цена 50
        
        bollinger = self.analyzer.calculate_bollinger_bands(volatile_prices)
        
        # Проверяем, что адаптация для волатильности работает
        assert bollinger['bollinger_width'] > 0
        band_range = bollinger['bollinger_upper'] - bollinger['bollinger_lower']
        assert band_range > 0
    
    def test_russian_market_specific_rsi_thresholds(self):
        """Тест специфических порогов RSI для российского рынка"""
        # Тест нижнего порога (25 вместо стандартных 30)
        indicators = TechnicalIndicators(
            symbol="ROSN",
            timestamp=datetime.now(),
            rsi=24.0
        )
        
        signals = self.analyzer.get_market_signal(indicators)
        assert signals['rsi'] == 'ПОКУПКА'
        
        # Тест верхнего порога (75 вместо стандартных 70)
        indicators.rsi = 76.0
        signals = self.analyzer.get_market_signal(indicators)
        assert signals['rsi'] == 'ПРОДАЖА'
    
    def test_technical_indicators_dataclass(self):
        """Тест структуры данных TechnicalIndicators"""
        indicators = TechnicalIndicators(
            symbol="NVTK",
            timestamp=datetime.now(),
            rsi=45.0,
            macd=1.5,
            sma_20=120.0
        )
        
        assert indicators.symbol == "NVTK"
        assert indicators.rsi == 45.0
        assert indicators.macd == 1.5
        assert indicators.sma_20 == 120.0
        assert indicators.macd_signal is None  # Не установлено
    
    def test_error_handling_invalid_data(self):
        """Тест обработки ошибок с некорректными данными"""
        # Тест с NaN значениями
        invalid_prices = [100.0, float('nan'), 102.0, 103.0]
        
        # Функции должны обрабатывать некорректные данные gracefully
        try:
            rsi = self.analyzer.calculate_rsi(invalid_prices)
            # Если функция не падает, это хорошо
            assert True
        except Exception:
            # Если падает, должна быть обработка ошибок
            assert False, "Функция должна обрабатывать некорректные данные"
    
    def test_performance_with_large_dataset(self):
        """Тест производительности с большим набором данных"""
        # Создаем большой набор данных (1000 точек)
        large_dataset = []
        base_price = 100.0
        for i in range(1000):
            base_price += np.random.normal(0, 2)
            large_dataset.append(max(base_price, 10))
        
        # Тест должен выполняться быстро
        import time
        start_time = time.time()
        
        rsi = self.analyzer.calculate_rsi(large_dataset)
        macd, signal, hist = self.analyzer.calculate_macd(large_dataset)
        
        end_time = time.time()
        
        assert rsi is not None
        assert macd is not None
        assert (end_time - start_time) < 1.0  # Должно выполняться менее чем за 1 секунду