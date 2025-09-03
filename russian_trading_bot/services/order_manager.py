"""
Order management system for Russian market orders
Coordinates between different brokers and manages order lifecycle
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
import uuid

from russian_trading_bot.api.broker_interface import RussianBrokerInterface, BrokerType
from russian_trading_bot.services.tinkoff_broker import TinkoffBroker
from russian_trading_bot.services.finam_broker import FinamBroker
from russian_trading_bot.models.trading import (
    TradeOrder, ExecutionResult, OrderStatus, Portfolio, Position,
    OrderType, OrderAction, TradingSignal
)


logger = logging.getLogger(__name__)


class OrderPriority(Enum):
    """Order execution priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


class ManagedOrder:
    """Extended order with management metadata"""
    
    def __init__(self, order: TradeOrder, priority: OrderPriority = OrderPriority.NORMAL):
        self.order = order
        self.priority = priority
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.attempts = 0
        self.max_attempts = 3
        self.broker_order_ids: Dict[str, str] = {}  # broker_name -> order_id
        self.execution_results: List[ExecutionResult] = []
        self.current_status = OrderStatus.PENDING
        self.error_messages: List[str] = []
        
        # Generate internal order ID if not provided
        if not self.order.order_id:
            self.order.order_id = str(uuid.uuid4())
    
    def add_execution_result(self, broker_name: str, result: ExecutionResult):
        """Add execution result from a broker"""
        self.execution_results.append(result)
        self.broker_order_ids[broker_name] = result.order_id
        self.current_status = result.status
        self.updated_at = datetime.now()
        
        if result.error_message:
            self.error_messages.append(f"{broker_name}: {result.error_message}")
    
    def is_final_status(self) -> bool:
        """Check if order is in final status"""
        return self.current_status in [
            OrderStatus.FILLED, 
            OrderStatus.CANCELLED, 
            OrderStatus.EXPIRED
        ]
    
    def should_retry(self) -> bool:
        """Check if order should be retried"""
        return (
            not self.is_final_status() and 
            self.attempts < self.max_attempts and
            self.current_status == OrderStatus.REJECTED
        )


class RussianOrderManager:
    """Order management system for Russian market"""
    
    def __init__(self):
        self.brokers: Dict[str, RussianBrokerInterface] = {}
        self.primary_broker: Optional[str] = None
        self.backup_brokers: List[str] = []
        self.managed_orders: Dict[str, ManagedOrder] = {}  # order_id -> ManagedOrder
        self.order_queue: List[ManagedOrder] = []
        self.is_running = False
        self._processing_task: Optional[asyncio.Task] = None
    
    def add_broker(self, name: str, broker: RussianBrokerInterface, is_primary: bool = False):
        """
        Add a broker to the order manager
        
        Args:
            name: Broker identifier
            broker: Broker implementation
            is_primary: Whether this is the primary broker
        """
        self.brokers[name] = broker
        
        if is_primary:
            self.primary_broker = name
        else:
            if name not in self.backup_brokers:
                self.backup_brokers.append(name)
        
        logger.info(f"Added broker {name}, primary: {is_primary}")
    
    def remove_broker(self, name: str):
        """Remove a broker from the order manager"""
        if name in self.brokers:
            del self.brokers[name]
            
        if self.primary_broker == name:
            self.primary_broker = None
            
        if name in self.backup_brokers:
            self.backup_brokers.remove(name)
        
        logger.info(f"Removed broker {name}")
    
    async def authenticate_all_brokers(self, credentials: Dict[str, Dict[str, str]]) -> Dict[str, bool]:
        """
        Authenticate all brokers
        
        Args:
            credentials: Dict of broker_name -> credentials
            
        Returns:
            Dict of broker_name -> authentication_success
        """
        results = {}
        
        for broker_name, broker in self.brokers.items():
            if broker_name in credentials:
                try:
                    success = await broker.authenticate(credentials[broker_name])
                    results[broker_name] = success
                    logger.info(f"Broker {broker_name} authentication: {'success' if success else 'failed'}")
                except Exception as e:
                    results[broker_name] = False
                    logger.error(f"Broker {broker_name} authentication error: {e}")
            else:
                results[broker_name] = False
                logger.warning(f"No credentials provided for broker {broker_name}")
        
        return results
    
    def get_available_brokers(self) -> List[str]:
        """Get list of available (authenticated) brokers"""
        # This is a simplified check - in production, you'd want to verify authentication status
        return list(self.brokers.keys())
    
    async def submit_order(self, order: TradeOrder, priority: OrderPriority = OrderPriority.NORMAL) -> str:
        """
        Submit an order for execution
        
        Args:
            order: Trading order to execute
            priority: Order priority level
            
        Returns:
            Internal order ID
        """
        managed_order = ManagedOrder(order, priority)
        self.managed_orders[managed_order.order.order_id] = managed_order
        
        # Add to queue based on priority
        self._insert_order_by_priority(managed_order)
        
        logger.info(f"Submitted order {managed_order.order.order_id} with priority {priority.name}")
        
        # Start processing if not already running
        if not self.is_running:
            await self.start_processing()
        
        return managed_order.order.order_id
    
    def _insert_order_by_priority(self, managed_order: ManagedOrder):
        """Insert order into queue based on priority"""
        inserted = False
        for i, existing_order in enumerate(self.order_queue):
            if managed_order.priority.value > existing_order.priority.value:
                self.order_queue.insert(i, managed_order)
                inserted = True
                break
        
        if not inserted:
            self.order_queue.append(managed_order)
    
    async def start_processing(self):
        """Start order processing loop"""
        if self.is_running:
            return
        
        self.is_running = True
        self._processing_task = asyncio.create_task(self._process_orders())
        logger.info("Started order processing")
    
    async def stop_processing(self):
        """Stop order processing loop"""
        self.is_running = False
        
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped order processing")
    
    async def _process_orders(self):
        """Main order processing loop"""
        while self.is_running:
            try:
                if self.order_queue:
                    managed_order = self.order_queue.pop(0)
                    await self._execute_order(managed_order)
                else:
                    # No orders to process, wait a bit
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Error in order processing loop: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _execute_order(self, managed_order: ManagedOrder):
        """Execute a single order"""
        managed_order.attempts += 1
        
        # Determine which broker to use
        broker_name = self._select_broker_for_order(managed_order)
        
        if not broker_name:
            logger.error(f"No available broker for order {managed_order.order.order_id}")
            managed_order.current_status = OrderStatus.REJECTED
            managed_order.error_messages.append("No available broker")
            return
        
        broker = self.brokers[broker_name]
        
        try:
            # Validate order first
            validation = await broker.validate_order(managed_order.order)
            
            if not validation["valid"]:
                logger.warning(f"Order {managed_order.order.order_id} validation failed: {validation['errors']}")
                managed_order.current_status = OrderStatus.REJECTED
                managed_order.error_messages.extend(validation["errors"])
                return
            
            # Execute order
            result = await broker.place_order(managed_order.order)
            managed_order.add_execution_result(broker_name, result)
            
            logger.info(f"Order {managed_order.order.order_id} executed on {broker_name}: {result.status.name}")
            
            # If order failed and should be retried, add back to queue
            if managed_order.should_retry():
                logger.info(f"Retrying order {managed_order.order.order_id} (attempt {managed_order.attempts})")
                self._insert_order_by_priority(managed_order)
            
        except Exception as e:
            logger.error(f"Error executing order {managed_order.order.order_id} on {broker_name}: {e}")
            
            result = ExecutionResult(
                order_id="",
                status=OrderStatus.REJECTED,
                error_message=str(e),
                timestamp=datetime.now()
            )
            managed_order.add_execution_result(broker_name, result)
            
            # Retry if possible
            if managed_order.should_retry():
                self._insert_order_by_priority(managed_order)
    
    def _select_broker_for_order(self, managed_order: ManagedOrder) -> Optional[str]:
        """Select the best broker for an order"""
        # Try primary broker first
        if self.primary_broker and self.primary_broker in self.brokers:
            return self.primary_broker
        
        # Try backup brokers
        for broker_name in self.backup_brokers:
            if broker_name in self.brokers:
                return broker_name
        
        # Use any available broker
        if self.brokers:
            return list(self.brokers.keys())[0]
        
        return None
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        if order_id not in self.managed_orders:
            logger.warning(f"Order {order_id} not found")
            return False
        
        managed_order = self.managed_orders[order_id]
        
        # Remove from queue if still pending
        if managed_order in self.order_queue:
            self.order_queue.remove(managed_order)
            managed_order.current_status = OrderStatus.CANCELLED
            logger.info(f"Cancelled queued order {order_id}")
            return True
        
        # Cancel with brokers if already submitted
        success = False
        for broker_name, broker_order_id in managed_order.broker_order_ids.items():
            if broker_name in self.brokers:
                try:
                    broker = self.brokers[broker_name]
                    if await broker.cancel_order(broker_order_id):
                        success = True
                        logger.info(f"Cancelled order {order_id} on {broker_name}")
                except Exception as e:
                    logger.error(f"Error cancelling order {order_id} on {broker_name}: {e}")
        
        if success:
            managed_order.current_status = OrderStatus.CANCELLED
        
        return success
    
    async def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """Get current status of an order"""
        if order_id not in self.managed_orders:
            return None
        
        managed_order = self.managed_orders[order_id]
        
        # If order is still in queue, return pending
        if managed_order in self.order_queue:
            return OrderStatus.PENDING
        
        # Update status from brokers if not in final state
        if not managed_order.is_final_status():
            await self._update_order_status(managed_order)
        
        return managed_order.current_status
    
    async def _update_order_status(self, managed_order: ManagedOrder):
        """Update order status from brokers"""
        for broker_name, broker_order_id in managed_order.broker_order_ids.items():
            if broker_name in self.brokers:
                try:
                    broker = self.brokers[broker_name]
                    status = await broker.get_order_status(broker_order_id)
                    
                    if status:
                        managed_order.current_status = status
                        managed_order.updated_at = datetime.now()
                        
                        # If filled or cancelled, we can stop checking
                        if status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
                            break
                            
                except Exception as e:
                    logger.error(f"Error updating status for order {managed_order.order.order_id} on {broker_name}: {e}")
    
    def get_order_history(self, days: int = 30) -> List[ManagedOrder]:
        """Get order history"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        return [
            order for order in self.managed_orders.values()
            if order.created_at >= cutoff_date
        ]
    
    async def get_combined_portfolio(self) -> Optional[Portfolio]:
        """Get combined portfolio from primary broker"""
        if not self.primary_broker or self.primary_broker not in self.brokers:
            return None
        
        try:
            broker = self.brokers[self.primary_broker]
            return await broker.get_portfolio()
        except Exception as e:
            logger.error(f"Error getting portfolio from {self.primary_broker}: {e}")
            return None
    
    def get_order_statistics(self) -> Dict[str, Any]:
        """Get order execution statistics"""
        total_orders = len(self.managed_orders)
        
        if total_orders == 0:
            return {"total_orders": 0}
        
        status_counts = {}
        for order in self.managed_orders.values():
            status = order.current_status.name
            status_counts[status] = status_counts.get(status, 0) + 1
        
        filled_orders = status_counts.get("FILLED", 0)
        success_rate = (filled_orders / total_orders) * 100 if total_orders > 0 else 0
        
        return {
            "total_orders": total_orders,
            "status_breakdown": status_counts,
            "success_rate": round(success_rate, 2),
            "orders_in_queue": len(self.order_queue),
            "brokers_available": len(self.brokers)
        }
    
    async def close(self):
        """Close all broker connections"""
        await self.stop_processing()
        
        for broker in self.brokers.values():
            if hasattr(broker, 'close'):
                await broker.close()
        
        logger.info("Closed all broker connections")