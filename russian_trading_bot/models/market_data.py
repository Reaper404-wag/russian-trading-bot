"""
Market data models for Russian stocks
"""

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from typing import Optional, Dict, Any, List, Tuple
from decimal import Decimal
import re
import pytz


# MOEX ticker validation patterns
MOEX_TICKER_PATTERN = re.compile(r'^[A-Z]{3,5}$')
VALID_RUSSIAN_SECTORS = {
    'ENERGY', 'FINANCIALS', 'MATERIALS', 'INDUSTRIALS', 'CONSUMER_DISCRETIONARY',
    'CONSUMER_STAPLES', 'HEALTH_CARE', 'INFORMATION_TECHNOLOGY', 'COMMUNICATION_SERVICES',
    'UTILITIES', 'REAL_ESTATE', 'TELECOM', 'METALS_MINING', 'OIL_GAS', 'BANKING'
}

def validate_moex_ticker(symbol: str) -> bool:
    """Validate MOEX ticker format"""
    if not symbol:
        return False
    return bool(MOEX_TICKER_PATTERN.match(symbol.upper()))

def validate_russian_sector(sector: str) -> bool:
    """Validate Russian market sector"""
    return sector.upper() in VALID_RUSSIAN_SECTORS

def validate_isin(isin: str) -> bool:
    """Validate ISIN format for Russian securities"""
    if not isin or len(isin) != 12:
        return False
    # Russian ISINs typically start with RU
    return isin.startswith('RU') and isin[2:].isalnum()

@dataclass
class RussianStock:
    """Russian stock information with MOEX-specific validation"""
    symbol: str  # MOEX ticker (e.g., "SBER", "GAZP")
    name: str    # Russian company name
    sector: str  # Russian market sector
    currency: str = "RUB"
    lot_size: int = 1
    isin: Optional[str] = None
    market: str = "MOEX"
    trading_status: str = "NORMAL"
    min_price_step: Optional[Decimal] = None
    face_value: Optional[Decimal] = None
    
    def __post_init__(self):
        """Validate Russian stock data"""
        if not validate_moex_ticker(self.symbol):
            raise ValueError(f"Invalid MOEX ticker format: {self.symbol}")
        
        if self.currency != "RUB":
            raise ValueError("Russian stocks must be in RUB currency")
            
        if self.lot_size < 1:
            raise ValueError("Lot size must be at least 1")
            
        if not validate_russian_sector(self.sector):
            raise ValueError(f"Invalid Russian market sector: {self.sector}")
            
        if self.isin and not validate_isin(self.isin):
            raise ValueError(f"Invalid ISIN format: {self.isin}")
            
        if self.trading_status not in ['NORMAL', 'SUSPENDED', 'DELISTED', 'HALT']:
            raise ValueError(f"Invalid trading status: {self.trading_status}")
            
        # Normalize symbol to uppercase
        self.symbol = self.symbol.upper()
        self.sector = self.sector.upper()


@dataclass
class MarketData:
    """Market data for Russian stocks with enhanced validation"""
    symbol: str
    timestamp: datetime
    price: Decimal
    volume: int
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    currency: str = "RUB"
    open_price: Optional[Decimal] = None
    high_price: Optional[Decimal] = None
    low_price: Optional[Decimal] = None
    previous_close: Optional[Decimal] = None
    change: Optional[Decimal] = None
    change_percent: Optional[Decimal] = None
    
    def __post_init__(self):
        """Validate market data"""
        if not validate_moex_ticker(self.symbol):
            raise ValueError(f"Invalid MOEX ticker format: {self.symbol}")
            
        if self.price <= 0:
            raise ValueError("Price must be positive")
            
        if self.volume < 0:
            raise ValueError("Volume cannot be negative")
            
        if self.currency != "RUB":
            raise ValueError("Russian market data must be in RUB")
            
        # Validate bid/ask spread
        if self.bid and self.ask and self.bid > self.ask:
            raise ValueError("Bid price cannot be higher than ask price")
            
        # Validate OHLC data consistency
        if all([self.open_price, self.high_price, self.low_price]):
            if self.high_price < max(self.open_price, self.price):
                raise ValueError("High price must be >= open and current price")
            if self.low_price > min(self.open_price, self.price):
                raise ValueError("Low price must be <= open and current price")
                
        # Normalize symbol
        self.symbol = self.symbol.upper()


@dataclass
class TechnicalIndicators:
    """Technical indicators for Russian stocks"""
    symbol: str
    timestamp: datetime
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    sma_20: Optional[Decimal] = None
    sma_50: Optional[Decimal] = None
    sma_200: Optional[Decimal] = None
    ema_12: Optional[Decimal] = None
    ema_26: Optional[Decimal] = None
    bollinger_upper: Optional[Decimal] = None
    bollinger_lower: Optional[Decimal] = None
    bollinger_middle: Optional[Decimal] = None
    volume_sma: Optional[float] = None
    
    def __post_init__(self):
        """Validate technical indicators"""
        if not validate_moex_ticker(self.symbol):
            raise ValueError(f"Invalid MOEX ticker format: {self.symbol}")
            
        if self.rsi is not None and (self.rsi < 0 or self.rsi > 100):
            raise ValueError("RSI must be between 0 and 100")
            
        # Validate Bollinger Bands order
        if all([self.bollinger_lower, self.bollinger_middle, self.bollinger_upper]):
            if not (self.bollinger_lower <= self.bollinger_middle <= self.bollinger_upper):
                raise ValueError("Bollinger Bands must be in order: lower <= middle <= upper")
                
        self.symbol = self.symbol.upper()


@dataclass
class MarketStatus:
    """MOEX market status information"""
    is_open: bool
    session_start: Optional[datetime] = None
    session_end: Optional[datetime] = None
    timezone: str = "Europe/Moscow"
    trading_day: Optional[datetime] = None
    market_phase: str = "CLOSED"  # PREMARKET, OPEN, CLOSED, POSTMARKET
    
    def __post_init__(self):
        """Validate market status"""
        valid_phases = ['PREMARKET', 'OPEN', 'CLOSED', 'POSTMARKET']
        if self.market_phase not in valid_phases:
            raise ValueError(f"Invalid market phase: {self.market_phase}")
    
    @property
    def is_trading_hours(self) -> bool:
        """Check if current time is within trading hours"""
        if not self.is_open or not self.session_start or not self.session_end:
            return False
        
        now = datetime.now()
        return self.session_start <= now <= self.session_end


# MOEX trading session constants
MOSCOW_TZ = pytz.timezone('Europe/Moscow')
MOEX_TRADING_START = time(10, 0)  # 10:00 MSK
MOEX_TRADING_END = time(18, 45)   # 18:45 MSK
MOEX_CLEARING_START = time(19, 0) # 19:00 MSK
MOEX_CLEARING_END = time(19, 5)   # 19:05 MSK


@dataclass
class MOEXTradingSession:
    """MOEX trading session information"""
    date: datetime
    main_session_start: time = MOEX_TRADING_START
    main_session_end: time = MOEX_TRADING_END
    clearing_start: time = MOEX_CLEARING_START
    clearing_end: time = MOEX_CLEARING_END
    is_trading_day: bool = True
    session_type: str = "NORMAL"  # NORMAL, SHORTENED, HOLIDAY
    
    def __post_init__(self):
        """Validate MOEX trading session"""
        valid_session_types = ['NORMAL', 'SHORTENED', 'HOLIDAY']
        if self.session_type not in valid_session_types:
            raise ValueError(f"Invalid session type: {self.session_type}")
            
        # Validate session times
        if self.main_session_start >= self.main_session_end:
            raise ValueError("Main session start must be before end")
            
        if self.clearing_start <= self.main_session_end:
            raise ValueError("Clearing must start after main session ends")
    
    def is_market_open(self, current_time: datetime = None) -> bool:
        """Check if MOEX market is currently open"""
        if not self.is_trading_day:
            return False
            
        if current_time is None:
            current_time = datetime.now(MOSCOW_TZ)
        
        # Convert to Moscow time if needed
        if current_time.tzinfo is None:
            current_time = MOSCOW_TZ.localize(current_time)
        else:
            current_time = current_time.astimezone(MOSCOW_TZ)
        
        current_time_only = current_time.time()
        return self.main_session_start <= current_time_only <= self.main_session_end
    
    def is_clearing_session(self, current_time: datetime = None) -> bool:
        """Check if currently in clearing session"""
        if not self.is_trading_day:
            return False
            
        if current_time is None:
            current_time = datetime.now(MOSCOW_TZ)
            
        if current_time.tzinfo is None:
            current_time = MOSCOW_TZ.localize(current_time)
        else:
            current_time = current_time.astimezone(MOSCOW_TZ)
            
        current_time_only = current_time.time()
        return self.clearing_start <= current_time_only <= self.clearing_end


@dataclass
class MOEXMarketData(MarketData):
    """Extended market data with MOEX-specific fields"""
    trading_session: Optional[MOEXTradingSession] = None
    lot_size: int = 1
    min_price_step: Optional[Decimal] = None
    face_value: Optional[Decimal] = None
    market_maker_spread: Optional[Decimal] = None
    total_demand: Optional[int] = None  # Total buy orders volume
    total_supply: Optional[int] = None  # Total sell orders volume
    
    def __post_init__(self):
        """Validate MOEX market data"""
        # Call parent validation first
        super().__post_init__()
        
        if self.lot_size < 1:
            raise ValueError("Lot size must be at least 1")
            
        if self.min_price_step and self.min_price_step <= 0:
            raise ValueError("Min price step must be positive")
            
        if self.face_value and self.face_value <= 0:
            raise ValueError("Face value must be positive")
            
        # Validate demand/supply
        if self.total_demand is not None and self.total_demand < 0:
            raise ValueError("Total demand cannot be negative")
            
        if self.total_supply is not None and self.total_supply < 0:
            raise ValueError("Total supply cannot be negative")
    
    def get_effective_spread(self) -> Optional[Decimal]:
        """Calculate effective bid-ask spread"""
        if self.bid and self.ask:
            return self.ask - self.bid
        return None
    
    def get_mid_price(self) -> Optional[Decimal]:
        """Calculate mid price between bid and ask"""
        if self.bid and self.ask:
            return (self.bid + self.ask) / 2
        return None


@dataclass
class MOEXOrderBook:
    """MOEX order book data"""
    symbol: str
    timestamp: datetime
    bids: List[Tuple[Decimal, int]]  # [(price, volume), ...]
    asks: List[Tuple[Decimal, int]]  # [(price, volume), ...]
    
    def __post_init__(self):
        """Validate order book data"""
        if not validate_moex_ticker(self.symbol):
            raise ValueError(f"Invalid MOEX ticker format: {self.symbol}")
            
        # Validate bids are in descending order
        for i in range(len(self.bids) - 1):
            if self.bids[i][0] < self.bids[i + 1][0]:
                raise ValueError("Bids must be in descending price order")
                
        # Validate asks are in ascending order
        for i in range(len(self.asks) - 1):
            if self.asks[i][0] > self.asks[i + 1][0]:
                raise ValueError("Asks must be in ascending price order")
                
        # Validate no negative volumes
        for price, volume in self.bids + self.asks:
            if volume < 0:
                raise ValueError("Order volume cannot be negative")
                
        self.symbol = self.symbol.upper()
    
    def get_best_bid(self) -> Optional[Tuple[Decimal, int]]:
        """Get best bid (highest price)"""
        return self.bids[0] if self.bids else None
    
    def get_best_ask(self) -> Optional[Tuple[Decimal, int]]:
        """Get best ask (lowest price)"""
        return self.asks[0] if self.asks else None
    
    def get_spread(self) -> Optional[Decimal]:
        """Get bid-ask spread"""
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        
        if best_bid and best_ask:
            return best_ask[0] - best_bid[0]
        return None
    
    def get_total_bid_volume(self) -> int:
        """Get total volume of all bids"""
        return sum(volume for _, volume in self.bids)
    
    def get_total_ask_volume(self) -> int:
        """Get total volume of all asks"""
        return sum(volume for _, volume in self.asks)


@dataclass
class MOEXTrade:
    """Individual trade on MOEX"""
    symbol: str
    timestamp: datetime
    price: Decimal
    volume: int
    trade_id: str
    buyer_initiated: bool = True  # True if buyer initiated, False if seller
    
    def __post_init__(self):
        """Validate trade data"""
        if not validate_moex_ticker(self.symbol):
            raise ValueError(f"Invalid MOEX ticker format: {self.symbol}")
            
        if self.price <= 0:
            raise ValueError("Trade price must be positive")
            
        if self.volume <= 0:
            raise ValueError("Trade volume must be positive")
            
        if not self.trade_id:
            raise ValueError("Trade ID is required")
            
        self.symbol = self.symbol.upper()


def validate_moex_trading_hours(timestamp: datetime) -> bool:
    """Validate if timestamp is within MOEX trading hours"""
    if timestamp.tzinfo is None:
        timestamp = MOSCOW_TZ.localize(timestamp)
    else:
        timestamp = timestamp.astimezone(MOSCOW_TZ)
    
    # Check if it's a weekday (Monday=0, Sunday=6)
    if timestamp.weekday() >= 5:  # Saturday or Sunday
        return False
    
    time_only = timestamp.time()
    return MOEX_TRADING_START <= time_only <= MOEX_TRADING_END


def get_next_trading_session(current_date: datetime = None) -> datetime:
    """Get next MOEX trading session start time"""
    if current_date is None:
        current_date = datetime.now(MOSCOW_TZ)
    
    if current_date.tzinfo is None:
        current_date = MOSCOW_TZ.localize(current_date)
    else:
        current_date = current_date.astimezone(MOSCOW_TZ)
    
    # Start from next day if current time is after trading hours or during trading hours
    next_date = current_date
    if current_date.time() >= MOEX_TRADING_START:
        next_date = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
        next_date += timedelta(days=1)
    
    # Find next weekday
    while next_date.weekday() >= 5:  # Skip weekends
        next_date += timedelta(days=1)
    
    # Set to trading start time
    return next_date.replace(
        hour=MOEX_TRADING_START.hour,
        minute=MOEX_TRADING_START.minute,
        second=0,
        microsecond=0
    )