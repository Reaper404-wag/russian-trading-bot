"""
Unit tests for Russian news data models
"""

import pytest
from datetime import datetime, timedelta
from russian_trading_bot.models.news_data import (
    RussianNewsArticle, NewsSentiment, NewsImpactScore, NewsEntity,
    NewsAnalysisResult, NewsAggregation,
    validate_russian_news_source, validate_news_category, validate_sentiment_level,
    detect_russian_financial_content, extract_mentioned_tickers,
    create_news_summary, filter_financial_news, group_news_by_stock,
    calculate_news_volume_score
)


class TestValidationFunctions:
    """Test validation helper functions"""
    
    def test_validate_russian_news_source_valid(self):
        """Test valid Russian news sources"""
        assert validate_russian_news_source("RBC") == True
        assert validate_russian_news_source("VEDOMOSTI") == True
        assert validate_russian_news_source("KOMMERSANT") == True
        assert validate_russian_news_source("INTERFAX") == True
        assert validate_russian_news_source("rbc") == True  # Case insensitive
        
    def test_validate_russian_news_source_invalid(self):
        """Test invalid Russian news sources"""
        assert validate_russian_news_source("CNN") == False
        assert validate_russian_news_source("BBC") == False
        assert validate_russian_news_source("") == False
        assert validate_russian_news_source("INVALID_SOURCE") == False
        
    def test_validate_news_category_valid(self):
        """Test valid news categories"""
        assert validate_news_category("MARKET_NEWS") == True
        assert validate_news_category("COMPANY_NEWS") == True
        assert validate_news_category("ECONOMIC_NEWS") == True
        assert validate_news_category("market_news") == True  # Case insensitive
        
    def test_validate_news_category_invalid(self):
        """Test invalid news categories"""
        assert validate_news_category("INVALID_CATEGORY") == False
        assert validate_news_category("") == False
        
    def test_validate_sentiment_level_valid(self):
        """Test valid sentiment levels"""
        assert validate_sentiment_level("POSITIVE") == True
        assert validate_sentiment_level("NEGATIVE") == True
        assert validate_sentiment_level("NEUTRAL") == True
        assert validate_sentiment_level("positive") == True  # Case insensitive
        
    def test_validate_sentiment_level_invalid(self):
        """Test invalid sentiment levels"""
        assert validate_sentiment_level("INVALID_SENTIMENT") == False
        assert validate_sentiment_level("") == False
        
    def test_detect_russian_financial_content_positive(self):
        """Test detection of Russian financial content"""
        financial_text = "Акции Сбербанка выросли на 5% после публикации отчета о прибыли"
        assert detect_russian_financial_content(financial_text) == True
        
        financial_text2 = "Центробанк повысил ключевую ставку до 15% из-за инфляции"
        assert detect_russian_financial_content(financial_text2) == True
        
    def test_detect_russian_financial_content_negative(self):
        """Test non-financial content detection"""
        non_financial_text = "Сегодня хорошая погода в Москве"
        assert detect_russian_financial_content(non_financial_text) == False
        
        single_keyword_text = "Банк открыл новое отделение"  # Only one financial keyword
        assert detect_russian_financial_content(single_keyword_text) == False
        
        assert detect_russian_financial_content("") == False
        
    def test_extract_mentioned_tickers(self):
        """Test extraction of MOEX tickers from text"""
        text_with_tickers = "Акции SBER и GAZP показали рост, а LKOH упал"
        tickers = extract_mentioned_tickers(text_with_tickers)
        assert set(tickers) == {"SBER", "GAZP", "LKOH"}
        
        text_without_tickers = "Сегодня хорошая погода"
        tickers = extract_mentioned_tickers(text_without_tickers)
        assert tickers == []
        
        text_with_unknown_tickers = "Компания ABCD показала рост"
        tickers = extract_mentioned_tickers(text_with_unknown_tickers)
        assert tickers == []  # ABCD is not a known ticker


class TestRussianNewsArticle:
    """Test RussianNewsArticle data model"""
    
    def test_valid_russian_news_article(self):
        """Test creating valid Russian news article"""
        article = RussianNewsArticle(
            title="Акции SBER выросли на 5%",
            content="Сегодня акции SBER показали рост на бирже после публикации отчета о прибыли",
            source="RBC",
            timestamp=datetime.now(),
            category="COMPANY_NEWS",
            is_financial=True  # Explicitly set as financial
        )
        assert article.title == "Акции SBER выросли на 5%"
        assert article.source == "RBC"
        assert article.language == "ru"
        assert article.is_financial == True
        assert "SBER" in article.mentioned_stocks  # Auto-extracted
        
    def test_empty_title_raises_error(self):
        """Test empty title raises error"""
        with pytest.raises(ValueError, match="Article title is required"):
            RussianNewsArticle(
                title="",
                content="Test content",
                source="RBC",
                timestamp=datetime.now()
            )
            
    def test_empty_content_raises_error(self):
        """Test empty content raises error"""
        with pytest.raises(ValueError, match="Article content is required"):
            RussianNewsArticle(
                title="Test title",
                content="",
                source="RBC",
                timestamp=datetime.now()
            )
            
    def test_invalid_source_raises_error(self):
        """Test invalid source raises error"""
        with pytest.raises(ValueError, match="Invalid Russian news source"):
            RussianNewsArticle(
                title="Test title",
                content="Test content",
                source="INVALID_SOURCE",
                timestamp=datetime.now()
            )
            
    def test_invalid_language_raises_error(self):
        """Test invalid language raises error"""
        with pytest.raises(ValueError, match="Russian news articles must have language 'ru'"):
            RussianNewsArticle(
                title="Test title",
                content="Test content",
                source="RBC",
                timestamp=datetime.now(),
                language="en"
            )
            
    def test_invalid_category_raises_error(self):
        """Test invalid category raises error"""
        with pytest.raises(ValueError, match="Invalid news category"):
            RussianNewsArticle(
                title="Test title",
                content="Test content",
                source="RBC",
                timestamp=datetime.now(),
                category="INVALID_CATEGORY"
            )
            
    def test_invalid_url_raises_error(self):
        """Test invalid URL raises error"""
        with pytest.raises(ValueError, match="Invalid URL format"):
            RussianNewsArticle(
                title="Test title",
                content="Test content",
                source="RBC",
                timestamp=datetime.now(),
                url="invalid-url"
            )
            
    def test_valid_url_accepted(self):
        """Test valid URLs are accepted"""
        article = RussianNewsArticle(
            title="Test title",
            content="Test content",
            source="RBC",
            timestamp=datetime.now(),
            url="https://www.rbc.ru/test-article"
        )
        assert article.url == "https://www.rbc.ru/test-article"
        
    def test_source_normalization(self):
        """Test source is normalized to uppercase"""
        article = RussianNewsArticle(
            title="Test title",
            content="Test content",
            source="rbc",
            timestamp=datetime.now()
        )
        assert article.source == "RBC"
        
    def test_category_normalization(self):
        """Test category is normalized to uppercase"""
        article = RussianNewsArticle(
            title="Test title",
            content="Test content",
            source="RBC",
            timestamp=datetime.now(),
            category="market_news"
        )
        assert article.category == "MARKET_NEWS"


class TestNewsSentiment:
    """Test NewsSentiment data model"""
    
    def test_valid_news_sentiment(self):
        """Test creating valid news sentiment"""
        sentiment = NewsSentiment(
            article_id="test_123",
            overall_sentiment="POSITIVE",
            sentiment_score=0.75,
            confidence=0.85,
            positive_keywords=["рост", "прибыль"],
            negative_keywords=[],
            timestamp=datetime.now()
        )
        assert sentiment.article_id == "test_123"
        assert sentiment.overall_sentiment == "POSITIVE"
        assert sentiment.sentiment_score == 0.75
        
    def test_empty_article_id_raises_error(self):
        """Test empty article ID raises error"""
        with pytest.raises(ValueError, match="Article ID is required"):
            NewsSentiment(
                article_id="",
                overall_sentiment="POSITIVE",
                sentiment_score=0.75,
                confidence=0.85
            )
            
    def test_invalid_sentiment_level_raises_error(self):
        """Test invalid sentiment level raises error"""
        with pytest.raises(ValueError, match="Invalid sentiment level"):
            NewsSentiment(
                article_id="test_123",
                overall_sentiment="INVALID_SENTIMENT",
                sentiment_score=0.75,
                confidence=0.85
            )
            
    def test_invalid_sentiment_score_raises_error(self):
        """Test invalid sentiment score raises error"""
        with pytest.raises(ValueError, match="Sentiment score must be between -1.0 and 1.0"):
            NewsSentiment(
                article_id="test_123",
                overall_sentiment="POSITIVE",
                sentiment_score=1.5,  # Invalid score
                confidence=0.85
            )
            
    def test_invalid_confidence_raises_error(self):
        """Test invalid confidence raises error"""
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            NewsSentiment(
                article_id="test_123",
                overall_sentiment="POSITIVE",
                sentiment_score=0.75,
                confidence=1.5  # Invalid confidence
            )
            
    def test_sentiment_normalization(self):
        """Test sentiment level is normalized to uppercase"""
        sentiment = NewsSentiment(
            article_id="test_123",
            overall_sentiment="positive",
            sentiment_score=0.75,
            confidence=0.85
        )
        assert sentiment.overall_sentiment == "POSITIVE"


class TestNewsImpactScore:
    """Test NewsImpactScore data model"""
    
    def test_valid_news_impact_score(self):
        """Test creating valid news impact score"""
        impact = NewsImpactScore(
            article_id="test_123",
            overall_impact=0.8,
            market_impact=0.6,
            stock_specific_impact={"SBER": 0.9, "GAZP": 0.5},
            sector_impact={"BANKING": 0.7},
            time_horizon="SHORT",
            confidence=0.85,
            reasoning="Положительные новости о прибыли банка"
        )
        assert impact.article_id == "test_123"
        assert impact.overall_impact == 0.8
        assert impact.stock_specific_impact["SBER"] == 0.9
        
    def test_invalid_overall_impact_raises_error(self):
        """Test invalid overall impact raises error"""
        with pytest.raises(ValueError, match="Overall impact must be between 0.0 and 1.0"):
            NewsImpactScore(
                article_id="test_123",
                overall_impact=1.5,  # Invalid impact
                market_impact=0.6,
                stock_specific_impact={},
                sector_impact={},
                time_horizon="SHORT",
                confidence=0.85
            )
            
    def test_invalid_stock_impact_raises_error(self):
        """Test invalid stock-specific impact raises error"""
        with pytest.raises(ValueError, match="Stock impact for SBER must be between 0.0 and 1.0"):
            NewsImpactScore(
                article_id="test_123",
                overall_impact=0.8,
                market_impact=0.6,
                stock_specific_impact={"SBER": 1.5},  # Invalid stock impact
                sector_impact={},
                time_horizon="SHORT",
                confidence=0.85
            )
            
    def test_invalid_time_horizon_raises_error(self):
        """Test invalid time horizon raises error"""
        with pytest.raises(ValueError, match="Invalid time horizon"):
            NewsImpactScore(
                article_id="test_123",
                overall_impact=0.8,
                market_impact=0.6,
                stock_specific_impact={},
                sector_impact={},
                time_horizon="INVALID_HORIZON",
                confidence=0.85
            )
            
    def test_time_horizon_normalization(self):
        """Test time horizon is normalized to uppercase"""
        impact = NewsImpactScore(
            article_id="test_123",
            overall_impact=0.8,
            market_impact=0.6,
            stock_specific_impact={},
            sector_impact={},
            time_horizon="short",
            confidence=0.85
        )
        assert impact.time_horizon == "SHORT"


class TestNewsEntity:
    """Test NewsEntity data model"""
    
    def test_valid_news_entity(self):
        """Test creating valid news entity"""
        entity = NewsEntity(
            text="Сбербанк",
            entity_type="ORGANIZATION",
            start_position=10,
            end_position=18,
            confidence=0.95,
            normalized_form="ПАО Сбербанк",
            linked_ticker="SBER"
        )
        assert entity.text == "Сбербанк"
        assert entity.entity_type == "ORGANIZATION"
        assert entity.linked_ticker == "SBER"
        
    def test_empty_text_raises_error(self):
        """Test empty entity text raises error"""
        with pytest.raises(ValueError, match="Entity text is required"):
            NewsEntity(
                text="",
                entity_type="ORGANIZATION",
                start_position=10,
                end_position=18,
                confidence=0.95
            )
            
    def test_invalid_entity_type_raises_error(self):
        """Test invalid entity type raises error"""
        with pytest.raises(ValueError, match="Invalid entity type"):
            NewsEntity(
                text="Сбербанк",
                entity_type="INVALID_TYPE",
                start_position=10,
                end_position=18,
                confidence=0.95
            )
            
    def test_invalid_positions_raise_error(self):
        """Test invalid positions raise errors"""
        with pytest.raises(ValueError, match="Start position cannot be negative"):
            NewsEntity(
                text="Сбербанк",
                entity_type="ORGANIZATION",
                start_position=-1,
                end_position=18,
                confidence=0.95
            )
            
        with pytest.raises(ValueError, match="End position must be greater than start position"):
            NewsEntity(
                text="Сбербанк",
                entity_type="ORGANIZATION",
                start_position=18,
                end_position=10,
                confidence=0.95
            )
            
    def test_entity_type_normalization(self):
        """Test entity type is normalized to uppercase"""
        entity = NewsEntity(
            text="Сбербанк",
            entity_type="organization",
            start_position=10,
            end_position=18,
            confidence=0.95
        )
        assert entity.entity_type == "ORGANIZATION"


class TestNewsAnalysisResult:
    """Test NewsAnalysisResult data model"""
    
    def test_valid_news_analysis_result(self):
        """Test creating valid news analysis result"""
        article = RussianNewsArticle(
            title="Test title",
            content="Test content with акции and прибыль",
            source="RBC",
            timestamp=datetime.now()
        )
        
        result = NewsAnalysisResult(
            article_id="test_123",
            article=article,
            keywords=["акции", "прибыль"],
            summary="Краткое содержание статьи",
            processing_time_ms=150
        )
        assert result.article_id == "test_123"
        assert result.article == article
        assert result.processing_time_ms == 150
        
    def test_invalid_processing_time_raises_error(self):
        """Test invalid processing time raises error"""
        article = RussianNewsArticle(
            title="Test title",
            content="Test content",
            source="RBC",
            timestamp=datetime.now()
        )
        
        with pytest.raises(ValueError, match="Processing time cannot be negative"):
            NewsAnalysisResult(
                article_id="test_123",
                article=article,
                processing_time_ms=-100
            )


class TestNewsAggregation:
    """Test NewsAggregation data model"""
    
    def test_valid_news_aggregation(self):
        """Test creating valid news aggregation"""
        start_time = datetime.now() - timedelta(hours=24)
        end_time = datetime.now()
        
        aggregation = NewsAggregation(
            start_time=start_time,
            end_time=end_time,
            total_articles=100,
            financial_articles=75,
            sentiment_distribution={"POSITIVE": 30, "NEUTRAL": 25, "NEGATIVE": 20},
            top_mentioned_stocks=[("SBER", 15), ("GAZP", 12)],
            top_sources=[("RBC", 25), ("VEDOMOSTI", 20)],
            category_distribution={"MARKET_NEWS": 40, "COMPANY_NEWS": 35},
            average_sentiment_score=0.15,
            market_impact_summary={"HIGH": 10, "MEDIUM": 30, "LOW": 35}
        )
        assert aggregation.total_articles == 100
        assert aggregation.financial_articles == 75
        assert aggregation.average_sentiment_score == 0.15
        
    def test_invalid_time_range_raises_error(self):
        """Test invalid time range raises error"""
        start_time = datetime.now()
        end_time = datetime.now() - timedelta(hours=1)  # End before start
        
        with pytest.raises(ValueError, match="Start time must be before end time"):
            NewsAggregation(
                start_time=start_time,
                end_time=end_time,
                total_articles=100,
                financial_articles=75,
                sentiment_distribution={},
                top_mentioned_stocks=[],
                top_sources=[],
                category_distribution={},
                average_sentiment_score=0.0,
                market_impact_summary={}
            )
            
    def test_invalid_article_counts_raise_error(self):
        """Test invalid article counts raise errors"""
        start_time = datetime.now() - timedelta(hours=24)
        end_time = datetime.now()
        
        with pytest.raises(ValueError, match="Financial articles cannot exceed total articles"):
            NewsAggregation(
                start_time=start_time,
                end_time=end_time,
                total_articles=50,
                financial_articles=75,  # More financial than total
                sentiment_distribution={},
                top_mentioned_stocks=[],
                top_sources=[],
                category_distribution={},
                average_sentiment_score=0.0,
                market_impact_summary={}
            )


class TestUtilityFunctions:
    """Test utility functions"""
    
    def test_create_news_summary(self):
        """Test creating news summary"""
        articles = [
            RussianNewsArticle(
                title="Акции SBER выросли",
                content="Сбербанк показал хорошие результаты",
                source="RBC",
                timestamp=datetime.now(),
                mentioned_stocks=["SBER"]
            ),
            RussianNewsArticle(
                title="GAZP упал на 2%",
                content="Газпром снизился из-за санкций",
                source="VEDOMOSTI",
                timestamp=datetime.now(),
                mentioned_stocks=["GAZP"]
            )
        ]
        
        summary = create_news_summary(articles)
        assert "Анализ 2 новостных статей" in summary
        assert "SBER" in summary or "GAZP" in summary
        
    def test_create_news_summary_empty_list(self):
        """Test creating summary for empty list"""
        summary = create_news_summary([])
        assert summary == ""
        
    def test_filter_financial_news(self):
        """Test filtering financial news"""
        articles = [
            RussianNewsArticle(
                title="Акции выросли на бирже",
                content="Торги показали рост котировок",
                source="RBC",
                timestamp=datetime.now(),
                is_financial=True
            ),
            RussianNewsArticle(
                title="Погода в Москве",
                content="Сегодня солнечно",
                source="RBC",
                timestamp=datetime.now(),
                is_financial=False
            )
        ]
        
        financial_articles = filter_financial_news(articles)
        assert len(financial_articles) == 1
        assert financial_articles[0].title == "Акции выросли на бирже"
        
    def test_group_news_by_stock(self):
        """Test grouping news by stock"""
        articles = [
            RussianNewsArticle(
                title="SBER news",
                content="Сбербанк новости",
                source="RBC",
                timestamp=datetime.now(),
                mentioned_stocks=["SBER"]
            ),
            RussianNewsArticle(
                title="GAZP and SBER news",
                content="Газпром и Сбербанк",
                source="RBC",
                timestamp=datetime.now(),
                mentioned_stocks=["GAZP", "SBER"]
            )
        ]
        
        grouped = group_news_by_stock(articles)
        assert len(grouped["SBER"]) == 2
        assert len(grouped["GAZP"]) == 1
        
    def test_calculate_news_volume_score(self):
        """Test calculating news volume score"""
        recent_articles = [
            RussianNewsArticle(
                title="Financial news",
                content="Акции и биржа",
                source="RBC",
                timestamp=datetime.now(),
                is_financial=True
            )
        ]
        
        score = calculate_news_volume_score(recent_articles)
        assert 0.0 <= score <= 1.0
        
        # Test with empty list
        empty_score = calculate_news_volume_score([])
        assert empty_score == 0.0