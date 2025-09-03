"""
Unit tests for Russian market data models
"""

import pytest
from datetime import datetime, time
from decimal import Decimal
import pytz
from russian_trading_bot.models.market_data import (
    RussianStock, MarketData, TechnicalIndicators, MarketStatus,
    MOEXTradingSession, MOEXMarketData, MOEXOrderBook, MOEXTrade,
    validate_moex_ticker, validate_russian_sector, validate_isin,
    validate_moex_trading_hours, get_next_trading_session
)


class TestValidationFunctions:
    """Test validation helper functions"""
    
    def test_validate_moex_ticker_valid(self):
        """Test valid MOEX ticker formats"""
        assert validate_moex_ticker("SBER") == True
        assert validate_moex_ticker("GAZP") == True
        assert validate_moex_ticker("LKOH") == True
        assert validate_moex_ticker("ROSN") == True
        assert validate_moex_ticker("NVTK") == True
        assert validate_moex_ticker("YNDX") == True  # 4 letters
        assert validate_moex_ticker("TCSG") == True  # 4 letters
        
    def test_validate_moex_ticker_invalid(self):
        """Test invalid MOEX ticker formats"""
        assert validate_moex_ticker("") == False
        assert validate_moex_ticker("SB") == False  # Too short
        assert validate_moex_ticker("SBERBANK") == False  # Too long
        assert validate_moex_ticker("sber") == True  # Lowercase is valid (converted to upper)
        assert validate_moex_ticker("123") == False  # Numbers
        assert validate_moex_ticker("SB-R") == False  # Special characters
        assert validate_moex_ticker(None) == False
        
    def test_validate_russian_sector_valid(self):
        """Test valid Russian market sectors"""
        assert validate_russian_sector("ENERGY") == True
        assert validate_russian_sector("FINANCIALS") == True
        assert validate_russian_sector("OIL_GAS") == True
        assert validate_russian_sector("BANKING") == True
        assert validate_russian_sector("energy") == True  # Case insensitive
        
    def test_validate_russian_sector_invalid(self):
        """Test invalid Russian market sectors"""
        assert validate_russian_sector("INVALID_SECTOR") == False
        assert validate_russian_sector("") == False
        
    def test_validate_isin_valid(self):
        """Test valid ISIN formats for Russian securities"""
        assert validate_isin("RU0009029540") == True  # Sberbank
        assert validate_isin("RU0007661625") == True  # Gazprom
        assert validate_isin("RU000A0JPEB3") == True  # With letters
        
    def test_validate_isin_invalid(self):
        """Test invalid ISIN formats"""
        assert validate_isin("") == False
        assert validate_isin("RU123") == False  # Too short
        assert validate_isin("US1234567890") == False  # Not Russian
        assert validate_isin("RU123456789012") == False  # Too long
        assert validate_isin("RU12345678901") == False  # Wrong length


class TestRussianStock:
    """Test RussianStock data model"""
    
    def test_valid_russian_stock(self):
        """Test creating valid Russian stock"""
        stock = RussianStock(
            symbol="SBER",
            name="Сбербанк России",
            sector="BANKING",
            lot_size=10,
            isin="RU0009029540"
        )
        assert stock.symbol == "SBER"
        assert stock.currency == "RUB"
        assert stock.market == "MOEX"
        assert stock.sector == "BANKING"
        
    def test_invalid_ticker_format(self):
        """Test invalid ticker format raises error"""
        with pytest.raises(ValueError, match="Invalid MOEX ticker format"):
            RussianStock(
                symbol="SB",  # Too short
                name="Test",
                sector="BANKING"
            )
            
    def test_invalid_currency(self):
        """Test invalid currency raises error"""
        with pytest.raises(ValueError, match="Russian stocks must be in RUB currency"):
            RussianStock(
                symbol="SBER",
                name="Test",
                sector="BANKING",
                currency="USD"
            )
            
    def test_invalid_lot_size(self):
        """Test invalid lot size raises error"""
        with pytest.raises(ValueError, match="Lot size must be at least 1"):
            RussianStock(
                symbol="SBER",
                name="Test",
                sector="BANKING",
                lot_size=0
            )
            
    def test_invalid_sector(self):
        """Test invalid sector raises error"""
        with pytest.raises(ValueError, match="Invalid Russian market sector"):
            RussianStock(
                symbol="SBER",
                name="Test",
                sector="INVALID_SECTOR"
            )
            
    def test_invalid_isin(self):
        """Test invalid ISIN raises error"""
        with pytest.raises(ValueError, match="Invalid ISIN format"):
            RussianStock(
                symbol="SBER",
                name="Test",
                sector="BANKING",
                isin="INVALID_ISIN"
            )
            
    def test_invalid_trading_status(self):
        """Test invalid trading status raises error"""
        with pytest.raises(ValueError, match="Invalid trading status"):
            RussianStock(
                symbol="SBER",
                name="Test",
                sector="BANKING",
                trading_status="INVALID"
            )
            
    def test_symbol_normalization(self):
        """Test symbol is normalized to uppercase"""
        stock = RussianStock(
            symbol="sber",
            name="Test",
            sector="banking"
        )
        assert stock.symbol == "SBER"
        assert stock.sector == "BANKING"


class TestMarketData:
    """Test MarketData model"""
    
    def test_valid_market_data(self):
        """Test creating valid market data"""
        data = MarketData(
            symbol="SBER",
            timestamp=datetime.now(),
            price=Decimal("250.50"),
            volume=1000000,
            bid=Decimal("250.40"),
            ask=Decimal("250.60")
        )
        assert data.symbol == "SBER"
        assert data.currency == "RUB"
        assert data.price == Decimal("250.50")
        
    def test_invalid_ticker(self):
        """Test invalid ticker raises error"""
        with pytest.raises(ValueError, match="Invalid MOEX ticker format"):
            MarketData(
                symbol="SB",
                timestamp=datetime.now(),
                price=Decimal("250.50"),
                volume=1000000
            )
            
    def test_invalid_price(self):
        """Test invalid price raises error"""
        with pytest.raises(ValueError, match="Price must be positive"):
            MarketData(
                symbol="SBER",
                timestamp=datetime.now(),
                price=Decimal("-10.00"),
                volume=1000000
            )
            
    def test_invalid_volume(self):
        """Test invalid volume raises error"""
        with pytest.raises(ValueError, match="Volume cannot be negative"):
            MarketData(
                symbol="SBER",
                timestamp=datetime.now(),
                price=Decimal("250.50"),
                volume=-1000
            )
            
    def test_invalid_currency(self):
        """Test invalid currency raises error"""
        with pytest.raises(ValueError, match="Russian market data must be in RUB"):
            MarketData(
                symbol="SBER",
                timestamp=datetime.now(),
                price=Decimal("250.50"),
                volume=1000000,
                currency="USD"
            )
            
    def test_invalid_bid_ask_spread(self):
        """Test invalid bid/ask spread raises error"""
        with pytest.raises(ValueError, match="Bid price cannot be higher than ask price"):
            MarketData(
                symbol="SBER",
                timestamp=datetime.now(),
                price=Decimal("250.50"),
                volume=1000000,
                bid=Decimal("250.60"),
                ask=Decimal("250.40")
            )
            
    def test_invalid_ohlc_data(self):
        """Test invalid OHLC data raises error"""
        with pytest.raises(ValueError, match="High price must be"):
            MarketData(
                symbol="SBER",
                timestamp=datetime.now(),
                price=Decimal("250.50"),
                volume=1000000,
                open_price=Decimal("250.00"),
                high_price=Decimal("249.00"),  # High < open
                low_price=Decimal("248.00")
            )


class TestTechnicalIndicators:
    """Test TechnicalIndicators model"""
    
    def test_valid_technical_indicators(self):
        """Test creating valid technical indicators"""
        indicators = TechnicalIndicators(
            symbol="SBER",
            timestamp=datetime.now(),
            rsi=65.5,
            macd=1.25,
            sma_20=Decimal("250.00")
        )
        assert indicators.symbol == "SBER"
        assert indicators.rsi == 65.5
        
    def test_invalid_rsi(self):
        """Test invalid RSI raises error"""
        with pytest.raises(ValueError, match="RSI must be between 0 and 100"):
            TechnicalIndicators(
                symbol="SBER",
                timestamp=datetime.now(),
                rsi=150.0  # Invalid RSI
            )
            
    def test_invalid_bollinger_bands(self):
        """Test invalid Bollinger Bands order raises error"""
        with pytest.raises(ValueError, match="Bollinger Bands must be in order"):
            TechnicalIndicators(
                symbol="SBER",
                timestamp=datetime.now(),
                bollinger_lower=Decimal("260.00"),
                bollinger_middle=Decimal("250.00"),
                bollinger_upper=Decimal("240.00")  # Wrong order
            )


class TestMarketStatus:
    """Test MarketStatus model"""
    
    def test_valid_market_status(self):
        """Test creating valid market status"""
        status = MarketStatus(
            is_open=True,
            market_phase="OPEN"
        )
        assert status.is_open == True
        assert status.market_phase == "OPEN"
        assert status.timezone == "Europe/Moscow"
        
    def test_invalid_market_phase(self):
        """Test invalid market phase raises error"""
        with pytest.raises(ValueError, match="Invalid market phase"):
            MarketStatus(
                is_open=True,
                market_phase="INVALID_PHASE"
            )
            
    def test_is_trading_hours(self):
        """Test trading hours property"""
        # Market closed
        status = MarketStatus(is_open=False)
        assert status.is_trading_hours == False
        
        # Market open but no session times
        status = MarketStatus(is_open=True)
        assert status.is_trading_hours == False

class TestMOEXTradingSession:
    """Test MOEX trading session functionality"""
    
    def test_valid_moex_trading_session(self):
        """Test creating valid MOEX trading session"""
        session = MOEXTradingSession(
            date=datetime(2024, 1, 15),  # Monday
            session_type="NORMAL"
        )
        assert session.is_trading_day == True
        assert session.main_session_start == time(10, 0)
        assert session.main_session_end == time(18, 45)
        
    def test_invalid_session_type(self):
        """Test invalid session type raises error"""
        with pytest.raises(ValueError, match="Invalid session type"):
            MOEXTradingSession(
                date=datetime(2024, 1, 15),
                session_type="INVALID"
            )
            
    def test_invalid_session_times(self):
        """Test invalid session times raise error"""
        with pytest.raises(ValueError, match="Main session start must be before end"):
            MOEXTradingSession(
                date=datetime(2024, 1, 15),
                main_session_start=time(19, 0),
                main_session_end=time(18, 0)
            )
            
    def test_clearing_validation(self):
        """Test clearing session validation"""
        with pytest.raises(ValueError, match="Clearing must start after main session ends"):
            MOEXTradingSession(
                date=datetime(2024, 1, 15),
                main_session_end=time(18, 45),
                clearing_start=time(18, 30)
            )
            
    def test_is_market_open_during_trading_hours(self):
        """Test market open detection during trading hours"""
        session = MOEXTradingSession(
            date=datetime(2024, 1, 15),  # Monday
            is_trading_day=True
        )
        
        # Test during trading hours (Moscow time)
        moscow_tz = pytz.timezone('Europe/Moscow')
        trading_time = moscow_tz.localize(datetime(2024, 1, 15, 14, 30))  # 14:30 MSK
        assert session.is_market_open(trading_time) == True
        
        # Test before trading hours
        before_trading = moscow_tz.localize(datetime(2024, 1, 15, 9, 30))  # 09:30 MSK
        assert session.is_market_open(before_trading) == False
        
        # Test after trading hours
        after_trading = moscow_tz.localize(datetime(2024, 1, 15, 19, 30))  # 19:30 MSK
        assert session.is_market_open(after_trading) == False
        
    def test_is_market_open_non_trading_day(self):
        """Test market open on non-trading day"""
        session = MOEXTradingSession(
            date=datetime(2024, 1, 15),
            is_trading_day=False
        )
        
        moscow_tz = pytz.timezone('Europe/Moscow')
        trading_time = moscow_tz.localize(datetime(2024, 1, 15, 14, 30))
        assert session.is_market_open(trading_time) == False
        
    def test_is_clearing_session(self):
        """Test clearing session detection"""
        session = MOEXTradingSession(
            date=datetime(2024, 1, 15),
            is_trading_day=True
        )
        
        moscow_tz = pytz.timezone('Europe/Moscow')
        clearing_time = moscow_tz.localize(datetime(2024, 1, 15, 19, 2))  # 19:02 MSK
        assert session.is_clearing_session(clearing_time) == True
        
        non_clearing_time = moscow_tz.localize(datetime(2024, 1, 15, 14, 30))  # 14:30 MSK
        assert session.is_clearing_session(non_clearing_time) == False


class TestMOEXMarketData:
    """Test MOEX-specific market data"""
    
    def test_valid_moex_market_data(self):
        """Test creating valid MOEX market data"""
        data = MOEXMarketData(
            symbol="SBER",
            timestamp=datetime.now(),
            price=Decimal("250.50"),
            volume=1000000,
            lot_size=10,
            min_price_step=Decimal("0.01")
        )
        assert data.symbol == "SBER"
        assert data.lot_size == 10
        assert data.min_price_step == Decimal("0.01")
        
    def test_invalid_lot_size(self):
        """Test invalid lot size raises error"""
        with pytest.raises(ValueError, match="Lot size must be at least 1"):
            MOEXMarketData(
                symbol="SBER",
                timestamp=datetime.now(),
                price=Decimal("250.50"),
                volume=1000000,
                lot_size=0
            )
            
    def test_invalid_min_price_step(self):
        """Test invalid min price step raises error"""
        with pytest.raises(ValueError, match="Min price step must be positive"):
            MOEXMarketData(
                symbol="SBER",
                timestamp=datetime.now(),
                price=Decimal("250.50"),
                volume=1000000,
                min_price_step=Decimal("-0.01")
            )
            
    def test_invalid_face_value(self):
        """Test invalid face value raises error"""
        with pytest.raises(ValueError, match="Face value must be positive"):
            MOEXMarketData(
                symbol="SBER",
                timestamp=datetime.now(),
                price=Decimal("250.50"),
                volume=1000000,
                face_value=Decimal("-1.00")
            )
            
    def test_invalid_demand_supply(self):
        """Test invalid demand/supply values raise errors"""
        with pytest.raises(ValueError, match="Total demand cannot be negative"):
            MOEXMarketData(
                symbol="SBER",
                timestamp=datetime.now(),
                price=Decimal("250.50"),
                volume=1000000,
                total_demand=-1000
            )
            
        with pytest.raises(ValueError, match="Total supply cannot be negative"):
            MOEXMarketData(
                symbol="SBER",
                timestamp=datetime.now(),
                price=Decimal("250.50"),
                volume=1000000,
                total_supply=-1000
            )
            
    def test_effective_spread_calculation(self):
        """Test effective spread calculation"""
        data = MOEXMarketData(
            symbol="SBER",
            timestamp=datetime.now(),
            price=Decimal("250.50"),
            volume=1000000,
            bid=Decimal("250.40"),
            ask=Decimal("250.60")
        )
        assert data.get_effective_spread() == Decimal("0.20")
        
    def test_mid_price_calculation(self):
        """Test mid price calculation"""
        data = MOEXMarketData(
            symbol="SBER",
            timestamp=datetime.now(),
            price=Decimal("250.50"),
            volume=1000000,
            bid=Decimal("250.40"),
            ask=Decimal("250.60")
        )
        assert data.get_mid_price() == Decimal("250.50")


class TestMOEXOrderBook:
    """Test MOEX order book functionality"""
    
    def test_valid_order_book(self):
        """Test creating valid order book"""
        order_book = MOEXOrderBook(
            symbol="SBER",
            timestamp=datetime.now(),
            bids=[(Decimal("250.50"), 1000), (Decimal("250.40"), 2000)],
            asks=[(Decimal("250.60"), 1500), (Decimal("250.70"), 2500)]
        )
        assert order_book.symbol == "SBER"
        assert len(order_book.bids) == 2
        assert len(order_book.asks) == 2
        
    def test_invalid_bid_order(self):
        """Test invalid bid order raises error"""
        with pytest.raises(ValueError, match="Bids must be in descending price order"):
            MOEXOrderBook(
                symbol="SBER",
                timestamp=datetime.now(),
                bids=[(Decimal("250.40"), 1000), (Decimal("250.50"), 2000)],  # Wrong order
                asks=[(Decimal("250.60"), 1500)]
            )
            
    def test_invalid_ask_order(self):
        """Test invalid ask order raises error"""
        with pytest.raises(ValueError, match="Asks must be in ascending price order"):
            MOEXOrderBook(
                symbol="SBER",
                timestamp=datetime.now(),
                bids=[(Decimal("250.50"), 1000)],
                asks=[(Decimal("250.70"), 1500), (Decimal("250.60"), 2500)]  # Wrong order
            )
            
    def test_negative_volume(self):
        """Test negative volume raises error"""
        with pytest.raises(ValueError, match="Order volume cannot be negative"):
            MOEXOrderBook(
                symbol="SBER",
                timestamp=datetime.now(),
                bids=[(Decimal("250.50"), -1000)],  # Negative volume
                asks=[(Decimal("250.60"), 1500)]
            )
            
    def test_best_bid_ask(self):
        """Test best bid/ask retrieval"""
        order_book = MOEXOrderBook(
            symbol="SBER",
            timestamp=datetime.now(),
            bids=[(Decimal("250.50"), 1000), (Decimal("250.40"), 2000)],
            asks=[(Decimal("250.60"), 1500), (Decimal("250.70"), 2500)]
        )
        
        best_bid = order_book.get_best_bid()
        best_ask = order_book.get_best_ask()
        
        assert best_bid == (Decimal("250.50"), 1000)
        assert best_ask == (Decimal("250.60"), 1500)
        
    def test_spread_calculation(self):
        """Test spread calculation"""
        order_book = MOEXOrderBook(
            symbol="SBER",
            timestamp=datetime.now(),
            bids=[(Decimal("250.50"), 1000)],
            asks=[(Decimal("250.60"), 1500)]
        )
        
        spread = order_book.get_spread()
        assert spread == Decimal("0.10")
        
    def test_total_volumes(self):
        """Test total volume calculations"""
        order_book = MOEXOrderBook(
            symbol="SBER",
            timestamp=datetime.now(),
            bids=[(Decimal("250.50"), 1000), (Decimal("250.40"), 2000)],
            asks=[(Decimal("250.60"), 1500), (Decimal("250.70"), 2500)]
        )
        
        assert order_book.get_total_bid_volume() == 3000
        assert order_book.get_total_ask_volume() == 4000


class TestMOEXTrade:
    """Test MOEX trade data"""
    
    def test_valid_trade(self):
        """Test creating valid trade"""
        trade = MOEXTrade(
            symbol="SBER",
            timestamp=datetime.now(),
            price=Decimal("250.50"),
            volume=1000,
            trade_id="12345",
            buyer_initiated=True
        )
        assert trade.symbol == "SBER"
        assert trade.trade_id == "12345"
        assert trade.buyer_initiated == True
        
    def test_invalid_trade_price(self):
        """Test invalid trade price raises error"""
        with pytest.raises(ValueError, match="Trade price must be positive"):
            MOEXTrade(
                symbol="SBER",
                timestamp=datetime.now(),
                price=Decimal("-250.50"),
                volume=1000,
                trade_id="12345"
            )
            
    def test_invalid_trade_volume(self):
        """Test invalid trade volume raises error"""
        with pytest.raises(ValueError, match="Trade volume must be positive"):
            MOEXTrade(
                symbol="SBER",
                timestamp=datetime.now(),
                price=Decimal("250.50"),
                volume=0,
                trade_id="12345"
            )
            
    def test_missing_trade_id(self):
        """Test missing trade ID raises error"""
        with pytest.raises(ValueError, match="Trade ID is required"):
            MOEXTrade(
                symbol="SBER",
                timestamp=datetime.now(),
                price=Decimal("250.50"),
                volume=1000,
                trade_id=""
            )


class TestMOEXTradingHours:
    """Test MOEX trading hours validation"""
    
    def test_validate_trading_hours_weekday(self):
        """Test trading hours validation on weekday"""
        moscow_tz = pytz.timezone('Europe/Moscow')
        
        # During trading hours
        trading_time = moscow_tz.localize(datetime(2024, 1, 15, 14, 30))  # Monday 14:30
        assert validate_moex_trading_hours(trading_time) == True
        
        # Before trading hours
        before_trading = moscow_tz.localize(datetime(2024, 1, 15, 9, 30))  # Monday 09:30
        assert validate_moex_trading_hours(before_trading) == False
        
        # After trading hours
        after_trading = moscow_tz.localize(datetime(2024, 1, 15, 19, 30))  # Monday 19:30
        assert validate_moex_trading_hours(after_trading) == False
        
    def test_validate_trading_hours_weekend(self):
        """Test trading hours validation on weekend"""
        moscow_tz = pytz.timezone('Europe/Moscow')
        
        # Saturday during normal trading hours
        saturday = moscow_tz.localize(datetime(2024, 1, 13, 14, 30))  # Saturday 14:30
        assert validate_moex_trading_hours(saturday) == False
        
        # Sunday during normal trading hours
        sunday = moscow_tz.localize(datetime(2024, 1, 14, 14, 30))  # Sunday 14:30
        assert validate_moex_trading_hours(sunday) == False
        
    def test_get_next_trading_session(self):
        """Test getting next trading session"""
        moscow_tz = pytz.timezone('Europe/Moscow')
        
        # Friday after trading hours
        friday_evening = moscow_tz.localize(datetime(2024, 1, 12, 20, 0))  # Friday 20:00
        next_session = get_next_trading_session(friday_evening)
        
        # Should be Monday 10:00
        assert next_session.weekday() == 0  # Monday
        assert next_session.time() == time(10, 0)
        
        # Wednesday during trading hours
        wednesday_trading = moscow_tz.localize(datetime(2024, 1, 10, 14, 30))  # Wednesday 14:30
        next_session = get_next_trading_session(wednesday_trading)
        
        # Should be Thursday 10:00 (next day)
        assert next_session.weekday() == 3  # Thursday
        assert next_session.time() == time(10, 0)