"""
News data models for Russian financial news
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal
import re


# Valid Russian news sources
VALID_RUSSIAN_NEWS_SOURCES = {
    'RBC', 'VEDOMOSTI', 'KOMMERSANT', 'INTERFAX', 'TASS', 'RIA',
    'GAZETA', 'LENTA', 'FORBES_RU', 'BUSINESS_FM', 'PRIME',
    'FINMARKET', 'BANKI_RU', 'INVESTING_RU', 'SMART_LAB'
}

# Russian financial keywords for relevance detection
RUSSIAN_FINANCIAL_KEYWORDS = {
    'акции', 'облигации', 'дивиденды', 'прибыль', 'убыток', 'выручка',
    'капитализация', 'котировки', 'торги', 'биржа', 'моекс', 'рубль',
    'доллар', 'евро', 'нефть', 'газ', 'золото', 'инвестиции',
    'инвесторы', 'трейдеры', 'аналитики', 'рейтинг', 'прогноз',
    'санкции', 'экономика', 'финансы', 'банк', 'кредит', 'ставка',
    'инфляция', 'цб', 'центробанк', 'минфин', 'налоги'
}

# News categories
NEWS_CATEGORIES = {
    'MARKET_NEWS', 'COMPANY_NEWS', 'ECONOMIC_NEWS', 'POLITICAL_NEWS',
    'SECTOR_NEWS', 'ANALYST_REPORT', 'EARNINGS', 'DIVIDENDS',
    'MERGERS_ACQUISITIONS', 'REGULATORY', 'SANCTIONS', 'CURRENCY'
}

# Sentiment levels
SENTIMENT_LEVELS = {
    'VERY_NEGATIVE', 'NEGATIVE', 'NEUTRAL', 'POSITIVE', 'VERY_POSITIVE'
}


def validate_russian_news_source(source: str) -> bool:
    """Validate Russian news source"""
    return source.upper() in VALID_RUSSIAN_NEWS_SOURCES


def validate_news_category(category: str) -> bool:
    """Validate news category"""
    return category.upper() in NEWS_CATEGORIES


def validate_sentiment_level(sentiment: str) -> bool:
    """Validate sentiment level"""
    return sentiment.upper() in SENTIMENT_LEVELS


def detect_russian_financial_content(text: str) -> bool:
    """Detect if text contains Russian financial content"""
    if not text:
        return False
    
    text_lower = text.lower()
    financial_word_count = sum(1 for keyword in RUSSIAN_FINANCIAL_KEYWORDS 
                              if keyword in text_lower)
    
    # Consider content financial if it contains at least 2 financial keywords
    return financial_word_count >= 2


def extract_mentioned_tickers(text: str) -> List[str]:
    """Extract mentioned MOEX tickers from Russian text"""
    if not text:
        return []
    
    # Common Russian MOEX tickers for validation
    known_tickers = {
        'SBER', 'GAZP', 'LKOH', 'ROSN', 'NVTK', 'YNDX', 'TCSG',
        'GMKN', 'NLMK', 'MAGN', 'ALRS', 'CHMF', 'SNGS', 'TATN',
        'VTBR', 'AFLT', 'RUAL', 'PLZL', 'PHOR', 'MOEX', 'FEES'
    }
    
    # Company name to ticker mapping for better extraction
    company_to_ticker = {
        'сбербанк': 'SBER',
        'сбер': 'SBER',
        'газпром': 'GAZP',
        'лукойл': 'LKOH',
        'роснефть': 'ROSN',
        'новатэк': 'NVTK',
        'яндекс': 'YNDX',
        'тинькофф': 'TCSG',
        'норникель': 'GMKN',
        'нлмк': 'NLMK',
        'магнит': 'MAGN',
        'алроса': 'ALRS',
        'северсталь': 'CHMF',
        'сургутнефтегаз': 'SNGS',
        'татнефть': 'TATN',
        'втб': 'VTBR',
        'аэрофлот': 'AFLT',
        'русал': 'RUAL',
        'полюс': 'PLZL',
        'фосагро': 'PHOR',
        'московская биржа': 'MOEX'
    }
    
    text_lower = text.lower()
    mentioned_tickers = set()
    
    # First, look for direct ticker mentions (3-5 uppercase letters)
    ticker_pattern = re.compile(r'\b[A-ZА-Я]{3,5}\b')
    potential_tickers = ticker_pattern.findall(text.upper())
    
    for ticker in potential_tickers:
        if ticker in known_tickers:
            mentioned_tickers.add(ticker)
    
    # Second, look for company name mentions
    for company_name, ticker in company_to_ticker.items():
        if company_name in text_lower:
            mentioned_tickers.add(ticker)
    
    # Third, look for partial company names (for better matching)
    for word in text_lower.split():
        # Remove punctuation from word
        clean_word = re.sub(r'[^\w]', '', word)
        if clean_word in company_to_ticker:
            mentioned_tickers.add(company_to_ticker[clean_word])
    
    return list(mentioned_tickers)


@dataclass
class RussianNewsArticle:
    """Russian financial news article with language-specific validation"""
    title: str
    content: str
    source: str
    timestamp: datetime
    url: Optional[str] = None
    author: Optional[str] = None
    language: str = "ru"
    mentioned_stocks: Optional[List[str]] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_financial: Optional[bool] = None
    
    def __post_init__(self):
        """Validate Russian news article data"""
        if not self.title or not self.title.strip():
            raise ValueError("Article title is required")
            
        if not self.content or not self.content.strip():
            raise ValueError("Article content is required")
            
        if not validate_russian_news_source(self.source):
            raise ValueError(f"Invalid Russian news source: {self.source}")
            
        if self.language != "ru":
            raise ValueError("Russian news articles must have language 'ru'")
            
        if self.category and not validate_news_category(self.category):
            raise ValueError(f"Invalid news category: {self.category}")
            
        # Auto-detect financial content if not specified
        if self.is_financial is None:
            self.is_financial = detect_russian_financial_content(
                self.title + " " + self.content
            )
            
        # Auto-extract mentioned stocks if not provided
        if self.mentioned_stocks is None:
            self.mentioned_stocks = extract_mentioned_tickers(
                self.title + " " + self.content
            )
            
        # Normalize source to uppercase
        self.source = self.source.upper()
        
        # Normalize category if provided
        if self.category:
            self.category = self.category.upper()
            
        # Validate URL format if provided
        if self.url and not (self.url.startswith('http://') or self.url.startswith('https://')):
            raise ValueError("Invalid URL format")


@dataclass
class NewsSentiment:
    """Sentiment analysis results for Russian news"""
    article_id: str
    overall_sentiment: str
    sentiment_score: float  # -1.0 to 1.0
    confidence: float  # 0.0 to 1.0
    positive_keywords: Optional[List[str]] = None
    negative_keywords: Optional[List[str]] = None
    neutral_keywords: Optional[List[str]] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate sentiment analysis data"""
        if not self.article_id:
            raise ValueError("Article ID is required")
            
        if not validate_sentiment_level(self.overall_sentiment):
            raise ValueError(f"Invalid sentiment level: {self.overall_sentiment}")
            
        if not (-1.0 <= self.sentiment_score <= 1.0):
            raise ValueError("Sentiment score must be between -1.0 and 1.0")
            
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")
            
        # Normalize sentiment level
        self.overall_sentiment = self.overall_sentiment.upper()


@dataclass
class NewsImpactScore:
    """Market impact score for Russian news articles"""
    article_id: str
    overall_impact: float  # 0.0 to 1.0
    market_impact: float  # 0.0 to 1.0
    stock_specific_impact: Dict[str, float]  # ticker -> impact score
    sector_impact: Dict[str, float]  # sector -> impact score
    time_horizon: str  # 'SHORT', 'MEDIUM', 'LONG'
    confidence: float  # 0.0 to 1.0
    reasoning: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate news impact score data"""
        if not self.article_id:
            raise ValueError("Article ID is required")
            
        if not (0.0 <= self.overall_impact <= 1.0):
            raise ValueError("Overall impact must be between 0.0 and 1.0")
            
        if not (0.0 <= self.market_impact <= 1.0):
            raise ValueError("Market impact must be between 0.0 and 1.0")
            
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")
            
        valid_time_horizons = {'SHORT', 'MEDIUM', 'LONG'}
        if self.time_horizon.upper() not in valid_time_horizons:
            raise ValueError(f"Invalid time horizon: {self.time_horizon}")
            
        # Validate stock-specific impact scores
        for ticker, impact in self.stock_specific_impact.items():
            if not (0.0 <= impact <= 1.0):
                raise ValueError(f"Stock impact for {ticker} must be between 0.0 and 1.0")
                
        # Validate sector impact scores
        for sector, impact in self.sector_impact.items():
            if not (0.0 <= impact <= 1.0):
                raise ValueError(f"Sector impact for {sector} must be between 0.0 and 1.0")
                
        # Normalize time horizon
        self.time_horizon = self.time_horizon.upper()


@dataclass
class NewsEntity:
    """Named entity extracted from Russian news"""
    text: str
    entity_type: str  # 'PERSON', 'ORGANIZATION', 'LOCATION', 'TICKER', 'CURRENCY', 'DATE'
    start_position: int
    end_position: int
    confidence: float  # 0.0 to 1.0
    normalized_form: Optional[str] = None
    linked_ticker: Optional[str] = None
    
    def __post_init__(self):
        """Validate news entity data"""
        if not self.text or not self.text.strip():
            raise ValueError("Entity text is required")
            
        valid_entity_types = {
            'PERSON', 'ORGANIZATION', 'LOCATION', 'TICKER', 
            'CURRENCY', 'DATE', 'MONEY', 'PERCENT'
        }
        if self.entity_type.upper() not in valid_entity_types:
            raise ValueError(f"Invalid entity type: {self.entity_type}")
            
        if self.start_position < 0:
            raise ValueError("Start position cannot be negative")
            
        if self.end_position <= self.start_position:
            raise ValueError("End position must be greater than start position")
            
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")
            
        # Normalize entity type
        self.entity_type = self.entity_type.upper()


@dataclass
class NewsAnalysisResult:
    """Complete analysis result for Russian news article"""
    article_id: str
    article: RussianNewsArticle
    sentiment: Optional[NewsSentiment] = None
    impact_score: Optional[NewsImpactScore] = None
    entities: Optional[List[NewsEntity]] = None
    keywords: Optional[List[str]] = None
    summary: Optional[str] = None
    analysis_timestamp: Optional[datetime] = None
    processing_time_ms: Optional[int] = None
    
    def __post_init__(self):
        """Validate news analysis result"""
        if not self.article_id:
            raise ValueError("Article ID is required")
            
        if not isinstance(self.article, RussianNewsArticle):
            raise ValueError("Article must be a RussianNewsArticle instance")
            
        if self.processing_time_ms is not None and self.processing_time_ms < 0:
            raise ValueError("Processing time cannot be negative")


@dataclass
class NewsAggregation:
    """Aggregated news data for a specific time period"""
    start_time: datetime
    end_time: datetime
    total_articles: int
    financial_articles: int
    sentiment_distribution: Dict[str, int]  # sentiment -> count
    top_mentioned_stocks: List[Tuple[str, int]]  # [(ticker, count), ...]
    top_sources: List[Tuple[str, int]]  # [(source, count), ...]
    category_distribution: Dict[str, int]  # category -> count
    average_sentiment_score: float
    market_impact_summary: Dict[str, float]  # impact_level -> count
    
    def __post_init__(self):
        """Validate news aggregation data"""
        if self.start_time >= self.end_time:
            raise ValueError("Start time must be before end time")
            
        if self.total_articles < 0:
            raise ValueError("Total articles cannot be negative")
            
        if self.financial_articles < 0:
            raise ValueError("Financial articles cannot be negative")
            
        if self.financial_articles > self.total_articles:
            raise ValueError("Financial articles cannot exceed total articles")
            
        if not (-1.0 <= self.average_sentiment_score <= 1.0):
            raise ValueError("Average sentiment score must be between -1.0 and 1.0")
            
        # Validate sentiment distribution
        for sentiment, count in self.sentiment_distribution.items():
            if not validate_sentiment_level(sentiment):
                raise ValueError(f"Invalid sentiment level: {sentiment}")
            if count < 0:
                raise ValueError("Sentiment count cannot be negative")


def create_news_summary(articles: List[RussianNewsArticle], 
                       max_length: int = 500) -> str:
    """Create a summary of multiple Russian news articles"""
    if not articles:
        return ""
    
    # Extract key information from articles
    all_titles = [article.title for article in articles]
    all_stocks = []
    for article in articles:
        if article.mentioned_stocks:
            all_stocks.extend(article.mentioned_stocks)
    
    # Count stock mentions
    stock_counts = {}
    for stock in all_stocks:
        stock_counts[stock] = stock_counts.get(stock, 0) + 1
    
    # Get top mentioned stocks
    top_stocks = sorted(stock_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Create summary
    summary_parts = []
    summary_parts.append(f"Анализ {len(articles)} новостных статей")
    
    if top_stocks:
        stocks_text = ", ".join([f"{stock} ({count})" for stock, count in top_stocks])
        summary_parts.append(f"Наиболее упоминаемые акции: {stocks_text}")
    
    # Get unique sources
    sources = list(set(article.source for article in articles))
    if sources:
        summary_parts.append(f"Источники: {', '.join(sources[:3])}")
    
    summary = ". ".join(summary_parts)
    
    # Truncate if too long
    if len(summary) > max_length:
        summary = summary[:max_length-3] + "..."
    
    return summary


def filter_financial_news(articles: List[RussianNewsArticle]) -> List[RussianNewsArticle]:
    """Filter articles to only include financial news"""
    return [article for article in articles if article.is_financial]


def group_news_by_stock(articles: List[RussianNewsArticle]) -> Dict[str, List[RussianNewsArticle]]:
    """Group news articles by mentioned stocks"""
    stock_groups = {}
    
    for article in articles:
        if article.mentioned_stocks:
            for stock in article.mentioned_stocks:
                if stock not in stock_groups:
                    stock_groups[stock] = []
                stock_groups[stock].append(article)
    
    return stock_groups


def calculate_news_volume_score(articles: List[RussianNewsArticle], 
                               time_window_hours: int = 24) -> float:
    """Calculate news volume score for market impact assessment"""
    if not articles:
        return 0.0
    
    # Count financial articles in the time window
    now = datetime.now()
    recent_articles = [
        article for article in articles
        if article.is_financial and 
        (now - article.timestamp).total_seconds() <= time_window_hours * 3600
    ]
    
    # Normalize score based on typical daily volume (assume 50 articles is high)
    volume_score = min(len(recent_articles) / 50.0, 1.0)
    
    return volume_score