"""
Unit tests for MOEX trading rules compliance system
"""

import pytest
from datetime import datetime, time, timedelta
from decimal import Decimal
import pytz

from russian_trading_bot.services.moex_compliance import (
    MOEXComplianceValidator, MOEXTradingSession, MOEXSecurityType
)
from russian_trading_bot.models.trading import TradeOrder, OrderAction, OrderType


class TestMOEXComplianceValidator:
    """Test MOEX compliance validator"""
    
    @pytest.fixture
    def validator(self):
        """Create MOEX compliance validator instance"""
        return MOEXComplianceValidator()
    
    @pytest.fixture
    def moscow_tz(self):
        """Moscow timezone"""
        return pytz.timezone('Europe/Moscow')
    
    def test_trading_session_detection_main_hours(self, validator, moscow_tz):
        """Test trading session detection during main hours"""
        # 12:00 MSK on a Wednesday (main session)
        test_time = moscow_tz.localize(datetime(2024, 1, 10, 12, 0))
        session = validator.get_trading_session(test_time)
        assert session == MOEXTradingSession.MAIN
    
    def test_trading_session_detection_evening_hours(self, validator, moscow_tz):
        """Test trading session detection during evening hours"""
        # 20:00 MSK on a Wednesday (evening session)
        test_time = moscow_tz.localize(datetime(2024, 1, 10, 20, 0))
        session = validator.get_trading_session(test_time)
        assert session == MOEXTradingSession.EVENING
    
    def test_trading_session_detection_closed_hours(self, validator, moscow_tz):
        """Test trading session detection during closed hours"""
        # 9:00 MSK on a Wednesday (before market open)
        test_time = moscow_tz.localize(datetime(2024, 1, 10, 9, 0))
        session = validator.get_trading_session(test_time)
        assert session == MOEXTradingSession.CLOSED
    
    def test_trading_session_detection_weekend(self, validator, moscow_tz):
        """Test trading session detection on weekend"""
        # 12:00 MSK on a Saturday
        test_time = moscow_tz.localize(datetime(2024, 1, 13, 12, 0))
        session = validator.get_trading_session(test_time)
        assert session == MOEXTradingSession.CLOSED
    
    def test_is_trading_hours_main_session(self, validator, moscow_tz):
        """Test trading hours check during main session"""
        test_time = moscow_tz.localize(datetime(2024, 1, 10, 15, 30))
        assert validator.is_trading_hours(test_time) is True
    
    def test_is_trading_hours_evening_session(self, validator, moscow_tz):
        """Test trading hours check during evening session"""
        test_time = moscow_tz.localize(datetime(2024, 1, 10, 21, 0))
        assert validator.is_trading_hours(test_time) is True
    
    def test_is_trading_hours_closed(self, validator, moscow_tz):
        """Test trading hours check when market is closed"""
        test_time = moscow_tz.localize(datetime(2024, 1, 10, 8, 0))
        assert validator.is_trading_hours(test_time) is False
    
    def test_get_next_trading_session_before_main(self, validator, moscow_tz):
        """Test getting next trading session before main session"""
        # 9:00 MSK on Wednesday
        current_time = moscow_tz.localize(datetime(2024, 1, 10, 9, 0))
        next_session = validator.get_next_trading_session(current_time)
        
        expected = moscow_tz.localize(datetime(2024, 1, 10, 10, 0))
        assert next_session == expected
    
    def test_get_next_trading_session_between_sessions(self, validator, moscow_tz):
        """Test getting next trading session between main and evening"""
        # 19:00 MSK on Wednesday (between sessions)
        current_time = moscow_tz.localize(datetime(2024, 1, 10, 19, 0))
        next_session = validator.get_next_trading_session(current_time)
        
        expected = moscow_tz.localize(datetime(2024, 1, 10, 19, 5))
        assert next_session == expected
    
    def test_get_next_trading_session_after_evening(self, validator, moscow_tz):
        """Test getting next trading session after evening session"""
        # 23:55 MSK on Wednesday (after evening session)
        current_time = moscow_tz.localize(datetime(2024, 1, 10, 23, 55))
        next_session = validator.get_next_trading_session(current_time)
        
        expected = moscow_tz.localize(datetime(2024, 1, 11, 10, 0))
        assert next_session == expected
    
    def test_get_next_trading_session_friday_evening(self, validator, moscow_tz):
        """Test getting next trading session on Friday evening (skip weekend)"""
        # 23:55 MSK on Friday
        current_time = moscow_tz.localize(datetime(2024, 1, 12, 23, 55))
        next_session = validator.get_next_trading_session(current_time)
        
        # Should be Monday 10:00
        expected = moscow_tz.localize(datetime(2024, 1, 15, 10, 0))
        assert next_session == expected
    
    def test_security_type_detection_stock(self, validator):
        """Test security type detection for stocks"""
        assert validator.get_security_type("SBER") == MOEXSecurityType.STOCK
        assert validator.get_security_type("GAZP") == MOEXSecurityType.STOCK
        assert validator.get_security_type("LKOH") == MOEXSecurityType.STOCK
    
    def test_security_type_detection_currency(self, validator):
        """Test security type detection for currencies"""
        assert validator.get_security_type("USDRUB_TOM") == MOEXSecurityType.CURRENCY
        assert validator.get_security_type("EURRUB_TOM") == MOEXSecurityType.CURRENCY
        assert validator.get_security_type("CNYRUB_TOM") == MOEXSecurityType.CURRENCY
    
    def test_security_type_detection_etf(self, validator):
        """Test security type detection for ETFs"""
        assert validator.get_security_type("FXRU") == MOEXSecurityType.ETF
        assert validator.get_security_type("FXUS") == MOEXSecurityType.ETF
        assert validator.get_security_type("FXGD") == MOEXSecurityType.ETF
    
    def test_security_type_detection_bond(self, validator):
        """Test security type detection for bonds"""
        assert validator.get_security_type("SU26230RMFS4") == MOEXSecurityType.BOND
        assert validator.get_security_type("RU000A0JX0J2") == MOEXSecurityType.BOND
        assert validator.get_security_type("OFZ12345") == MOEXSecurityType.BOND
    
    def test_lot_size_major_stocks(self, validator):
        """Test lot sizes for major Russian stocks"""
        assert validator.get_lot_size("SBER") == 10
        assert validator.get_lot_size("GAZP") == 10
        assert validator.get_lot_size("LKOH") == 1
        assert validator.get_lot_size("VTBR") == 10000
        assert validator.get_lot_size("HYDR") == 1000
    
    def test_lot_size_unknown_stock(self, validator):
        """Test lot size for unknown stock (should use default)"""
        assert validator.get_lot_size("UNKNOWN") == 1  # Default for stocks
    
    def test_lot_size_currency(self, validator):
        """Test lot size for currency pairs"""
        assert validator.get_lot_size("USDRUB_TOM") == 1000  # Default for currency
    
    def test_validate_lot_size_valid(self, validator):
        """Test lot size validation for valid quantities"""
        # SBER has lot size 10
        valid, error = validator.validate_lot_size("SBER", 100)  # 10 lots
        assert valid is True
        assert error == ""
        
        # LKOH has lot size 1
        valid, error = validator.validate_lot_size("LKOH", 5)  # 5 lots
        assert valid is True
        assert error == ""
    
    def test_validate_lot_size_invalid(self, validator):
        """Test lot size validation for invalid quantities"""
        # SBER has lot size 10
        valid, error = validator.validate_lot_size("SBER", 15)  # Not multiple of 10
        assert valid is False
        assert "multiple of lot size 10" in error
        
        # Negative quantity
        valid, error = validator.validate_lot_size("SBER", -10)
        assert valid is False
        assert "must be positive" in error
    
    def test_validate_minimum_order_value_valid(self, validator):
        """Test minimum order value validation for valid orders"""
        # Stock order above minimum
        valid, error = validator.validate_minimum_order_value("SBER", 10, Decimal("200"))
        assert valid is True  # 10 * 200 = 2000 RUB > 1000 RUB minimum
        assert error == ""
    
    def test_validate_minimum_order_value_invalid(self, validator):
        """Test minimum order value validation for invalid orders"""
        # Stock order below minimum
        valid, error = validator.validate_minimum_order_value("SBER", 1, Decimal("500"))
        assert valid is False  # 1 * 500 = 500 RUB < 1000 RUB minimum
        assert "below minimum" in error
    
    def test_validate_trading_hours_valid(self, validator, moscow_tz):
        """Test trading hours validation during valid hours"""
        # Mock current time to be during trading hours
        test_time = moscow_tz.localize(datetime(2024, 1, 10, 15, 0))
        valid, error = validator.validate_trading_hours(test_time)
        assert valid is True
        assert error == ""
    
    def test_validate_trading_hours_invalid(self, validator, moscow_tz):
        """Test trading hours validation during invalid hours"""
        # Mock current time to be outside trading hours
        test_time = moscow_tz.localize(datetime(2024, 1, 10, 8, 0))
        valid, error = validator.validate_trading_hours(test_time)
        assert valid is False
        assert "Market is closed" in error
        assert "Next trading session" in error
    
    def test_calculate_settlement_date_weekday(self, validator, moscow_tz):
        """Test T+2 settlement calculation for weekday trade"""
        # Trade on Wednesday
        trade_date = moscow_tz.localize(datetime(2024, 1, 10, 15, 0))
        settlement = validator.calculate_settlement_date(trade_date)
        
        # Should be Friday (2 business days later)
        expected_date = datetime(2024, 1, 12, 10, 0)
        expected = moscow_tz.localize(expected_date)
        assert settlement == expected
    
    def test_calculate_settlement_date_friday(self, validator, moscow_tz):
        """Test T+2 settlement calculation for Friday trade"""
        # Trade on Friday
        trade_date = moscow_tz.localize(datetime(2024, 1, 12, 15, 0))
        settlement = validator.calculate_settlement_date(trade_date)
        
        # Should be Tuesday (skip weekend)
        expected_date = datetime(2024, 1, 16, 10, 0)
        expected = moscow_tz.localize(expected_date)
        assert settlement == expected
    
    def test_validate_order_compliance_valid_order(self, validator, moscow_tz):
        """Test comprehensive order validation for valid order"""
        # Create valid order during trading hours
        order = TradeOrder(
            symbol="SBER",
            action=OrderAction.BUY,
            quantity=100,  # 10 lots (valid for SBER)
            order_type=OrderType.LIMIT,
            price=Decimal("250")  # 100 * 250 = 25,000 RUB (above minimum)
        )
        
        # Mock trading hours
        test_time = moscow_tz.localize(datetime(2024, 1, 10, 15, 0))
        
        with pytest.MonkeyPatch().context() as m:
            m.setattr(validator, 'get_current_moscow_time', lambda: test_time)
            result = validator.validate_order_compliance(order)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert result["compliance_info"]["lot_size"] == 10
        assert result["compliance_info"]["lots_ordered"] == 10
        assert result["compliance_info"]["trading_session"] == "main"
        assert "settlement_date" in result["compliance_info"]
    
    def test_validate_order_compliance_invalid_lot_size(self, validator, moscow_tz):
        """Test comprehensive order validation for invalid lot size"""
        order = TradeOrder(
            symbol="SBER",
            action=OrderAction.BUY,
            quantity=15,  # Not multiple of 10 (invalid for SBER)
            order_type=OrderType.MARKET
        )
        
        # Mock trading hours
        test_time = moscow_tz.localize(datetime(2024, 1, 10, 15, 0))
        
        with pytest.MonkeyPatch().context() as m:
            m.setattr(validator, 'get_current_moscow_time', lambda: test_time)
            result = validator.validate_order_compliance(order)
        
        assert result["valid"] is False
        assert any("multiple of lot size" in error for error in result["errors"])
    
    def test_validate_order_compliance_outside_trading_hours(self, validator, moscow_tz):
        """Test comprehensive order validation outside trading hours"""
        order = TradeOrder(
            symbol="SBER",
            action=OrderAction.BUY,
            quantity=100,
            order_type=OrderType.MARKET
        )
        
        # Mock time outside trading hours
        test_time = moscow_tz.localize(datetime(2024, 1, 10, 8, 0))
        
        with pytest.MonkeyPatch().context() as m:
            m.setattr(validator, 'get_current_moscow_time', lambda: test_time)
            result = validator.validate_order_compliance(order)
        
        assert result["valid"] is False
        assert any("Market is closed" in error for error in result["errors"])
    
    def test_validate_order_compliance_low_order_value(self, validator, moscow_tz):
        """Test comprehensive order validation for low order value"""
        order = TradeOrder(
            symbol="SBER",
            action=OrderAction.BUY,
            quantity=10,
            order_type=OrderType.LIMIT,
            price=Decimal("50")  # 10 * 50 = 500 RUB (below 1000 RUB minimum)
        )
        
        # Mock trading hours
        test_time = moscow_tz.localize(datetime(2024, 1, 10, 15, 0))
        
        with pytest.MonkeyPatch().context() as m:
            m.setattr(validator, 'get_current_moscow_time', lambda: test_time)
            result = validator.validate_order_compliance(order)
        
        assert result["valid"] is False
        assert any("below minimum" in error for error in result["errors"])
    
    def test_validate_order_compliance_warnings(self, validator, moscow_tz):
        """Test order validation warnings"""
        # Large order
        order = TradeOrder(
            symbol="SBER",
            action=OrderAction.BUY,
            quantity=2000000,  # Large quantity
            order_type=OrderType.MARKET
        )
        
        # Mock trading hours
        test_time = moscow_tz.localize(datetime(2024, 1, 10, 15, 0))
        
        with pytest.MonkeyPatch().context() as m:
            m.setattr(validator, 'get_current_moscow_time', lambda: test_time)
            result = validator.validate_order_compliance(order)
        
        assert any("Large order" in warning for warning in result["warnings"])
        
        # Currency order
        currency_order = TradeOrder(
            symbol="USDRUB_TOM",
            action=OrderAction.BUY,
            quantity=1000,
            order_type=OrderType.MARKET
        )
        
        with pytest.MonkeyPatch().context() as m:
            m.setattr(validator, 'get_current_moscow_time', lambda: test_time)
            result = validator.validate_order_compliance(currency_order)
        
        assert any("Currency trading" in warning for warning in result["warnings"])
    
    def test_get_compliance_summary(self, validator):
        """Test compliance summary generation"""
        summary = validator.get_compliance_summary()
        
        assert "trading_hours" in summary
        assert "settlement" in summary
        assert "lot_sizes" in summary
        assert "minimum_values" in summary
        assert "current_time_msk" in summary
        
        # Check trading hours format
        assert "main_session" in summary["trading_hours"]
        assert "evening_session" in summary["trading_hours"]
        assert "current_session" in summary["trading_hours"]
        
        # Check settlement info
        assert summary["settlement"]["standard_settlement"] == "T+2 business days"
        
        # Check lot sizes
        assert "SBER" in summary["lot_sizes"]["major_stocks"]
        assert summary["lot_sizes"]["major_stocks"]["SBER"] == 10


if __name__ == "__main__":
    pytest.main([__file__])