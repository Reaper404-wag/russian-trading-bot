"""
Сервис технического анализа для российского рынка MOEX.
Реализует технические индикаторы, адаптированные для российского рынка.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class TechnicalIndicators:
    """Структура данных для технических индикаторов"""
    symbol: str
    timestamp: datetime
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_middle: Optional[float] = None
    bollinger_lower: Optional[float] = None
    bollinger_width: Optional[float] = None
    atr: Optional[float] = None
    stochastic_k: Optional[float] = None
    stochastic_d: Optional[float] = None


class TechnicalAnalyzer:
    """
    Технический анализатор для российского рынка MOEX.
    Адаптирован для особенностей российского рынка и волатильности.
    """
    
    def __init__(self):
        # Параметры, адаптированные для российского рынка
        self.rsi_period = 14
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.bollinger_period = 20
        self.bollinger_std = 2.0  # Увеличено для российского рынка
        self.atr_period = 14
        self.stochastic_k_period = 14
        self.stochastic_d_period = 3
        
        # Адаптация для российской волатильности
        self.volatility_adjustment = 1.2  # Коэффициент для российского рынка
        
    def calculate_rsi(self, prices: List[float], period: int = None) -> float:
        """
        Расчет RSI (Relative Strength Index) адаптированный для MOEX.
        
        Args:
            prices: Список цен закрытия
            period: Период для расчета (по умолчанию 14)
            
        Returns:
            Значение RSI (0-100)
        """
        if period is None:
            period = self.rsi_period
            
        if len(prices) < period + 1:
            return None
            
        prices_array = np.array(prices)
        deltas = np.diff(prices_array)
        
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # Используем экспоненциальное сглаживание для российского рынка
        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])
        
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
        if avg_loss == 0:
            return 100.0
            
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi, 2)
    
    def calculate_macd(self, prices: List[float]) -> Tuple[float, float, float]:
        """
        Расчет MACD адаптированный для российского рынка.
        
        Args:
            prices: Список цен закрытия
            
        Returns:
            Кортеж (MACD, Signal, Histogram)
        """
        if len(prices) < self.macd_slow:
            return None, None, None
            
        prices_series = pd.Series(prices)
        
        # EMA с адаптацией для российского рынка
        ema_fast = prices_series.ewm(span=self.macd_fast).mean()
        ema_slow = prices_series.ewm(span=self.macd_slow).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.macd_signal).mean()
        histogram = macd_line - signal_line
        
        return (
            round(macd_line.iloc[-1], 4),
            round(signal_line.iloc[-1], 4),
            round(histogram.iloc[-1], 4)
        )
    
    def calculate_moving_averages(self, prices: List[float]) -> Dict[str, float]:
        """
        Расчет скользящих средних для российского рынка.
        
        Args:
            prices: Список цен закрытия
            
        Returns:
            Словарь со значениями SMA и EMA
        """
        if len(prices) < 50:
            return {}
            
        prices_series = pd.Series(prices)
        
        result = {}
        
        # Simple Moving Averages
        if len(prices) >= 20:
            result['sma_20'] = round(prices_series.rolling(20).mean().iloc[-1], 2)
        if len(prices) >= 50:
            result['sma_50'] = round(prices_series.rolling(50).mean().iloc[-1], 2)
            
        # Exponential Moving Averages
        if len(prices) >= 12:
            result['ema_12'] = round(prices_series.ewm(span=12).mean().iloc[-1], 2)
        if len(prices) >= 26:
            result['ema_26'] = round(prices_series.ewm(span=26).mean().iloc[-1], 2)
            
        return result
    
    def calculate_bollinger_bands(self, prices: List[float], period: int = None, std_dev: float = None) -> Dict[str, float]:
        """
        Расчет полос Боллинджера адаптированных для российского рынка.
        
        Args:
            prices: Список цен закрытия
            period: Период для расчета
            std_dev: Количество стандартных отклонений
            
        Returns:
            Словарь с верхней, средней и нижней полосами
        """
        if period is None:
            period = self.bollinger_period
        if std_dev is None:
            std_dev = self.bollinger_std
            
        if len(prices) < period:
            return {}
            
        prices_series = pd.Series(prices)
        
        # Средняя линия (SMA)
        middle_band = prices_series.rolling(period).mean()
        
        # Стандартное отклонение с адаптацией для российского рынка
        std = prices_series.rolling(period).std() * self.volatility_adjustment
        
        upper_band = middle_band + (std * std_dev)
        lower_band = middle_band - (std * std_dev)
        
        # Ширина полос (индикатор волатильности)
        band_width = (upper_band - lower_band) / middle_band * 100
        
        return {
            'bollinger_upper': round(upper_band.iloc[-1], 2),
            'bollinger_middle': round(middle_band.iloc[-1], 2),
            'bollinger_lower': round(lower_band.iloc[-1], 2),
            'bollinger_width': round(band_width.iloc[-1], 2)
        }
    
    def calculate_atr(self, high_prices: List[float], low_prices: List[float], 
                     close_prices: List[float], period: int = None) -> float:
        """
        Расчет Average True Range для российского рынка.
        
        Args:
            high_prices: Список максимальных цен
            low_prices: Список минимальных цен
            close_prices: Список цен закрытия
            period: Период для расчета
            
        Returns:
            Значение ATR
        """
        if period is None:
            period = self.atr_period
            
        if len(high_prices) < period + 1:
            return None
            
        true_ranges = []
        
        for i in range(1, len(close_prices)):
            tr1 = high_prices[i] - low_prices[i]
            tr2 = abs(high_prices[i] - close_prices[i-1])
            tr3 = abs(low_prices[i] - close_prices[i-1])
            
            true_range = max(tr1, tr2, tr3)
            true_ranges.append(true_range)
            
        if len(true_ranges) < period:
            return None
            
        # Используем экспоненциальное сглаживание
        atr = np.mean(true_ranges[:period])
        
        for i in range(period, len(true_ranges)):
            atr = (atr * (period - 1) + true_ranges[i]) / period
            
        return round(atr, 4)
    
    def calculate_stochastic(self, high_prices: List[float], low_prices: List[float], 
                           close_prices: List[float]) -> Tuple[float, float]:
        """
        Расчет стохастического осциллятора для российского рынка.
        
        Args:
            high_prices: Список максимальных цен
            low_prices: Список минимальных цен
            close_prices: Список цен закрытия
            
        Returns:
            Кортеж (%K, %D)
        """
        if len(close_prices) < self.stochastic_k_period:
            return None, None
            
        k_values = []
        
        for i in range(self.stochastic_k_period - 1, len(close_prices)):
            period_high = max(high_prices[i - self.stochastic_k_period + 1:i + 1])
            period_low = min(low_prices[i - self.stochastic_k_period + 1:i + 1])
            
            if period_high == period_low:
                k_percent = 50.0  # Избегаем деления на ноль
            else:
                k_percent = ((close_prices[i] - period_low) / (period_high - period_low)) * 100
                
            k_values.append(k_percent)
            
        if len(k_values) < self.stochastic_d_period:
            return round(k_values[-1], 2), None
            
        # %D - скользящая средняя от %K
        d_percent = np.mean(k_values[-self.stochastic_d_period:])
        
        return round(k_values[-1], 2), round(d_percent, 2)
    
    def calculate_all_indicators(self, symbol: str, market_data: Dict) -> TechnicalIndicators:
        """
        Расчет всех технических индикаторов для российской акции.
        
        Args:
            symbol: Тикер российской акции (например, "SBER", "GAZP")
            market_data: Словарь с историческими данными
            
        Returns:
            Объект TechnicalIndicators со всеми рассчитанными индикаторами
        """
        try:
            close_prices = market_data.get('close', [])
            high_prices = market_data.get('high', [])
            low_prices = market_data.get('low', [])
            
            if not close_prices:
                logger.warning(f"Нет данных о ценах для {symbol}")
                return TechnicalIndicators(symbol=symbol, timestamp=datetime.now())
            
            indicators = TechnicalIndicators(symbol=symbol, timestamp=datetime.now())
            
            # RSI
            indicators.rsi = self.calculate_rsi(close_prices)
            
            # MACD
            macd, signal, histogram = self.calculate_macd(close_prices)
            indicators.macd = macd
            indicators.macd_signal = signal
            indicators.macd_histogram = histogram
            
            # Скользящие средние
            ma_values = self.calculate_moving_averages(close_prices)
            indicators.sma_20 = ma_values.get('sma_20')
            indicators.sma_50 = ma_values.get('sma_50')
            indicators.ema_12 = ma_values.get('ema_12')
            indicators.ema_26 = ma_values.get('ema_26')
            
            # Полосы Боллинджера
            bollinger = self.calculate_bollinger_bands(close_prices)
            indicators.bollinger_upper = bollinger.get('bollinger_upper')
            indicators.bollinger_middle = bollinger.get('bollinger_middle')
            indicators.bollinger_lower = bollinger.get('bollinger_lower')
            indicators.bollinger_width = bollinger.get('bollinger_width')
            
            # ATR
            if high_prices and low_prices:
                indicators.atr = self.calculate_atr(high_prices, low_prices, close_prices)
            
            # Стохастический осциллятор
            if high_prices and low_prices:
                stoch_k, stoch_d = self.calculate_stochastic(high_prices, low_prices, close_prices)
                indicators.stochastic_k = stoch_k
                indicators.stochastic_d = stoch_d
            
            logger.info(f"Рассчитаны технические индикаторы для {symbol}")
            return indicators
            
        except Exception as e:
            logger.error(f"Ошибка при расчете индикаторов для {symbol}: {e}")
            return TechnicalIndicators(symbol=symbol, timestamp=datetime.now())
    
    def get_market_signal(self, indicators: TechnicalIndicators) -> Dict[str, str]:
        """
        Генерация торговых сигналов на основе технических индикаторов.
        Адаптировано для российского рынка.
        
        Args:
            indicators: Рассчитанные технические индикаторы
            
        Returns:
            Словарь с торговыми сигналами
        """
        signals = {}
        
        # RSI сигналы (адаптированы для российского рынка)
        if indicators.rsi is not None:
            if indicators.rsi < 25:  # Более низкий порог для российского рынка
                signals['rsi'] = 'ПОКУПКА'
            elif indicators.rsi > 75:  # Более высокий порог
                signals['rsi'] = 'ПРОДАЖА'
            else:
                signals['rsi'] = 'НЕЙТРАЛЬНО'
        
        # MACD сигналы
        if indicators.macd is not None and indicators.macd_signal is not None:
            if indicators.macd > indicators.macd_signal:
                signals['macd'] = 'ПОКУПКА'
            else:
                signals['macd'] = 'ПРОДАЖА'
        
        # Полосы Боллинджера
        if all([indicators.bollinger_upper, indicators.bollinger_lower, indicators.bollinger_middle]):
            current_price = indicators.bollinger_middle  # Используем среднюю линию как текущую цену
            
            if current_price <= indicators.bollinger_lower:
                signals['bollinger'] = 'ПОКУПКА'
            elif current_price >= indicators.bollinger_upper:
                signals['bollinger'] = 'ПРОДАЖА'
            else:
                signals['bollinger'] = 'НЕЙТРАЛЬНО'
        
        # Стохастический осциллятор
        if indicators.stochastic_k is not None:
            if indicators.stochastic_k < 20:
                signals['stochastic'] = 'ПОКУПКА'
            elif indicators.stochastic_k > 80:
                signals['stochastic'] = 'ПРОДАЖА'
            else:
                signals['stochastic'] = 'НЕЙТРАЛЬНО'
        
        return signals