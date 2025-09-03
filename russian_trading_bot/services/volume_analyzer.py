"""
Сервис анализа объемов торгов для российского рынка MOEX.
Реализует индикаторы на основе объемов, адаптированные для российского рынка.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class VolumeIndicators:
    """Структура данных для индикаторов объема"""
    symbol: str
    timestamp: datetime
    volume_sma_20: Optional[float] = None
    volume_ratio: Optional[float] = None  # Отношение текущего объема к среднему
    vwap: Optional[float] = None  # Volume Weighted Average Price
    obv: Optional[float] = None  # On-Balance Volume
    ad_line: Optional[float] = None  # Accumulation/Distribution Line
    cmf: Optional[float] = None  # Chaikin Money Flow
    volume_profile: Optional[Dict[str, float]] = None
    unusual_volume_detected: bool = False
    volume_trend: Optional[str] = None  # "РАСТЕТ", "ПАДАЕТ", "СТАБИЛЬНО"


@dataclass
class VolumeProfile:
    """Профиль объемов для торговой сессии"""
    price_levels: List[float]
    volume_at_price: List[float]
    poc: float  # Point of Control - уровень с максимальным объемом
    value_area_high: float  # Верхняя граница области стоимости
    value_area_low: float  # Нижняя граница области стоимости
    total_volume: float


class VolumeAnalyzer:
    """
    Анализатор объемов торгов для российского рынка MOEX.
    Адаптирован для особенностей российских торговых сессий и паттернов объемов.
    """
    
    def __init__(self):
        # Параметры для российского рынка
        self.volume_sma_period = 20
        self.unusual_volume_threshold = 2.0  # Превышение среднего объема в 2 раза
        self.cmf_period = 20
        self.value_area_percentage = 0.7  # 70% объема для области стоимости
        
        # Время торговых сессий MOEX (MSK)
        self.main_session_start = 10  # 10:00
        self.main_session_end = 18  # 18:45
        self.evening_session_start = 19  # 19:05
        self.evening_session_end = 23  # 23:50
        
        # Адаптация для российского рынка
        self.russian_market_multiplier = 1.5  # Коэффициент для российской волатильности
        
    def calculate_volume_sma(self, volumes: List[float], period: int = None) -> float:
        """
        Расчет скользящей средней объема.
        
        Args:
            volumes: Список объемов торгов
            period: Период для расчета
            
        Returns:
            Средний объем за период
        """
        if period is None:
            period = self.volume_sma_period
            
        if len(volumes) < period:
            return None
            
        return round(np.mean(volumes[-period:]), 0)
    
    def calculate_volume_ratio(self, current_volume: float, volumes: List[float]) -> float:
        """
        Расчет отношения текущего объема к среднему.
        
        Args:
            current_volume: Текущий объем
            volumes: Исторические объемы
            
        Returns:
            Отношение текущего объема к среднему
        """
        avg_volume = self.calculate_volume_sma(volumes)
        if avg_volume is None or avg_volume == 0:
            return None
            
        return round(current_volume / avg_volume, 2)
    
    def calculate_vwap(self, prices: List[float], volumes: List[float]) -> float:
        """
        Расчет Volume Weighted Average Price (VWAP).
        
        Args:
            prices: Список цен (обычно средняя цена за период)
            volumes: Список объемов
            
        Returns:
            VWAP значение
        """
        if len(prices) != len(volumes) or len(prices) == 0:
            return None
            
        total_volume = sum(volumes)
        if total_volume == 0:
            return None
            
        weighted_sum = sum(price * volume for price, volume in zip(prices, volumes))
        return round(weighted_sum / total_volume, 2)
    
    def calculate_obv(self, prices: List[float], volumes: List[float]) -> float:
        """
        Расчет On-Balance Volume (OBV).
        
        Args:
            prices: Список цен закрытия
            volumes: Список объемов
            
        Returns:
            Текущее значение OBV
        """
        if len(prices) != len(volumes) or len(prices) < 2:
            return None
            
        obv = 0
        
        for i in range(1, len(prices)):
            if prices[i] > prices[i-1]:
                obv += volumes[i]
            elif prices[i] < prices[i-1]:
                obv -= volumes[i]
            # Если цены равны, объем не добавляется
            
        return round(obv, 0)
    
    def calculate_ad_line(self, high_prices: List[float], low_prices: List[float], 
                         close_prices: List[float], volumes: List[float]) -> float:
        """
        Расчет Accumulation/Distribution Line.
        
        Args:
            high_prices: Список максимальных цен
            low_prices: Список минимальных цен
            close_prices: Список цен закрытия
            volumes: Список объемов
            
        Returns:
            Значение A/D Line
        """
        if not all(len(lst) == len(volumes) for lst in [high_prices, low_prices, close_prices]):
            return None
            
        ad_line = 0
        
        for i in range(len(volumes)):
            high_low_diff = high_prices[i] - low_prices[i]
            
            if high_low_diff == 0:
                money_flow_multiplier = 0
            else:
                money_flow_multiplier = ((close_prices[i] - low_prices[i]) - 
                                       (high_prices[i] - close_prices[i])) / high_low_diff
            
            money_flow_volume = money_flow_multiplier * volumes[i]
            ad_line += money_flow_volume
            
        return round(ad_line, 0)
    
    def calculate_cmf(self, high_prices: List[float], low_prices: List[float], 
                     close_prices: List[float], volumes: List[float], period: int = None) -> float:
        """
        Расчет Chaikin Money Flow (CMF).
        
        Args:
            high_prices: Список максимальных цен
            low_prices: Список минимальных цен
            close_prices: Список цен закрытия
            volumes: Список объемов
            period: Период для расчета
            
        Returns:
            Значение CMF
        """
        if period is None:
            period = self.cmf_period
            
        if len(volumes) < period:
            return None
            
        # Берем последние period значений
        recent_high = high_prices[-period:]
        recent_low = low_prices[-period:]
        recent_close = close_prices[-period:]
        recent_volume = volumes[-period:]
        
        money_flow_volume_sum = 0
        volume_sum = 0
        
        for i in range(period):
            high_low_diff = recent_high[i] - recent_low[i]
            
            if high_low_diff == 0:
                money_flow_multiplier = 0
            else:
                money_flow_multiplier = ((recent_close[i] - recent_low[i]) - 
                                       (recent_high[i] - recent_close[i])) / high_low_diff
            
            money_flow_volume = money_flow_multiplier * recent_volume[i]
            money_flow_volume_sum += money_flow_volume
            volume_sum += recent_volume[i]
        
        if volume_sum == 0:
            return None
            
        cmf = money_flow_volume_sum / volume_sum
        return round(cmf, 4)
    
    def detect_unusual_volume(self, current_volume: float, volumes: List[float]) -> bool:
        """
        Обнаружение необычного объема торгов.
        
        Args:
            current_volume: Текущий объем
            volumes: Исторические объемы
            
        Returns:
            True если объем необычно высокий
        """
        volume_ratio = self.calculate_volume_ratio(current_volume, volumes)
        
        if volume_ratio is None:
            return False
            
        # Адаптация для российского рынка - учитываем повышенную волатильность
        threshold = self.unusual_volume_threshold * self.russian_market_multiplier
        
        return volume_ratio >= threshold
    
    def calculate_volume_profile(self, prices: List[float], volumes: List[float], 
                               price_bins: int = 50) -> VolumeProfile:
        """
        Расчет профиля объемов для торговой сессии.
        
        Args:
            prices: Список цен
            volumes: Список объемов
            price_bins: Количество ценовых уровней
            
        Returns:
            Объект VolumeProfile с данными профиля
        """
        if len(prices) != len(volumes) or len(prices) == 0:
            return None
            
        min_price = min(prices)
        max_price = max(prices)
        
        if min_price == max_price:
            return VolumeProfile(
                price_levels=[min_price],
                volume_at_price=[sum(volumes)],
                poc=min_price,
                value_area_high=min_price,
                value_area_low=min_price,
                total_volume=sum(volumes)
            )
        
        # Создаем ценовые уровни
        price_step = (max_price - min_price) / price_bins
        price_levels = [min_price + i * price_step for i in range(price_bins + 1)]
        volume_at_price = [0] * len(price_levels)
        
        # Распределяем объемы по ценовым уровням
        for price, volume in zip(prices, volumes):
            bin_index = min(int((price - min_price) / price_step), price_bins - 1)
            volume_at_price[bin_index] += volume
        
        # Находим Point of Control (уровень с максимальным объемом)
        max_volume_index = volume_at_price.index(max(volume_at_price))
        poc = price_levels[max_volume_index]
        
        # Рассчитываем область стоимости (Value Area)
        total_volume = sum(volumes)
        target_volume = total_volume * self.value_area_percentage
        
        # Начинаем с POC и расширяем область
        value_area_volume = volume_at_price[max_volume_index]
        low_index = high_index = max_volume_index
        
        while value_area_volume < target_volume and (low_index > 0 or high_index < len(volume_at_price) - 1):
            # Выбираем направление с большим объемом
            low_volume = volume_at_price[low_index - 1] if low_index > 0 else 0
            high_volume = volume_at_price[high_index + 1] if high_index < len(volume_at_price) - 1 else 0
            
            if low_volume >= high_volume and low_index > 0:
                low_index -= 1
                value_area_volume += volume_at_price[low_index]
            elif high_index < len(volume_at_price) - 1:
                high_index += 1
                value_area_volume += volume_at_price[high_index]
            else:
                break
        
        value_area_low = price_levels[low_index]
        value_area_high = price_levels[high_index]
        
        return VolumeProfile(
            price_levels=price_levels,
            volume_at_price=volume_at_price,
            poc=round(poc, 2),
            value_area_high=round(value_area_high, 2),
            value_area_low=round(value_area_low, 2),
            total_volume=total_volume
        )
    
    def analyze_volume_trend(self, volumes: List[float], period: int = 10) -> str:
        """
        Анализ тренда объемов торгов.
        
        Args:
            volumes: Список объемов
            period: Период для анализа тренда
            
        Returns:
            Направление тренда: "РАСТЕТ", "ПАДАЕТ", "СТАБИЛЬНО"
        """
        if len(volumes) < period:
            return None
            
        recent_volumes = volumes[-period:]
        
        # Используем линейную регрессию для определения тренда
        x = np.arange(len(recent_volumes))
        slope = np.polyfit(x, recent_volumes, 1)[0]
        
        # Определяем значимость тренда
        avg_volume = np.mean(recent_volumes)
        slope_percentage = (slope * period) / avg_volume * 100
        
        if slope_percentage > 10:  # Рост более чем на 10%
            return "РАСТЕТ"
        elif slope_percentage < -10:  # Падение более чем на 10%
            return "ПАДАЕТ"
        else:
            return "СТАБИЛЬНО"
    
    def calculate_all_volume_indicators(self, symbol: str, market_data: Dict) -> VolumeIndicators:
        """
        Расчет всех индикаторов объема для российской акции.
        
        Args:
            symbol: Тикер российской акции
            market_data: Словарь с историческими данными
            
        Returns:
            Объект VolumeIndicators со всеми рассчитанными индикаторами
        """
        try:
            volumes = market_data.get('volume', [])
            close_prices = market_data.get('close', [])
            high_prices = market_data.get('high', [])
            low_prices = market_data.get('low', [])
            
            if not volumes:
                logger.warning(f"Нет данных об объемах для {symbol}")
                return VolumeIndicators(symbol=symbol, timestamp=datetime.now())
            
            indicators = VolumeIndicators(symbol=symbol, timestamp=datetime.now())
            
            # Средний объем
            indicators.volume_sma_20 = self.calculate_volume_sma(volumes)
            
            # Отношение текущего объема к среднему
            if volumes:
                indicators.volume_ratio = self.calculate_volume_ratio(volumes[-1], volumes)
                indicators.unusual_volume_detected = self.detect_unusual_volume(volumes[-1], volumes)
            
            # VWAP (используем средние цены)
            if close_prices and high_prices and low_prices:
                typical_prices = [(h + l + c) / 3 for h, l, c in zip(high_prices, low_prices, close_prices)]
                indicators.vwap = self.calculate_vwap(typical_prices, volumes)
            
            # On-Balance Volume
            if close_prices:
                indicators.obv = self.calculate_obv(close_prices, volumes)
            
            # Accumulation/Distribution Line
            if all([high_prices, low_prices, close_prices]):
                indicators.ad_line = self.calculate_ad_line(high_prices, low_prices, close_prices, volumes)
            
            # Chaikin Money Flow
            if all([high_prices, low_prices, close_prices]):
                indicators.cmf = self.calculate_cmf(high_prices, low_prices, close_prices, volumes)
            
            # Профиль объемов (для последних данных)
            if close_prices and len(close_prices) >= 20:
                recent_prices = close_prices[-20:]
                recent_volumes = volumes[-20:]
                volume_profile = self.calculate_volume_profile(recent_prices, recent_volumes)
                if volume_profile:
                    indicators.volume_profile = {
                        'poc': volume_profile.poc,
                        'value_area_high': volume_profile.value_area_high,
                        'value_area_low': volume_profile.value_area_low,
                        'total_volume': volume_profile.total_volume
                    }
            
            # Тренд объемов
            indicators.volume_trend = self.analyze_volume_trend(volumes)
            
            logger.info(f"Рассчитаны индикаторы объема для {symbol}")
            return indicators
            
        except Exception as e:
            logger.error(f"Ошибка при расчете индикаторов объема для {symbol}: {e}")
            return VolumeIndicators(symbol=symbol, timestamp=datetime.now())
    
    def get_volume_signals(self, indicators: VolumeIndicators) -> Dict[str, str]:
        """
        Генерация торговых сигналов на основе анализа объемов.
        
        Args:
            indicators: Рассчитанные индикаторы объема
            
        Returns:
            Словарь с торговыми сигналами
        """
        signals = {}
        
        # Сигнал необычного объема
        if indicators.unusual_volume_detected:
            signals['unusual_volume'] = 'ВНИМАНИЕ - НЕОБЫЧНЫЙ ОБЪЕМ'
        
        # Сигнал на основе отношения объемов
        if indicators.volume_ratio is not None:
            if indicators.volume_ratio >= 2.0:
                signals['volume_ratio'] = 'ВЫСОКИЙ ИНТЕРЕС'
            elif indicators.volume_ratio <= 0.5:
                signals['volume_ratio'] = 'НИЗКИЙ ИНТЕРЕС'
            else:
                signals['volume_ratio'] = 'НОРМАЛЬНЫЙ ОБЪЕМ'
        
        # Сигнал Chaikin Money Flow
        if indicators.cmf is not None:
            if indicators.cmf > 0.1:
                signals['cmf'] = 'НАКОПЛЕНИЕ'
            elif indicators.cmf < -0.1:
                signals['cmf'] = 'РАСПРЕДЕЛЕНИЕ'
            else:
                signals['cmf'] = 'НЕЙТРАЛЬНО'
        
        # Сигнал тренда объемов
        if indicators.volume_trend:
            if indicators.volume_trend == 'РАСТЕТ':
                signals['volume_trend'] = 'РАСТУЩИЙ ИНТЕРЕС'
            elif indicators.volume_trend == 'ПАДАЕТ':
                signals['volume_trend'] = 'СНИЖАЮЩИЙСЯ ИНТЕРЕС'
            else:
                signals['volume_trend'] = 'СТАБИЛЬНЫЙ ИНТЕРЕС'
        
        return signals
    
    def analyze_session_volume_pattern(self, hourly_volumes: List[float], 
                                     session_hours: List[int]) -> Dict[str, any]:
        """
        Анализ паттернов объема в течение торговой сессии MOEX.
        
        Args:
            hourly_volumes: Объемы по часам
            session_hours: Часы торговой сессии
            
        Returns:
            Анализ паттернов объема
        """
        if len(hourly_volumes) != len(session_hours):
            return {}
        
        analysis = {}
        
        # Разделяем на основную и вечернюю сессии
        main_session_volumes = []
        evening_session_volumes = []
        
        for hour, volume in zip(session_hours, hourly_volumes):
            if self.main_session_start <= hour <= self.main_session_end:
                main_session_volumes.append(volume)
            elif self.evening_session_start <= hour <= self.evening_session_end:
                evening_session_volumes.append(volume)
        
        # Анализ основной сессии
        if main_session_volumes:
            analysis['main_session'] = {
                'total_volume': sum(main_session_volumes),
                'avg_volume': np.mean(main_session_volumes),
                'peak_hour_volume': max(main_session_volumes),
                'opening_volume': main_session_volumes[0] if main_session_volumes else 0,
                'closing_volume': main_session_volumes[-1] if main_session_volumes else 0
            }
        
        # Анализ вечерней сессии
        if evening_session_volumes:
            analysis['evening_session'] = {
                'total_volume': sum(evening_session_volumes),
                'avg_volume': np.mean(evening_session_volumes),
                'peak_hour_volume': max(evening_session_volumes)
            }
        
        # Сравнение сессий
        if main_session_volumes and evening_session_volumes:
            main_total = sum(main_session_volumes)
            evening_total = sum(evening_session_volumes)
            
            analysis['session_comparison'] = {
                'main_to_evening_ratio': round(main_total / evening_total, 2) if evening_total > 0 else None,
                'dominant_session': 'ОСНОВНАЯ' if main_total > evening_total else 'ВЕЧЕРНЯЯ'
            }
        
        return analysis