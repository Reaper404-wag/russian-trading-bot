"""
Interface for MOEX (Moscow Exchange) data handling
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime
from russian_trading_bot.models.market_data import MarketData, RussianStock


class MOEXDataInterface(ABC):
    """Abstract interface for MOEX data operations"""
    
    @abstractmethod
    async def get_stock_data(self, symbol: str) -> Optional[MarketData]:
        """
        Fetch current market data for a Russian stock
        
        Args:
            symbol: MOEX ticker symbol (e.g., 'SBER', 'GAZP')
            
        Returns:
            MarketData object or None if not found
        """
        pass
    
    @abstractmethod
    async def get_multiple_stocks_data(self, symbols: List[str]) -> Dict[str, MarketData]:
        """
        Fetch market data for multiple Russian stocks
        
        Args:
            symbols: List of MOEX ticker symbols
            
        Returns:
            Dictionary mapping symbols to MarketData objects
        """
        pass
    
    @abstractmethod
    async def get_historical_data(self, symbol: str, start_date: datetime, end_date: datetime) -> List[MarketData]:
        """
        Fetch historical market data for a Russian stock
        
        Args:
            symbol: MOEX ticker symbol
            start_date: Start date for historical data
            end_date: End date for historical data
            
        Returns:
            List of MarketData objects
        """
        pass
    
    @abstractmethod
    async def get_stock_info(self, symbol: str) -> Optional[RussianStock]:
        """
        Get detailed information about a Russian stock
        
        Args:
            symbol: MOEX ticker symbol
            
        Returns:
            RussianStock object or None if not found
        """
        pass
    
    @abstractmethod
    async def search_stocks(self, query: str) -> List[RussianStock]:
        """
        Search for Russian stocks by name or symbol
        
        Args:
            query: Search query (company name or ticker)
            
        Returns:
            List of matching RussianStock objects
        """
        pass
    
    @abstractmethod
    async def get_market_status(self) -> Dict[str, any]:
        """
        Get current MOEX market status
        
        Returns:
            Dictionary with market status information
        """
        pass