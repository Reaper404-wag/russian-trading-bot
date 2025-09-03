#!/usr/bin/env python3
"""
Russian News Feeds Configuration and Management
Production-ready configuration for Russian financial news sources
"""

import os
import logging
import asyncio
import aiohttp
import feedparser
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class NewsSourceConfig:
    """Configuration for a news source"""
    name: str
    url: str
    source_type: str  # 'rss', 'api', 'scraper'
    language: str = 'ru'
    update_interval: int = 300  # seconds
    timeout: int = 30
    rate_limit: int = 5  # requests per minute
    api_key: Optional[str] = None
    headers: Optional[Dict] = None
    enabled: bool = True

class RussianNewsManager:
    """Manages Russian financial news sources"""
    
    def __init__(self):
        self.sources = self._initialize_sources()
        self.session: Optional[aiohttp.ClientSession] = None
        self.last_request_times = {}
        self.request_counts = {}
        self.error_counts = {}
        
    def _initialize_sources(self) -> Dict[str, NewsSourceConfig]:
        """Initialize Russian news sources configuration"""
        return {
            'rbc': NewsSourceConfig(
                name='RBC',
                url=os.getenv('RBC_RSS_URL', 'https://www.rbc.ru/v10/ajax/get-news-feed/project/rbcnews.rbc.ru/lastDate/'),
                source_type='api',
                update_interval=180,  # 3 minutes
                headers={'User-Agent': 'RussianTradingBot/1.0'}
            ),
            'vedomosti': NewsSourceConfig(
                name='Vedomosti',
                url=os.getenv('VEDOMOSTI_RSS_URL', 'https://www.vedomosti.ru/rss/news'),
                source_type='rss',
                update_interval=300,  # 5 minutes
                headers={'User-Agent': 'RussianTradingBot/1.0'}
            ),
            'kommersant': NewsSourceConfig(
                name='Kommersant',
                url=os.getenv('KOMMERSANT_RSS_URL', 'https://www.kommersant.ru/RSS/news.xml'),
                source_type='rss',
                update_interval=300,  # 5 minutes
                headers={'User-Agent': 'RussianTradingBot/1.0'}
            ),
            'interfax': NewsSourceConfig(
                name='Interfax',
                url=os.getenv('INTERFAX_API_URL', 'https://www.interfax.ru/rss.asp'),
                source_type='rss',
                update_interval=240,  # 4 minutes
                api_key=os.getenv('INTERFAX_API_KEY'),
                headers={'User-Agent': 'RussianTradingBot/1.0'}
            ),
            'tass': NewsSourceConfig(
                name='TASS',
                url='https://tass.ru/rss/v2.xml',
                source_type='rss',
                update_interval=360,  # 6 minutes
                headers={'User-Agent': 'RussianTradingBot/1.0'}
            ),
            'ria': NewsSourceConfig(
                name='RIA Novosti',
                url='https://ria.ru/export/rss2/archive/index.xml',
                source_type='rss',
                update_interval=300,  # 5 minutes
                headers={'User-Agent': 'RussianTradingBot/1.0'}
            ),
            'cbr': NewsSourceConfig(
                name='Central Bank of Russia',
                url='https://cbr.ru/rss/RssPress/',
                source_type='rss',
                update_interval=1800,  # 30 minutes
                headers={'User-Agent': 'RussianTradingBot/1.0'}
            )
        }
        
    async def __aenter__(self):
        """Async context manager entry"""
        connector = aiohttp.TCPConnector(
            limit=50,
            limit_per_host=5,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8'}
        )
        
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            
    async def _rate_limit(self, source_name: str, rate_limit: int):
        """Implement rate limiting per source"""
        current_time = time.time()
        last_request = self.last_request_times.get(source_name, 0)
        time_since_last = current_time - last_request
        
        min_interval = 60.0 / rate_limit  # Convert rate limit to minimum interval
        
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            await asyncio.sleep(sleep_time)
            
        self.last_request_times[source_name] = time.time()
        
    async def _fetch_rss_feed(self, source: NewsSourceConfig) -> Optional[List[Dict]]:
        """Fetch and parse RSS feed"""
        try:
            await self._rate_limit(source.name, source.rate_limit)
            
            headers = source.headers or {}
            
            async with self.session.get(source.url, headers=headers) as response:
                if response.status != 200:
                    logger.error(f"RSS feed {source.name} returned status {response.status}")
                    return None
                    
                content = await response.text()
                
                # Parse RSS feed
                feed = feedparser.parse(content)
                
                articles = []
                for entry in feed.entries[:20]:  # Limit to 20 most recent articles
                    article = {
                        'title': entry.get('title', ''),
                        'description': entry.get('description', ''),
                        'link': entry.get('link', ''),
                        'published': entry.get('published', ''),
                        'source': source.name,
                        'language': source.language,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    
                    # Extract publication date
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                        article['published_date'] = pub_date.isoformat()
                    
                    articles.append(article)
                    
                self.request_counts[source.name] = self.request_counts.get(source.name, 0) + 1
                logger.info(f"Fetched {len(articles)} articles from {source.name}")
                
                return articles
                
        except Exception as e:
            logger.error(f"Error fetching RSS feed from {source.name}: {e}")
            self.error_counts[source.name] = self.error_counts.get(source.name, 0) + 1
            return None
            
    async def _fetch_api_feed(self, source: NewsSourceConfig) -> Optional[List[Dict]]:
        """Fetch news from API endpoint"""
        try:
            await self._rate_limit(source.name, source.rate_limit)
            
            headers = source.headers or {}
            if source.api_key:
                headers['Authorization'] = f'Bearer {source.api_key}'
                
            params = {}
            if source.name.lower() == 'rbc':
                # RBC specific parameters
                params = {
                    'limit': 20,
                    'offset': 0,
                    'category': 'economics'
                }
                
            async with self.session.get(source.url, headers=headers, params=params) as response:
                if response.status != 200:
                    logger.error(f"API feed {source.name} returned status {response.status}")
                    return None
                    
                data = await response.json()
                
                articles = []
                
                if source.name.lower() == 'rbc':
                    # Parse RBC API response
                    items = data.get('items', [])
                    for item in items[:20]:
                        article = {
                            'title': item.get('title', ''),
                            'description': item.get('anons', ''),
                            'link': item.get('url', ''),
                            'published': item.get('publish_date', ''),
                            'source': source.name,
                            'language': source.language,
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        }
                        articles.append(article)
                        
                self.request_counts[source.name] = self.request_counts.get(source.name, 0) + 1
                logger.info(f"Fetched {len(articles)} articles from {source.name} API")
                
                return articles
                
        except Exception as e:
            logger.error(f"Error fetching API feed from {source.name}: {e}")
            self.error_counts[source.name] = self.error_counts.get(source.name, 0) + 1
            return None
            
    async def fetch_news_from_source(self, source_name: str) -> Optional[List[Dict]]:
        """Fetch news from a specific source"""
        if source_name not in self.sources:
            logger.error(f"Unknown news source: {source_name}")
            return None
            
        source = self.sources[source_name]
        
        if not source.enabled:
            logger.info(f"News source {source_name} is disabled")
            return None
            
        if source.source_type == 'rss':
            return await self._fetch_rss_feed(source)
        elif source.source_type == 'api':
            return await self._fetch_api_feed(source)
        else:
            logger.error(f"Unsupported source type: {source.source_type}")
            return None
            
    async def fetch_all_news(self) -> Dict[str, List[Dict]]:
        """Fetch news from all enabled sources"""
        results = {}
        
        tasks = []
        for source_name, source in self.sources.items():
            if source.enabled:
                task = asyncio.create_task(
                    self.fetch_news_from_source(source_name),
                    name=f"fetch_{source_name}"
                )
                tasks.append((source_name, task))
                
        # Wait for all tasks to complete
        for source_name, task in tasks:
            try:
                articles = await task
                if articles:
                    results[source_name] = articles
                else:
                    results[source_name] = []
            except Exception as e:
                logger.error(f"Error fetching news from {source_name}: {e}")
                results[source_name] = []
                
        return results
        
    async def test_source_connectivity(self, source_name: str) -> Dict:
        """Test connectivity to a specific news source"""
        if source_name not in self.sources:
            return {'status': 'error', 'message': f'Unknown source: {source_name}'}
            
        source = self.sources[source_name]
        start_time = time.time()
        
        try:
            headers = source.headers or {}
            
            async with self.session.get(source.url, headers=headers) as response:
                response_time = time.time() - start_time
                
                return {
                    'status': 'success' if response.status == 200 else 'error',
                    'status_code': response.status,
                    'response_time': response_time,
                    'url': source.url,
                    'source_type': source.source_type
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e),
                'response_time': time.time() - start_time,
                'url': source.url
            }
            
    async def test_all_sources(self) -> Dict:
        """Test connectivity to all news sources"""
        results = {}
        
        for source_name in self.sources:
            results[source_name] = await self.test_source_connectivity(source_name)
            
        return results
        
    def get_source_stats(self) -> Dict:
        """Get statistics for all news sources"""
        stats = {}
        
        for source_name, source in self.sources.items():
            stats[source_name] = {
                'enabled': source.enabled,
                'source_type': source.source_type,
                'update_interval': source.update_interval,
                'request_count': self.request_counts.get(source_name, 0),
                'error_count': self.error_counts.get(source_name, 0),
                'last_request': self.last_request_times.get(source_name, 0),
                'error_rate': self.error_counts.get(source_name, 0) / max(self.request_counts.get(source_name, 1), 1)
            }
            
        return stats
        
    def update_source_config(self, source_name: str, config_updates: Dict):
        """Update configuration for a news source"""
        if source_name not in self.sources:
            raise ValueError(f"Unknown news source: {source_name}")
            
        source = self.sources[source_name]
        
        for key, value in config_updates.items():
            if hasattr(source, key):
                setattr(source, key, value)
                logger.info(f"Updated {source_name} config: {key} = {value}")
            else:
                logger.warning(f"Unknown config key for {source_name}: {key}")

class NewsConfigManager:
    """Manages news sources configuration"""
    
    def __init__(self, config_file: str = None):
        self.config_file = config_file or "/app/config/production/news_sources.json"
        
    def save_config(self, news_manager: RussianNewsManager):
        """Save news sources configuration to file"""
        try:
            config_data = {}
            
            for source_name, source in news_manager.sources.items():
                config_data[source_name] = asdict(source)
                
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"News sources configuration saved to {self.config_file}")
            
        except Exception as e:
            logger.error(f"Failed to save news configuration: {e}")
            
    def load_config(self) -> Optional[Dict]:
        """Load news sources configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load news configuration: {e}")
            
        return None

async def test_news_feeds():
    """Test all Russian news feeds"""
    logger.info("Testing Russian news feeds...")
    
    async with RussianNewsManager() as news_manager:
        # Test connectivity to all sources
        connectivity_results = await news_manager.test_all_sources()
        
        logger.info("Connectivity test results:")
        for source_name, result in connectivity_results.items():
            status = result['status']
            response_time = result.get('response_time', 0)
            logger.info(f"  {source_name}: {status} ({response_time:.2f}s)")
            
        # Test fetching news from a few sources
        test_sources = ['vedomosti', 'kommersant', 'cbr']
        
        for source_name in test_sources:
            if source_name in news_manager.sources:
                logger.info(f"Testing news fetch from {source_name}...")
                articles = await news_manager.fetch_news_from_source(source_name)
                
                if articles:
                    logger.info(f"  Successfully fetched {len(articles)} articles")
                    if articles:
                        logger.info(f"  Sample title: {articles[0]['title'][:100]}...")
                else:
                    logger.warning(f"  No articles fetched from {source_name}")
                    
        # Display statistics
        stats = news_manager.get_source_stats()
        logger.info("News sources statistics:")
        for source_name, source_stats in stats.items():
            logger.info(f"  {source_name}: {source_stats['request_count']} requests, {source_stats['error_count']} errors")

if __name__ == "__main__":
    asyncio.run(test_news_feeds())