"""
Transaction logging system for Russian regulatory compliance
Handles comprehensive trade logging, audit trails, and tax reporting
"""

import logging
import json
import hashlib
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
import uuid
import os
from pathlib import Path

from russian_trading_bot.models.trading import (
    TradeOrder, ExecutionResult, OrderStatus, Portfolio, Position
)


logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Transaction log levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    AUDIT = "audit"


class TransactionType(Enum):
    """Types of transactions to log"""
    ORDER_PLACED = "order_placed"
    ORDER_EXECUTED = "order_executed"
    ORDER_CANCELLED = "order_cancelled"
    ORDER_REJECTED = "order_rejected"
    PORTFOLIO_UPDATE = "portfolio_update"
    BALANCE_CHANGE = "balance_change"
    COMPLIANCE_CHECK = "compliance_check"
    SYSTEM_EVENT = "system_event"


class RussianTaxEvent(Enum):
    """Russian tax-relevant events"""
    STOCK_PURCHASE = "stock_purchase"
    STOCK_SALE = "stock_sale"
    DIVIDEND_RECEIVED = "dividend_received"
    COUPON_RECEIVED = "coupon_received"
    CURRENCY_EXCHANGE = "currency_exchange"
    BROKER_COMMISSION = "broker_commission"


class TransactionRecord:
    """Immutable transaction record for audit trail"""
    
    def __init__(self, 
                 transaction_id: str,
                 timestamp: datetime,
                 transaction_type: TransactionType,
                 level: LogLevel,
                 data: Dict[str, Any],
                 user_id: Optional[str] = None,
                 session_id: Optional[str] = None):
        """
        Initialize transaction record
        
        Args:
            transaction_id: Unique transaction identifier
            timestamp: Transaction timestamp
            transaction_type: Type of transaction
            level: Log level
            data: Transaction data
            user_id: Optional user identifier
            session_id: Optional session identifier
        """
        self._transaction_id = transaction_id
        self._timestamp = timestamp
        self._transaction_type = transaction_type
        self._level = level
        self._data = data.copy()  # Make a copy to prevent external modification
        self._user_id = user_id
        self._session_id = session_id
        
        # Generate hash for integrity verification
        self._hash = self._generate_hash()
    
    def _generate_hash(self) -> str:
        """Generate SHA-256 hash for record integrity"""
        record_string = f"{self._transaction_id}{self._timestamp.isoformat()}{self._transaction_type.value}{json.dumps(self._data, sort_keys=True, default=str)}"
        return hashlib.sha256(record_string.encode()).hexdigest()
    
    @property
    def transaction_id(self) -> str:
        return self._transaction_id
    
    @property
    def timestamp(self) -> datetime:
        return self._timestamp
    
    @property
    def transaction_type(self) -> TransactionType:
        return self._transaction_type
    
    @property
    def level(self) -> LogLevel:
        return self._level
    
    @property
    def data(self) -> Dict[str, Any]:
        return self._data.copy()  # Return copy to maintain immutability
    
    @property
    def user_id(self) -> Optional[str]:
        return self._user_id
    
    @property
    def session_id(self) -> Optional[str]:
        return self._session_id
    
    @property
    def hash(self) -> str:
        return self._hash
    
    def verify_integrity(self) -> bool:
        """Verify record integrity using hash"""
        return self._hash == self._generate_hash()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert record to dictionary for serialization"""
        return {
            "transaction_id": self._transaction_id,
            "timestamp": self._timestamp.isoformat(),
            "transaction_type": self._transaction_type.value,
            "level": self._level.value,
            "data": self._data,
            "user_id": self._user_id,
            "session_id": self._session_id,
            "hash": self._hash
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TransactionRecord':
        """Create record from dictionary"""
        return cls(
            transaction_id=data["transaction_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            transaction_type=TransactionType(data["transaction_type"]),
            level=LogLevel(data["level"]),
            data=data["data"],
            user_id=data.get("user_id"),
            session_id=data.get("session_id")
        )


class RussianTransactionLogger:
    """Transaction logger for Russian regulatory compliance"""
    
    def __init__(self, 
                 log_directory: str = "logs/transactions",
                 max_file_size_mb: int = 100,
                 retention_days: int = 2555,  # 7 years as required by Russian law
                 enable_encryption: bool = True):
        """
        Initialize transaction logger
        
        Args:
            log_directory: Directory for log files
            max_file_size_mb: Maximum log file size in MB
            retention_days: Log retention period in days (default 7 years)
            enable_encryption: Enable log encryption
        """
        self.log_directory = Path(log_directory)
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.retention_days = retention_days
        self.enable_encryption = enable_encryption
        
        # Create log directory if it doesn't exist
        self.log_directory.mkdir(parents=True, exist_ok=True)
        
        # Current session ID
        self.session_id = str(uuid.uuid4())
        
        # In-memory cache for recent transactions
        self.transaction_cache: List[TransactionRecord] = []
        self.cache_max_size = 1000
        
        # Initialize logging
        self._setup_file_logging()
        
        logger.info(f"Transaction logger initialized with session {self.session_id}")
    
    def _setup_file_logging(self):
        """Setup file-based logging"""
        log_file = self.log_directory / f"transactions_{datetime.now().strftime('%Y%m%d')}.log"
        
        # Configure file handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Create formatter for structured logging
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        
        # Add handler to logger
        transaction_logger = logging.getLogger('russian_trading_bot.transactions')
        transaction_logger.addHandler(file_handler)
        transaction_logger.setLevel(logging.INFO)
    
    def _generate_transaction_id(self) -> str:
        """Generate unique transaction ID"""
        return f"TXN_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:8]}"
    
    def log_transaction(self,
                       transaction_type: TransactionType,
                       data: Dict[str, Any],
                       level: LogLevel = LogLevel.INFO,
                       user_id: Optional[str] = None) -> str:
        """
        Log a transaction
        
        Args:
            transaction_type: Type of transaction
            data: Transaction data
            level: Log level
            user_id: Optional user identifier
            
        Returns:
            Transaction ID
        """
        transaction_id = self._generate_transaction_id()
        timestamp = datetime.now()
        
        # Create transaction record
        record = TransactionRecord(
            transaction_id=transaction_id,
            timestamp=timestamp,
            transaction_type=transaction_type,
            level=level,
            data=data,
            user_id=user_id,
            session_id=self.session_id
        )
        
        # Add to cache
        self.transaction_cache.append(record)
        if len(self.transaction_cache) > self.cache_max_size:
            self.transaction_cache.pop(0)
        
        # Log to file
        self._write_to_file(record)
        
        # Log to standard logger
        log_message = f"[{transaction_type.value}] {transaction_id}: {json.dumps(data, default=str)}"
        transaction_logger = logging.getLogger('russian_trading_bot.transactions')
        
        if level == LogLevel.ERROR:
            transaction_logger.error(log_message)
        elif level == LogLevel.WARNING:
            transaction_logger.warning(log_message)
        else:
            transaction_logger.info(log_message)
        
        return transaction_id
    
    def _write_to_file(self, record: TransactionRecord):
        """Write transaction record to file"""
        try:
            # Determine log file
            date_str = record.timestamp.strftime('%Y%m%d')
            log_file = self.log_directory / f"transactions_{date_str}.jsonl"
            
            # Check file size and rotate if necessary
            if log_file.exists() and log_file.stat().st_size > self.max_file_size_bytes:
                self._rotate_log_file(log_file)
            
            # Write record
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record.to_dict(), default=str) + '\n')
                
        except Exception as e:
            logger.error(f"Failed to write transaction record: {e}")
    
    def _rotate_log_file(self, log_file: Path):
        """Rotate log file when it gets too large"""
        timestamp = datetime.now().strftime('%H%M%S')
        rotated_file = log_file.with_suffix(f'.{timestamp}.jsonl')
        log_file.rename(rotated_file)
        logger.info(f"Rotated log file to {rotated_file}")
    
    def log_order_placed(self, order: TradeOrder, user_id: Optional[str] = None) -> str:
        """Log order placement"""
        data = {
            "order_id": order.order_id,
            "symbol": order.symbol,
            "action": order.action.value,
            "quantity": order.quantity,
            "order_type": order.order_type.value,
            "price": float(order.price) if order.price else None,
            "stop_price": float(order.stop_price) if order.stop_price else None,
            "currency": order.currency,
            "time_in_force": order.time_in_force
        }
        
        return self.log_transaction(
            TransactionType.ORDER_PLACED,
            data,
            LogLevel.INFO,
            user_id
        )
    
    def log_order_executed(self, order: TradeOrder, result: ExecutionResult, user_id: Optional[str] = None) -> str:
        """Log order execution"""
        data = {
            "order_id": order.order_id,
            "symbol": order.symbol,
            "action": order.action.value,
            "quantity": order.quantity,
            "executed_quantity": result.filled_quantity,
            "execution_price": float(result.average_price) if result.average_price else None,
            "commission": float(result.commission) if result.commission else None,
            "status": result.status.value,
            "broker_order_id": result.order_id,
            "execution_timestamp": result.timestamp.isoformat() if result.timestamp else None
        }
        
        return self.log_transaction(
            TransactionType.ORDER_EXECUTED,
            data,
            LogLevel.INFO,
            user_id
        )
    
    def log_order_cancelled(self, order_id: str, reason: str, user_id: Optional[str] = None) -> str:
        """Log order cancellation"""
        data = {
            "order_id": order_id,
            "cancellation_reason": reason
        }
        
        return self.log_transaction(
            TransactionType.ORDER_CANCELLED,
            data,
            LogLevel.INFO,
            user_id
        )
    
    def log_compliance_check(self, order: TradeOrder, validation_result: Dict[str, Any], user_id: Optional[str] = None) -> str:
        """Log compliance validation"""
        data = {
            "order_id": order.order_id,
            "symbol": order.symbol,
            "validation_result": validation_result
        }
        
        level = LogLevel.WARNING if not validation_result.get("valid", True) else LogLevel.INFO
        
        return self.log_transaction(
            TransactionType.COMPLIANCE_CHECK,
            data,
            level,
            user_id
        )
    
    def log_portfolio_update(self, portfolio: Portfolio, user_id: Optional[str] = None) -> str:
        """Log portfolio state update"""
        data = {
            "cash_balance": float(portfolio.cash_balance),
            "currency": portfolio.currency,
            "total_value": float(portfolio.total_value) if portfolio.total_value else None,
            "positions_count": len(portfolio.positions),
            "positions": {
                symbol: {
                    "quantity": pos.quantity,
                    "average_price": float(pos.average_price),
                    "current_price": float(pos.current_price) if pos.current_price else None,
                    "market_value": float(pos.market_value) if pos.market_value else None
                }
                for symbol, pos in portfolio.positions.items()
            }
        }
        
        return self.log_transaction(
            TransactionType.PORTFOLIO_UPDATE,
            data,
            LogLevel.INFO,
            user_id
        )
    
    def log_tax_event(self, 
                     tax_event: RussianTaxEvent,
                     symbol: str,
                     quantity: int,
                     price: Decimal,
                     commission: Optional[Decimal] = None,
                     user_id: Optional[str] = None) -> str:
        """Log tax-relevant event for Russian reporting"""
        data = {
            "tax_event": tax_event.value,
            "symbol": symbol,
            "quantity": quantity,
            "price": float(price),
            "commission": float(commission) if commission else None,
            "total_amount": float(quantity * price),
            "currency": "RUB"
        }
        
        return self.log_transaction(
            TransactionType.SYSTEM_EVENT,
            data,
            LogLevel.AUDIT,
            user_id
        )
    
    def get_transactions(self,
                        start_date: Optional[datetime] = None,
                        end_date: Optional[datetime] = None,
                        transaction_type: Optional[TransactionType] = None,
                        user_id: Optional[str] = None) -> List[TransactionRecord]:
        """
        Retrieve transactions based on filters
        
        Args:
            start_date: Start date filter
            end_date: End date filter
            transaction_type: Transaction type filter
            user_id: User ID filter
            
        Returns:
            List of matching transaction records
        """
        # First check cache for recent transactions
        results = []
        
        for record in self.transaction_cache:
            if self._matches_filters(record, start_date, end_date, transaction_type, user_id):
                results.append(record)
        
        # If we need older transactions, read from files
        if start_date and start_date < datetime.now() - timedelta(hours=1):
            file_results = self._read_from_files(start_date, end_date, transaction_type, user_id)
            results.extend(file_results)
        
        # Sort by timestamp
        results.sort(key=lambda x: x.timestamp)
        
        return results
    
    def _matches_filters(self,
                        record: TransactionRecord,
                        start_date: Optional[datetime],
                        end_date: Optional[datetime],
                        transaction_type: Optional[TransactionType],
                        user_id: Optional[str]) -> bool:
        """Check if record matches filters"""
        if start_date and record.timestamp < start_date:
            return False
        
        if end_date and record.timestamp > end_date:
            return False
        
        if transaction_type and record.transaction_type != transaction_type:
            return False
        
        if user_id and record.user_id != user_id:
            return False
        
        return True
    
    def _read_from_files(self,
                        start_date: Optional[datetime],
                        end_date: Optional[datetime],
                        transaction_type: Optional[TransactionType],
                        user_id: Optional[str]) -> List[TransactionRecord]:
        """Read transactions from log files"""
        results = []
        
        try:
            # Determine date range for files to check
            if start_date:
                current_date = start_date.date()
            else:
                current_date = datetime.now().date() - timedelta(days=30)
            
            if end_date:
                end_date_check = end_date.date()
            else:
                end_date_check = datetime.now().date()
            
            # Read from relevant log files
            while current_date <= end_date_check:
                date_str = current_date.strftime('%Y%m%d')
                log_files = list(self.log_directory.glob(f"transactions_{date_str}*.jsonl"))
                
                for log_file in log_files:
                    try:
                        with open(log_file, 'r', encoding='utf-8') as f:
                            for line in f:
                                if line.strip():
                                    record_data = json.loads(line)
                                    record = TransactionRecord.from_dict(record_data)
                                    
                                    if self._matches_filters(record, start_date, end_date, transaction_type, user_id):
                                        results.append(record)
                    except Exception as e:
                        logger.error(f"Error reading log file {log_file}: {e}")
                
                current_date += timedelta(days=1)
                
        except Exception as e:
            logger.error(f"Error reading transaction files: {e}")
        
        return results
    
    def generate_audit_report(self,
                             start_date: datetime,
                             end_date: datetime,
                             user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate audit report for Russian regulatory compliance
        
        Args:
            start_date: Report start date
            end_date: Report end date
            user_id: Optional user filter
            
        Returns:
            Comprehensive audit report
        """
        transactions = self.get_transactions(start_date, end_date, user_id=user_id)
        
        # Categorize transactions
        by_type = {}
        by_date = {}
        tax_events = []
        
        for record in transactions:
            # Group by type
            type_name = record.transaction_type.value
            if type_name not in by_type:
                by_type[type_name] = []
            by_type[type_name].append(record)
            
            # Group by date
            date_str = record.timestamp.strftime('%Y-%m-%d')
            if date_str not in by_date:
                by_date[date_str] = []
            by_date[date_str].append(record)
            
            # Collect tax events
            if record.transaction_type == TransactionType.ORDER_EXECUTED:
                tax_events.append(record)
        
        # Calculate statistics
        total_transactions = len(transactions)
        orders_placed = len(by_type.get('order_placed', []))
        orders_executed = len(by_type.get('order_executed', []))
        orders_cancelled = len(by_type.get('order_cancelled', []))
        
        # Verify integrity
        integrity_issues = []
        for record in transactions:
            if not record.verify_integrity():
                integrity_issues.append(record.transaction_id)
        
        return {
            "report_period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "summary": {
                "total_transactions": total_transactions,
                "orders_placed": orders_placed,
                "orders_executed": orders_executed,
                "orders_cancelled": orders_cancelled,
                "integrity_issues": len(integrity_issues)
            },
            "by_type": {k: len(v) for k, v in by_type.items()},
            "by_date": {k: len(v) for k, v in by_date.items()},
            "tax_events_count": len(tax_events),
            "integrity_issues": integrity_issues,
            "generated_at": datetime.now().isoformat(),
            "session_id": self.session_id
        }
    
    def cleanup_old_logs(self):
        """Clean up logs older than retention period"""
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        try:
            for log_file in self.log_directory.glob("transactions_*.jsonl"):
                # Extract date from filename
                try:
                    date_str = log_file.stem.split('_')[1][:8]  # YYYYMMDD
                    file_date = datetime.strptime(date_str, '%Y%m%d')
                    
                    if file_date < cutoff_date:
                        log_file.unlink()
                        logger.info(f"Deleted old log file: {log_file}")
                        
                except (ValueError, IndexError):
                    logger.warning(f"Could not parse date from log file: {log_file}")
                    
        except Exception as e:
            logger.error(f"Error during log cleanup: {e}")
    
    def export_for_tax_reporting(self,
                                year: int,
                                user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Export transactions for Russian tax reporting
        
        Args:
            year: Tax year
            user_id: Optional user filter
            
        Returns:
            Tax reporting data
        """
        start_date = datetime(year, 1, 1)
        end_date = datetime(year, 12, 31, 23, 59, 59)
        
        executed_orders = self.get_transactions(
            start_date, end_date, TransactionType.ORDER_EXECUTED, user_id
        )
        
        # Calculate capital gains/losses
        purchases = {}  # symbol -> list of purchases
        sales = []
        dividends = []
        commissions = Decimal(0)
        
        for record in executed_orders:
            data = record.data
            symbol = data.get('symbol')
            action = data.get('action')
            quantity = data.get('executed_quantity', 0)
            price = Decimal(str(data.get('execution_price', 0)))
            commission = Decimal(str(data.get('commission', 0)))
            
            commissions += commission
            
            if action == 'buy':
                if symbol not in purchases:
                    purchases[symbol] = []
                purchases[symbol].append({
                    'date': record.timestamp,
                    'quantity': quantity,
                    'price': price,
                    'commission': commission
                })
            elif action == 'sell':
                sales.append({
                    'date': record.timestamp,
                    'symbol': symbol,
                    'quantity': quantity,
                    'price': price,
                    'commission': commission
                })
        
        return {
            "tax_year": year,
            "user_id": user_id,
            "purchases": purchases,
            "sales": sales,
            "dividends": dividends,
            "total_commissions": float(commissions),
            "currency": "RUB",
            "generated_at": datetime.now().isoformat()
        }