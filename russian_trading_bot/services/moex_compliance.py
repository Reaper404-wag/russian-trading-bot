"""
MOEX trading rules compliance system
Handles lot size validation, trading hours enforcement, and T+2 settlement
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, time, timedelta
from decimal import Decimal
from enum import Enum
import pytz

from russian_trading_bot.models.trading import TradeOrder, OrderAction, OrderType


logger = logging.getLogger(__name__)


class MOEXTradingSession(Enum):
    """MOEX trading session types"""
    MAIN = "main"  # 10:00-18:45 MSK
    EVENING = "evening"  # 19:05-23:50 MSK
    CLOSED = "closed"


class MOEXSecurityType(Enum):
    """MOEX security types with different rules"""
    STOCK = "stock"
    BOND = "bond"
    ETF = "etf"
    CURRENCY = "currency"


class MOEXComplianceValidator:
    """MOEX trading rules compliance validator"""
    
    def __init__(self):
        """Initialize MOEX compliance validator"""
        self.moscow_tz = pytz.timezone('Europe/Moscow')
        
        # MOEX trading hours (Moscow time)
        self.main_session_start = time(10, 0)  # 10:00 MSK
        self.main_session_end = time(18, 45)   # 18:45 MSK
        self.evening_session_start = time(19, 5)  # 19:05 MSK
        self.evening_session_end = time(23, 50)   # 23:50 MSK
        
        # Standard lot sizes for different security types
        self.standard_lot_sizes = {
            MOEXSecurityType.STOCK: 1,      # 1 share per lot
            MOEXSecurityType.BOND: 1,       # 1 bond per lot
            MOEXSecurityType.ETF: 1,        # 1 unit per lot
            MOEXSecurityType.CURRENCY: 1000 # 1000 units per lot
        }
        
        # Minimum order values (in RUB)
        self.minimum_order_values = {
            MOEXSecurityType.STOCK: Decimal("1000"),    # 1,000 RUB
            MOEXSecurityType.BOND: Decimal("1000"),     # 1,000 RUB
            MOEXSecurityType.ETF: Decimal("1000"),      # 1,000 RUB
            MOEXSecurityType.CURRENCY: Decimal("100")   # 100 RUB
        }
        
        # Security-specific lot sizes (symbol -> lot_size)
        self.security_lot_sizes: Dict[str, int] = {}
        
        # Load known security lot sizes
        self._load_security_lot_sizes()
    
    def _load_security_lot_sizes(self):
        """Load known security lot sizes"""
        # Major Russian stocks and their lot sizes
        self.security_lot_sizes.update({
            # Blue chips
            "SBER": 10,      # Sberbank - 10 shares per lot
            "GAZP": 10,      # Gazprom - 10 shares per lot
            "LKOH": 1,       # Lukoil - 1 share per lot
            "ROSN": 1,       # Rosneft - 1 share per lot
            "NVTK": 1,       # Novatek - 1 share per lot
            "GMKN": 1,       # Nornickel - 1 share per lot
            "YNDX": 1,       # Yandex - 1 share per lot
            "MGNT": 1,       # Magnit - 1 share per lot
            "MTSS": 10,      # MTS - 10 shares per lot
            "RTKM": 10,      # Rostelecom - 10 shares per lot
            
            # Second tier stocks
            "AFLT": 10,      # Aeroflot - 10 shares per lot
            "ALRS": 1,       # Alrosa - 1 share per lot
            "CHMF": 1,       # Severstal - 1 share per lot
            "FEES": 1,       # FGC UES - 1 share per lot
            "HYDR": 1000,    # RusHydro - 1000 shares per lot
            "IRAO": 1000,    # Inter RAO - 1000 shares per lot
            "MAIL": 1,       # Mail.ru - 1 share per lot
            "MOEX": 10,      # Moscow Exchange - 10 shares per lot
            "NLMK": 1,       # NLMK - 1 share per lot
            "PLZL": 1,       # Polyus - 1 share per lot
            "POLY": 1,       # Polymetal - 1 share per lot
            "RUAL": 100,     # Rusal - 100 shares per lot
            "SNGS": 1,       # Surgutneftegas - 1 share per lot
            "TATN": 1,       # Tatneft - 1 share per lot
            "TRNFP": 1,      # Transneft pref - 1 share per lot
            "VTBR": 10000,   # VTB - 10,000 shares per lot
        })
    
    def get_current_moscow_time(self) -> datetime:
        """Get current Moscow time"""
        return datetime.now(self.moscow_tz)
    
    def get_trading_session(self, timestamp: Optional[datetime] = None) -> MOEXTradingSession:
        """
        Get current MOEX trading session
        
        Args:
            timestamp: Optional timestamp to check (defaults to current time)
            
        Returns:
            Current trading session
        """
        if timestamp is None:
            timestamp = self.get_current_moscow_time()
        
        # Convert to Moscow time if needed
        if timestamp.tzinfo is None:
            timestamp = self.moscow_tz.localize(timestamp)
        elif timestamp.tzinfo != self.moscow_tz:
            timestamp = timestamp.astimezone(self.moscow_tz)
        
        current_time = timestamp.time()
        current_weekday = timestamp.weekday()
        
        # Check if it's a weekend
        if current_weekday >= 5:  # Saturday = 5, Sunday = 6
            return MOEXTradingSession.CLOSED
        
        # Check trading sessions
        if self.main_session_start <= current_time <= self.main_session_end:
            return MOEXTradingSession.MAIN
        elif self.evening_session_start <= current_time <= self.evening_session_end:
            return MOEXTradingSession.EVENING
        else:
            return MOEXTradingSession.CLOSED
    
    def is_trading_hours(self, timestamp: Optional[datetime] = None) -> bool:
        """
        Check if current time is within MOEX trading hours
        
        Args:
            timestamp: Optional timestamp to check
            
        Returns:
            True if within trading hours
        """
        session = self.get_trading_session(timestamp)
        return session in [MOEXTradingSession.MAIN, MOEXTradingSession.EVENING]
    
    def get_next_trading_session(self, timestamp: Optional[datetime] = None) -> datetime:
        """
        Get the start time of the next trading session
        
        Args:
            timestamp: Optional timestamp to check from
            
        Returns:
            Datetime of next trading session start
        """
        if timestamp is None:
            timestamp = self.get_current_moscow_time()
        
        # Convert to Moscow time if needed
        if timestamp.tzinfo is None:
            timestamp = self.moscow_tz.localize(timestamp)
        elif timestamp.tzinfo != self.moscow_tz:
            timestamp = timestamp.astimezone(self.moscow_tz)
        
        current_date = timestamp.date()
        current_time = timestamp.time()
        
        # If it's before main session today
        if current_time < self.main_session_start:
            next_session = datetime.combine(current_date, self.main_session_start)
            return self.moscow_tz.localize(next_session)
        
        # If it's between main and evening session today
        elif self.main_session_end < current_time < self.evening_session_start:
            next_session = datetime.combine(current_date, self.evening_session_start)
            return self.moscow_tz.localize(next_session)
        
        # Otherwise, next main session (tomorrow or Monday if weekend)
        next_date = current_date + timedelta(days=1)
        
        # Skip weekends
        while next_date.weekday() >= 5:
            next_date += timedelta(days=1)
        
        next_session = datetime.combine(next_date, self.main_session_start)
        return self.moscow_tz.localize(next_session)
    
    def get_security_type(self, symbol: str) -> MOEXSecurityType:
        """
        Determine security type from symbol
        
        Args:
            symbol: Security symbol
            
        Returns:
            Security type
        """
        # Simple heuristics for security type detection
        symbol = symbol.upper()
        
        # Currency pairs
        if any(curr in symbol for curr in ['USD', 'EUR', 'CNY', 'RUB']):
            return MOEXSecurityType.CURRENCY
        
        # ETFs typically have specific prefixes or suffixes
        if any(etf_marker in symbol for etf_marker in ['ETF', 'FXRU', 'FXUS', 'FXGD']):
            return MOEXSecurityType.ETF
        
        # Bonds typically have specific patterns
        if any(bond_marker in symbol for bond_marker in ['SU', 'RU', 'OFZ']):
            return MOEXSecurityType.BOND
        
        # Default to stock
        return MOEXSecurityType.STOCK
    
    def get_lot_size(self, symbol: str) -> int:
        """
        Get lot size for a security
        
        Args:
            symbol: Security symbol
            
        Returns:
            Lot size (number of securities per lot)
        """
        symbol = symbol.upper()
        
        # Check if we have specific lot size for this security
        if symbol in self.security_lot_sizes:
            return self.security_lot_sizes[symbol]
        
        # Use default lot size based on security type
        security_type = self.get_security_type(symbol)
        return self.standard_lot_sizes.get(security_type, 1)
    
    def validate_lot_size(self, symbol: str, quantity: int) -> Tuple[bool, str]:
        """
        Validate if quantity is a valid multiple of lot size
        
        Args:
            symbol: Security symbol
            quantity: Order quantity
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        lot_size = self.get_lot_size(symbol)
        
        if quantity % lot_size != 0:
            return False, f"Quantity {quantity} must be a multiple of lot size {lot_size} for {symbol}"
        
        if quantity <= 0:
            return False, f"Quantity must be positive, got {quantity}"
        
        return True, ""
    
    def validate_minimum_order_value(self, symbol: str, quantity: int, price: Decimal) -> Tuple[bool, str]:
        """
        Validate minimum order value
        
        Args:
            symbol: Security symbol
            quantity: Order quantity
            price: Order price
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        security_type = self.get_security_type(symbol)
        min_value = self.minimum_order_values.get(security_type, Decimal("1000"))
        
        order_value = quantity * price
        
        if order_value < min_value:
            return False, f"Order value {order_value} RUB is below minimum {min_value} RUB for {security_type.value}"
        
        return True, ""
    
    def validate_trading_hours(self, timestamp: Optional[datetime] = None) -> Tuple[bool, str]:
        """
        Validate if current time is within trading hours
        
        Args:
            timestamp: Optional timestamp to check
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.is_trading_hours(timestamp):
            next_session = self.get_next_trading_session(timestamp)
            return False, f"Market is closed. Next trading session starts at {next_session.strftime('%Y-%m-%d %H:%M %Z')}"
        
        return True, ""
    
    def calculate_settlement_date(self, trade_date: datetime) -> datetime:
        """
        Calculate T+2 settlement date for Russian market
        
        Args:
            trade_date: Trade execution date
            
        Returns:
            Settlement date (T+2 business days)
        """
        # Convert to Moscow time if needed
        if trade_date.tzinfo is None:
            trade_date = self.moscow_tz.localize(trade_date)
        elif trade_date.tzinfo != self.moscow_tz:
            trade_date = trade_date.astimezone(self.moscow_tz)
        
        settlement_date = trade_date.date()
        business_days_added = 0
        
        # Add 2 business days
        while business_days_added < 2:
            settlement_date += timedelta(days=1)
            
            # Skip weekends
            if settlement_date.weekday() < 5:  # Monday = 0, Friday = 4
                business_days_added += 1
        
        # Return as datetime at market open
        settlement_datetime = datetime.combine(settlement_date, self.main_session_start)
        return self.moscow_tz.localize(settlement_datetime)
    
    def validate_order_compliance(self, order: TradeOrder) -> Dict[str, any]:
        """
        Comprehensive order compliance validation
        
        Args:
            order: Trading order to validate
            
        Returns:
            Dictionary with validation results
        """
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "compliance_info": {}
        }
        
        try:
            # Validate lot size
            lot_valid, lot_error = self.validate_lot_size(order.symbol, order.quantity)
            if not lot_valid:
                validation_result["valid"] = False
                validation_result["errors"].append(lot_error)
            else:
                lot_size = self.get_lot_size(order.symbol)
                validation_result["compliance_info"]["lot_size"] = lot_size
                validation_result["compliance_info"]["lots_ordered"] = order.quantity // lot_size
            
            # Validate trading hours
            hours_valid, hours_error = self.validate_trading_hours()
            if not hours_valid:
                validation_result["valid"] = False
                validation_result["errors"].append(hours_error)
            else:
                current_session = self.get_trading_session()
                validation_result["compliance_info"]["trading_session"] = current_session.value
            
            # Validate minimum order value (for limit orders)
            if order.price and order.order_type in [OrderType.LIMIT]:
                value_valid, value_error = self.validate_minimum_order_value(
                    order.symbol, order.quantity, order.price
                )
                if not value_valid:
                    validation_result["valid"] = False
                    validation_result["errors"].append(value_error)
                else:
                    order_value = order.quantity * order.price
                    validation_result["compliance_info"]["order_value_rub"] = float(order_value)
            
            # Add settlement information
            current_time = self.get_current_moscow_time()
            settlement_date = self.calculate_settlement_date(current_time)
            validation_result["compliance_info"]["settlement_date"] = settlement_date.isoformat()
            
            # Security type information
            security_type = self.get_security_type(order.symbol)
            validation_result["compliance_info"]["security_type"] = security_type.value
            
            # Add warnings for specific conditions
            if security_type == MOEXSecurityType.CURRENCY:
                validation_result["warnings"].append("Currency trading has different settlement rules")
            
            if order.quantity > 1000000:  # Large order warning
                validation_result["warnings"].append("Large order may require additional compliance checks")
            
        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Validation error: {str(e)}")
            logger.error(f"Order compliance validation failed: {e}")
        
        return validation_result
    
    def get_compliance_summary(self) -> Dict[str, any]:
        """
        Get summary of MOEX compliance rules
        
        Returns:
            Dictionary with compliance rules summary
        """
        current_time = self.get_current_moscow_time()
        current_session = self.get_trading_session()
        next_session = self.get_next_trading_session()
        
        return {
            "trading_hours": {
                "main_session": f"{self.main_session_start} - {self.main_session_end} MSK",
                "evening_session": f"{self.evening_session_start} - {self.evening_session_end} MSK",
                "current_session": current_session.value,
                "next_session_start": next_session.isoformat()
            },
            "settlement": {
                "standard_settlement": "T+2 business days",
                "currency_settlement": "T+0 or T+1 depending on pair"
            },
            "lot_sizes": {
                "major_stocks": dict(list(self.security_lot_sizes.items())[:10]),
                "default_by_type": {k.value: v for k, v in self.standard_lot_sizes.items()}
            },
            "minimum_values": {k.value: float(v) for k, v in self.minimum_order_values.items()},
            "current_time_msk": current_time.strftime("%Y-%m-%d %H:%M:%S %Z")
        }