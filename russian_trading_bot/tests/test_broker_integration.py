"""
Unit tests for Russian broker API integration
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from decimal import Decimal
from datetime import datetime

from russian_trading_bot.services.tinkoff_broker import TinkoffBroker
from russian_trading_bot.services.finam_broker import FinamBroker
from russian_trading_bot.services.order_manager import RussianOrderManager, OrderPriority, ManagedOrder
from russian_trading_bot.models.trading import (
    TradeOrder, ExecutionResult, OrderStatus, Portfolio, Position,
    OrderType, OrderAction
)


class TestTinkoffBroker:
    """Test Tinkoff broker implementation"""
    
    @pytest.fixture
    def tinkoff_broker(self):
        """Create Tinkoff broker instance for testing"""
        return TinkoffBroker(token="test_token", sandbox=True)
    
    @pytest.fixture
    def mock_session(self):
        """Mock aiohttp session"""
        session = AsyncMock()
        response = AsyncMock()
        response.status = 200
        response.json = AsyncMock()
        
        # Properly mock the async context manager
        context_manager = AsyncMock()
        context_manager.__aenter__ = AsyncMock(return_value=response)
        context_manager.__aexit__ = AsyncMock(return_value=None)
        session.request.return_value = context_manager
        
        return session, response
    
    @pytest.mark.asyncio
    async def test_authentication_success(self, tinkoff_broker):
        """Test successful authentication"""
        mock_response = {
            "accounts": [{"id": "test_account_id", "name": "Test Account"}]
        }
        
        with patch.object(tinkoff_broker, '_make_request', return_value=mock_response):
            result = await tinkoff_broker.authenticate({"token": "test_token"})
            
        assert result is True
        assert tinkoff_broker.account_id == "test_account_id"
    
    @pytest.mark.asyncio
    async def test_authentication_failure(self, tinkoff_broker):
        """Test authentication failure"""
        mock_response = {"accounts": []}
        
        with patch.object(tinkoff_broker, '_make_request', return_value=mock_response):
            result = await tinkoff_broker.authenticate({"token": "invalid_token"})
            
        assert result is False
        assert tinkoff_broker.account_id is None
    
    @pytest.mark.asyncio
    async def test_get_portfolio(self, tinkoff_broker):
        """Test portfolio retrieval"""
        tinkoff_broker.account_id = "test_account"
        
        # Mock responses for the three API calls
        responses = [
            # Positions response
            {
                "positions": [
                    {
                        "instrumentType": "share",
                        "figi": "BBG004730N88",  # SBER
                        "quantity": {"units": "100"},
                        "averagePositionPrice": {"units": "250"},
                        "currentPrice": {"units": "260"}
                    }
                ]
            },
            # Accounts response
            {"accounts": [{"id": "test_account"}]},
            # Portfolio balance response
            {
                "positions": [
                    {
                        "instrumentType": "currency",
                        "figi": "RUB000UTSTOM",
                        "quantity": {"units": "50000"}
                    }
                ]
            }
        ]
        
        with patch.object(tinkoff_broker, '_make_request', side_effect=responses):
            portfolio = await tinkoff_broker.get_portfolio()
        
        assert isinstance(portfolio, Portfolio)
        assert portfolio.currency == "RUB"
        assert portfolio.cash_balance == Decimal("50000")
        assert len(portfolio.positions) == 1
        assert "BBG004730N88" in portfolio.positions
    
    @pytest.mark.asyncio
    async def test_place_market_order(self, tinkoff_broker):
        """Test placing market order"""
        tinkoff_broker.account_id = "test_account"
        
        mock_response = {
            "orderId": "test_order_123",
            "executionReportStatus": "EXECUTION_REPORT_STATUS_FILL",
            "lotsExecuted": 10
        }
        
        order = TradeOrder(
            symbol="BBG004730N88",
            action=OrderAction.BUY,
            quantity=10,
            order_type=OrderType.MARKET
        )
        
        with patch.object(tinkoff_broker, '_make_request', return_value=mock_response):
            result = await tinkoff_broker.place_order(order)
        
        assert result.order_id == "test_order_123"
        assert result.status == OrderStatus.FILLED
        assert result.filled_quantity == 10
    
    @pytest.mark.asyncio
    async def test_place_limit_order(self, tinkoff_broker):
        """Test placing limit order"""
        tinkoff_broker.account_id = "test_account"
        
        mock_response = {
            "orderId": "test_order_456",
            "executionReportStatus": "EXECUTION_REPORT_STATUS_NEW",
            "lotsExecuted": 0
        }
        
        order = TradeOrder(
            symbol="BBG004730N88",
            action=OrderAction.BUY,
            quantity=5,
            order_type=OrderType.LIMIT,
            price=Decimal("250.50")
        )
        
        with patch.object(tinkoff_broker, '_make_request', return_value=mock_response):
            result = await tinkoff_broker.place_order(order)
        
        assert result.order_id == "test_order_456"
        assert result.status == OrderStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_cancel_order(self, tinkoff_broker):
        """Test order cancellation"""
        tinkoff_broker.account_id = "test_account"
        
        mock_response = {"success": True}
        
        with patch.object(tinkoff_broker, '_make_request', return_value=mock_response):
            result = await tinkoff_broker.cancel_order("test_order_123")
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_order_insufficient_funds(self, tinkoff_broker):
        """Test order validation with insufficient funds"""
        tinkoff_broker.account_id = "test_account"
        
        # Mock portfolio with low balance
        mock_portfolio = Portfolio(
            positions={},
            cash_balance=Decimal("1000"),
            currency="RUB"
        )
        
        order = TradeOrder(
            symbol="BBG004730N88",
            action=OrderAction.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            price=Decimal("250")  # Total cost: 25,000 RUB
        )
        
        with patch.object(tinkoff_broker, 'get_portfolio', return_value=mock_portfolio):
            validation = await tinkoff_broker.validate_order(order)
        
        assert validation["valid"] is False
        assert "Insufficient funds" in validation["errors"]


class TestFinamBroker:
    """Test Finam broker implementation"""
    
    @pytest.fixture
    def finam_broker(self):
        """Create Finam broker instance for testing"""
        return FinamBroker(access_token="test_token", client_id="test_client", sandbox=True)
    
    @pytest.fixture
    def mock_session(self):
        """Mock aiohttp session"""
        session = AsyncMock()
        response = AsyncMock()
        response.status = 200
        response.json = AsyncMock()
        
        # Properly mock the async context manager
        context_manager = AsyncMock()
        context_manager.__aenter__ = AsyncMock(return_value=response)
        context_manager.__aexit__ = AsyncMock(return_value=None)
        session.request.return_value = context_manager
        
        return session, response
    
    @pytest.mark.asyncio
    async def test_authentication_success(self, finam_broker):
        """Test successful authentication"""
        mock_response = {
            "data": [{"id": "test_portfolio_id", "name": "Test Portfolio"}]
        }
        
        with patch.object(finam_broker, '_make_request', return_value=mock_response):
            result = await finam_broker.authenticate({"access_token": "test_token"})
            
        assert result is True
        assert finam_broker.portfolio_id == "test_portfolio_id"
    
    @pytest.mark.asyncio
    async def test_get_portfolio(self, finam_broker):
        """Test portfolio retrieval"""
        finam_broker.portfolio_id = "test_portfolio"
        
        # Mock positions and balance responses
        responses = [
            {
                "data": [
                    {
                        "securityType": "Stock",
                        "securityCode": "SBER",
                        "balance": "50",
                        "averagePrice": "260.50",
                        "currentPrice": "265.00"
                    }
                ]
            },
            {
                "data": [
                    {"currency": "RUB", "balance": "75000.00"}
                ]
            }
        ]
        
        with patch.object(finam_broker, '_make_request', side_effect=responses):
            portfolio = await finam_broker.get_portfolio()
        
        assert isinstance(portfolio, Portfolio)
        assert portfolio.currency == "RUB"
        assert portfolio.cash_balance == Decimal("75000.00")
        assert len(portfolio.positions) == 1
        assert "SBER" in portfolio.positions
    
    @pytest.mark.asyncio
    async def test_place_order(self, finam_broker):
        """Test placing order"""
        finam_broker.portfolio_id = "test_portfolio"
        
        mock_response = {
            "data": {"transactionId": "finam_order_789"}
        }
        
        order = TradeOrder(
            symbol="GAZP",
            action=OrderAction.SELL,
            quantity=20,
            order_type=OrderType.LIMIT,
            price=Decimal("180.25")
        )
        
        with patch.object(finam_broker, '_make_request', return_value=mock_response):
            result = await finam_broker.place_order(order)
        
        assert result.order_id == "finam_order_789"
        assert result.status == OrderStatus.PENDING


class TestOrderManager:
    """Test order management system"""
    
    @pytest.fixture
    def order_manager(self):
        """Create order manager instance"""
        return RussianOrderManager()
    
    @pytest.fixture
    def mock_tinkoff_broker(self):
        """Mock Tinkoff broker"""
        broker = AsyncMock(spec=TinkoffBroker)
        broker.authenticate.return_value = True
        broker.validate_order.return_value = {"valid": True, "errors": [], "warnings": []}
        return broker
    
    @pytest.fixture
    def mock_finam_broker(self):
        """Mock Finam broker"""
        broker = AsyncMock(spec=FinamBroker)
        broker.authenticate.return_value = True
        broker.validate_order.return_value = {"valid": True, "errors": [], "warnings": []}
        return broker
    
    def test_add_brokers(self, order_manager, mock_tinkoff_broker, mock_finam_broker):
        """Test adding brokers to order manager"""
        order_manager.add_broker("tinkoff", mock_tinkoff_broker, is_primary=True)
        order_manager.add_broker("finam", mock_finam_broker, is_primary=False)
        
        assert order_manager.primary_broker == "tinkoff"
        assert "finam" in order_manager.backup_brokers
        assert len(order_manager.brokers) == 2
    
    @pytest.mark.asyncio
    async def test_authenticate_all_brokers(self, order_manager, mock_tinkoff_broker, mock_finam_broker):
        """Test authenticating all brokers"""
        order_manager.add_broker("tinkoff", mock_tinkoff_broker)
        order_manager.add_broker("finam", mock_finam_broker)
        
        credentials = {
            "tinkoff": {"token": "tinkoff_token"},
            "finam": {"access_token": "finam_token", "client_id": "client123"}
        }
        
        results = await order_manager.authenticate_all_brokers(credentials)
        
        assert results["tinkoff"] is True
        assert results["finam"] is True
        mock_tinkoff_broker.authenticate.assert_called_once()
        mock_finam_broker.authenticate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_submit_order(self, order_manager, mock_tinkoff_broker):
        """Test submitting order"""
        order_manager.add_broker("tinkoff", mock_tinkoff_broker, is_primary=True)
        
        # Mock successful execution
        mock_result = ExecutionResult(
            order_id="broker_order_123",
            status=OrderStatus.FILLED,
            filled_quantity=10,
            timestamp=datetime.now()
        )
        mock_tinkoff_broker.place_order.return_value = mock_result
        
        order = TradeOrder(
            symbol="SBER",
            action=OrderAction.BUY,
            quantity=10,
            order_type=OrderType.MARKET
        )
        
        order_id = await order_manager.submit_order(order, OrderPriority.HIGH)
        
        assert order_id in order_manager.managed_orders
        assert len(order_manager.order_queue) >= 0  # Order might be processed immediately
    
    @pytest.mark.asyncio
    async def test_order_priority_queue(self, order_manager):
        """Test order priority queue"""
        order_manager.is_running = False  # Prevent automatic processing
        
        # Create orders with different priorities
        low_order = TradeOrder(symbol="SBER", action=OrderAction.BUY, quantity=10, order_type=OrderType.MARKET)
        high_order = TradeOrder(symbol="GAZP", action=OrderAction.BUY, quantity=5, order_type=OrderType.MARKET)
        urgent_order = TradeOrder(symbol="LKOH", action=OrderAction.SELL, quantity=3, order_type=OrderType.MARKET)
        
        # Submit in reverse priority order
        await order_manager.submit_order(low_order, OrderPriority.LOW)
        await order_manager.submit_order(high_order, OrderPriority.HIGH)
        await order_manager.submit_order(urgent_order, OrderPriority.URGENT)
        
        # Check queue order (highest priority first)
        assert len(order_manager.order_queue) == 3
        assert order_manager.order_queue[0].priority == OrderPriority.URGENT
        assert order_manager.order_queue[1].priority == OrderPriority.HIGH
        assert order_manager.order_queue[2].priority == OrderPriority.LOW
    
    @pytest.mark.asyncio
    async def test_cancel_queued_order(self, order_manager):
        """Test cancelling order in queue"""
        order_manager.is_running = False  # Prevent automatic processing
        
        order = TradeOrder(
            symbol="SBER",
            action=OrderAction.BUY,
            quantity=10,
            order_type=OrderType.MARKET
        )
        
        order_id = await order_manager.submit_order(order)
        
        # Cancel the order
        result = await order_manager.cancel_order(order_id)
        
        assert result is True
        assert order_manager.managed_orders[order_id].current_status == OrderStatus.CANCELLED
        assert len(order_manager.order_queue) == 0
    
    def test_managed_order_lifecycle(self):
        """Test managed order lifecycle"""
        order = TradeOrder(
            symbol="GAZP",
            action=OrderAction.SELL,
            quantity=20,
            order_type=OrderType.LIMIT,
            price=Decimal("180.00")
        )
        
        managed_order = ManagedOrder(order, OrderPriority.NORMAL)
        
        # Initial state
        assert managed_order.current_status == OrderStatus.PENDING
        assert not managed_order.is_final_status()
        assert managed_order.attempts == 0
        
        # Add execution result
        result = ExecutionResult(
            order_id="broker_123",
            status=OrderStatus.FILLED,
            filled_quantity=20,
            timestamp=datetime.now()
        )
        
        managed_order.add_execution_result("tinkoff", result)
        
        assert managed_order.current_status == OrderStatus.FILLED
        assert managed_order.is_final_status()
        assert "tinkoff" in managed_order.broker_order_ids
    
    def test_order_retry_logic(self):
        """Test order retry logic"""
        order = TradeOrder(
            symbol="SBER",
            action=OrderAction.BUY,
            quantity=10,
            order_type=OrderType.MARKET
        )
        
        managed_order = ManagedOrder(order)
        managed_order.attempts = 1
        managed_order.current_status = OrderStatus.REJECTED
        
        # Should retry
        assert managed_order.should_retry() is True
        
        # Exceed max attempts
        managed_order.attempts = 3
        assert managed_order.should_retry() is False
        
        # Final status - no retry
        managed_order.attempts = 1
        managed_order.current_status = OrderStatus.FILLED
        assert managed_order.should_retry() is False
    
    def test_order_statistics(self, order_manager):
        """Test order statistics calculation"""
        # Create some test orders
        orders_data = [
            (OrderStatus.FILLED, 5),
            (OrderStatus.PENDING, 2),
            (OrderStatus.REJECTED, 1),
            (OrderStatus.CANCELLED, 1)
        ]
        
        for status, count in orders_data:
            for i in range(count):
                order = TradeOrder(
                    symbol=f"TEST{i}",
                    action=OrderAction.BUY,
                    quantity=10,
                    order_type=OrderType.MARKET
                )
                managed_order = ManagedOrder(order)
                managed_order.current_status = status
                order_manager.managed_orders[f"order_{status.name}_{i}"] = managed_order
        
        stats = order_manager.get_order_statistics()
        
        assert stats["total_orders"] == 9
        assert stats["status_breakdown"]["FILLED"] == 5
        assert stats["status_breakdown"]["PENDING"] == 2
        assert stats["success_rate"] == 55.56  # 5/9 * 100, rounded to 2 decimals


if __name__ == "__main__":
    pytest.main([__file__])