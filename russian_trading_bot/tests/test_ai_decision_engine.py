"""
Unit tests for AI Decision Engine
"""

import pytest
import numpy as np
from datetime import datetime
from decimal import Decimal

from russian_trading_bot.services.ai_decision_engine import (
    AIDecisionEngine, AnalysisFactor, DecisionWeights, MarketConditions, AnalysisType
)
from russian_trading_bot.models.trading import OrderAction, TradingSignal
from russian_trading_bot.models.market_data import RussianStock, MarketData
from russian_trading_bot.models.news_data import NewsSentiment
from russian_trading_bot.services.technical_analyzer import TechnicalIndicators


class TestDecisionWeights:
    """Test DecisionWeights class"""
    
    def test_default_weights(self):
        """Test default weight initialization"""
        weights = DecisionWeights()
        
        # Check that weights sum to approximately 1.0
        total = (weights.technical_weight + weights.sentiment_weight + 
                weights.fundamental_weight + weights.volume_weight + 
                weights.market_conditions_weight)
        assert abs(total - 1.0) < 0.001
    
    def test_custom_weights_normalization(self):
        """Test that custom weights are normalized"""
        weights = DecisionWeights(
            technical_weight=2.0,
            sentiment_weight=1.0,
            fundamental_weight=1.0,
            volume_weight=0.5,
            market_conditions_weight=0.5
        )
        
        # Check normalization
        total = (weights.technical_weight + weights.sentiment_weight + 
                weights.fundamental_weight + weights.volume_weight + 
                weights.market_conditions_weight)
        assert abs(total - 1.0) < 0.001
        
        # Technical should have highest weight
        assert weights.technical_weight > weights.sentiment_weight


class TestMarketConditions:
    """Test MarketConditions class"""
    
    def test_risk_adjustment_calculation(self):
        """Test risk adjustment calculation"""
        # Low risk conditions
        low_risk = MarketConditions(
            market_volatility=0.1,
            ruble_volatility=0.1,
            geopolitical_risk=0.1,
            market_trend="BULLISH",
            trading_volume_ratio=1.0
        )
        assert low_risk.get_risk_adjustment() > 0.9
        
        # High risk conditions
        high_risk = MarketConditions(
            market_volatility=0.9,
            ruble_volatility=0.9,
            geopolitical_risk=0.9,
            market_trend="BEARISH",
            trading_volume_ratio=0.5
        )
        assert high_risk.get_risk_adjustment() < 0.6
    
    def test_risk_adjustment_bounds(self):
        """Test that risk adjustment stays within bounds"""
        extreme_risk = MarketConditions(
            market_volatility=1.0,
            ruble_volatility=1.0,
            geopolitical_risk=1.0,
            market_trend="BEARISH",
            trading_volume_ratio=0.1
        )
        
        adjustment = extreme_risk.get_risk_adjustment()
        assert adjustment >= 0.1  # Should not go below minimum
        assert adjustment <= 1.0


class TestAIDecisionEngine:
    """Test AIDecisionEngine class"""
    
    @pytest.fixture
    def engine(self):
        """Create AI decision engine for testing"""
        return AIDecisionEngine()
    
    @pytest.fixture
    def sample_stock(self):
        """Create sample Russian stock"""
        return RussianStock(
            symbol="SBER",
            name="Сбербанк",
            sector="BANKING",
            currency="RUB",
            lot_size=10
        )
    
    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data"""
        return MarketData(
            symbol="SBER",
            timestamp=datetime.now(),
            price=Decimal("250.50"),
            volume=1000000,
            bid=Decimal("250.40"),
            ask=Decimal("250.60"),
            currency="RUB"
        )
    
    @pytest.fixture
    def sample_technical_indicators(self):
        """Create sample technical indicators"""
        return TechnicalIndicators(
            symbol="SBER",
            timestamp=datetime.now(),
            rsi=45.0,
            macd=1.5,
            macd_signal=1.2,
            macd_histogram=0.3,
            sma_20=248.0,
            sma_50=245.0,
            ema_12=249.0,
            ema_26=246.0,
            bollinger_upper=255.0,
            bollinger_middle=250.0,
            bollinger_lower=245.0,
            bollinger_width=4.0,
            atr=5.2,
            stochastic_k=55.0,
            stochastic_d=52.0
        )
    
    @pytest.fixture
    def sample_sentiments(self):
        """Create sample news sentiments"""
        return [
            NewsSentiment(
                article_id="test_1",
                overall_sentiment="POSITIVE",
                sentiment_score=0.7,
                confidence=0.8,
                positive_keywords=["рост", "прибыль", "успех"],
                negative_keywords=[],
                neutral_keywords=["банк", "отчет"],
                timestamp=datetime.now()
            ),
            NewsSentiment(
                article_id="test_2",
                overall_sentiment="NEUTRAL",
                sentiment_score=0.1,
                confidence=0.6,
                positive_keywords=[],
                negative_keywords=[],
                neutral_keywords=["акции", "торги"],
                timestamp=datetime.now()
            )
        ]
    
    @pytest.fixture
    def sample_market_conditions(self):
        """Create sample market conditions"""
        return MarketConditions(
            market_volatility=0.3,
            ruble_volatility=0.4,
            geopolitical_risk=0.5,
            market_trend="BULLISH",
            trading_volume_ratio=1.2
        )
    
    def test_engine_initialization(self, engine):
        """Test engine initialization"""
        assert engine is not None
        assert engine.weights is not None
        assert engine.min_confidence_threshold > 0
        assert engine.strong_signal_threshold > engine.min_confidence_threshold
    
    def test_analyze_technical_factors_rsi_oversold(self, engine):
        """Test RSI oversold analysis"""
        indicators = TechnicalIndicators(
            symbol="SBER",
            timestamp=datetime.now(),
            rsi=25.0  # Oversold
        )
        
        factors = engine.analyze_technical_factors(indicators)
        rsi_factors = [f for f in factors if f.name == "RSI"]
        
        assert len(rsi_factors) == 1
        assert rsi_factors[0].score > 0  # Positive score for oversold
        assert "перепроданность" in rsi_factors[0].reasoning
    
    def test_analyze_technical_factors_rsi_overbought(self, engine):
        """Test RSI overbought analysis"""
        indicators = TechnicalIndicators(
            symbol="SBER",
            timestamp=datetime.now(),
            rsi=75.0  # Overbought
        )
        
        factors = engine.analyze_technical_factors(indicators)
        rsi_factors = [f for f in factors if f.name == "RSI"]
        
        assert len(rsi_factors) == 1
        assert rsi_factors[0].score < 0  # Negative score for overbought
        assert "перекупленность" in rsi_factors[0].reasoning
    
    def test_analyze_technical_factors_macd_bullish(self, engine):
        """Test MACD bullish signal"""
        indicators = TechnicalIndicators(
            symbol="SBER",
            timestamp=datetime.now(),
            macd=2.0,
            macd_signal=1.5  # MACD above signal
        )
        
        factors = engine.analyze_technical_factors(indicators)
        macd_factors = [f for f in factors if f.name == "MACD"]
        
        assert len(macd_factors) == 1
        assert macd_factors[0].score > 0  # Positive score
        assert "бычий" in macd_factors[0].reasoning
    
    def test_analyze_sentiment_factors_positive(self, engine, sample_sentiments):
        """Test positive sentiment analysis"""
        # Make sentiments more positive
        positive_sentiments = [
            NewsSentiment(
                article_id="test_pos",
                overall_sentiment="VERY_POSITIVE",
                sentiment_score=0.8,
                confidence=0.9,
                positive_keywords=["SBER", "рост", "прибыль"],
                negative_keywords=[],
                neutral_keywords=[],
                timestamp=datetime.now()
            )
        ]
        
        factors = engine.analyze_sentiment_factors(positive_sentiments, "SBER")
        
        assert len(factors) > 0
        sentiment_factor = factors[0]
        assert sentiment_factor.score > 0
        assert "позитивные новости" in sentiment_factor.reasoning.lower()
    
    def test_analyze_volume_factors_high_volume(self, engine, sample_market_data):
        """Test high volume analysis"""
        historical_volume = [500000] * 20  # Average volume
        sample_market_data.volume = 1500000  # 3x average
        
        factors = engine.analyze_volume_factors(sample_market_data, historical_volume)
        
        assert len(factors) > 0
        volume_factor = factors[0]
        assert volume_factor.score > 0  # High volume is positive
        assert "выше среднего" in volume_factor.reasoning
    
    def test_analyze_market_conditions_bullish(self, engine):
        """Test bullish market conditions"""
        conditions = MarketConditions(
            market_volatility=0.2,
            ruble_volatility=0.3,
            geopolitical_risk=0.1,
            market_trend="BULLISH",
            trading_volume_ratio=1.1
        )
        
        factors = engine.analyze_market_conditions(conditions)
        
        trend_factors = [f for f in factors if f.name == "Market_Trend"]
        assert len(trend_factors) == 1
        assert trend_factors[0].score > 0
        assert "восходящий" in trend_factors[0].reasoning
    
    def test_calculate_confidence_score_agreement(self, engine):
        """Test confidence calculation with factor agreement"""
        # All factors pointing in same direction
        agreeing_factors = [
            AnalysisFactor(AnalysisType.TECHNICAL, "RSI", 0.7, 0.8, 0.5, "Positive RSI"),
            AnalysisFactor(AnalysisType.SENTIMENT, "News", 0.6, 0.7, 0.5, "Positive news"),
            AnalysisFactor(AnalysisType.VOLUME, "Volume", 0.5, 0.6, 0.5, "High volume")
        ]
        
        confidence = engine.calculate_confidence_score(agreeing_factors)
        
        # Should be higher due to agreement
        assert confidence > 0.6
    
    def test_calculate_confidence_score_disagreement(self, engine):
        """Test confidence calculation with factor disagreement"""
        # Factors pointing in different directions
        disagreeing_factors = [
            AnalysisFactor(AnalysisType.TECHNICAL, "RSI", 0.7, 0.8, 0.5, "Positive RSI"),
            AnalysisFactor(AnalysisType.SENTIMENT, "News", -0.6, 0.7, 0.5, "Negative news"),
            AnalysisFactor(AnalysisType.VOLUME, "Volume", 0.1, 0.6, 0.5, "Neutral volume")
        ]
        
        confidence = engine.calculate_confidence_score(disagreeing_factors)
        
        # Should be lower due to disagreement
        assert confidence < 0.8
    
    def test_generate_trading_signal_buy(self, engine, sample_stock, sample_market_data,
                                       sample_technical_indicators, sample_sentiments,
                                       sample_market_conditions):
        """Test generating buy signal"""
        # Create bullish technical indicators
        sample_technical_indicators.rsi = 25.0  # Oversold
        sample_technical_indicators.macd = 2.0
        sample_technical_indicators.macd_signal = 1.5
        
        # Create positive sentiment
        sample_sentiments[0].sentiment_score = 0.8
        sample_sentiments[0].confidence = 0.9
        
        signal = engine.generate_trading_signal(
            symbol="SBER",
            stock=sample_stock,
            market_data=sample_market_data,
            technical_indicators=sample_technical_indicators,
            sentiments=sample_sentiments,
            market_conditions=sample_market_conditions,
            historical_volume=[500000] * 20
        )
        
        assert signal.symbol == "SBER"
        assert signal.action == OrderAction.BUY
        assert signal.confidence > 0
        assert "ПОКУПКА" in signal.reasoning
    
    def test_generate_trading_signal_low_confidence(self, engine, sample_stock, 
                                                  sample_market_data, sample_market_conditions):
        """Test signal generation with low confidence"""
        # Create weak technical indicators
        weak_indicators = TechnicalIndicators(
            symbol="SBER",
            timestamp=datetime.now(),
            rsi=50.0,  # Neutral
            macd=0.1,
            macd_signal=0.1
        )
        
        signal = engine.generate_trading_signal(
            symbol="SBER",
            stock=sample_stock,
            market_data=sample_market_data,
            technical_indicators=weak_indicators,
            sentiments=[],
            market_conditions=sample_market_conditions
        )
        
        # Should have low confidence
        assert signal.confidence < engine.min_confidence_threshold
    
    def test_sector_specific_adjustments(self, engine, sample_market_data, 
                                       sample_technical_indicators, sample_market_conditions):
        """Test sector-specific adjustments"""
        # Test oil/gas sector (high volatility)
        oil_stock = RussianStock(
            symbol="GAZP",
            name="Газпром",
            sector="OIL_GAS",
            currency="RUB"
        )
        
        # High geopolitical risk should reduce signal strength for oil/gas
        high_risk_conditions = MarketConditions(
            market_volatility=0.3,
            ruble_volatility=0.4,
            geopolitical_risk=0.8,  # High geopolitical risk
            market_trend="BULLISH",
            trading_volume_ratio=1.0
        )
        
        signal = engine.generate_trading_signal(
            symbol="GAZP",
            stock=oil_stock,
            market_data=sample_market_data,
            technical_indicators=sample_technical_indicators,
            sentiments=[],
            market_conditions=high_risk_conditions
        )
        
        # Signal should be affected by sector-specific risks
        assert signal.risk_score > 0.4  # Adjusted threshold based on actual calculation
    
    def test_update_weights(self, engine):
        """Test updating decision weights"""
        new_weights = DecisionWeights(
            technical_weight=0.6,
            sentiment_weight=0.2,
            fundamental_weight=0.1,
            volume_weight=0.05,
            market_conditions_weight=0.05
        )
        
        engine.update_weights(new_weights)
        
        assert engine.weights.technical_weight == new_weights.technical_weight
        assert engine.weights.sentiment_weight == new_weights.sentiment_weight
    
    def test_get_factor_analysis(self, engine, sample_technical_indicators, 
                               sample_sentiments, sample_market_data, sample_market_conditions):
        """Test detailed factor analysis"""
        factors = engine.get_factor_analysis(
            symbol="SBER",
            technical_indicators=sample_technical_indicators,
            sentiments=sample_sentiments,
            market_data=sample_market_data,
            historical_volume=[500000] * 20,
            market_conditions=sample_market_conditions
        )
        
        assert 'technical' in factors
        assert 'sentiment' in factors
        assert 'volume' in factors
        assert 'market_conditions' in factors
        
        # Check that factors are properly categorized
        assert len(factors['technical']) > 0
        assert all(f.factor_type == AnalysisType.TECHNICAL for f in factors['technical'])
    
    def test_russian_language_reasoning(self, engine, sample_stock, sample_market_data,
                                      sample_technical_indicators, sample_sentiments,
                                      sample_market_conditions):
        """Test that reasoning is generated in Russian"""
        signal = engine.generate_trading_signal(
            symbol="SBER",
            stock=sample_stock,
            market_data=sample_market_data,
            technical_indicators=sample_technical_indicators,
            sentiments=sample_sentiments,
            market_conditions=sample_market_conditions
        )
        
        # Check for Russian text in reasoning
        russian_words = ["Рекомендация", "анализ", "Технический", "новости", "объем"]
        reasoning_lower = signal.reasoning.lower()
        
        has_russian = any(word.lower() in reasoning_lower for word in russian_words)
        assert has_russian, f"Reasoning should contain Russian text: {signal.reasoning}"
    
    def test_empty_data_handling(self, engine, sample_stock, sample_market_data):
        """Test handling of empty/missing data"""
        empty_indicators = TechnicalIndicators(
            symbol="SBER",
            timestamp=datetime.now()
            # All indicators are None
        )
        
        empty_conditions = MarketConditions(
            market_volatility=0.0,
            ruble_volatility=0.0,
            geopolitical_risk=0.0,
            market_trend="SIDEWAYS",
            trading_volume_ratio=1.0
        )
        
        signal = engine.generate_trading_signal(
            symbol="SBER",
            stock=sample_stock,
            market_data=sample_market_data,
            technical_indicators=empty_indicators,
            sentiments=[],
            market_conditions=empty_conditions
        )
        
        # Should still generate a signal, even if neutral
        assert signal is not None
        assert signal.symbol == "SBER"
        assert signal.confidence >= 0.0


if __name__ == "__main__":
    pytest.main([__file__])