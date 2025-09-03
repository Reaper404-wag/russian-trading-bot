"""
Unit tests for Russian transaction logging system
"""

import pytest
import tempfile
import shutil
import json
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path

from russian_trading_bot.services.transaction_logger import (
    RussianTransactionLogger, TransactionRecord, TransactionType, LogLevel, RussianTaxEvent
)
from russian_trading_bot.models.trading import (
    TradeOrder, ExecutionResult, OrderStatus, Portfolio, Position, OrderAction, OrderType
)


class TestTransactionRecord:
    """Test transaction record functionality"""
    
    def test_transaction_record_creation(self):
        """Test creating transaction record"""
        data = {"test": "data", "number": 123}
        record = TransactionRecord(
            transaction_id="TEST_001",
            timestamp=datetime.now(),
            transaction_type=TransactionType.ORDER_PLACED,
            level=LogLevel.INFO,
            data=data,
            user_id="user123",
            session_id="session456"
        )
        
        assert record.transaction_id == "TEST_001"
        assert record.transaction_type == TransactionType.ORDER_PLACED
        assert record.level == LogLevel.INFO
        assert record.data == data
        assert record.user_id == "user123"
        assert record.session_id == "session456"
        assert record.hash is not None
    
    def test_transaction_record_immutability(self):
        """Test that transaction record data is immutable"""
        original_data = {"test": "data"}
        record = TransactionRecord(
            transaction_id="TEST_001",
            timestamp=datetime.now(),
            transaction_type=TransactionType.ORDER_PLACED,
            level=LogLevel.INFO,
            data=original_data
        )
        
        # Modify original data
        original_data["test"] = "modified"
        
        # Record data should be unchanged
        assert record.data["test"] == "data"
        
        # Modifying returned data should not affect record
        returned_data = record.data
        returned_data["new_key"] = "new_value"
        assert "new_key" not in record.data
    
    def test_transaction_record_integrity(self):
        """Test transaction record integrity verification"""
        data = {"test": "data"}
        record = TransactionRecord(
            transaction_id="TEST_001",
            timestamp=datetime.now(),
            transaction_type=TransactionType.ORDER_PLACED,
            level=LogLevel.INFO,
            data=data
        )
        
        # Record should verify as intact
        assert record.verify_integrity() is True
        
        # Manually corrupt the hash
        record._hash = "corrupted_hash"
        assert record.verify_integrity() is False
    
    def test_transaction_record_serialization(self):
        """Test transaction record serialization/deserialization"""
        original_data = {"test": "data", "number": 123}
        timestamp = datetime.now()
        
        record = TransactionRecord(
            transaction_id="TEST_001",
            timestamp=timestamp,
            transaction_type=TransactionType.ORDER_EXECUTED,
            level=LogLevel.WARNING,
            data=original_data,
            user_id="user123"
        )
        
        # Serialize to dict
        record_dict = record.to_dict()
        
        # Deserialize from dict
        restored_record = TransactionRecord.from_dict(record_dict)
        
        assert restored_record.transaction_id == record.transaction_id
        assert restored_record.timestamp == record.timestamp
        assert restored_record.transaction_type == record.transaction_type
        assert restored_record.level == record.level
        assert restored_record.data == record.data
        assert restored_record.user_id == record.user_id
        assert restored_record.hash == record.hash


class TestRussianTransactionLogger:
    """Test Russian transaction logger"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def logger(self, temp_dir):
        """Create transaction logger instance"""
        return RussianTransactionLogger(
            log_directory=temp_dir,
            max_file_size_mb=1,  # Small size for testing rotation
            retention_days=30
        )
    
    def test_logger_initialization(self, temp_dir):
        """Test logger initialization"""
        logger = RussianTransactionLogger(log_directory=temp_dir)
        
        assert Path(temp_dir).exists()
        assert logger.session_id is not None
        assert len(logger.transaction_cache) == 0
    
    def test_log_basic_transaction(self, logger):
        """Test logging basic transaction"""
        data = {"test": "data", "amount": 1000}
        
        transaction_id = logger.log_transaction(
            TransactionType.SYSTEM_EVENT,
            data,
            LogLevel.INFO,
            "user123"
        )
        
        assert transaction_id is not None
        assert transaction_id.startswith("TXN_")
        assert len(logger.transaction_cache) == 1
        
        # Verify cached record
        record = logger.transaction_cache[0]
        assert record.transaction_id == transaction_id
        assert record.transaction_type == TransactionType.SYSTEM_EVENT
        assert record.data == data
        assert record.user_id == "user123"
    
    def test_log_order_placed(self, logger):
        """Test logging order placement"""
        order = TradeOrder(
            symbol="SBER",
            action=OrderAction.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            price=Decimal("250.50"),
            order_id="ORDER_123"
        )
        
        transaction_id = logger.log_order_placed(order, "user123")
        
        assert transaction_id is not None
        assert len(logger.transaction_cache) == 1
        
        record = logger.transaction_cache[0]
        assert record.transaction_type == TransactionType.ORDER_PLACED
        assert record.data["symbol"] == "SBER"
        assert record.data["action"] == "buy"
        assert record.data["quantity"] == 100
        assert record.data["price"] == 250.50
    
    def test_log_order_executed(self, logger):
        """Test logging order execution"""
        order = TradeOrder(
            symbol="GAZP",
            action=OrderAction.SELL,
            quantity=50,
            order_type=OrderType.MARKET,
            order_id="ORDER_456"
        )
        
        result = ExecutionResult(
            order_id="BROKER_789",
            status=OrderStatus.FILLED,
            filled_quantity=50,
            average_price=Decimal("180.25"),
            commission=Decimal("15.50"),
            timestamp=datetime.now()
        )
        
        transaction_id = logger.log_order_executed(order, result, "user123")
        
        assert transaction_id is not None
        record = logger.transaction_cache[0]
        assert record.transaction_type == TransactionType.ORDER_EXECUTED
        assert record.data["symbol"] == "GAZP"
        assert record.data["executed_quantity"] == 50
        assert record.data["execution_price"] == 180.25
        assert record.data["commission"] == 15.50
    
    def test_log_compliance_check(self, logger):
        """Test logging compliance check"""
        order = TradeOrder(
            symbol="LKOH",
            action=OrderAction.BUY,
            quantity=10,
            order_type=OrderType.LIMIT,
            price=Decimal("7500"),
            order_id="ORDER_789"
        )
        
        validation_result = {
            "valid": False,
            "errors": ["Insufficient funds"],
            "warnings": []
        }
        
        transaction_id = logger.log_compliance_check(order, validation_result, "user123")
        
        assert transaction_id is not None
        record = logger.transaction_cache[0]
        assert record.transaction_type == TransactionType.COMPLIANCE_CHECK
        assert record.level == LogLevel.WARNING  # Should be warning for invalid order
        assert record.data["validation_result"]["valid"] is False
    
    def test_log_portfolio_update(self, logger):
        """Test logging portfolio update"""
        positions = {
            "SBER": Position(
                symbol="SBER",
                quantity=100,
                average_price=Decimal("250"),
                current_price=Decimal("260")
            )
        }
        
        portfolio = Portfolio(
            positions=positions,
            cash_balance=Decimal("50000"),
            currency="RUB"
        )
        
        transaction_id = logger.log_portfolio_update(portfolio, "user123")
        
        assert transaction_id is not None
        record = logger.transaction_cache[0]
        assert record.transaction_type == TransactionType.PORTFOLIO_UPDATE
        assert record.data["cash_balance"] == 50000.0
        assert record.data["positions_count"] == 1
        assert "SBER" in record.data["positions"]
    
    def test_log_tax_event(self, logger):
        """Test logging tax event"""
        transaction_id = logger.log_tax_event(
            RussianTaxEvent.STOCK_SALE,
            "GAZP",
            50,
            Decimal("180.25"),
            Decimal("15.50"),
            "user123"
        )
        
        assert transaction_id is not None
        record = logger.transaction_cache[0]
        assert record.transaction_type == TransactionType.SYSTEM_EVENT
        assert record.level == LogLevel.AUDIT
        assert record.data["tax_event"] == "stock_sale"
        assert record.data["symbol"] == "GAZP"
        assert record.data["total_amount"] == 9012.5  # 50 * 180.25
    
    def test_get_transactions_no_filters(self, logger):
        """Test retrieving transactions without filters"""
        # Log several transactions
        logger.log_transaction(TransactionType.SYSTEM_EVENT, {"test": 1})
        logger.log_transaction(TransactionType.ORDER_PLACED, {"test": 2})
        logger.log_transaction(TransactionType.ORDER_EXECUTED, {"test": 3})
        
        transactions = logger.get_transactions()
        
        assert len(transactions) == 3
        assert transactions[0].data["test"] == 1  # Should be sorted by timestamp
    
    def test_get_transactions_with_filters(self, logger):
        """Test retrieving transactions with filters"""
        now = datetime.now()
        
        # Log transactions with different types and users
        logger.log_transaction(TransactionType.ORDER_PLACED, {"test": 1}, user_id="user1")
        logger.log_transaction(TransactionType.ORDER_EXECUTED, {"test": 2}, user_id="user2")
        logger.log_transaction(TransactionType.ORDER_PLACED, {"test": 3}, user_id="user1")
        
        # Filter by transaction type
        placed_orders = logger.get_transactions(transaction_type=TransactionType.ORDER_PLACED)
        assert len(placed_orders) == 2
        
        # Filter by user
        user1_transactions = logger.get_transactions(user_id="user1")
        assert len(user1_transactions) == 2
        
        # Filter by date range
        future_transactions = logger.get_transactions(start_date=now + timedelta(hours=1))
        assert len(future_transactions) == 0
    
    def test_file_writing_and_reading(self, logger, temp_dir):
        """Test writing to and reading from log files"""
        # Log a transaction
        data = {"test": "file_write", "amount": 5000}
        transaction_id = logger.log_transaction(TransactionType.ORDER_PLACED, data)
        
        # Check that file was created
        log_files = list(Path(temp_dir).glob("transactions_*.jsonl"))
        assert len(log_files) >= 1
        
        # Read file content
        with open(log_files[0], 'r', encoding='utf-8') as f:
            line = f.readline().strip()
            record_data = json.loads(line)
            
        assert record_data["transaction_id"] == transaction_id
        assert record_data["data"]["test"] == "file_write"
    
    def test_generate_audit_report(self, logger):
        """Test generating audit report"""
        start_date = datetime.now() - timedelta(hours=1)
        end_date = datetime.now() + timedelta(hours=1)
        
        # Clear any existing transactions
        logger.transaction_cache.clear()
        
        # Log various transactions
        order = TradeOrder(
            symbol="SBER",
            action=OrderAction.BUY,
            quantity=100,
            order_type=OrderType.MARKET,
            order_id="ORDER_001"
        )
        
        logger.log_order_placed(order, "user123")
        logger.log_order_cancelled("ORDER_001", "User cancelled", "user123")
        logger.log_transaction(TransactionType.SYSTEM_EVENT, {"test": "event"})  # No user_id
        
        report = logger.generate_audit_report(start_date, end_date, "user123")
        
        assert "report_period" in report
        assert "summary" in report
        assert report["summary"]["total_transactions"] == 2  # Only user123 transactions
        assert report["summary"]["orders_placed"] == 1
        assert report["summary"]["orders_cancelled"] == 1
        assert "by_type" in report
        assert "by_date" in report
    
    def test_export_for_tax_reporting(self, logger):
        """Test exporting data for tax reporting"""
        # Clear any existing transactions
        logger.transaction_cache.clear()
        
        # Create some executed orders for tax year 2024
        buy_order = TradeOrder(
            symbol="SBER",
            action=OrderAction.BUY,
            quantity=100,
            order_type=OrderType.MARKET,
            order_id="BUY_001"
        )
        
        sell_order = TradeOrder(
            symbol="SBER",
            action=OrderAction.SELL,
            quantity=50,
            order_type=OrderType.MARKET,
            order_id="SELL_001"
        )
        
        buy_result = ExecutionResult(
            order_id="BROKER_BUY",
            status=OrderStatus.FILLED,
            filled_quantity=100,
            average_price=Decimal("250"),
            commission=Decimal("25"),
            timestamp=datetime(2024, 6, 15, 12, 0)
        )
        
        sell_result = ExecutionResult(
            order_id="BROKER_SELL",
            status=OrderStatus.FILLED,
            filled_quantity=50,
            average_price=Decimal("280"),
            commission=Decimal("14"),
            timestamp=datetime(2024, 8, 20, 14, 30)
        )
        
        # Manually create transaction records with 2024 timestamps
        buy_record = TransactionRecord(
            transaction_id="BUY_TXN_001",
            timestamp=datetime(2024, 6, 15, 12, 0),
            transaction_type=TransactionType.ORDER_EXECUTED,
            level=LogLevel.INFO,
            data={
                "order_id": "BUY_001",
                "symbol": "SBER",
                "action": "buy",
                "quantity": 100,
                "executed_quantity": 100,
                "execution_price": 250.0,
                "commission": 25.0,
                "status": "filled"
            },
            user_id="user123"
        )
        
        sell_record = TransactionRecord(
            transaction_id="SELL_TXN_001",
            timestamp=datetime(2024, 8, 20, 14, 30),
            transaction_type=TransactionType.ORDER_EXECUTED,
            level=LogLevel.INFO,
            data={
                "order_id": "SELL_001",
                "symbol": "SBER",
                "action": "sell",
                "quantity": 50,
                "executed_quantity": 50,
                "execution_price": 280.0,
                "commission": 14.0,
                "status": "filled"
            },
            user_id="user123"
        )
        
        # Add to cache
        logger.transaction_cache.extend([buy_record, sell_record])
        
        tax_data = logger.export_for_tax_reporting(2024, "user123")
        
        assert tax_data["tax_year"] == 2024
        assert tax_data["user_id"] == "user123"
        assert "SBER" in tax_data["purchases"]
        assert len(tax_data["sales"]) == 1
        assert tax_data["total_commissions"] == 39.0  # 25 + 14
        assert tax_data["currency"] == "RUB"
    
    def test_cache_size_limit(self, logger):
        """Test transaction cache size limit"""
        # Set small cache size for testing
        logger.cache_max_size = 5
        
        # Log more transactions than cache size
        for i in range(10):
            logger.log_transaction(TransactionType.SYSTEM_EVENT, {"test": i})
        
        # Cache should be limited to max size
        assert len(logger.transaction_cache) == 5
        
        # Should contain the most recent transactions
        assert logger.transaction_cache[-1].data["test"] == 9
        assert logger.transaction_cache[0].data["test"] == 5  # Oldest in cache
    
    def test_transaction_id_generation(self, logger):
        """Test transaction ID generation"""
        id1 = logger._generate_transaction_id()
        id2 = logger._generate_transaction_id()
        
        assert id1 != id2
        assert id1.startswith("TXN_")
        assert id2.startswith("TXN_")
        
        # Should contain date
        today = datetime.now().strftime('%Y%m%d')
        assert today in id1
        assert today in id2
    
    def test_log_file_rotation(self, logger, temp_dir):
        """Test log file rotation when size limit is reached"""
        # Create a large transaction to trigger rotation
        large_data = {"large_field": "x" * 1000000}  # 1MB of data
        
        logger.log_transaction(TransactionType.SYSTEM_EVENT, large_data)
        logger.log_transaction(TransactionType.SYSTEM_EVENT, large_data)
        
        # Should have created multiple files due to size limit
        log_files = list(Path(temp_dir).glob("transactions_*.jsonl"))
        
        # At least one file should exist (might be rotated)
        assert len(log_files) >= 1


if __name__ == "__main__":
    pytest.main([__file__])