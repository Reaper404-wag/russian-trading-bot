"""
Tinkoff Invest API integration for Russian stock trading
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


class TinkoffBroker(RussianBrokerInterface):
    """Tinkoff Invest API implementation"""
    
    def __init__(self, token: str, sandbox: bool = True):
        """
        Initialize Tinkoff broker client
        
        Args:
            token: Tinkoff Invest API token
            sandbox: Use sandbox environment for testing
        """
        self.token = token
        self.sandbox = sandbox
        self.base_url = (
            "https://invest-public-api.tinkoff.ru/rest" if not sandbox
            else "https://invest-public-api.tinkoff.ru/rest/tinkoff.public.invest.api.contract.v1.SandboxService"
        )
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "accept": "application/json"
        }
        self.session: Optional[aiohttp.ClientSession] = None
        self.account_id: Optional[str] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session
    
    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request to Tinkoff API"""
        session = await self._get_session()
        url = f"{self.base_url}/{endpoint}"
        
        try:
            async with session.request(method, url, json=data) as response:
                response_data = await response.json()
                
                if response.status != 200:
                    logger.error(f"Tinkoff API error: {response.status} - {response_data}")
                    raise Exception(f"API request failed: {response_data}")
                
                return response_data
        except Exception as e:
            logger.error(f"Request to {url} failed: {e}")
            raise
    
    async def authenticate(self, credentials: Dict[str, str]) -> bool:
        """
        Authenticate with Tinkoff Invest API
        
        Args:
            credentials: Should contain 'token' key
            
        Returns:
            True if authentication successful
        """
        try:
            # Get user accounts to verify authentication
            response = await self._make_request("POST", "GetAccounts", {})
            
            if "accounts" in response and response["accounts"]:
                # Use first account for trading
                self.account_id = response["accounts"][0]["id"]
                logger.info(f"Authenticated with Tinkoff, account ID: {self.account_id}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    async def get_portfolio(self) -> Portfolio:
        """Get current portfolio information"""
        if not self.account_id:
            raise Exception("Not authenticated")
        
        try:
            # Get positions
            positions_response = await self._make_request(
                "POST", "GetPositions", {"accountId": self.account_id}
            )
            
            # Get account balance
            balance_response = await self._make_request(
                "POST", "GetAccounts", {}
            )
            
            positions = {}
            cash_balance = Decimal(0)
            
            # Process positions
            if "positions" in positions_response:
                for pos_data in positions_response["positions"]:
                    if pos_data["instrumentType"] == "share":
                        symbol = pos_data["figi"]  # Using FIGI as symbol
                        quantity = int(pos_data["quantity"]["units"])
                        
                        if quantity != 0:  # Only include non-zero positions
                            avg_price = Decimal(str(pos_data["averagePositionPrice"]["units"]))
                            current_price = Decimal(str(pos_data["currentPrice"]["units"]))
                            
                            position = Position(
                                symbol=symbol,
                                quantity=quantity,
                                average_price=avg_price,
                                current_price=current_price,
                                currency="RUB"
                            )
                            positions[symbol] = position
            
            # Get cash balance
            for account in balance_response.get("accounts", []):
                if account["id"] == self.account_id:
                    # Get account balance details
                    balance_detail = await self._make_request(
                        "POST", "GetPortfolio", {"accountId": self.account_id}
                    )
                    
                    for position in balance_detail.get("positions", []):
                        if position["instrumentType"] == "currency" and position["figi"] == "RUB000UTSTOM":
                            cash_balance = Decimal(str(position["quantity"]["units"]))
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
    
    def _convert_order_to_tinkoff(self, order: TradeOrder) -> Dict[str, Any]:
        """Convert TradeOrder to Tinkoff API format"""
        tinkoff_order = {
            "figi": order.symbol,  # Assuming symbol is FIGI
            "quantity": order.quantity,
            "direction": "ORDER_DIRECTION_BUY" if order.action == OrderAction.BUY else "ORDER_DIRECTION_SELL",
            "accountId": self.account_id
        }
        
        # Set order type
        if order.order_type == OrderType.MARKET:
            tinkoff_order["orderType"] = "ORDER_TYPE_MARKET"
        elif order.order_type == OrderType.LIMIT:
            tinkoff_order["orderType"] = "ORDER_TYPE_LIMIT"
            tinkoff_order["price"] = {
                "units": str(int(order.price)),
                "nano": int((order.price % 1) * 1_000_000_000)
            }
        
        return tinkoff_order
    
    async def place_order(self, order: TradeOrder) -> ExecutionResult:
        """Place a trading order"""
        if not self.account_id:
            raise Exception("Not authenticated")
        
        try:
            tinkoff_order = self._convert_order_to_tinkoff(order)
            
            response = await self._make_request("POST", "PostOrder", tinkoff_order)
            
            order_id = response.get("orderId", "")
            execution_status = response.get("executionReportStatus", "")
            
            # Convert Tinkoff status to our status
            status_mapping = {
                "EXECUTION_REPORT_STATUS_FILL": OrderStatus.FILLED,
                "EXECUTION_REPORT_STATUS_PARTIALLYFILL": OrderStatus.PARTIALLY_FILLED,
                "EXECUTION_REPORT_STATUS_NEW": OrderStatus.PENDING,
                "EXECUTION_REPORT_STATUS_CANCELLED": OrderStatus.CANCELLED,
                "EXECUTION_REPORT_STATUS_REJECTED": OrderStatus.REJECTED
            }
            
            status = status_mapping.get(execution_status, OrderStatus.PENDING)
            
            return ExecutionResult(
                order_id=order_id,
                status=status,
                filled_quantity=response.get("lotsExecuted", 0),
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
        if not self.account_id:
            raise Exception("Not authenticated")
        
        try:
            await self._make_request(
                "POST", 
                "CancelOrder", 
                {"accountId": self.account_id, "orderId": order_id}
            )
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    async def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """Get status of a specific order"""
        if not self.account_id:
            raise Exception("Not authenticated")
        
        try:
            response = await self._make_request(
                "POST", 
                "GetOrderState", 
                {"accountId": self.account_id, "orderId": order_id}
            )
            
            execution_status = response.get("executionReportStatus", "")
            
            status_mapping = {
                "EXECUTION_REPORT_STATUS_FILL": OrderStatus.FILLED,
                "EXECUTION_REPORT_STATUS_PARTIALLYFILL": OrderStatus.PARTIALLY_FILLED,
                "EXECUTION_REPORT_STATUS_NEW": OrderStatus.PENDING,
                "EXECUTION_REPORT_STATUS_CANCELLED": OrderStatus.CANCELLED,
                "EXECUTION_REPORT_STATUS_REJECTED": OrderStatus.REJECTED
            }
            
            return status_mapping.get(execution_status, OrderStatus.PENDING)
            
        except Exception as e:
            logger.error(f"Failed to get order status for {order_id}: {e}")
            return None
    
    async def get_order_history(self, days: int = 30) -> List[OrderStatus]:
        """Get order history"""
        if not self.account_id:
            raise Exception("Not authenticated")
        
        try:
            from_date = datetime.now() - timedelta(days=days)
            to_date = datetime.now()
            
            response = await self._make_request(
                "POST", 
                "GetOrders", 
                {
                    "accountId": self.account_id,
                    "from": from_date.isoformat(),
                    "to": to_date.isoformat()
                }
            )
            
            orders = []
            for order_data in response.get("orders", []):
                execution_status = order_data.get("executionReportStatus", "")
                
                status_mapping = {
                    "EXECUTION_REPORT_STATUS_FILL": OrderStatus.FILLED,
                    "EXECUTION_REPORT_STATUS_PARTIALLYFILL": OrderStatus.PARTIALLY_FILLED,
                    "EXECUTION_REPORT_STATUS_NEW": OrderStatus.PENDING,
                    "EXECUTION_REPORT_STATUS_CANCELLED": OrderStatus.CANCELLED,
                    "EXECUTION_REPORT_STATUS_REJECTED": OrderStatus.REJECTED
                }
                
                status = status_mapping.get(execution_status, OrderStatus.PENDING)
                orders.append(status)
            
            return orders
            
        except Exception as e:
            logger.error(f"Failed to get order history: {e}")
            return []
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        if not self.account_id:
            raise Exception("Not authenticated")
        
        try:
            response = await self._make_request("POST", "GetAccounts", {})
            
            for account in response.get("accounts", []):
                if account["id"] == self.account_id:
                    return {
                        "account_id": account["id"],
                        "name": account.get("name", ""),
                        "type": account.get("type", ""),
                        "status": account.get("status", ""),
                        "access_level": account.get("accessLevel", "")
                    }
            
            return {}
            
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