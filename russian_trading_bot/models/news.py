"""
News data models for Russian financial news analysis
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict
from enum import Enum


class NewsSource(Enum):
    """Russian news sources"""
    RBC = "rbc"
    VEDOMOSTI = "vedomosti"
    KOMMERSANT = "kommersant"
    INTERFAX = "interfax"
    TASS = "tass"
    PRIME = "prime"
    FINMARKET = "finmarket"


class SentimentScore(Enum):
    """Sentiment classification"""
    VERY_NEGATIVE = -2
    NEGATIVE = -1
    NEUTRAL = 0
    POSITIVE = 1
    VERY_POSITIVE = 2


@dataclass
class NewsArticle:
    """Russian financial news article"""
    title: str
    content: str
    source: NewsSource
    timestamp: datetime
    url: Optional[str] = None
    language: str = "ru"
    mentioned_stocks: List[str] = None
    sentiment_score: Optional[float] = None
    sentiment_classification: Optional[SentimentScore] = None
    relevance_score: Optional[float] = None
    
    def __post_init__(self):
        """Initialize default values"""
        if self.mentioned_stocks is None:
            self.mentioned_stocks = []
        
        # Validate sentiment score
        if self.sentiment_score is not None:
            if not -1.0 <= self.sentiment_score <= 1.0:
                raise ValueError("Sentiment score must be between -1.0 and 1.0")


@dataclass
class NewsAnalysis:
    """Analysis results for news article"""
    article_id: str
    entities: List[str]  # Extracted company names and stock symbols
    keywords: List[str]  # Important financial keywords
    sentiment_confidence: float
    market_impact_score: float  # 0-1 scale
    category: str  # earnings, merger, regulatory, etc.
    summary: str  # Brief summary in Russian
    
    def __post_init__(self):
        """Validate analysis data"""
        if not 0 <= self.sentiment_confidence <= 1:
            raise ValueError("Sentiment confidence must be between 0 and 1")
        if not 0 <= self.market_impact_score <= 1:
            raise ValueError("Market impact score must be between 0 and 1")


@dataclass
class MarketEvent:
    """Significant market event extracted from news"""
    event_type: str  # earnings, dividend, merger, regulatory, etc.
    affected_stocks: List[str]
    event_date: datetime
    description: str  # In Russian
    impact_assessment: str  # positive, negative, neutral
    confidence: float
    source_articles: List[str]  # Article IDs