"""
Тесты для сервиса распознавания именованных сущностей российских компаний.
"""

import pytest
from unittest.mock import Mock, patch
import sys
import os

# Добавляем путь к модулям проекта
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from russian_trading_bot.services.entity_recognizer import (
    RussianEntityRecognizer,
    RussianCompanyDictionary,
    CompanyEntity,
    EntityRecognitionResult
)


class TestRussianCompanyDictionary:
    """Тесты для словаря российских компаний."""
    
    def setup_method(self):
        """Настройка перед каждым тестом."""
        self.dictionary = RussianCompanyDictionary()
    
    def test_initialization(self):
        """Тест инициализации словаря."""
        assert len(self.dictionary.companies_data) > 0
        assert len(self.dictionary.ticker_to_company) > 0
        assert len(self.dictionary.alias_to_ticker) > 0
    
    def test_get_ticker_by_alias(self):
        """Тест получения тикера по алиасу."""
        # Тестируем основные алиасы
        assert self.dictionary.get_ticker_by_alias('сбер') == 'SBER'
        assert self.dictionary.get_ticker_by_alias('сбербанк') == 'SBER'
        assert self.dictionary.get_ticker_by_alias('газпром') == 'GAZP'
        assert self.dictionary.get_ticker_by_alias('лукойл') == 'LKOH'
        
        # Тестируем регистронезависимость
        assert self.dictionary.get_ticker_by_alias('СБЕР') == 'SBER'
        assert self.dictionary.get_ticker_by_alias('Газпром') == 'GAZP'
        
        # Тестируем несуществующий алиас
        assert self.dictionary.get_ticker_by_alias('несуществующая_компания') is None
    
    def test_get_company_data(self):
        """Тест получения данных компании по тикеру."""
        sber_data = self.dictionary.get_company_data('SBER')
        assert sber_data is not None
        assert sber_data['name'] == 'Сбербанк'
        assert sber_data['sector'] == 'Банки'
        assert 'сбер' in sber_data['aliases']
        
        # Тестируем несуществующий тикер
        assert self.dictionary.get_company_data('FAKE') is None
    
    def test_get_all_tickers(self):
        """Тест получения всех тикеров."""
        tickers = self.dictionary.get_all_tickers()
        assert isinstance(tickers, list)
        assert len(tickers) > 0
        assert 'SBER' in tickers
        assert 'GAZP' in tickers
    
    def test_get_companies_by_sector(self):
        """Тест получения компаний по сектору."""
        banks = self.dictionary.get_companies_by_sector('Банки')
        assert isinstance(banks, list)
        assert 'SBER' in banks
        assert 'TCS' in banks
        
        oil_gas = self.dictionary.get_companies_by_sector('Нефть и газ')
        assert 'GAZP' in oil_gas
        assert 'LKOH' in oil_gas


class TestRussianEntityRecognizer:
    """Тесты для распознавателя сущностей."""
    
    def setup_method(self):
        """Настройка перед каждым тестом."""
        # Мокаем NLP pipeline для ускорения тестов
        with patch('russian_trading_bot.services.entity_recognizer.RussianNLPPipeline'):
            self.recognizer = RussianEntityRecognizer()
    
    def test_initialization(self):
        """Тест инициализации распознавателя."""
        assert self.recognizer.company_dict is not None
        assert self.recognizer.confidence_threshold == 0.5
    
    def test_recognize_entities_simple(self):
        """Тест простого распознавания сущностей."""
        text = "Акции Сбербанка выросли на 5% после публикации отчетности."
        result = self.recognizer.recognize_entities(text)
        
        assert isinstance(result, EntityRecognitionResult)
        assert len(result.companies) > 0
        assert 'SBER' in result.tickers_mentioned
        assert result.confidence_score > 0
    
    def test_recognize_entities_multiple_companies(self):
        """Тест распознавания нескольких компаний."""
        text = "Сегодня выросли акции Газпрома и Лукойла, а Сбербанк остался без изменений."
        result = self.recognizer.recognize_entities(text)
        
        expected_tickers = {'GAZP', 'LKOH', 'SBER'}
        found_tickers = set(result.tickers_mentioned)
        
        assert len(expected_tickers.intersection(found_tickers)) >= 2
        assert len(result.companies) >= 2
    
    def test_recognize_entities_with_direct_tickers(self):
        """Тест распознавания прямых упоминаний тикеров."""
        text = "Рекомендуем покупать SBER и GAZP на текущих уровнях."
        result = self.recognizer.recognize_entities(text)
        
        assert 'SBER' in result.tickers_mentioned
        assert 'GAZP' in result.tickers_mentioned
    
    def test_recognize_entities_empty_text(self):
        """Тест обработки пустого текста."""
        result = self.recognizer.recognize_entities("")
        
        assert len(result.companies) == 0
        assert len(result.tickers_mentioned) == 0
        assert result.confidence_score == 0.0
    
    def test_recognize_entities_no_companies(self):
        """Тест текста без упоминаний компаний."""
        text = "Сегодня хорошая погода, завтра будет дождь."
        result = self.recognizer.recognize_entities(text)
        
        assert len(result.companies) == 0
        assert len(result.tickers_mentioned) == 0
    
    def test_link_news_to_stocks(self):
        """Тест связывания новости с акциями."""
        title = "Сбербанк увеличил прибыль"
        text = "ПАО Сбербанк опубликовал финансовые результаты за квартал."
        
        result = self.recognizer.link_news_to_stocks(text, title)
        
        assert isinstance(result, dict)
        assert 'tickers' in result
        assert 'companies' in result
        assert 'sectors_affected' in result
        assert 'SBER' in result['tickers']
    
    def test_get_company_info(self):
        """Тест получения информации о компании."""
        info = self.recognizer.get_company_info('SBER')
        
        assert info is not None
        assert info['name'] == 'Сбербанк'
        assert info['sector'] == 'Банки'
    
    def test_search_companies(self):
        """Тест поиска компаний."""
        results = self.recognizer.search_companies('сбер')
        
        assert len(results) > 0
        assert any(company['ticker'] == 'SBER' for company in results)
        
        # Тест поиска по сектору
        results = self.recognizer.search_companies('банк')
        bank_tickers = [company['ticker'] for company in results]
        assert 'SBER' in bank_tickers or 'TCS' in bank_tickers
    
    def test_set_confidence_threshold(self):
        """Тест установки порога уверенности."""
        self.recognizer.set_confidence_threshold(0.5)
        assert self.recognizer.confidence_threshold == 0.5
        
        # Тест неверного значения
        with pytest.raises(ValueError):
            self.recognizer.set_confidence_threshold(1.5)
    
    def test_get_statistics(self):
        """Тест получения статистики."""
        stats = self.recognizer.get_statistics()
        
        assert isinstance(stats, dict)
        assert 'total_companies' in stats
        assert 'total_aliases' in stats
        assert 'sectors' in stats
        assert stats['total_companies'] > 0


class TestCompanyEntity:
    """Тесты для сущности компании."""
    
    def test_company_entity_creation(self):
        """Тест создания сущности компании."""
        entity = CompanyEntity(
            name="Сбербанк",
            ticker="SBER",
            aliases=["сбер", "сбербанк"],
            sector="Банки",
            full_name="ПАО Сбербанк России",
            confidence=0.9,
            start_pos=10,
            end_pos=18
        )
        
        assert entity.name == "Сбербанк"
        assert entity.ticker == "SBER"
        assert entity.confidence == 0.9
        assert entity.start_pos == 10
        assert entity.end_pos == 18


class TestEntityRecognitionResult:
    """Тесты для результата распознавания сущностей."""
    
    def test_entity_recognition_result_creation(self):
        """Тест создания результата распознавания."""
        companies = [
            CompanyEntity(
                name="Сбербанк",
                ticker="SBER",
                aliases=["сбер"],
                sector="Банки",
                full_name="ПАО Сбербанк России"
            )
        ]
        
        result = EntityRecognitionResult(
            text="Тестовый текст",
            companies=companies,
            tickers_mentioned=["SBER"],
            confidence_score=0.8,
            processing_time=0.1
        )
        
        assert result.text == "Тестовый текст"
        assert len(result.companies) == 1
        assert result.tickers_mentioned == ["SBER"]
        assert result.confidence_score == 0.8
        assert result.processing_time == 0.1


class TestIntegrationScenarios:
    """Интеграционные тесты для реальных сценариев."""
    
    def setup_method(self):
        """Настройка перед каждым тестом."""
        with patch('russian_trading_bot.services.entity_recognizer.RussianNLPPipeline'):
            self.recognizer = RussianEntityRecognizer()
    
    def test_financial_news_scenario(self):
        """Тест сценария обработки финансовой новости."""
        news_text = """
        Московская биржа: итоги торгов 15 декабря
        
        По итогам торговой сессии 15 декабря индекс MOEX вырос на 1,2%.
        Лидерами роста стали акции Сбербанка (+3,1%), Газпрома (+2,8%) и Лукойла (+2,3%).
        Бумаги Яндекса потеряли 1,5% на фоне новостей о регулировании IT-сектора.
        Капитализация Норникеля достигла 2,1 трлн рублей.
        """
        
        result = self.recognizer.recognize_entities(news_text)
        
        # Проверяем, что найдены основные компании
        expected_tickers = {'SBER', 'GAZP', 'LKOH', 'YNDX', 'GMKN'}
        found_tickers = set(result.tickers_mentioned)
        
        # Должно быть найдено минимум 3 компании из 5
        assert len(expected_tickers.intersection(found_tickers)) >= 3
        
        # Проверяем качество распознавания
        assert result.confidence_score > 0.5
        assert len(result.companies) >= 3
    
    def test_sector_analysis_scenario(self):
        """Тест сценария анализа по секторам."""
        news_text = """
        Банковский сектор показал уверенный рост.
        Сбербанк и ВТБ продемонстрировали лучшую динамику среди банков.
        Тинькофф Банк также показал положительные результаты.
        """
        
        linking_result = self.recognizer.link_news_to_stocks(news_text)
        
        # Проверяем, что найдены банки
        assert 'sectors_affected' in linking_result
        sectors = linking_result['sectors_affected']
        
        # Должен быть найден банковский сектор
        assert 'Банки' in sectors or any('банк' in sector.lower() for sector in sectors.keys())
        
        # Проверяем конкретные банки
        bank_tickers = {'SBER', 'VTBR', 'TCS'}
        found_tickers = set(linking_result['tickers'])
        assert len(bank_tickers.intersection(found_tickers)) >= 2
    
    def test_mixed_content_scenario(self):
        """Тест сценария смешанного контента."""
        news_text = """
        Аналитики рекомендуют SBER и GAZP к покупке.
        Также стоит обратить внимание на акции Магнита в ритейл-секторе.
        Роснефть может показать хорошие результаты в следующем квартале.
        """
        
        result = self.recognizer.recognize_entities(news_text)
        
        # Проверяем смешанное распознавание (тикеры + названия)
        expected_tickers = {'SBER', 'GAZP', 'MGNT', 'ROSN'}
        found_tickers = set(result.tickers_mentioned)
        
        assert len(expected_tickers.intersection(found_tickers)) >= 3
        
        # Проверяем разные секторы
        sectors = set()
        for company in result.companies:
            sectors.add(company.sector)
        
        assert len(sectors) >= 2  # Должно быть минимум 2 разных сектора


if __name__ == '__main__':
    pytest.main([__file__, '-v'])