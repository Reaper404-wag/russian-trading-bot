"""
Unit tests for Russian market risk management service
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List

from ..services.risk_manager import (
    RussianMarketRiskManager,
    RiskParameters,
    RiskLevel,
    GeopoliticalRiskLevel,
    Position,
    Portfolio,
    TradeOrder,
    RiskAssessment,
    ValidationResult
)
from ..models.market_data import MarketData


class TestRussianMarketRiskManager:
    """Test cases for Russian market risk management"""
    
    @pytest.fixture
    def risk_manager(self):
        """Create risk manager instance for testing"""
        return RussianMarketRiskManager()
    
    @pytest.fixture
    def custom_risk_params(self):
        """Create custom risk parameters for testing"""
        return RiskParameters(
            max_position_size_percent=15.0,
            stop_loss_percent=8.0,
            volatility_adjustment_factor=2.0,
            ruble_volatility_threshold=3.0
        )
    
    @pytest.fixture
    def sample_portfolio(self):
        """Create sample portfolio for testing"""
        positions = {
            "SBER": Position(
                symbol="SBER",
                quantity=100,
                entry_price=Decimal("250.0"),
                current_price=Decimal("260.0"),
                market_value=Decimal("26000.0"),
                unrealized_pnl=Decimal("1000.0"),
                entry_date=datetime.now() - timedelta(days=5),
                sector="Banking"
            ),
            "GAZP": Position(
                symbol="GAZP",
                quantity=50,
                entry_price=Decimal("180.0"),
                current_price=Decimal("175.0"),
                market_value=Decimal("8750.0"),
                unrealized_pnl=Decimal("-250.0"),
                entry_date=datetime.now() - timedelta(days=3),
                sector="Energy"
            )
        }
        return Portfolio(
            positions=positions,
            cash_balance=Decimal("15000.0"),
            currency="RUB"
        )
    
    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data for testing"""
        return {
            "SBER": MarketData(
                symbol="SBER",
                timestamp=datetime.now(),
                price=Decimal("260.0"),
                volume=1000000,
                bid=Decimal("259.5"),
                ask=Decimal("260.5"),
                currency="RUB"
            ),
            "GAZP": MarketData(
                symbol="GAZP",
                timestamp=datetime.now(),
                price=Decimal("175.0"),
                volume=500000,
                bid=Decimal("174.8"),
                ask=Decimal("175.2"),
                currency="RUB"
            )
        }


class TestVolatilityAdjustedStopLoss:
    """Test volatility-adjusted stop loss calculations"""
    
    def test_stop_loss_with_low_volatility(self, risk_manager):
        """Test stop loss calculation with low volatility"""
        entry_price = Decimal("100.0")
        # Low volatility historical prices (1% daily moves)
        historical_prices = [
            Decimal("100.0"), Decimal("101.0"), Decimal("100.5"),
            Decimal("101.5"), Decimal("100.8"), Decimal("101.2")
        ]
        
        stop_loss = risk_manager.calculate_volatility_adjusted_stop_loss(
            "TEST", entry_price, historical_prices
        )
        
        # Should be close to default stop loss for low volatility
        expected_range = (Decimal("92.0"), Decimal("98.0"))  # 2-8% stop loss
        assert expected_range[0] <= stop_loss <= expected_range[1]
    
    def test_stop_loss_with_high_volatility(self, risk_manager):
        """Test stop loss calculation with high volatility"""
        entry_price = Decimal("100.0")
        # High volatility historical prices (5% daily moves)
        historical_prices = [
            Decimal("100.0"), Decimal("105.0"), Decimal("98.0"),
            Decimal("103.0"), Decimal("95.0"), Decimal("102.0")
        ]
        
        stop_loss = risk_manager.calculate_volatility_adjusted_stop_loss(
            "TEST", entry_price, historical_prices
        )
        
        # Should have wider stop loss for high volatility
        expected_range = (Decimal("80.0"), Decimal("95.0"))  # Wider range
        assert expected_range[0] <= stop_loss <= expected_range[1]
    
    def test_stop_loss_with_insufficient_data(self, risk_manager):
        """Test stop loss calculation with insufficient historical data"""
        entry_price = Decimal("100.0")
        historical_prices = [Decimal("100.0")]  # Only one price point
        
        stop_loss = risk_manager.calculate_volatility_adjusted_stop_loss(
            "TEST", entry_price, historical_prices
        )
        
        # Should fallback to default stop loss
        expected_stop_loss = entry_price * Decimal("0.95")  # 5% default
        assert abs(stop_loss - expected_stop_loss) < Decimal("0.1")
    
    def test_stop_loss_bounds(self, risk_manager):
        """Test that stop loss is within reasonable bounds"""
        entry_price = Decimal("100.0")
        # Extreme volatility
        historical_prices = [
            Decimal("100.0"), Decimal("150.0"), Decimal("50.0"),
            Decimal("120.0"), Decimal("30.0"), Decimal("180.0")
        ]
        
        stop_loss = risk_manager.calculate_volatility_adjusted_stop_loss(
            "TEST", entry_price, historical_prices
        )
        
        # Should be capped at reasonable levels (2% min, 25% max)
        assert Decimal("75.0") <= stop_loss <= Decimal("98.0")


class TestPositionSizing:
    """Test position sizing calculations"""
    
    def test_position_size_normal_conditions(self, risk_manager, sample_portfolio):
        """Test position sizing under normal market conditions"""
        entry_price = Decimal("200.0")
        
        position_size = risk_manager.calculate_position_size(
            "LKOH", entry_price, sample_portfolio
        )
        
        # Should respect maximum position size limits
        max_position_value = sample_portfolio.total_value * Decimal("0.10")  # 10% max
        max_shares = int(max_position_value / entry_price)
        
        assert 0 <= position_size <= max_shares
    
    def test_position_size_with_high_volatility(self, risk_manager, sample_portfolio):
        """Test position sizing with high volatility adjustment"""
        entry_price = Decimal("200.0")
        high_volatility = 0.15  # 15% daily volatility
        
        position_size = risk_manager.calculate_position_size(
            "LKOH", entry_price, sample_portfolio, volatility=high_volatility
        )
        
        # Should be smaller than normal position due to volatility
        normal_size = risk_manager.calculate_position_size(
            "LKOH", entry_price, sample_portfolio
        )
        
        assert position_size < normal_size
    
    def test_position_size_with_geopolitical_risk(self, risk_manager, sample_portfolio):
        """Test position sizing with elevated geopolitical risk"""
        entry_price = Decimal("200.0")
        
        # Normal conditions
        normal_size = risk_manager.calculate_position_size(
            "LKOH", entry_price, sample_portfolio,
            geopolitical_risk_level=GeopoliticalRiskLevel.NORMAL
        )
        
        # High geopolitical risk
        high_risk_size = risk_manager.calculate_position_size(
            "LKOH", entry_price, sample_portfolio,
            geopolitical_risk_level=GeopoliticalRiskLevel.HIGH
        )
        
        # Critical geopolitical risk
        critical_risk_size = risk_manager.calculate_position_size(
            "LKOH", entry_price, sample_portfolio,
            geopolitical_risk_level=GeopoliticalRiskLevel.CRITICAL
        )
        
        # Position sizes should decrease with increasing risk
        assert critical_risk_size < high_risk_size < normal_size
    
    def test_position_size_zero_portfolio(self, risk_manager):
        """Test position sizing with zero portfolio value"""
        empty_portfolio = Portfolio(
            positions={},
            cash_balance=Decimal("0.0")
        )
        
        position_size = risk_manager.calculate_position_size(
            "TEST", Decimal("100.0"), empty_portfolio
        )
        
        assert position_size == 0


class TestPortfolioRiskAssessment:
    """Test portfolio risk assessment functionality"""
    
    def test_risk_assessment_balanced_portfolio(self, risk_manager, sample_portfolio, sample_market_data):
        """Test risk assessment for a balanced portfolio"""
        risk_assessment = risk_manager.assess_portfolio_risk(
            sample_portfolio, sample_market_data
        )
        
        assert isinstance(risk_assessment, RiskAssessment)
        assert risk_assessment.overall_risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM]
        assert 0.0 <= risk_assessment.portfolio_risk_score <= 1.0
        assert isinstance(risk_assessment.recommendations, list)
        assert isinstance(risk_assessment.risk_factors, dict)
    
    def test_risk_assessment_concentrated_portfolio(self, risk_manager, sample_market_data):
        """Test risk assessment for a concentrated portfolio"""
        # Create highly concentrated portfolio
        concentrated_positions = {
            "SBER": Position(
                symbol="SBER",
                quantity=1000,
                entry_price=Decimal("250.0"),
                current_price=Decimal("260.0"),
                market_value=Decimal("260000.0"),
                unrealized_pnl=Decimal("10000.0"),
                entry_date=datetime.now(),
                sector="Banking"
            )
        }
        concentrated_portfolio = Portfolio(
            positions=concentrated_positions,
            cash_balance=Decimal("10000.0")
        )
        
        risk_assessment = risk_manager.assess_portfolio_risk(
            concentrated_portfolio, sample_market_data
        )
        
        # Should detect high concentration risk
        assert risk_assessment.concentration_risk_score > 0.5
        assert any("concentration" in rec.lower() for rec in risk_assessment.recommendations)
    
    def test_risk_assessment_with_negative_sentiment(self, risk_manager, sample_portfolio, sample_market_data):
        """Test risk assessment with negative news sentiment"""
        negative_sentiment = {
            "SBER": -0.8,  # Very negative sentiment
            "GAZP": -0.6   # Negative sentiment
        }
        
        risk_assessment = risk_manager.assess_portfolio_risk(
            sample_portfolio, sample_market_data, negative_sentiment
        )
        
        # Should detect elevated geopolitical risk
        assert risk_assessment.geopolitical_risk_level in [
            GeopoliticalRiskLevel.HIGH, GeopoliticalRiskLevel.CRITICAL
        ]
    
    def test_risk_assessment_empty_portfolio(self, risk_manager, sample_market_data):
        """Test risk assessment for empty portfolio"""
        empty_portfolio = Portfolio(
            positions={},
            cash_balance=Decimal("100000.0")
        )
        
        risk_assessment = risk_manager.assess_portfolio_risk(
            empty_portfolio, sample_market_data
        )
        
        assert risk_assessment.overall_risk_level == RiskLevel.LOW
        assert risk_assessment.concentration_risk_score == 0.0


class TestTradeValidation:
    """Test trade validation functionality"""
    
    def test_valid_buy_order(self, risk_manager, sample_portfolio, sample_market_data):
        """Test validation of a valid buy order"""
        buy_order = TradeOrder(
            symbol="LKOH",
            action="BUY",
            quantity=10,
            price=Decimal("5000.0")
        )
        
        # Add LKOH to market data
        sample_market_data["LKOH"] = MarketData(
            symbol="LKOH",
            timestamp=datetime.now(),
            price=Decimal("5000.0"),
            volume=100000,
            bid=Decimal("4995.0"),
            ask=Decimal("5005.0"),
            currency="RUB"
        )
        
        validation = risk_manager.validate_trade(
            buy_order, sample_portfolio, sample_market_data
        )
        
        assert isinstance(validation, ValidationResult)
        assert validation.is_valid
        assert 0.0 <= validation.risk_score <= 1.0
    
    def test_oversized_position_validation(self, risk_manager, sample_portfolio, sample_market_data):
        """Test validation of oversized position"""
        # Order that would exceed position size limits
        large_order = TradeOrder(
            symbol="SBER",
            action="BUY",
            quantity=1000,  # Very large quantity
            price=Decimal("260.0")
        )
        
        validation = risk_manager.validate_trade(
            large_order, sample_portfolio, sample_market_data
        )
        
        # Should be invalid due to position size
        assert not validation.is_valid
        assert any("position size" in error.lower() for error in validation.errors)
        assert "quantity" in validation.recommended_adjustments
    
    def test_insufficient_cash_validation(self, risk_manager, sample_market_data):
        """Test validation with insufficient cash"""
        low_cash_portfolio = Portfolio(
            positions={},
            cash_balance=Decimal("1000.0")  # Low cash
        )
        
        expensive_order = TradeOrder(
            symbol="SBER",
            action="BUY",
            quantity=100,
            price=Decimal("260.0")  # Requires 26,000 RUB
        )
        
        validation = risk_manager.validate_trade(
            expensive_order, low_cash_portfolio, sample_market_data
        )
        
        assert not validation.is_valid
        assert any("insufficient cash" in error.lower() for error in validation.errors)
    
    def test_sell_order_validation(self, risk_manager, sample_portfolio, sample_market_data):
        """Test validation of sell order"""
        sell_order = TradeOrder(
            symbol="SBER",
            action="SELL",
            quantity=50  # Selling part of existing position
        )
        
        validation = risk_manager.validate_trade(
            sell_order, sample_portfolio, sample_market_data
        )
        
        assert validation.is_valid
        assert len(validation.errors) == 0
    
    def test_validation_with_critical_risk(self, risk_manager, sample_portfolio, sample_market_data):
        """Test validation when portfolio risk is critical"""
        critical_risk_assessment = RiskAssessment(
            overall_risk_level=RiskLevel.CRITICAL,
            portfolio_risk_score=0.9,
            geopolitical_risk_level=GeopoliticalRiskLevel.CRITICAL,
            volatility_risk_score=0.8,
            concentration_risk_score=0.9,
            currency_risk_score=0.7,
            recommendations=["Reduce positions immediately"],
            risk_factors={"overall": 0.9},
            timestamp=datetime.now()
        )
        
        buy_order = TradeOrder(
            symbol="LKOH",
            action="BUY",
            quantity=10
        )
        
        # Add LKOH to market data
        sample_market_data["LKOH"] = MarketData(
            symbol="LKOH",
            timestamp=datetime.now(),
            price=Decimal("5000.0"),
            volume=100000,
            bid=Decimal("4995.0"),
            ask=Decimal("5005.0"),
            currency="RUB"
        )
        
        validation = risk_manager.validate_trade(
            buy_order, sample_portfolio, sample_market_data, critical_risk_assessment
        )
        
        # Should reject buy orders when risk is critical
        assert not validation.is_valid
        assert any("critical" in error.lower() for error in validation.errors)


class TestRiskParameters:
    """Test risk parameters functionality"""
    
    def test_custom_risk_parameters(self, custom_risk_params):
        """Test custom risk parameters"""
        risk_manager = RussianMarketRiskManager(custom_risk_params)
        
        assert risk_manager.risk_params.max_position_size_percent == 15.0
        assert risk_manager.risk_params.stop_loss_percent == 8.0
        assert risk_manager.risk_params.volatility_adjustment_factor == 2.0
    
    def test_default_risk_parameters(self):
        """Test default risk parameters"""
        risk_manager = RussianMarketRiskManager()
        
        assert risk_manager.risk_params.max_position_size_percent == 10.0
        assert risk_manager.risk_params.stop_loss_percent == 5.0
        assert risk_manager.risk_params.currency == "RUB"


class TestRussianMarketSpecifics:
    """Test Russian market-specific functionality"""
    
    def test_ruble_volatility_assessment(self, risk_manager, sample_portfolio, sample_market_data):
        """Test RUB volatility assessment"""
        risk_assessment = risk_manager.assess_portfolio_risk(
            sample_portfolio, sample_market_data
        )
        
        # Should include currency risk assessment
        assert "currency" in risk_assessment.risk_factors
        assert 0.0 <= risk_assessment.currency_risk_score <= 1.0
    
    def test_geopolitical_risk_levels(self, risk_manager):
        """Test geopolitical risk level assessment"""
        # Test with very negative sentiment (sanctions scenario)
        negative_sentiment = {"SBER": -0.9, "GAZP": -0.8}
        risk_level = risk_manager._assess_geopolitical_risk(negative_sentiment)
        
        assert risk_level == GeopoliticalRiskLevel.CRITICAL
        
        # Test with neutral sentiment
        neutral_sentiment = {"SBER": 0.1, "GAZP": -0.1}
        risk_level = risk_manager._assess_geopolitical_risk(neutral_sentiment)
        
        assert risk_level == GeopoliticalRiskLevel.NORMAL
    
    def test_sector_concentration_russian_sectors(self, risk_manager):
        """Test sector concentration for Russian market sectors"""
        # Create portfolio concentrated in energy sector
        energy_positions = {
            "GAZP": Position(
                symbol="GAZP",
                quantity=100,
                entry_price=Decimal("180.0"),
                current_price=Decimal("175.0"),
                market_value=Decimal("17500.0"),
                unrealized_pnl=Decimal("-500.0"),
                entry_date=datetime.now(),
                sector="Energy"
            ),
            "LKOH": Position(
                symbol="LKOH",
                quantity=5,
                entry_price=Decimal("5000.0"),
                current_price=Decimal("5100.0"),
                market_value=Decimal("25500.0"),
                unrealized_pnl=Decimal("500.0"),
                entry_date=datetime.now(),
                sector="Energy"
            )
        }
        
        energy_portfolio = Portfolio(
            positions=energy_positions,
            cash_balance=Decimal("7000.0")
        )
        
        sector_risk = risk_manager._assess_sector_concentration_risk(energy_portfolio)
        
        # Should detect high sector concentration (Energy = 86% of portfolio)
        assert sector_risk > 0.8


if __name__ == "__main__":
    pytest.main([__file__])