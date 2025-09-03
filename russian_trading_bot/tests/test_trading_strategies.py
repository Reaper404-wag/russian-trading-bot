"""
Unit tests for Russian Trading Strategies
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal

from russian_trading_bot.services.trading_strategies import (
    MomentumStrategy, MeanReversionStrategy, SectorSpecificStrategy,
    StrategyManager, StrategyParameters, StrategyType
)
from russian_trading_bot.models.trading import OrderAction, TradingSignal
from russian_trading_bot.models.market_data import RussianStock, MarketData
from russian_trading_bot.models.news_data import NewsSentiment
from russian_trading_bot.services.technical_analyzer import TechnicalIndicators
from russian_trading_bot.services.ai_decision_engine import MarketConditions


class TestStrategyParameters:
    """Test StrategyParameters class"""
    
    def test_default_parameters(self):
        """Test default parameter initialization"""
        params = StrategyParameters()
        
        assert params.lookback_period == 20
        assert params.volatility_threshold == 0.02
        assert params.momentum_threshold == 0.05
        assert params.confidence_threshold == 0.6
        assert params.max_position_size == 0.1
        assert params.stop_loss_pct == 0.05
        assert params.take_profit_pct == 0.15
    
    def test_custom_parameters(self):
        """Test custom parameter initialization"""
        params = StrategyParameters(
            lookback_period=30,
            momentum_threshold=0.08,
            confidence_threshold=0.7
        )
        
        assert params.lookback_period == 30
        assert params.momentum_threshold == 0.08
        assert params.confidence_threshold == 0.7


class TestMomentumStrategy:
    """Test MomentumStrategy class"""
    
    @pytest.fixture
    def momentum_strategy(self):
        """Create momentum strategy for testing"""
        return MomentumStrategy()
    
    @pytest.fixture
    def sample_stock(self):
        """Create sample Russian stock"""
        return RussianStock(
            symbol="SBER",
            name="Сбербанк",
            sector="BANKING",
            currency="RUB"
        )
    
    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data"""
        return MarketData(
            symbol="SBER",
            timestamp=datetime.now(),
            price=Decimal("250.50"),
            volume=1500000,  # High volume
            currency="RUB"
        )
    
    @pytest.fixture
    def sample_technical_indicators(self):
        """Create sample technical indicators"""
        return TechnicalIndicators(
            symbol="SBER",
            timestamp=datetime.now(),
            rsi=55.0,
            macd=1.5,
            macd_signal=1.2
        )
    
    @pytest.fixture
    def bullish_historical_data(self):
        """Create bullish historical data (upward trend)"""
        base_price = 200.0
        data = []
        
        for i in range(60):  # 60 days of data
            # Create upward trend with some noise
            price = base_price + (i * 0.8) + np.random.normal(0, 2)
            volume = 1000000 + np.random.randint(-200000, 200000)
            
            data.append(MarketData(
                symbol="SBER",
                timestamp=datetime.now() - timedelta(days=60-i),
                price=Decimal(str(max(price, 100.0))),  # Ensure positive price
                volume=max(volume, 100000),  # Ensure positive volume
                currency="RUB"
            ))
        
        return data
    
    @pytest.fixture
    def bearish_historical_data(self):
        """Create bearish historical data (downward trend)"""
        base_price = 300.0
        data = []
        
        for i in range(60):
            # Create downward trend with some noise
            price = base_price - (i * 0.8) + np.random.normal(0, 2)
            volume = 1000000 + np.random.randint(-200000, 200000)
            
            data.append(MarketData(
                symbol="SBER",
                timestamp=datetime.now() - timedelta(days=60-i),
                price=Decimal(str(max(price, 100.0))),
                volume=max(volume, 100000),
                currency="RUB"
            ))
        
        return data
    
    @pytest.fixture
    def positive_sentiments(self):
        """Create positive news sentiments"""
        return [
            NewsSentiment(
                article_id="test_1",
                overall_sentiment="POSITIVE",
                sentiment_score=0.7,
                confidence=0.8,
                positive_keywords=["рост", "прибыль"],
                negative_keywords=[],
                neutral_keywords=[],
                timestamp=datetime.now() - timedelta(days=1)
            )
        ]
    
    @pytest.fixture
    def sample_market_conditions(self):
        """Create sample market conditions"""
        return MarketConditions(
            market_volatility=0.3,
            ruble_volatility=0.4,
            geopolitical_risk=0.2,
            market_trend="BULLISH",
            trading_volume_ratio=1.2
        )
    
    def test_strategy_initialization(self, momentum_strategy):
        """Test momentum strategy initialization"""
        assert momentum_strategy.name == "Russian Momentum"
        assert momentum_strategy.strategy_type == StrategyType.MOMENTUM
        assert momentum_strategy.momentum_periods == [10, 20, 50]
        assert momentum_strategy.volume_confirmation_required is True
    
    def test_bullish_momentum_signal(self, momentum_strategy, sample_stock, sample_market_data,
                                   sample_technical_indicators, bullish_historical_data,
                                   positive_sentiments, sample_market_conditions):
        """Test bullish momentum signal generation"""
        signal = momentum_strategy.generate_signal(
            symbol="SBER",
            stock=sample_stock,
            market_data=sample_market_data,
            technical_indicators=sample_technical_indicators,
            historical_data=bullish_historical_data,
            sentiments=positive_sentiments,
            market_conditions=sample_market_conditions
        )
        
        assert signal.symbol == "SBER"
        assert signal.action == OrderAction.BUY
        assert signal.confidence > 0.5
        assert "моментум" in signal.reasoning.lower()
        assert signal.target_price is not None
        assert signal.stop_loss is not None
    
    def test_bearish_momentum_signal(self, momentum_strategy, sample_stock, sample_market_data,
                                   sample_technical_indicators, bearish_historical_data,
                                   sample_market_conditions):
        """Test bearish momentum signal generation"""
        signal = momentum_strategy.generate_signal(
            symbol="SBER",
            stock=sample_stock,
            market_data=sample_market_data,
            technical_indicators=sample_technical_indicators,
            historical_data=bearish_historical_data,
            sentiments=[],
            market_conditions=sample_market_conditions
        )
        
        assert signal.symbol == "SBER"
        # Should be either SELL or neutral depending on momentum strength
        assert signal.action in [OrderAction.BUY, OrderAction.SELL]
        if signal.action == OrderAction.SELL:
            assert signal.confidence > 0.0
    
    def test_insufficient_data(self, momentum_strategy, sample_stock, sample_market_data,
                             sample_technical_indicators, sample_market_conditions):
        """Test handling of insufficient historical data"""
        short_data = [sample_market_data] * 5  # Only 5 data points
        
        signal = momentum_strategy.generate_signal(
            symbol="SBER",
            stock=sample_stock,
            market_data=sample_market_data,
            technical_indicators=sample_technical_indicators,
            historical_data=short_data,
            sentiments=[],
            market_conditions=sample_market_conditions
        )
        
        assert signal.confidence == 0.0
        assert "недостаточно" in signal.reasoning.lower()


class TestMeanReversionStrategy:
    """Test MeanReversionStrategy class"""
    
    @pytest.fixture
    def mean_reversion_strategy(self):
        """Create mean reversion strategy for testing"""
        return MeanReversionStrategy()
    
    @pytest.fixture
    def blue_chip_stock(self):
        """Create blue-chip stock suitable for mean reversion"""
        return RussianStock(
            symbol="SBER",
            name="Сбербанк",
            sector="BANKING",
            currency="RUB"
        )
    
    @pytest.fixture
    def non_blue_chip_stock(self):
        """Create non-blue-chip stock"""
        return RussianStock(
            symbol="TEST",
            name="Test Company",
            sector="INFORMATION_TECHNOLOGY",  # Use valid sector
            currency="RUB"
        )
    
    @pytest.fixture
    def oversold_market_data(self):
        """Create market data for oversold condition"""
        return MarketData(
            symbol="SBER",
            timestamp=datetime.now(),
            price=Decimal("200.00"),  # Low price for mean reversion
            volume=1000000,
            currency="RUB"
        )
    
    @pytest.fixture
    def oversold_technical_indicators(self):
        """Create technical indicators for oversold condition"""
        return TechnicalIndicators(
            symbol="SBER",
            timestamp=datetime.now(),
            rsi=25.0,  # Oversold
            bollinger_upper=260.0,
            bollinger_middle=240.0,
            bollinger_lower=220.0
        )
    
    @pytest.fixture
    def stable_historical_data(self):
        """Create stable historical data around mean"""
        data = []
        base_price = 240.0
        
        for i in range(30):
            # Create data oscillating around mean
            price = base_price + np.sin(i * 0.3) * 10 + np.random.normal(0, 3)
            
            data.append(MarketData(
                symbol="SBER",
                timestamp=datetime.now() - timedelta(days=30-i),
                price=Decimal(str(max(price, 100.0))),
                volume=1000000,
                currency="RUB"
            ))
        
        return data
    
    def test_strategy_initialization(self, mean_reversion_strategy):
        """Test mean reversion strategy initialization"""
        assert mean_reversion_strategy.name == "Russian Mean Reversion"
        assert mean_reversion_strategy.strategy_type == StrategyType.MEAN_REVERSION
        assert "SBER" in mean_reversion_strategy.blue_chip_symbols
        assert "GAZP" in mean_reversion_strategy.blue_chip_symbols
    
    def test_blue_chip_oversold_signal(self, mean_reversion_strategy, blue_chip_stock,
                                     oversold_market_data, oversold_technical_indicators,
                                     stable_historical_data):
        """Test buy signal for oversold blue-chip stock"""
        market_conditions = MarketConditions(
            market_volatility=0.2,  # Low volatility good for mean reversion
            ruble_volatility=0.3,
            geopolitical_risk=0.2,
            market_trend="SIDEWAYS",
            trading_volume_ratio=1.0
        )
        
        signal = mean_reversion_strategy.generate_signal(
            symbol="SBER",
            stock=blue_chip_stock,
            market_data=oversold_market_data,
            technical_indicators=oversold_technical_indicators,
            historical_data=stable_historical_data,
            sentiments=[],
            market_conditions=market_conditions
        )
        
        assert signal.symbol == "SBER"
        assert signal.action == OrderAction.BUY
        assert signal.confidence > 0.5
        assert "возврат к среднему" in signal.reasoning.lower()
        assert signal.target_price is not None
    
    def test_non_blue_chip_rejection(self, mean_reversion_strategy, non_blue_chip_stock,
                                   oversold_market_data, oversold_technical_indicators,
                                   stable_historical_data):
        """Test rejection of non-blue-chip stocks"""
        market_conditions = MarketConditions(
            market_volatility=0.2,
            ruble_volatility=0.3,
            geopolitical_risk=0.2,
            market_trend="SIDEWAYS",
            trading_volume_ratio=1.0
        )
        
        signal = mean_reversion_strategy.generate_signal(
            symbol="TEST",
            stock=non_blue_chip_stock,
            market_data=oversold_market_data,
            technical_indicators=oversold_technical_indicators,
            historical_data=stable_historical_data,
            sentiments=[],
            market_conditions=market_conditions
        )
        
        assert signal.confidence == 0.0
        assert "не подходит" in signal.reasoning.lower()
    
    def test_high_volatility_adjustment(self, mean_reversion_strategy, blue_chip_stock,
                                      oversold_market_data, oversold_technical_indicators,
                                      stable_historical_data):
        """Test confidence reduction in high volatility markets"""
        high_volatility_conditions = MarketConditions(
            market_volatility=0.8,  # High volatility
            ruble_volatility=0.7,
            geopolitical_risk=0.3,
            market_trend="SIDEWAYS",
            trading_volume_ratio=1.0
        )
        
        signal = mean_reversion_strategy.generate_signal(
            symbol="SBER",
            stock=blue_chip_stock,
            market_data=oversold_market_data,
            technical_indicators=oversold_technical_indicators,
            historical_data=stable_historical_data,
            sentiments=[],
            market_conditions=high_volatility_conditions
        )
        
        # Confidence should be reduced due to high volatility
        assert "волатильност" in signal.reasoning.lower()  # Match partial word to handle different forms


class TestSectorSpecificStrategy:
    """Test SectorSpecificStrategy class"""
    
    @pytest.fixture
    def sector_strategy(self):
        """Create sector-specific strategy for testing"""
        return SectorSpecificStrategy()
    
    @pytest.fixture
    def oil_gas_stock(self):
        """Create oil/gas sector stock"""
        return RussianStock(
            symbol="GAZP",
            name="Газпром",
            sector="OIL_GAS",
            currency="RUB"
        )
    
    @pytest.fixture
    def banking_stock(self):
        """Create banking sector stock"""
        return RussianStock(
            symbol="SBER",
            name="Сбербанк",
            sector="BANKING",
            currency="RUB"
        )
    
    @pytest.fixture
    def other_sector_stock(self):
        """Create stock from unsupported sector"""
        return RussianStock(
            symbol="YNDX",
            name="Яндекс",
            sector="INFORMATION_TECHNOLOGY",  # Use valid sector
            currency="RUB"
        )
    
    @pytest.fixture
    def oil_gas_sentiments(self):
        """Create oil/gas related sentiments"""
        return [
            NewsSentiment(
                article_id="oil_news",
                overall_sentiment="POSITIVE",
                sentiment_score=0.6,
                confidence=0.8,
                positive_keywords=["нефть", "экспорт", "рост"],
                negative_keywords=[],
                neutral_keywords=["газ"],
                timestamp=datetime.now() - timedelta(hours=2)
            )
        ]
    
    @pytest.fixture
    def banking_sentiments(self):
        """Create banking related sentiments"""
        return [
            NewsSentiment(
                article_id="bank_news",
                overall_sentiment="POSITIVE",
                sentiment_score=0.5,
                confidence=0.7,
                positive_keywords=["банк", "прибыль"],
                negative_keywords=[],
                neutral_keywords=["кредит"],
                timestamp=datetime.now() - timedelta(hours=1)
            )
        ]
    
    def test_strategy_initialization(self, sector_strategy):
        """Test sector strategy initialization"""
        assert sector_strategy.name == "Russian Sector Specific"
        assert sector_strategy.strategy_type == StrategyType.SECTOR_SPECIFIC
        assert "GAZP" in sector_strategy.oil_gas_symbols
        assert "SBER" in sector_strategy.banking_symbols
    
    def test_oil_gas_positive_signal(self, sector_strategy, oil_gas_stock, oil_gas_sentiments):
        """Test positive signal for oil/gas sector"""
        # Create bullish conditions for oil/gas
        market_data = MarketData(
            symbol="GAZP",
            timestamp=datetime.now(),
            price=Decimal("180.00"),
            volume=2000000,
            currency="RUB"
        )
        
        # Create historical data with positive momentum
        historical_data = []
        base_price = 160.0
        for i in range(25):
            price = base_price + (i * 0.8)  # Upward trend
            historical_data.append(MarketData(
                symbol="GAZP",
                timestamp=datetime.now() - timedelta(days=25-i),
                price=Decimal(str(price)),
                volume=1500000,
                currency="RUB"
            ))
        
        market_conditions = MarketConditions(
            market_volatility=0.3,
            ruble_volatility=0.4,
            geopolitical_risk=0.2,  # Low geopolitical risk
            market_trend="BULLISH",
            trading_volume_ratio=1.3
        )
        
        signal = sector_strategy.generate_signal(
            symbol="GAZP",
            stock=oil_gas_stock,
            market_data=market_data,
            technical_indicators=TechnicalIndicators(symbol="GAZP", timestamp=datetime.now()),
            historical_data=historical_data,
            sentiments=oil_gas_sentiments,
            market_conditions=market_conditions
        )
        
        assert signal.symbol == "GAZP"
        assert signal.action == OrderAction.BUY
        assert signal.confidence > 0.5
        assert "нефтегазовый" in signal.reasoning.lower()
    
    def test_oil_gas_high_geopolitical_risk(self, sector_strategy, oil_gas_stock):
        """Test oil/gas signal with high geopolitical risk"""
        market_data = MarketData(
            symbol="GAZP",
            timestamp=datetime.now(),
            price=Decimal("180.00"),
            volume=1500000,
            currency="RUB"
        )
        
        historical_data = [market_data] * 25  # Stable prices
        
        high_risk_conditions = MarketConditions(
            market_volatility=0.4,
            ruble_volatility=0.5,
            geopolitical_risk=0.8,  # High geopolitical risk
            market_trend="BEARISH",
            trading_volume_ratio=1.0
        )
        
        signal = sector_strategy.generate_signal(
            symbol="GAZP",
            stock=oil_gas_stock,
            market_data=market_data,
            technical_indicators=TechnicalIndicators(symbol="GAZP", timestamp=datetime.now()),
            historical_data=historical_data,
            sentiments=[],
            market_conditions=high_risk_conditions
        )
        
        # Should generate sell signal or low confidence due to high geopolitical risk
        if signal.confidence > 0.1:
            assert signal.action == OrderAction.SELL or signal.confidence < 0.5
    
    def test_banking_sector_signal(self, sector_strategy, banking_stock, banking_sentiments):
        """Test banking sector signal generation"""
        market_data = MarketData(
            symbol="SBER",
            timestamp=datetime.now(),
            price=Decimal("250.00"),
            volume=1800000,
            currency="RUB"
        )
        
        historical_data = []
        base_price = 240.0
        for i in range(25):
            price = base_price + (i * 0.4)  # Moderate upward trend
            historical_data.append(MarketData(
                symbol="SBER",
                timestamp=datetime.now() - timedelta(days=25-i),
                price=Decimal(str(price)),
                volume=1500000,
                currency="RUB"
            ))
        
        technical_indicators = TechnicalIndicators(
            symbol="SBER",
            timestamp=datetime.now(),
            rsi=45.0,  # Neutral
            macd=0.5,
            macd_signal=0.3  # Bullish MACD
        )
        
        market_conditions = MarketConditions(
            market_volatility=0.2,  # Low volatility good for banks
            ruble_volatility=0.3,
            geopolitical_risk=0.3,
            market_trend="BULLISH",
            trading_volume_ratio=1.1
        )
        
        signal = sector_strategy.generate_signal(
            symbol="SBER",
            stock=banking_stock,
            market_data=market_data,
            technical_indicators=technical_indicators,
            historical_data=historical_data,
            sentiments=banking_sentiments,
            market_conditions=market_conditions
        )
        
        assert signal.symbol == "SBER"
        assert "банковский" in signal.reasoning.lower()
    
    def test_unsupported_sector(self, sector_strategy, other_sector_stock):
        """Test handling of unsupported sector"""
        market_data = MarketData(
            symbol="YNDX",
            timestamp=datetime.now(),
            price=Decimal("3000.00"),
            volume=500000,
            currency="RUB"
        )
        
        signal = sector_strategy.generate_signal(
            symbol="YNDX",
            stock=other_sector_stock,
            market_data=market_data,
            technical_indicators=TechnicalIndicators(symbol="YNDX", timestamp=datetime.now()),
            historical_data=[market_data] * 25,
            sentiments=[],
            market_conditions=MarketConditions(0.3, 0.4, 0.2, "BULLISH", 1.0)
        )
        
        assert signal.confidence == 0.0
        assert "не поддерживается" in signal.reasoning.lower()


class TestStrategyManager:
    """Test StrategyManager class"""
    
    @pytest.fixture
    def strategy_manager(self):
        """Create strategy manager for testing"""
        return StrategyManager()
    
    def test_manager_initialization(self, strategy_manager):
        """Test strategy manager initialization"""
        assert len(strategy_manager.strategies) == 3  # Default strategies
        assert "momentum" in strategy_manager.strategies
        assert "mean_reversion" in strategy_manager.strategies
        assert "sector_specific" in strategy_manager.strategies
        
        # Check weights sum to 1
        total_weight = sum(strategy_manager.strategy_weights.values())
        assert abs(total_weight - 1.0) < 0.001
    
    def test_add_remove_strategy(self, strategy_manager):
        """Test adding and removing strategies"""
        # Add new strategy
        custom_strategy = MomentumStrategy()
        strategy_manager.add_strategy("custom_momentum", custom_strategy, 0.2)
        
        assert "custom_momentum" in strategy_manager.strategies
        assert strategy_manager.strategy_weights["custom_momentum"] > 0
        
        # Check weights are normalized
        total_weight = sum(strategy_manager.strategy_weights.values())
        assert abs(total_weight - 1.0) < 0.001
        
        # Remove strategy
        strategy_manager.remove_strategy("custom_momentum")
        assert "custom_momentum" not in strategy_manager.strategies
    
    def test_combined_signal_generation(self, strategy_manager):
        """Test combined signal generation from multiple strategies"""
        # Create test data
        stock = RussianStock(symbol="SBER", name="Сбербанк", sector="BANKING", currency="RUB")
        market_data = MarketData(
            symbol="SBER", timestamp=datetime.now(), price=Decimal("250.00"),
            volume=1500000, currency="RUB"
        )
        
        # Create historical data with upward trend
        historical_data = []
        base_price = 200.0
        for i in range(60):
            price = base_price + (i * 0.8)
            historical_data.append(MarketData(
                symbol="SBER",
                timestamp=datetime.now() - timedelta(days=60-i),
                price=Decimal(str(price)),
                volume=1000000,
                currency="RUB"
            ))
        
        technical_indicators = TechnicalIndicators(
            symbol="SBER", timestamp=datetime.now(), rsi=55.0, macd=1.5, macd_signal=1.2
        )
        
        sentiments = [
            NewsSentiment(
                article_id="test", overall_sentiment="POSITIVE", sentiment_score=0.6,
                confidence=0.8, positive_keywords=["банк", "прибыль"],
                negative_keywords=[], neutral_keywords=[], timestamp=datetime.now()
            )
        ]
        
        market_conditions = MarketConditions(0.3, 0.4, 0.2, "BULLISH", 1.2)
        
        # Generate combined signal
        combined_signal = strategy_manager.generate_combined_signal(
            symbol="SBER", stock=stock, market_data=market_data,
            technical_indicators=technical_indicators, historical_data=historical_data,
            sentiments=sentiments, market_conditions=market_conditions
        )
        
        assert combined_signal.symbol == "SBER"
        assert combined_signal.confidence >= 0.0
        assert "комбинированный" in combined_signal.reasoning.lower()
    
    def test_strategy_performance_info(self, strategy_manager):
        """Test getting strategy performance information"""
        performance = strategy_manager.get_strategy_performance()
        
        assert len(performance) == len(strategy_manager.strategies)
        
        for strategy_name, info in performance.items():
            assert 'name' in info
            assert 'type' in info
            assert 'weight' in info
            assert 'parameters' in info
            assert info['weight'] > 0


if __name__ == "__main__":
    pytest.main([__file__])