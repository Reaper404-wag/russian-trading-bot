"""
Trading models for Russian stock market operations
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List
from enum import Enum
from decimal import Decimal


class OrderType(Enum):
    """Order types supported by Russian brokers"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderAction(Enum):
    """Order actions"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """Order status values"""
    PENDING = "pending"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class TradeOrder:
    """Trading order for Russian stocks"""
    symbol: str
    action: OrderAction
    quantity: int
    order_type: OrderType
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    currency: str = "RUB"
    time_in_force: str = "DAY"  # DAY, GTC, IOC, FOK
    order_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        """Validate trade order"""
        if self.quantity <= 0:
            raise ValueError("Quantity must be positive")
        if self.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT] and not self.price:
            raise ValueError("Price required for limit orders")
        if self.order_type in [OrderType.STOP, OrderType.STOP_LIMIT] and not self.stop_price:
            raise ValueError("Stop price required for stop orders")
        if self.currency != "RUB":
            raise ValueError("Russian orders must be in RUB currency")


@dataclass
class ExecutionResult:
    """Result of order execution"""
    order_id: str
    status: OrderStatus
    filled_quantity: int = 0
    average_price: Optional[Decimal] = None
    commission: Optional[Decimal] = None
    timestamp: Optional[datetime] = None
    error_message: Optional[str] = None
    
    @property
    def is_successful(self) -> bool:
        """Check if execution was successful"""
        return self.status in [OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED]


@dataclass
class Position:
    """Portfolio position in Russian stock"""
    symbol: str
    quantity: int
    average_price: Decimal
    current_price: Optional[Decimal] = None
    currency: str = "RUB"
    market_value: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    realized_pnl: Optional[Decimal] = None
    
    def __post_init__(self):
        """Calculate derived values"""
        if self.current_price:
            self.market_value = self.current_price * self.quantity
            self.unrealized_pnl = (self.current_price - self.average_price) * self.quantity


@dataclass
class Portfolio:
    """Portfolio information"""
    positions: Dict[str, Position]
    cash_balance: Decimal
    currency: str = "RUB"
    total_value: Optional[Decimal] = None
    daily_pnl: Optional[Decimal] = None
    total_pnl: Optional[Decimal] = None
    
    def __post_init__(self):
        """Calculate portfolio totals"""
        positions_value = sum(
            pos.market_value or Decimal(0) 
            for pos in self.positions.values()
        )
        self.total_value = self.cash_balance + positions_value
        
        self.total_pnl = sum(
            (pos.unrealized_pnl or Decimal(0)) + (pos.realized_pnl or Decimal(0))
            for pos in self.positions.values()
        )


@dataclass
class TradingSignal:
    """AI-generated trading signal"""
    symbol: str
    action: OrderAction
    confidence: float
    target_price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    reasoning: str = ""  # In Russian
    timestamp: Optional[datetime] = None
    expected_return: Optional[float] = None
    risk_score: Optional[float] = None
    
    def __post_init__(self):
        """Validate trading signal"""
        if not 0 <= self.confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")
        if self.risk_score is not None and not 0 <= self.risk_score <= 1:
            raise ValueError("Risk score must be between 0 and 1")