"""
Unit tests for Russian news aggregation service
Тесты для сервиса агрегации российских новостей
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import feedparser

from russian_trading_bot.services.news_aggregator import (
    RussianNewsAggregator, RussianNewsSource, NewsDeduplicator,
    NewsAggregatorError, NewsSourceError, NewsParsingError,
    create_news_aggregator, create_custom_source
)
from russian_trading_bot.models.news_data import RussianNewsArticle, NewsAggregation


class TestRussianNewsSource:
    """Тесты для источника новостей"""
    
    def test_valid_source_creation(self):
        """Тест: создание валидного источника"""
        source = RussianNewsSource(
            name="RBC",
            rss_url="https://rbc.ru/rss/rbcnews.rss",
            base_url="https://rbc.ru"
        )
        
        assert source.name == "RBC"
        assert source.rss_url == "https://rbc.ru/rss/rbcnews.rss"
        assert source.base_url == "https://rbc.ru"
        assert source.encoding == "utf-8"
        assert source.update_interval_minutes == 15
        assert source.max_articles_per_fetch == 50
    
    def test_invalid_source_creation(self):
        """Тест: создание невалидного источника"""
        with pytest.raises(ValueError, match="Invalid Russian news source"):
            RussianNewsSource(
                name="INVALID_SOURCE",
                rss_url="https://example.com/rss",
                base_url="https://example.com"
            )
    
    def test_custom_parameters(self):
        """Тест: пользовательские параметры источника"""
        source = RussianNewsSource(
            name="VEDOMOSTI",
            rss_url="https://vedomosti.ru/rss",
            base_url="https://vedomosti.ru",
            encoding="windows-1251",
            update_interval_minutes=30,
            max_articles_per_fetch=100
        )
        
        assert source.encoding == "windows-1251"
        assert source.update_interval_minutes == 30
        assert source.max_articles_per_fetch == 100


class TestNewsDeduplicator:
    """Тесты для дедупликатора новостей"""
    
    def test_exact_duplicate_detection(self):
        """Тест: обнаружение точных дубликатов"""
        deduplicator = NewsDeduplicator()
        
        article1 = RussianNewsArticle(
            title="Тестовая новость",
            content="Содержание тестовой новости",
            source="RBC",
            timestamp=datetime.now()
        )
        
        article2 = RussianNewsArticle(
            title="Тестовая новость",
            content="Содержание тестовой новости",
            source="VEDOMOSTI",
            timestamp=datetime.now()
        )
        
        assert not deduplicator.is_duplicate(article1)
        assert deduplicator.is_duplicate(article2)
    
    def test_similar_title_detection(self):
        """Тест: обнаружение схожих заголовков"""
        deduplicator = NewsDeduplicator(similarity_threshold=0.7)
        
        article1 = RussianNewsArticle(
            title="Сбербанк увеличил прибыль на 20 процентов",
            content="Содержание 1",
            source="RBC",
            timestamp=datetime.now()
        )
        
        article2 = RussianNewsArticle(
            title="Сбербанк увеличил прибыль на 20%",
            content="Содержание 2",
            source="VEDOMOSTI",
            timestamp=datetime.now()
        )
        
        assert not deduplicator.is_duplicate(article1)
        assert deduplicator.is_duplicate(article2)
    
    def test_different_articles(self):
        """Тест: разные статьи не считаются дубликатами"""
        deduplicator = NewsDeduplicator()
        
        article1 = RussianNewsArticle(
            title="Сбербанк увеличил прибыль",
            content="Содержание о Сбербанке",
            source="RBC",
            timestamp=datetime.now()
        )
        
        article2 = RussianNewsArticle(
            title="Газпром снизил добычу",
            content="Содержание о Газпроме",
            source="VEDOMOSTI",
            timestamp=datetime.now()
        )
        
        assert not deduplicator.is_duplicate(article1)
        assert not deduplicator.is_duplicate(article2)


class TestRussianNewsAggregator:
    """Тесты для агрегатора новостей"""
    
    @pytest.fixture
    def aggregator(self):
        """Фикстура для создания агрегатора"""
        return RussianNewsAggregator()
    
    @pytest.fixture
    def mock_rss_content(self):
        """Мок RSS контента"""
        return """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Test RSS</title>
                <item>
                    <title>Сбербанк увеличил прибыль</title>
                    <description>Сбербанк отчитался о росте прибыли на 15%</description>
                    <link>https://example.com/news1</link>
                    <pubDate>Mon, 01 Jan 2024 10:00:00 GMT</pubDate>
                    <author>Тестовый автор</author>
                </item>
                <item>
                    <title>Газпром объявил дивиденды</title>
                    <description>Газпром рекомендовал дивиденды акционерам</description>
                    <link>https://example.com/news2</link>
                    <pubDate>Mon, 01 Jan 2024 11:00:00 GMT</pubDate>
                </item>
            </channel>
        </rss>"""
    
    def test_aggregator_initialization(self, aggregator):
        """Тест: инициализация агрегатора"""
        assert len(aggregator.sources) == 5  # DEFAULT_SOURCES
        assert aggregator.max_concurrent_requests == 5
        assert aggregator.request_timeout == 30
        assert aggregator.enable_deduplication is True
        assert aggregator.deduplicator is not None
    
    def test_custom_aggregator_initialization(self):
        """Тест: инициализация с пользовательскими параметрами"""
        custom_source = RussianNewsSource(
            name="RBC",
            rss_url="https://rbc.ru/rss",
            base_url="https://rbc.ru"
        )
        
        aggregator = RussianNewsAggregator(
            sources=[custom_source],
            max_concurrent_requests=10,
            request_timeout=60,
            enable_deduplication=False
        )
        
        assert len(aggregator.sources) == 1
        assert aggregator.sources[0].name == "RBC"
        assert aggregator.max_concurrent_requests == 10
        assert aggregator.request_timeout == 60
        assert aggregator.enable_deduplication is False
        assert aggregator.deduplicator is None
    
    def test_parse_rss_feed(self, aggregator, mock_rss_content):
        """Тест: парсинг RSS фида"""
        source = RussianNewsSource(
            name="RBC",
            rss_url="https://rbc.ru/rss",
            base_url="https://rbc.ru"
        )
        
        articles = aggregator._parse_rss_feed(mock_rss_content, source)
        
        assert len(articles) == 2
        
        # Проверяем первую статью
        article1 = articles[0]
        assert article1.title == "Сбербанк увеличил прибыль"
        assert "Сбербанк отчитался о росте прибыли" in article1.content
        assert article1.source == "RBC"
        assert article1.url == "https://example.com/news1"
        assert article1.author == "Тестовый автор"
        assert article1.language == "ru"
        assert article1.is_financial is True  # Должно автоматически определиться
        assert "SBER" in article1.mentioned_stocks  # Должно автоматически извлечься
        
        # Проверяем вторую статью
        article2 = articles[1]
        assert article2.title == "Газпром объявил дивиденды"
        assert article2.source == "RBC"
        assert article2.author is None
    
    @pytest.mark.asyncio
    async def test_fetch_rss_feed_success(self, aggregator):
        """Тест: успешное получение RSS фида"""
        source = RussianNewsSource(
            name="RBC",
            rss_url="https://rbc.ru/rss",
            base_url="https://rbc.ru"
        )
        
        # Используем patch для мокирования aiohttp запроса
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value="<rss>test content</rss>")
            
            # Мокаем контекстный менеджер
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await aggregator._fetch_rss_feed(source)
            
            assert result == "<rss>test content</rss>"
    
    @pytest.mark.asyncio
    async def test_fetch_rss_feed_error(self, aggregator):
        """Тест: ошибка получения RSS фида"""
        source = RussianNewsSource(
            name="RBC",
            rss_url="https://rbc.ru/rss",
            base_url="https://rbc.ru"
        )
        
        # Мокаем HTTP сессию с ошибкой
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_session.get.return_value.__aenter__.return_value = mock_response
        
        aggregator.session = mock_session
        
        result = await aggregator._fetch_rss_feed(source)
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_fetch_source_articles(self, aggregator, mock_rss_content):
        """Тест: получение статей от источника"""
        source = RussianNewsSource(
            name="RBC",
            rss_url="https://rbc.ru/rss",
            base_url="https://rbc.ru"
        )
        
        # Мокаем получение RSS
        with patch.object(aggregator, '_fetch_rss_feed', return_value=mock_rss_content):
            articles = await aggregator._fetch_source_articles(source)
        
        assert len(articles) == 2
        assert all(isinstance(article, RussianNewsArticle) for article in articles)
        assert source.last_update is not None
    
    @pytest.mark.asyncio
    async def test_fetch_all_articles(self, aggregator):
        """Тест: получение всех статей"""
        # Создаем агрегатор с одним источником для упрощения теста
        single_source = RussianNewsSource(
            name="RBC",
            rss_url="https://rbc.ru/rss",
            base_url="https://rbc.ru"
        )
        test_aggregator = RussianNewsAggregator(sources=[single_source])
        
        # Мокаем получение статей от источников
        mock_articles = [
            RussianNewsArticle(
                title="Сбербанк увеличил прибыль",
                content="Банк показал рост прибыли и дивиденды акционерам",
                source="RBC",
                timestamp=datetime.now()
            ),
            RussianNewsArticle(
                title="Погода в Москве",
                content="Завтра будет солнечно и тепло",
                source="RBC",
                timestamp=datetime.now()
            )
        ]
        
        with patch.object(test_aggregator, '_fetch_source_articles', return_value=mock_articles):
            # Тест с только финансовыми новостями
            financial_articles = await test_aggregator.fetch_all_articles(financial_only=True)
            assert len(financial_articles) == 1
            assert financial_articles[0].is_financial is True
            
            # Тест со всеми новостями
            all_articles = await test_aggregator.fetch_all_articles(financial_only=False)
            assert len(all_articles) == 2
    
    @pytest.mark.asyncio
    async def test_fetch_articles_by_keywords(self, aggregator):
        """Тест: получение статей по ключевым словам"""
        mock_articles = [
            RussianNewsArticle(
                title="Сбербанк увеличил прибыль",
                content="Банк показал хорошие результаты",
                source="RBC",
                timestamp=datetime.now()
            ),
            RussianNewsArticle(
                title="Газпром снизил добычу",
                content="Компания сократила производство",
                source="VEDOMOSTI",
                timestamp=datetime.now()
            )
        ]
        
        with patch.object(aggregator, 'fetch_all_articles', return_value=mock_articles):
            # Поиск по ключевому слову "Сбербанк"
            sber_articles = await aggregator.fetch_articles_by_keywords(["Сбербанк"])
            assert len(sber_articles) == 1
            assert "Сбербанк" in sber_articles[0].title
            
            # Поиск по ключевому слову "компания"
            company_articles = await aggregator.fetch_articles_by_keywords(["компания"])
            assert len(company_articles) == 1
            assert "Газпром" in company_articles[0].title
    
    @pytest.mark.asyncio
    async def test_fetch_articles_by_stocks(self, aggregator):
        """Тест: получение статей по тикерам акций"""
        mock_articles = [
            RussianNewsArticle(
                title="Новости Сбербанка",
                content="Содержание о SBER",
                source="RBC",
                timestamp=datetime.now(),
                mentioned_stocks=["SBER"]
            ),
            RussianNewsArticle(
                title="Новости Газпрома",
                content="Содержание о GAZP",
                source="VEDOMOSTI",
                timestamp=datetime.now(),
                mentioned_stocks=["GAZP"]
            )
        ]
        
        with patch.object(aggregator, 'fetch_all_articles', return_value=mock_articles):
            stock_articles = await aggregator.fetch_articles_by_stocks(["SBER", "GAZP"])
            
            assert "SBER" in stock_articles
            assert "GAZP" in stock_articles
            assert len(stock_articles["SBER"]) == 1
            assert len(stock_articles["GAZP"]) == 1
    
    @pytest.mark.asyncio
    async def test_get_news_summary(self, aggregator):
        """Тест: получение сводки новостей"""
        mock_articles = [
            RussianNewsArticle(
                title="Финансовая новость 1",
                content="Содержание о SBER",
                source="RBC",
                timestamp=datetime.now(),
                mentioned_stocks=["SBER"],
                is_financial=True
            ),
            RussianNewsArticle(
                title="Финансовая новость 2",
                content="Содержание о GAZP",
                source="VEDOMOSTI",
                timestamp=datetime.now(),
                mentioned_stocks=["GAZP"],
                is_financial=True
            ),
            RussianNewsArticle(
                title="Обычная новость",
                content="Обычное содержание",
                source="RBC",
                timestamp=datetime.now(),
                is_financial=False
            )
        ]
        
        with patch.object(aggregator, 'fetch_all_articles', return_value=mock_articles):
            summary = await aggregator.get_news_summary()
            
            assert isinstance(summary, NewsAggregation)
            assert summary.total_articles == 3
            assert summary.financial_articles == 2
            assert len(summary.top_mentioned_stocks) == 2
            assert summary.top_mentioned_stocks[0][0] in ["SBER", "GAZP"]
            assert len(summary.top_sources) >= 1
    
    def test_add_remove_source(self, aggregator):
        """Тест: добавление и удаление источников"""
        initial_count = len(aggregator.sources)
        
        # Добавляем новый источник
        new_source = RussianNewsSource(
            name="TASS",
            rss_url="https://tass.ru/rss",
            base_url="https://tass.ru"
        )
        
        aggregator.add_source(new_source)
        assert len(aggregator.sources) == initial_count + 1
        
        # Удаляем источник
        aggregator.remove_source("TASS")
        assert len(aggregator.sources) == initial_count
    
    def test_clear_cache(self, aggregator):
        """Тест: очистка кэша"""
        # Добавляем данные в кэш
        aggregator._articles_cache = [
            RussianNewsArticle(
                title="Тест",
                content="Содержание",
                source="RBC",
                timestamp=datetime.now()
            )
        ]
        aggregator._cache_last_update = datetime.now()
        
        # Очищаем кэш
        aggregator.clear_cache()
        
        assert len(aggregator._articles_cache) == 0
        assert aggregator._cache_last_update is None


class TestHelperFunctions:
    """Тесты для вспомогательных функций"""
    
    @pytest.mark.asyncio
    async def test_create_news_aggregator(self):
        """Тест: создание агрегатора новостей"""
        aggregator = await create_news_aggregator()
        
        assert isinstance(aggregator, RussianNewsAggregator)
        assert aggregator.session is not None
        
        await aggregator.close()
    
    def test_create_custom_source(self):
        """Тест: создание пользовательского источника"""
        source = create_custom_source(
            name="RBC",
            rss_url="https://rbc.ru/rss",
            base_url="https://rbc.ru",
            encoding="utf-8",
            update_interval_minutes=10
        )
        
        assert isinstance(source, RussianNewsSource)
        assert source.name == "RBC"
        assert source.encoding == "utf-8"
        assert source.update_interval_minutes == 10


if __name__ == "__main__":
    # Запуск тестов
    pytest.main([__file__, "-v"])