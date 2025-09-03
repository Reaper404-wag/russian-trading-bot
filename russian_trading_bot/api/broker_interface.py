"""
Interface for Russian broker integration
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from enum import Enum
from russian_trading_bot.models.trading import TradeOrder, ExecutionResult, OrderStatus, Portfolio, Position


class BrokerType(Enum):
    """Supported Russian brokers"""
    TINKOFF = "tinkoff"
    FINAM = "finam"
    SBERBANK = "sberbank"
    VTB = "vtb"


class RussianBrokerInterface(ABC):
    """Abstract interface for Russian broker operations"""
    
    @abstractmethod
    async def authenticate(self, credentials: Dict[str, str]) -> bool:
        """
        Authenticate with the Russian broker
        
        Args:
            credentials: Broker-specific authentication credentials
            
        Returns:
            True if authentication successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_portfolio(self) -> Portfolio:
        """
        Get current portfolio information
        
        Returns:
            Portfolio object with current positions and balance
        """
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """
        Get all current positions
        
        Returns:
            List of Position objects
        """
        pass
    
    @abstractmethod
    async def place_order(self, order: TradeOrder) -> ExecutionResult:
        """
        Place a trading order
        
        Args:
            order: TradeOrder object with order details
            
        Returns:
            ExecutionResult with order execution details
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an existing order
        
        Args:
            order_id: Unique order identifier
            
        Returns:
            True if cancellation successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """
        Get status of a specific order
        
        Args:
            order_id: Unique order identifier
            
        Returns:
            OrderStatus object or None if order not found
        """
        pass
    
    @abstractmethod
    async def get_order_history(self, days: int = 30) -> List[OrderStatus]:
        """
        Get order history
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of OrderStatus objects
        """
        pass
    
    @abstractmethod
    async def get_account_info(self) -> Dict[str, any]:
        """
        Get account information
        
        Returns:
            Dictionary with account details
        """
        pass
    
    @abstractmethod
    async def validate_order(self, order: TradeOrder) -> Dict[str, any]:
        """
        Validate order before placement
        
        Args:
            order: TradeOrder to validate
            
        Returns:
            Dictionary with validation results
        """
        pass