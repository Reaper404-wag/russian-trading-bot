"""
Russian news aggregation service
Сервис агрегации российских финансовых новостей
"""

import asyncio
import aiohttp
import feedparser
import logging
from typing import List, Dict, Optional, Any, Set
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
import re
import hashlib
from dataclasses import asdict
import xml.etree.ElementTree as ET

from russian_trading_bot.models.news_data import (
    RussianNewsArticle, NewsAnalysisResult, NewsAggregation,
    VALID_RUSSIAN_NEWS_SOURCES, detect_russian_financial_content,
    extract_mentioned_tickers, create_news_summary, filter_financial_news
)


logger = logging.getLogger(__name__)


class NewsAggregatorError(Exception):
    """Исключение для ошибок агрегатора новостей"""
    pass


class NewsSourceError(NewsAggregatorError):
    """Исключение для ошибок источников новостей"""
    pass


class NewsParsingError(NewsAggregatorError):
    """Исключение для ошибок парсинга новостей"""
    pass


class RussianNewsSource:
    """Конфигурация источника российских новостей"""
    
    def __init__(self, 
                 name: str,
                 rss_url: str,
                 base_url: str,
                 encoding: str = 'utf-8',
                 update_interval_minutes: int = 15,
                 max_articles_per_fetch: int = 50):
        self.name = name.upper()
        self.rss_url = rss_url
        self.base_url = base_url
        self.encoding = encoding
        self.update_interval_minutes = update_interval_minutes
        self.max_articles_per_fetch = max_articles_per_fetch
        self.last_update = None
        
        if self.name not in VALID_RUSSIAN_NEWS_SOURCES:
            raise ValueError(f"Invalid Russian news source: {name}")


class NewsDeduplicator:
    """Дедупликатор новостей для избежания дублирования"""
    
    def __init__(self, similarity_threshold: float = 0.8):
        self.similarity_threshold = similarity_threshold
        self.seen_articles: Set[str] = set()
        self.title_hashes: Dict[str, str] = {}
    
    def _calculate_content_hash(self, title: str, content: str) -> str:
        """Вычислить хэш контента статьи"""
        combined = f"{title.lower().strip()} {content.lower().strip()}"
        return hashlib.md5(combined.encode('utf-8')).hexdigest()
    
    def _calculate_title_similarity(self, title1: str, title2: str) -> float:
        """Вычислить схожесть заголовков"""
        import string
        
        def normalize_title(title):
            # Нормализуем различные варианты написания
            title = title.replace('%', ' процентов')
            title = title.replace('₽', ' рублей')
            title = title.replace('$', ' долларов')
            title = title.replace('€', ' евро')
            
            # Убираем знаки препинания
            translator = str.maketrans('', '', string.punctuation)
            normalized = title.translate(translator).lower().strip()
            
            # Убираем лишние пробелы
            return ' '.join(normalized.split())
        
        norm_title1 = normalize_title(title1)
        norm_title2 = normalize_title(title2)
        
        words1 = set(norm_title1.split())
        words2 = set(norm_title2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        # Базовый коэффициент Жаккара
        jaccard_similarity = len(intersection) / len(union) if union else 0.0
        
        # Дополнительные проверки для повышения точности
        
        # 1. Проверяем ключевые слова (длиннее 3 символов)
        key_words1 = {word for word in words1 if len(word) > 3}
        key_words2 = {word for word in words2 if len(word) > 3}
        
        key_similarity = 0.0
        if key_words1 and key_words2:
            key_intersection = key_words1.intersection(key_words2)
            key_similarity = len(key_intersection) / max(len(key_words1), len(key_words2))
        
        # 2. Проверяем порядок слов (для очень похожих заголовков)
        sequence_similarity = 0.0
        if jaccard_similarity > 0.5:
            words1_list = norm_title1.split()
            words2_list = norm_title2.split()
            
            # Простая проверка последовательности
            common_sequences = 0
            for i in range(min(len(words1_list), len(words2_list))):
                if words1_list[i] == words2_list[i]:
                    common_sequences += 1
                else:
                    break
            
            sequence_similarity = common_sequences / max(len(words1_list), len(words2_list))
        
        # Комбинируем все метрики
        final_similarity = (jaccard_similarity * 0.5 + key_similarity * 0.3 + sequence_similarity * 0.2)
        
        return min(final_similarity, 1.0)
    
    def is_duplicate(self, article: RussianNewsArticle) -> bool:
        """Проверить, является ли статья дубликатом"""
        content_hash = self._calculate_content_hash(article.title, article.content)
        
        # Проверяем точное совпадение по хэшу
        if content_hash in self.seen_articles:
            return True
        
        # Проверяем схожесть заголовков
        for existing_title, existing_hash in self.title_hashes.items():
            similarity = self._calculate_title_similarity(article.title, existing_title)
            if similarity >= self.similarity_threshold:
                logger.debug(f"Найден дубликат по схожести заголовков: {similarity:.2f}")
                return True
        
        # Добавляем в список просмотренных
        self.seen_articles.add(content_hash)
        self.title_hashes[article.title] = content_hash
        
        return False
    
    def clear_old_entries(self, max_age_hours: int = 24):
        """Очистить старые записи для экономии памяти"""
        # В реальной реализации здесь была бы логика очистки по времени
        # Для простоты очищаем все, если слишком много записей
        if len(self.seen_articles) > 10000:
            self.seen_articles.clear()
            self.title_hashes.clear()
            logger.info("Очищен кэш дедупликатора новостей")


class RussianNewsAggregator:
    """Агрегатор российских финансовых новостей"""
    
    # Предустановленные источники российских новостей
    DEFAULT_SOURCES = [
        RussianNewsSource(
            name="RBC",
            rss_url="https://rbc.ru/rss/rbcnews.rss",
            base_url="https://rbc.ru",
            update_interval_minutes=10
        ),
        RussianNewsSource(
            name="VEDOMOSTI",
            rss_url="https://www.vedomosti.ru/rss/news",
            base_url="https://www.vedomosti.ru",
            update_interval_minutes=15
        ),
        RussianNewsSource(
            name="INTERFAX",
            rss_url="https://www.interfax.ru/rss.asp",
            base_url="https://www.interfax.ru",
            update_interval_minutes=10
        ),
        RussianNewsSource(
            name="KOMMERSANT",
            rss_url="https://www.kommersant.ru/RSS/news.xml",
            base_url="https://www.kommersant.ru",
            update_interval_minutes=15
        ),
        RussianNewsSource(
            name="PRIME",
            rss_url="https://1prime.ru/export/rss2/index.xml",
            base_url="https://1prime.ru",
            update_interval_minutes=20
        )
    ]
    
    def __init__(self, 
                 sources: Optional[List[RussianNewsSource]] = None,
                 max_concurrent_requests: int = 5,
                 request_timeout: int = 30,
                 enable_deduplication: bool = True):
        """
        Инициализация агрегатора новостей
        
        Args:
            sources: Список источников новостей
            max_concurrent_requests: Максимум одновременных запросов
            request_timeout: Таймаут запроса в секундах
            enable_deduplication: Включить дедупликацию
        """
        self.sources = sources or self.DEFAULT_SOURCES
        self.max_concurrent_requests = max_concurrent_requests
        self.request_timeout = request_timeout
        self.enable_deduplication = enable_deduplication
        
        self.session: Optional[aiohttp.ClientSession] = None
        self.deduplicator = NewsDeduplicator() if enable_deduplication else None
        
        # Кэш статей
        self._articles_cache: List[RussianNewsArticle] = []
        self._cache_last_update: Optional[datetime] = None
        self._cache_ttl_minutes = 5
    
    async def __aenter__(self):
        """Асинхронный контекстный менеджер - вход"""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Асинхронный контекстный менеджер - выход"""
        await self.close()
    
    async def _ensure_session(self):
        """Создать HTTP сессию если её нет"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.request_timeout)
            headers = {
                'User-Agent': 'Russian-Trading-Bot-News-Aggregator/1.0',
                'Accept': 'application/rss+xml, application/xml, text/xml'
            }
            
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers,
                connector=aiohttp.TCPConnector(limit=self.max_concurrent_requests)
            )
    
    async def close(self):
        """Закрыть HTTP сессию"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _fetch_rss_feed(self, source: RussianNewsSource) -> Optional[str]:
        """
        Получить RSS фид от источника
        
        Args:
            source: Источник новостей
            
        Returns:
            Содержимое RSS фида или None при ошибке
        """
        try:
            await self._ensure_session()
            
            logger.debug(f"Получение RSS фида от {source.name}: {source.rss_url}")
            
            async with self.session.get(source.rss_url) as response:
                if response.status == 200:
                    content = await response.text(encoding=source.encoding)
                    logger.debug(f"Получен RSS фид от {source.name}, размер: {len(content)} символов")
                    return content
                else:
                    logger.warning(f"Ошибка получения RSS от {source.name}: HTTP {response.status}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.error(f"Таймаут при получении RSS от {source.name}")
            return None
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка соединения с {source.name}: {e}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при получении RSS от {source.name}: {e}")
            return None
    
    def _parse_rss_feed(self, rss_content: str, source: RussianNewsSource) -> List[RussianNewsArticle]:
        """
        Парсинг RSS фида в список статей
        
        Args:
            rss_content: Содержимое RSS фида
            source: Источник новостей
            
        Returns:
            Список статей
        """
        articles = []
        
        try:
            # Используем feedparser для парсинга RSS
            feed = feedparser.parse(rss_content)
            
            if feed.bozo:
                logger.warning(f"RSS фид от {source.name} содержит ошибки парсинга")
            
            logger.debug(f"Найдено {len(feed.entries)} записей в RSS от {source.name}")
            
            for entry in feed.entries[:source.max_articles_per_fetch]:
                try:
                    # Извлекаем основные поля
                    title = entry.get('title', '').strip()
                    summary = entry.get('summary', entry.get('description', '')).strip()
                    link = entry.get('link', '')
                    
                    if not title:
                        continue
                    
                    # Парсим дату публикации
                    published_parsed = entry.get('published_parsed')
                    if published_parsed:
                        timestamp = datetime(*published_parsed[:6])
                    else:
                        # Если дата не указана, используем текущее время
                        timestamp = datetime.now()
                    
                    # Извлекаем автора
                    author = entry.get('author', '')
                    
                    # Создаем статью
                    article = RussianNewsArticle(
                        title=title,
                        content=summary,  # В RSS обычно краткое содержание
                        source=source.name,
                        timestamp=timestamp,
                        url=link,
                        author=author if author else None,
                        language="ru"
                    )
                    
                    # Проверяем на дубликаты
                    if self.deduplicator and self.deduplicator.is_duplicate(article):
                        logger.debug(f"Пропускаем дубликат: {title[:50]}...")
                        continue
                    
                    articles.append(article)
                    
                except Exception as e:
                    logger.warning(f"Ошибка парсинга записи RSS от {source.name}: {e}")
                    continue
            
            logger.info(f"Успешно обработано {len(articles)} статей от {source.name}")
            
        except Exception as e:
            logger.error(f"Ошибка парсинга RSS фида от {source.name}: {e}")
            raise NewsParsingError(f"Не удалось парсить RSS от {source.name}: {e}")
        
        return articles
    
    async def _fetch_source_articles(self, source: RussianNewsSource) -> List[RussianNewsArticle]:
        """
        Получить статьи от одного источника
        
        Args:
            source: Источник новостей
            
        Returns:
            Список статей
        """
        try:
            # Проверяем, нужно ли обновлять источник
            if (source.last_update and 
                datetime.now() - source.last_update < timedelta(minutes=source.update_interval_minutes)):
                logger.debug(f"Пропускаем обновление {source.name} - слишком рано")
                return []
            
            # Получаем RSS фид
            rss_content = await self._fetch_rss_feed(source)
            if not rss_content:
                return []
            
            # Парсим статьи
            articles = self._parse_rss_feed(rss_content, source)
            
            # Обновляем время последнего обновления
            source.last_update = datetime.now()
            
            return articles
            
        except Exception as e:
            logger.error(f"Ошибка получения статей от {source.name}: {e}")
            raise NewsSourceError(f"Не удалось получить статьи от {source.name}: {e}")
    
    async def fetch_all_articles(self, 
                                financial_only: bool = True,
                                max_age_hours: int = 24) -> List[RussianNewsArticle]:
        """
        Получить статьи от всех источников
        
        Args:
            financial_only: Только финансовые новости
            max_age_hours: Максимальный возраст статей в часах
            
        Returns:
            Список статей
        """
        # Проверяем кэш
        if (self._cache_last_update and 
            datetime.now() - self._cache_last_update < timedelta(minutes=self._cache_ttl_minutes)):
            logger.debug("Используем кэшированные статьи")
            cached_articles = self._articles_cache
        else:
            # Получаем статьи от всех источников параллельно
            logger.info(f"Получение новостей от {len(self.sources)} источников...")
            
            tasks = [self._fetch_source_articles(source) for source in self.sources]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Собираем все статьи
            all_articles = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Ошибка получения статей от {self.sources[i].name}: {result}")
                    continue
                
                all_articles.extend(result)
            
            # Обновляем кэш
            self._articles_cache = all_articles
            self._cache_last_update = datetime.now()
            cached_articles = all_articles
        
        # Фильтруем по возрасту
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        recent_articles = [
            article for article in cached_articles
            if article.timestamp >= cutoff_time
        ]
        
        # Фильтруем только финансовые новости если требуется
        if financial_only:
            recent_articles = filter_financial_news(recent_articles)
        
        logger.info(f"Получено {len(recent_articles)} статей "
                   f"({'только финансовые' if financial_only else 'все'})")
        
        return recent_articles
    
    async def fetch_articles_by_keywords(self, 
                                       keywords: List[str],
                                       max_age_hours: int = 24) -> List[RussianNewsArticle]:
        """
        Получить статьи по ключевым словам
        
        Args:
            keywords: Список ключевых слов для поиска
            max_age_hours: Максимальный возраст статей в часах
            
        Returns:
            Список релевантных статей
        """
        all_articles = await self.fetch_all_articles(financial_only=False, max_age_hours=max_age_hours)
        
        # Фильтруем по ключевым словам
        keywords_lower = [kw.lower() for kw in keywords]
        relevant_articles = []
        
        for article in all_articles:
            article_text = f"{article.title} {article.content}".lower()
            
            # Проверяем наличие ключевых слов
            if any(keyword in article_text for keyword in keywords_lower):
                relevant_articles.append(article)
        
        logger.info(f"Найдено {len(relevant_articles)} статей по ключевым словам: {keywords}")
        
        return relevant_articles
    
    async def fetch_articles_by_stocks(self, 
                                     stock_symbols: List[str],
                                     max_age_hours: int = 24) -> Dict[str, List[RussianNewsArticle]]:
        """
        Получить статьи, упоминающие определенные акции
        
        Args:
            stock_symbols: Список тикеров акций
            max_age_hours: Максимальный возраст статей в часах
            
        Returns:
            Словарь тикер -> список статей
        """
        all_articles = await self.fetch_all_articles(financial_only=True, max_age_hours=max_age_hours)
        
        stock_articles = {}
        
        for symbol in stock_symbols:
            symbol_upper = symbol.upper()
            stock_articles[symbol_upper] = []
            
            for article in all_articles:
                if article.mentioned_stocks and symbol_upper in article.mentioned_stocks:
                    stock_articles[symbol_upper].append(article)
        
        # Логируем результаты
        for symbol, articles in stock_articles.items():
            logger.info(f"Найдено {len(articles)} статей для {symbol}")
        
        return stock_articles
    
    async def get_news_summary(self, 
                             max_age_hours: int = 24,
                             max_articles: int = 100) -> NewsAggregation:
        """
        Получить сводку новостей за период
        
        Args:
            max_age_hours: Максимальный возраст статей в часах
            max_articles: Максимальное количество статей для анализа
            
        Returns:
            Агрегированная сводка новостей
        """
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=max_age_hours)
        
        # Получаем все статьи
        all_articles = await self.fetch_all_articles(financial_only=False, max_age_hours=max_age_hours)
        
        # Ограничиваем количество для анализа
        articles_to_analyze = all_articles[:max_articles]
        
        # Подсчитываем статистику
        total_articles = len(articles_to_analyze)
        financial_articles = len(filter_financial_news(articles_to_analyze))
        
        # Распределение по источникам
        source_counts = {}
        for article in articles_to_analyze:
            source_counts[article.source] = source_counts.get(article.source, 0) + 1
        
        top_sources = sorted(source_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Наиболее упоминаемые акции
        stock_counts = {}
        for article in articles_to_analyze:
            if article.mentioned_stocks:
                for stock in article.mentioned_stocks:
                    stock_counts[stock] = stock_counts.get(stock, 0) + 1
        
        top_mentioned_stocks = sorted(stock_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Распределение по категориям
        category_counts = {}
        for article in articles_to_analyze:
            category = article.category or 'UNKNOWN'
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Создаем агрегацию
        aggregation = NewsAggregation(
            start_time=start_time,
            end_time=end_time,
            total_articles=total_articles,
            financial_articles=financial_articles,
            sentiment_distribution={'NEUTRAL': total_articles},  # Упрощенно
            top_mentioned_stocks=top_mentioned_stocks,
            top_sources=top_sources,
            category_distribution=category_counts,
            average_sentiment_score=0.0,  # Упрощенно
            market_impact_summary={'LOW': 1.0}  # Упрощенно
        )
        
        logger.info(f"Создана сводка новостей: {total_articles} статей, "
                   f"{financial_articles} финансовых")
        
        return aggregation
    
    def add_source(self, source: RussianNewsSource):
        """Добавить новый источник новостей"""
        if source.name not in [s.name for s in self.sources]:
            self.sources.append(source)
            logger.info(f"Добавлен источник новостей: {source.name}")
        else:
            logger.warning(f"Источник {source.name} уже существует")
    
    def remove_source(self, source_name: str):
        """Удалить источник новостей"""
        self.sources = [s for s in self.sources if s.name != source_name.upper()]
        logger.info(f"Удален источник новостей: {source_name}")
    
    def clear_cache(self):
        """Очистить кэш статей"""
        self._articles_cache.clear()
        self._cache_last_update = None
        if self.deduplicator:
            self.deduplicator.clear_old_entries(0)  # Очистить все
        logger.info("Очищен кэш агрегатора новостей")


# Вспомогательные функции

async def create_news_aggregator(sources: Optional[List[RussianNewsSource]] = None) -> RussianNewsAggregator:
    """
    Создать и инициализировать агрегатор новостей
    
    Args:
        sources: Список источников новостей
        
    Returns:
        Инициализированный агрегатор
    """
    aggregator = RussianNewsAggregator(sources=sources)
    await aggregator._ensure_session()
    return aggregator


def create_custom_source(name: str, 
                        rss_url: str, 
                        base_url: str,
                        **kwargs) -> RussianNewsSource:
    """
    Создать пользовательский источник новостей
    
    Args:
        name: Название источника
        rss_url: URL RSS фида
        base_url: Базовый URL сайта
        **kwargs: Дополнительные параметры
        
    Returns:
        Объект источника новостей
    """
    return RussianNewsSource(
        name=name,
        rss_url=rss_url,
        base_url=base_url,
        **kwargs
    )