"""
Unit tests for enhanced market monitoring service
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from decimal import Decimal

from russian_trading_bot.models.market_data import MOEXMarketData
from russian_trading_bot.models.trading import Portfolio, Position
from russian_trading_bot.models.notifications import NotificationPreferences
from russian_trading_bot.services.enhanced_market_monitor import (
    EnhancedMarketMonitor, MarketSentiment, RiskAssessment, MarketRegimeChange
)
from russian_trading_bot.services.notification_service import NotificationService


class TestEnhancedMarketMonitor:
    """Test enhanced market monitoring functionality"""
    
    @pytest.fixture
    def config(self):
        """Test configuration"""
        return {
            'volatility_threshold': 0.03,
            'sentiment_threshold': 0.3,
            'risk_escalation_threshold': 0.7,
            'regime_change_threshold': 0.8
        }
    
    @pytest.fixture
    def notification_service(self):
        """Mock notification service"""
        return Mock(spec=NotificationService)
    
    @pytest.fixture
    def enhanced_monitor(self, notification_service, config):
        """Create enhanced market monitor instance"""
        return EnhancedMarketMonitor(notification_service, config)
    
    @pytest.fixture
    def sample_market_data(self):
        """Sample market data for testing"""
        return [
            MOEXMarketData(
                symbol="SBER",
                price=Decimal("250.50"),
                volume=2000000,
                timestamp=datetime.now(),
                change_percent=0.05,
                previous_close=Decimal("238.57")
            ),
            MOEXMarketData(
                symbol="GAZP",
                price=Decimal("180.75"),
                volume=1500000,
                timestamp=datetime.now(),
                change_percent=-0.03,
                previous_close=Decimal("186.44")
            )
        ]
    
    @pytest.fixture
    def sample_news_data(self):
        """Sample news data for testing"""
        return [
            {
                'title': 'Сбербанк показал рост прибыли',
                'source': 'rbc.ru',
                'timestamp': datetime.now()
            },
            {
                'title': 'Новые санкции против российских банков',
                'source': 'reuters.com',
                'timestamp': datetime.now()
            }
        ]
    
    @pytest.fixture
    def sample_portfolio(self):
        """Sample portfolio for testing"""
        return Portfolio(
            positions={
                "SBER": Position(
                    symbol="SBER",
                    quantity=100,
                    average_price=Decimal("240.00"),
                    current_price=Decimal("250.50"),
                    market_value=Decimal("25050.00"),
                    unrealized_pnl=Decimal("1050.00")
                )
            },
            cash_balance=Decimal("50000.00"),
            total_value=Decimal("75050.00"),
            total_pnl=Decimal("1050.00")
        )
    
    @pytest.mark.asyncio
    async def test_monitor_market_sentiment(self, enhanced_monitor, sample_market_data, sample_news_data):
        """Test market sentiment monitoring"""
        # Mock internal methods
        enhanced_monitor._analyze_price_sentiment = Mock(return_value=0.4)
        enhanced_monitor._analyze_news_sentiment = AsyncMock(return_value=0.2)
        enhanced_monitor._analyze_volume_sentiment = Mock(return_value=0.3)
        enhanced_monitor._identify_sentiment_factors = Mock(return_value=["Positive price action"])
        enhanced_monitor._analyze_sector_sentiments = Mock(return_value={"БАНКИ": 0.3})
        
        # Monitor sentiment
        sentiment = await enhanced_monitor.monitor_market_sentiment(
            sample_market_data, sample_news_data
        )
        
        # Verify sentiment
        assert isinstance(sentiment, MarketSentiment)
        assert sentiment.overall_sentiment in ["BULLISH", "BEARISH", "NEUTRAL"]
        assert -1.0 <= sentiment.sentiment_score <= 1.0
        assert 0.0 <= sentiment.confidence <= 1.0
        assert isinstance(sentiment.key_factors, list)
        assert isinstance(sentiment.sector_sentiments, dict)
        
        # Verify sentiment was stored
        assert len(enhanced_monitor.sentiment_history) == 1
        assert enhanced_monitor.sentiment_history[0] == sentiment
    
    @pytest.mark.asyncio
    async def test_assess_comprehensive_risk(self, enhanced_monitor, sample_market_data, sample_portfolio):
        """Test comprehensive risk assessment"""
        # Mock internal risk calculation methods
        enhanced_monitor._calculate_volatility_risk = AsyncMock(return_value=0.4)
        enhanced_monitor._assess_geopolitical_risk = AsyncMock(return_value=0.6)
        enhanced_monitor._calculate_liquidity_risk = Mock(return_value=0.3)
        enhanced_monitor._assess_currency_risk = AsyncMock(return_value=0.5)
        enhanced_monitor._generate_risk_recommendations = Mock(
            return_value=["Reduce position sizes", "Monitor news"]
        )
        
        # Assess risk
        risk_assessment = await enhanced_monitor.assess_comprehensive_risk(
            sample_market_data, sample_portfolio
        )
        
        # Verify risk assessment
        assert isinstance(risk_assessment, RiskAssessment)
        assert risk_assessment.overall_risk_level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        assert 0.0 <= risk_assessment.risk_score <= 1.0
        assert 0.0 <= risk_assessment.volatility_risk <= 1.0
        assert 0.0 <= risk_assessment.geopolitical_risk <= 1.0
        assert 0.0 <= risk_assessment.liquidity_risk <= 1.0
        assert 0.0 <= risk_assessment.currency_risk <= 1.0
        assert isinstance(risk_assessment.recommendations, list)
        
        # Verify risk assessment was stored
        assert len(enhanced_monitor.risk_assessments) == 1
        assert enhanced_monitor.risk_assessments[0] == risk_assessment
    
    @pytest.mark.asyncio
    async def test_detect_market_regime_changes(self, enhanced_monitor, sample_market_data):
        """Test market regime change detection"""
        # Mock market condition
        mock_condition = Mock()
        mock_condition.market_phase = "VOLATILE"
        enhanced_monitor.get_market_condition = Mock(return_value=mock_condition)
        
        # First call - should create initial regime
        regime_change = await enhanced_monitor.detect_market_regime_changes(sample_market_data)
        assert regime_change is None  # No change on first call
        assert len(enhanced_monitor.regime_history) == 1
        
        # Mock regime change confidence calculation
        enhanced_monitor._calculate_regime_change_confidence = Mock(return_value=0.9)
        enhanced_monitor._identify_regime_change_indicators = Mock(
            return_value=["High volatility", "Volume spike"]
        )
        enhanced_monitor._estimate_regime_duration = Mock(return_value="1-2 weeks")
        
        # Change market phase
        mock_condition.market_phase = "CRISIS"
        
        # Second call - should detect regime change
        regime_change = await enhanced_monitor.detect_market_regime_changes(sample_market_data)
        
        # Verify regime change detection
        assert isinstance(regime_change, MarketRegimeChange)
        assert regime_change.previous_regime == "VOLATILE"
        assert regime_change.current_regime == "CRISIS"
        assert regime_change.confidence >= 0.8  # Above threshold
        assert isinstance(regime_change.key_indicators, list)
        assert regime_change.expected_duration is not None
        
        # Verify regime change was stored
        assert len(enhanced_monitor.regime_history) == 2
    
    @pytest.mark.asyncio
    async def test_monitor_russian_economic_indicators(self, enhanced_monitor):
        """Test Russian economic indicators monitoring"""
        # Mock external data fetching
        enhanced_monitor._fetch_rub_usd_rate = AsyncMock(return_value=Decimal("75.50"))
        enhanced_monitor._fetch_oil_price = AsyncMock(return_value=Decimal("80.25"))
        enhanced_monitor._fetch_cbr_rate = AsyncMock(return_value=16.0)
        enhanced_monitor._calculate_rub_volatility = Mock(return_value=0.05)
        enhanced_monitor._calculate_oil_price_change = Mock(return_value=0.02)
        enhanced_monitor._analyze_rate_trend = Mock(return_value="RISING")
        enhanced_monitor._calculate_economic_stress_index = Mock(return_value=0.6)
        
        # Monitor indicators
        indicators = await enhanced_monitor.monitor_russian_economic_indicators()
        
        # Verify indicators
        assert isinstance(indicators, dict)
        assert 'rub_usd_rate' in indicators
        assert 'rub_volatility' in indicators
        assert 'oil_price' in indicators
        assert 'oil_change' in indicators
        assert 'cbr_rate' in indicators
        assert 'rate_trend' in indicators
        assert 'economic_stress_index' in indicators
        
        # Verify data was stored
        assert len(enhanced_monitor.rub_usd_history) == 1
        assert len(enhanced_monitor.oil_price_history) == 1
        assert len(enhanced_monitor.cbr_rate_history) == 1
    
    @pytest.mark.asyncio
    async def test_send_enhanced_market_alerts(self, enhanced_monitor, sample_market_data):
        """Test sending enhanced market alerts"""
        # Set up preferences
        preferences = NotificationPreferences(
            user_id="test_user",
            email="test@example.com"
        )
        
        # Mock monitoring methods to trigger alerts
        enhanced_monitor.monitor_market_sentiment = AsyncMock(
            return_value=MarketSentiment(
                timestamp=datetime.now(),
                overall_sentiment="BEARISH",
                sentiment_score=-0.5,  # Above threshold
                confidence=0.8,
                key_factors=["Negative news"],
                sector_sentiments={}
            )
        )
        
        enhanced_monitor.assess_comprehensive_risk = AsyncMock(
            return_value=RiskAssessment(
                timestamp=datetime.now(),
                overall_risk_level="HIGH",
                risk_score=0.8,  # Above threshold
                volatility_risk=0.7,
                geopolitical_risk=0.8,
                liquidity_risk=0.6,
                currency_risk=0.7,
                recommendations=[]
            )
        )
        
        enhanced_monitor.detect_market_regime_changes = AsyncMock(
            return_value=MarketRegimeChange(
                timestamp=datetime.now(),
                previous_regime="NORMAL",
                current_regime="CRISIS",
                confidence=0.9,
                key_indicators=["Market crash"]
            )
        )
        
        enhanced_monitor.monitor_russian_economic_indicators = AsyncMock(
            return_value={'economic_stress_index': 0.8}  # Above threshold
        )
        
        # Mock notification service
        enhanced_monitor.notification_service.send_market_alert = AsyncMock(
            return_value=[Mock()]
        )
        
        # Send alerts
        alerts = await enhanced_monitor.send_enhanced_market_alerts(
            sample_market_data, preferences
        )
        
        # Verify alerts were sent
        assert len(alerts) >= 1
        assert enhanced_monitor.notification_service.send_market_alert.call_count >= 1
    
    def test_analyze_price_sentiment(self, enhanced_monitor, sample_market_data):
        """Test price sentiment analysis"""
        sentiment = enhanced_monitor._analyze_price_sentiment(sample_market_data)
        
        # Should be positive due to SBER +5% outweighing GAZP -3%
        assert isinstance(sentiment, float)
        assert -1.0 <= sentiment <= 1.0
    
    @pytest.mark.asyncio
    async def test_analyze_news_sentiment(self, enhanced_monitor, sample_news_data):
        """Test news sentiment analysis"""
        sentiment = await enhanced_monitor._analyze_news_sentiment(sample_news_data)
        
        # Should be mixed due to positive and negative news
        assert isinstance(sentiment, float)
        assert -1.0 <= sentiment <= 1.0
    
    def test_analyze_volume_sentiment(self, enhanced_monitor, sample_market_data):
        """Test volume sentiment analysis"""
        # Mock average volume
        enhanced_monitor._get_average_volume = AsyncMock(return_value=1000000)
        
        sentiment = enhanced_monitor._analyze_volume_sentiment(sample_market_data)
        
        # Should reflect volume patterns
        assert isinstance(sentiment, float)
        assert -1.0 <= sentiment <= 1.0
    
    def test_identify_sentiment_factors(self, enhanced_monitor):
        """Test sentiment factor identification"""
        factors = enhanced_monitor._identify_sentiment_factors(0.4, -0.2, 0.1)
        
        assert isinstance(factors, list)
        assert any("положительная" in factor for factor in factors)  # Positive price sentiment
    
    def test_analyze_sector_sentiments(self, enhanced_monitor, sample_market_data):
        """Test sector sentiment analysis"""
        sentiments = enhanced_monitor._analyze_sector_sentiments(sample_market_data)
        
        assert isinstance(sentiments, dict)
        # Should have banking sector sentiment
        assert any("БАНКИ" in sector or "НЕФТЕГАЗ" in sector for sector in sentiments.keys())
    
    @pytest.mark.asyncio
    async def test_calculate_volatility_risk(self, enhanced_monitor, sample_market_data):
        """Test volatility risk calculation"""
        # Mock volatility metrics
        enhanced_monitor._calculate_volatility_metrics = AsyncMock(
            return_value=Mock(current_volatility=0.05)
        )
        
        risk = await enhanced_monitor._calculate_volatility_risk(sample_market_data)
        
        assert isinstance(risk, float)
        assert 0.0 <= risk <= 1.0
    
    @pytest.mark.asyncio
    async def test_assess_geopolitical_risk(self, enhanced_monitor):
        """Test geopolitical risk assessment"""
        # Add some geopolitical events
        enhanced_monitor.geopolitical_events = [
            {'timestamp': datetime.now(), 'type': 'SANCTIONS'},
            {'timestamp': datetime.now() - timedelta(days=2), 'type': 'POLICY'}
        ]
        
        risk = await enhanced_monitor._assess_geopolitical_risk()
        
        assert isinstance(risk, float)
        assert 0.0 <= risk <= 1.0
    
    def test_calculate_liquidity_risk(self, enhanced_monitor, sample_market_data):
        """Test liquidity risk calculation"""
        # Mock average volume
        enhanced_monitor._get_average_volume = AsyncMock(return_value=2000000)
        
        risk = enhanced_monitor._calculate_liquidity_risk(sample_market_data)
        
        assert isinstance(risk, float)
        assert 0.0 <= risk <= 1.0
    
    @pytest.mark.asyncio
    async def test_assess_currency_risk(self, enhanced_monitor):
        """Test currency risk assessment"""
        # Add RUB history
        enhanced_monitor.rub_usd_history = [
            (datetime.now() - timedelta(days=i), Decimal(str(75 + i * 0.5)))
            for i in range(20)
        ]
        
        risk = await enhanced_monitor._assess_currency_risk()
        
        assert isinstance(risk, float)
        assert 0.0 <= risk <= 1.0
    
    def test_generate_risk_recommendations(self, enhanced_monitor, sample_portfolio):
        """Test risk recommendation generation"""
        recommendations = enhanced_monitor._generate_risk_recommendations(
            0.8, 0.7, 0.8, 0.6, 0.7, sample_portfolio
        )
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        assert all(isinstance(rec, str) for rec in recommendations)
    
    def test_calculate_economic_stress_index(self, enhanced_monitor):
        """Test economic stress index calculation"""
        # Add some economic data
        enhanced_monitor.rub_usd_history = [
            (datetime.now() - timedelta(days=i), Decimal(str(75 + i * 0.2)))
            for i in range(10)
        ]
        enhanced_monitor.oil_price_history = [
            (datetime.now() - timedelta(days=i), Decimal(str(80 + i * 0.5)))
            for i in range(10)
        ]
        enhanced_monitor.cbr_rate_history = [
            (datetime.now() - timedelta(days=i), 16.0 + i * 0.1)
            for i in range(5)
        ]
        
        stress_index = enhanced_monitor._calculate_economic_stress_index()
        
        assert isinstance(stress_index, float)
        assert 0.0 <= stress_index <= 1.0
    
    def test_get_enhanced_market_summary(self, enhanced_monitor):
        """Test enhanced market summary generation"""
        # Add some test data
        enhanced_monitor.sentiment_history.append(
            MarketSentiment(
                timestamp=datetime.now(),
                overall_sentiment="BULLISH",
                sentiment_score=0.3,
                confidence=0.8,
                key_factors=[],
                sector_sentiments={}
            )
        )
        
        enhanced_monitor.risk_assessments.append(
            RiskAssessment(
                timestamp=datetime.now(),
                overall_risk_level="MEDIUM",
                risk_score=0.5,
                volatility_risk=0.4,
                geopolitical_risk=0.5,
                liquidity_risk=0.3,
                currency_risk=0.6,
                recommendations=[]
            )
        )
        
        summary = enhanced_monitor.get_enhanced_market_summary()
        
        assert isinstance(summary, dict)
        assert 'timestamp' in summary
        assert 'basic_condition' in summary
        assert 'sentiment' in summary
        assert 'risk_assessment' in summary
        assert 'economic_indicators' in summary
    
    def test_data_history_limits(self, enhanced_monitor):
        """Test that data history is properly limited"""
        # Add more than the limit of sentiment history
        for i in range(150):
            enhanced_monitor.sentiment_history.append(
                MarketSentiment(
                    timestamp=datetime.now(),
                    overall_sentiment="NEUTRAL",
                    sentiment_score=0.0,
                    confidence=0.5,
                    key_factors=[],
                    sector_sentiments={}
                )
            )
        
        # Should be limited to 100
        assert len(enhanced_monitor.sentiment_history) == 100
        
        # Add more than the limit of risk assessments
        for i in range(80):
            enhanced_monitor.risk_assessments.append(
                RiskAssessment(
                    timestamp=datetime.now(),
                    overall_risk_level="LOW",
                    risk_score=0.2,
                    volatility_risk=0.1,
                    geopolitical_risk=0.2,
                    liquidity_risk=0.1,
                    currency_risk=0.3,
                    recommendations=[]
                )
            )
        
        # Should be limited to 50
        assert len(enhanced_monitor.risk_assessments) == 50


class TestMarketSentiment:
    """Test MarketSentiment data class"""
    
    def test_market_sentiment_creation(self):
        """Test creating market sentiment"""
        sentiment = MarketSentiment(
            timestamp=datetime.now(),
            overall_sentiment="BULLISH",
            sentiment_score=0.4,
            confidence=0.8,
            key_factors=["Positive earnings", "Strong volume"],
            sector_sentiments={"БАНКИ": 0.3, "НЕФТЕГАЗ": 0.1}
        )
        
        assert sentiment.overall_sentiment == "BULLISH"
        assert sentiment.sentiment_score == 0.4
        assert sentiment.confidence == 0.8
        assert len(sentiment.key_factors) == 2
        assert "БАНКИ" in sentiment.sector_sentiments


class TestRiskAssessment:
    """Test RiskAssessment data class"""
    
    def test_risk_assessment_creation(self):
        """Test creating risk assessment"""
        risk = RiskAssessment(
            timestamp=datetime.now(),
            overall_risk_level="HIGH",
            risk_score=0.8,
            volatility_risk=0.7,
            geopolitical_risk=0.9,
            liquidity_risk=0.6,
            currency_risk=0.8,
            recommendations=["Reduce positions", "Monitor news"]
        )
        
        assert risk.overall_risk_level == "HIGH"
        assert risk.risk_score == 0.8
        assert risk.geopolitical_risk == 0.9
        assert len(risk.recommendations) == 2


class TestMarketRegimeChange:
    """Test MarketRegimeChange data class"""
    
    def test_market_regime_change_creation(self):
        """Test creating market regime change"""
        regime_change = MarketRegimeChange(
            timestamp=datetime.now(),
            previous_regime="NORMAL",
            current_regime="VOLATILE",
            confidence=0.9,
            key_indicators=["High volatility", "Volume spike"],
            expected_duration="1-2 weeks"
        )
        
        assert regime_change.previous_regime == "NORMAL"
        assert regime_change.current_regime == "VOLATILE"
        assert regime_change.confidence == 0.9
        assert len(regime_change.key_indicators) == 2
        assert regime_change.expected_duration == "1-2 weeks"


if __name__ == "__main__":
    pytest.main([__file__])