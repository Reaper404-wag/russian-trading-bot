"""
Finam API integration for Russian stock trading (backup broker)
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import aiohttp
import json

from russian_trading_bot.api.broker_interface import RussianBrokerInterface, BrokerType
from russian_trading_bot.models.trading import (
    TradeOrder, ExecutionResult, OrderStatus, Portfolio, Position,
    OrderType, OrderAction
)


logger = logging.getLogger(__name__)


class FinamBroker(RussianBrokerInterface):
    """Finam API implementation (backup broker)"""
    
    def __init__(self, access_token: str, client_id: str, sandbox: bool = True):
        """
        Initialize Finam broker client
        
        Args:
            access_token: Finam API access token
            client_id: Client ID for Finam API
            sandbox: Use sandbox environment for testing
        """
        self.access_token = access_token
        self.client_id = client_id
        self.sandbox = sandbox
        self.base_url = (
            "https://trade-api.finam.ru" if not sandbox
            else "https://trade-api.finam.ru/public/api/v1"  # Sandbox URL
        )
        self.headers = {
            "X-Api-Key": access_token,
            "Content-Type": "application/json",
            "accept": "application/json"
        }
        self.session: Optional[aiohttp.ClientSession] = None
        self.portfolio_id: Optional[str] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session
    
    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to Finam API"""
        session = await self._get_session()
        url = f"{self.base_url}/{endpoint}"
        
        try:
            async with session.request(method, url, json=data) as response:
                response_data = await response.json()
                
                if response.status != 200:
                    logger.error(f"Finam API error: {response.status} - {response_data}")
                    raise Exception(f"API request failed: {response_data}")
                
                return response_data
        except Exception as e:
            logger.error(f"Request to {url} failed: {e}")
            raise
    
    async def authenticate(self, credentials: Dict[str, str]) -> bool:
        """
        Authenticate with Finam API
        
        Args:
            credentials: Should contain 'access_token' and 'client_id'
            
        Returns:
            True if authentication successful
        """
        try:
            # Get portfolios to verify authentication
            response = await self._make_request("GET", f"portfolios/{self.client_id}")
            
            if "data" in response and response["data"]:
                # Use first portfolio for trading
                self.portfolio_id = response["data"][0]["id"]
                logger.info(f"Authenticated with Finam, portfolio ID: {self.portfolio_id}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    async def get_portfolio(self) -> Portfolio:
        """Get current portfolio information"""
        if not self.portfolio_id:
            raise Exception("Not authenticated")
        
        try:
            # Get portfolio positions
            positions_response = await self._make_request(
                "GET", f"portfolios/{self.client_id}/{self.portfolio_id}/positions"
            )
            
            # Get portfolio balance
            balance_response = await self._make_request(
                "GET", f"portfolios/{self.client_id}/{self.portfolio_id}/balance"
            )
            
            positions = {}
            cash_balance = Decimal(0)
            
            # Process positions
            if "data" in positions_response:
                for pos_data in positions_response["data"]:
                    if pos_data["securityType"] == "Stock":
                        symbol = pos_data["securityCode"]
                        quantity = int(pos_data["balance"])
                        
                        if quantity != 0:  # Only include non-zero positions
                            avg_price = Decimal(str(pos_data["averagePrice"]))
                            current_price = Decimal(str(pos_data["currentPrice"]))
                            
                            position = Position(
                                symbol=symbol,
                                quantity=quantity,
                                average_price=avg_price,
                                current_price=current_price,
                                currency="RUB"
                            )
                            positions[symbol] = position
            
            # Get cash balance
            if "data" in balance_response:
                for balance_item in balance_response["data"]:
                    if balance_item["currency"] == "RUB":
                        cash_balance = Decimal(str(balance_item["balance"]))
                        break
            
            return Portfolio(
                positions=positions,
                cash_balance=cash_balance,
                currency="RUB"
            )
            
        except Exception as e:
            logger.error(f"Failed to get portfolio: {e}")
            raise
    
    async def get_positions(self) -> List[Position]:
        """Get all current positions"""
        portfolio = await self.get_portfolio()
        return list(portfolio.positions.values())
    
    def _convert_order_to_finam(self, order: TradeOrder) -> Dict[str, Any]:
        """Convert TradeOrder to Finam API format"""
        finam_order = {
            "clientId": self.client_id,
            "securityBoard": "TQBR",  # Main board for Russian stocks
            "securityCode": order.symbol,
            "buySell": "Buy" if order.action == OrderAction.BUY else "Sell",
            "quantity": order.quantity
        }
        
        # Set order type and price
        if order.order_type == OrderType.MARKET:
            finam_order["useCredit"] = False
            finam_order["price"] = 0  # Market order
        elif order.order_type == OrderType.LIMIT:
            finam_order["useCredit"] = False
            finam_order["price"] = float(order.price)
        
        return finam_order
    
    async def place_order(self, order: TradeOrder) -> ExecutionResult:
        """Place a trading order"""
        if not self.portfolio_id:
            raise Exception("Not authenticated")
        
        try:
            finam_order = self._convert_order_to_finam(order)
            
            response = await self._make_request("POST", "orders", finam_order)
            
            order_id = str(response.get("data", {}).get("transactionId", ""))
            
            # Finam typically returns success for order placement
            # Actual execution status needs to be checked separately
            return ExecutionResult(
                order_id=order_id,
                status=OrderStatus.PENDING,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            return ExecutionResult(
                order_id="",
                status=OrderStatus.REJECTED,
                error_message=str(e),
                timestamp=datetime.now()
            )
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order"""
        if not self.portfolio_id:
            raise Exception("Not authenticated")
        
        try:
            await self._make_request(
                "DELETE", 
                f"orders/{order_id}",
                {"clientId": self.client_id}
            )
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    async def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """Get status of a specific order"""
        if not self.portfolio_id:
            raise Exception("Not authenticated")
        
        try:
            response = await self._make_request(
                "GET", 
                f"orders/{order_id}",
                {"clientId": self.client_id}
            )
            
            status_str = response.get("data", {}).get("status", "")
            
            # Map Finam status to our status
            status_mapping = {
                "Active": OrderStatus.PENDING,
                "Matched": OrderStatus.FILLED,
                "Cancelled": OrderStatus.CANCELLED,
                "Rejected": OrderStatus.REJECTED,
                "PartiallyMatched": OrderStatus.PARTIALLY_FILLED
            }
            
            return status_mapping.get(status_str, OrderStatus.PENDING)
            
        except Exception as e:
            logger.error(f"Failed to get order status for {order_id}: {e}")
            return None
    
    async def get_order_history(self, days: int = 30) -> List[OrderStatus]:
        """Get order history"""
        if not self.portfolio_id:
            raise Exception("Not authenticated")
        
        try:
            from_date = datetime.now() - timedelta(days=days)
            to_date = datetime.now()
            
            response = await self._make_request(
                "GET", 
                f"orders/history",
                {
                    "clientId": self.client_id,
                    "from": from_date.strftime("%Y-%m-%d"),
                    "to": to_date.strftime("%Y-%m-%d")
                }
            )
            
            orders = []
            for order_data in response.get("data", []):
                status_str = order_data.get("status", "")
                
                status_mapping = {
                    "Active": OrderStatus.PENDING,
                    "Matched": OrderStatus.FILLED,
                    "Cancelled": OrderStatus.CANCELLED,
                    "Rejected": OrderStatus.REJECTED,
                    "PartiallyMatched": OrderStatus.PARTIALLY_FILLED
                }
                
                status = status_mapping.get(status_str, OrderStatus.PENDING)
                orders.append(status)
            
            return orders
            
        except Exception as e:
            logger.error(f"Failed to get order history: {e}")
            return []
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        if not self.portfolio_id:
            raise Exception("Not authenticated")
        
        try:
            response = await self._make_request(
                "GET", 
                f"portfolios/{self.client_id}/{self.portfolio_id}"
            )
            
            data = response.get("data", {})
            return {
                "portfolio_id": data.get("id", ""),
                "name": data.get("name", ""),
                "type": data.get("type", ""),
                "status": data.get("status", ""),
                "currency": data.get("currency", "RUB")
            }
            
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            return {}
    
    async def validate_order(self, order: TradeOrder) -> Dict[str, Any]:
        """Validate order before placement"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": []
        }
        
        try:
            # Basic validation
            if order.quantity <= 0:
                validation_result["valid"] = False
                validation_result["errors"].append("Quantity must be positive")
            
            if order.currency != "RUB":
                validation_result["valid"] = False
                validation_result["errors"].append("Only RUB currency supported")
            
            # Check account balance for buy orders
            if order.action == OrderAction.BUY:
                portfolio = await self.get_portfolio()
                estimated_cost = order.quantity * (order.price or Decimal(0))
                
                if estimated_cost > portfolio.cash_balance:
                    validation_result["valid"] = False
                    validation_result["errors"].append("Insufficient funds")
            
            # Check position for sell orders
            if order.action == OrderAction.SELL:
                positions = await self.get_positions()
                position = next((p for p in positions if p.symbol == order.symbol), None)
                
                if not position or position.quantity < order.quantity:
                    validation_result["valid"] = False
                    validation_result["errors"].append("Insufficient position to sell")
            
        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Validation error: {str(e)}")
        
        return validation_result
    
    async def close(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()