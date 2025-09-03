"""
Тесты для сервиса анализа объемов торгов российского рынка.
"""

import unittest
from unittest.mock import patch, MagicMock
import numpy as np
from datetime import datetime

from russian_trading_bot.services.volume_analyzer import (
    VolumeAnalyzer, VolumeIndicators, VolumeProfile
)


class TestVolumeAnalyzer(unittest.TestCase):
    """Тесты для VolumeAnalyzer"""
    
    def setUp(self):
        """Настройка тестов"""
        self.analyzer = VolumeAnalyzer()
        
        # Тестовые данные для российских акций
        self.test_volumes = [1000, 1200, 800, 1500, 2000, 1800, 1100, 900, 1300, 1600,
                           1400, 1700, 1200, 1000, 1900, 2200, 1500, 1300, 1100, 1800]
        
        self.test_prices = [100.0, 102.0, 98.0, 105.0, 110.0, 108.0, 103.0, 99.0, 
                          104.0, 109.0, 107.0, 112.0, 106.0, 101.0, 115.0, 118.0, 
                          113.0, 108.0, 105.0, 116.0]
        
        self.test_high_prices = [p + 2 for p in self.test_prices]
        self.test_low_prices = [p - 2 for p in self.test_prices]
        
    def test_calculate_volume_sma(self):
        """Тест расчета скользящей средней объема"""
        # Тест с достаточным количеством данных
        result = self.analyzer.calculate_volume_sma(self.test_volumes, period=10)
        expected = np.mean(self.test_volumes[-10:])
        self.assertAlmostEqual(result, expected, places=0)
        
        # Тест с недостаточным количеством данных
        short_volumes = [1000, 1200, 800]
        result = self.analyzer.calculate_volume_sma(short_volumes, period=10)
        self.assertIsNone(result)
        
        # Тест с пустым списком
        result = self.analyzer.calculate_volume_sma([])
        self.assertIsNone(result)
    
    def test_calculate_volume_ratio(self):
        """Тест расчета отношения текущего объема к среднему"""
        current_volume = 3000  # Высокий объем
        result = self.analyzer.calculate_volume_ratio(current_volume, self.test_volumes)
        
        avg_volume = np.mean(self.test_volumes[-20:])
        expected = current_volume / avg_volume
        self.assertAlmostEqual(result, expected, places=2)
        
        # Тест с нулевым средним объемом
        zero_volumes = [0] * 20
        result = self.analyzer.calculate_volume_ratio(1000, zero_volumes)
        self.assertIsNone(result)
    
    def test_calculate_vwap(self):
        """Тест расчета VWAP"""
        result = self.analyzer.calculate_vwap(self.test_prices, self.test_volumes)
        
        # Ручной расчет VWAP
        total_volume = sum(self.test_volumes)
        weighted_sum = sum(p * v for p, v in zip(self.test_prices, self.test_volumes))
        expected = weighted_sum / total_volume
        
        self.assertAlmostEqual(result, expected, places=2)
        
        # Тест с разной длиной списков
        result = self.analyzer.calculate_vwap([100, 200], [1000, 2000, 3000])
        self.assertIsNone(result)
        
        # Тест с нулевым объемом
        result = self.analyzer.calculate_vwap([100, 200], [0, 0])
        self.assertIsNone(result)
    
    def test_calculate_obv(self):
        """Тест расчета On-Balance Volume"""
        result = self.analyzer.calculate_obv(self.test_prices, self.test_volumes)
        
        # Ручной расчет OBV
        obv = 0
        for i in range(1, len(self.test_prices)):
            if self.test_prices[i] > self.test_prices[i-1]:
                obv += self.test_volumes[i]
            elif self.test_prices[i] < self.test_prices[i-1]:
                obv -= self.test_volumes[i]
        
        self.assertEqual(result, obv)
        
        # Тест с недостаточными данными
        result = self.analyzer.calculate_obv([100], [1000])
        self.assertIsNone(result)
    
    def test_calculate_ad_line(self):
        """Тест расчета Accumulation/Distribution Line"""
        result = self.analyzer.calculate_ad_line(
            self.test_high_prices, self.test_low_prices, 
            self.test_prices, self.test_volumes
        )
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, float)
        
        # Тест с разной длиной списков
        result = self.analyzer.calculate_ad_line([100], [90], [95, 96], [1000, 2000])
        self.assertIsNone(result)
    
    def test_calculate_cmf(self):
        """Тест расчета Chaikin Money Flow"""
        result = self.analyzer.calculate_cmf(
            self.test_high_prices, self.test_low_prices, 
            self.test_prices, self.test_volumes, period=10
        )
        
        self.assertIsNotNone(result)
        self.assertIsInstance(result, float)
        self.assertGreaterEqual(result, -1.0)
        self.assertLessEqual(result, 1.0)
        
        # Тест с недостаточными данными
        short_data = [100, 200, 300]
        result = self.analyzer.calculate_cmf(short_data, short_data, short_data, short_data, period=10)
        self.assertIsNone(result)
    
    def test_detect_unusual_volume(self):
        """Тест обнаружения необычного объема"""
        # Нормальный объем
        normal_volume = 1500
        result = self.analyzer.detect_unusual_volume(normal_volume, self.test_volumes)
        self.assertFalse(result)
        
        # Необычно высокий объем
        high_volume = 5000  # Значительно выше среднего
        result = self.analyzer.detect_unusual_volume(high_volume, self.test_volumes)
        self.assertTrue(result)
        
        # Тест с недостаточными данными
        result = self.analyzer.detect_unusual_volume(1000, [])
        self.assertFalse(result)
    
    def test_calculate_volume_profile(self):
        """Тест расчета профиля объемов"""
        result = self.analyzer.calculate_volume_profile(self.test_prices, self.test_volumes)
        
        self.assertIsInstance(result, VolumeProfile)
        self.assertIsNotNone(result.poc)
        self.assertIsNotNone(result.value_area_high)
        self.assertIsNotNone(result.value_area_low)
        self.assertEqual(result.total_volume, sum(self.test_volumes))
        
        # Проверяем, что область стоимости корректна
        self.assertLessEqual(result.value_area_low, result.poc)
        self.assertGreaterEqual(result.value_area_high, result.poc)
        
        # Тест с одинаковыми ценами
        same_prices = [100.0] * 10
        same_volumes = [1000] * 10
        result = self.analyzer.calculate_volume_profile(same_prices, same_volumes)
        
        self.assertEqual(result.poc, 100.0)
        self.assertEqual(result.value_area_high, 100.0)
        self.assertEqual(result.value_area_low, 100.0)
        
        # Тест с пустыми данными
        result = self.analyzer.calculate_volume_profile([], [])
        self.assertIsNone(result)
    
    def test_analyze_volume_trend(self):
        """Тест анализа тренда объемов"""
        # Растущий тренд
        growing_volumes = list(range(1000, 2000, 50))  # Растущие объемы
        result = self.analyzer.analyze_volume_trend(growing_volumes)
        self.assertEqual(result, "РАСТЕТ")
        
        # Падающий тренд
        falling_volumes = list(range(2000, 1000, -50))  # Падающие объемы
        result = self.analyzer.analyze_volume_trend(falling_volumes)
        self.assertEqual(result, "ПАДАЕТ")
        
        # Стабильный тренд
        stable_volumes = [1500] * 20  # Стабильные объемы
        result = self.analyzer.analyze_volume_trend(stable_volumes)
        self.assertEqual(result, "СТАБИЛЬНО")
        
        # Тест с недостаточными данными
        result = self.analyzer.analyze_volume_trend([1000, 2000], period=10)
        self.assertIsNone(result)
    
    def test_calculate_all_volume_indicators(self):
        """Тест расчета всех индикаторов объема"""
        market_data = {
            'volume': self.test_volumes,
            'close': self.test_prices,
            'high': self.test_high_prices,
            'low': self.test_low_prices
        }
        
        result = self.analyzer.calculate_all_volume_indicators("SBER", market_data)
        
        self.assertIsInstance(result, VolumeIndicators)
        self.assertEqual(result.symbol, "SBER")
        self.assertIsNotNone(result.timestamp)
        
        # Проверяем, что основные индикаторы рассчитаны
        self.assertIsNotNone(result.volume_sma_20)
        self.assertIsNotNone(result.volume_ratio)
        self.assertIsNotNone(result.vwap)
        self.assertIsNotNone(result.obv)
        self.assertIsNotNone(result.ad_line)
        self.assertIsNotNone(result.cmf)
        self.assertIsNotNone(result.volume_trend)
        
        # Тест с пустыми данными
        empty_data = {}
        result = self.analyzer.calculate_all_volume_indicators("GAZP", empty_data)
        self.assertEqual(result.symbol, "GAZP")
        self.assertIsNone(result.volume_sma_20)
    
    def test_get_volume_signals(self):
        """Тест генерации торговых сигналов на основе объемов"""
        # Создаем индикаторы с различными значениями
        indicators = VolumeIndicators(
            symbol="SBER",
            timestamp=datetime.now(),
            volume_ratio=3.0,  # Высокий объем
            cmf=0.15,  # Накопление
            volume_trend="РАСТЕТ",
            unusual_volume_detected=True
        )
        
        signals = self.analyzer.get_volume_signals(indicators)
        
        self.assertIn('unusual_volume', signals)
        self.assertEqual(signals['unusual_volume'], 'ВНИМАНИЕ - НЕОБЫЧНЫЙ ОБЪЕМ')
        
        self.assertIn('volume_ratio', signals)
        self.assertEqual(signals['volume_ratio'], 'ВЫСОКИЙ ИНТЕРЕС')
        
        self.assertIn('cmf', signals)
        self.assertEqual(signals['cmf'], 'НАКОПЛЕНИЕ')
        
        self.assertIn('volume_trend', signals)
        self.assertEqual(signals['volume_trend'], 'РАСТУЩИЙ ИНТЕРЕС')
    
    def test_analyze_session_volume_pattern(self):
        """Тест анализа паттернов объема в течение торговой сессии"""
        # Данные для полной торговой сессии MOEX
        session_hours = list(range(10, 19)) + list(range(19, 24))  # 10:00-18:00 + 19:00-23:00
        hourly_volumes = [1000, 1500, 2000, 2500, 3000, 2800, 2200, 1800, 1500,  # Основная сессия
                         800, 600, 500, 400, 300]  # Вечерняя сессия
        
        result = self.analyzer.analyze_session_volume_pattern(hourly_volumes, session_hours)
        
        self.assertIn('main_session', result)
        self.assertIn('evening_session', result)
        self.assertIn('session_comparison', result)
        
        # Проверяем основную сессию
        main_session = result['main_session']
        self.assertIn('total_volume', main_session)
        self.assertIn('avg_volume', main_session)
        self.assertIn('peak_hour_volume', main_session)
        
        # Проверяем сравнение сессий
        comparison = result['session_comparison']
        self.assertIn('dominant_session', comparison)
        self.assertEqual(comparison['dominant_session'], 'ОСНОВНАЯ')  # Основная сессия должна быть доминирующей
        
        # Тест с неправильными данными
        result = self.analyzer.analyze_session_volume_pattern([1000], [10, 11])
        self.assertEqual(result, {})
    
    def test_russian_market_adaptations(self):
        """Тест адаптаций для российского рынка"""
        # Проверяем, что коэффициент российского рынка применяется
        self.assertEqual(self.analyzer.russian_market_multiplier, 1.5)
        
        # Проверяем время торговых сессий MOEX
        self.assertEqual(self.analyzer.main_session_start, 10)
        self.assertEqual(self.analyzer.main_session_end, 18)
        self.assertEqual(self.analyzer.evening_session_start, 19)
        self.assertEqual(self.analyzer.evening_session_end, 23)
        
        # Проверяем адаптированный порог необычного объема
        normal_volume = 1000
        volumes = [1000] * 20
        
        # Объем, который был бы необычным без адаптации
        test_volume = 2500  # 2.5x от среднего
        
        # С адаптацией порог становится выше (2.0 * 1.5 = 3.0)
        result = self.analyzer.detect_unusual_volume(test_volume, volumes)
        self.assertFalse(result)  # Не должен считаться необычным
        
        # Действительно необычный объем для российского рынка
        high_volume = 4000  # 4x от среднего
        result = self.analyzer.detect_unusual_volume(high_volume, volumes)
        self.assertTrue(result)  # Должен считаться необычным


if __name__ == '__main__':
    unittest.main()