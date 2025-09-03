"""
Paper Trading Engine for Russian Stock Market

This module implements a simulated trading system that uses live MOEX data
but executes trades in a virtual environment without real money.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import asyncio
import threading
import time
from enum import Enum
import json

from models.trading import TradingSignal, OrderAction, TradeOrder, ExecutionResult, Portfolio, Position
from models.market_data import RussianStock, MarketData
from services.portfolio_manager import PortfolioManager, PerformanceMetrics
from services.ai_decision_engine import AIDecisionEngine, MarketConditions

logger = logging.getLogger(__name__)


class PaperTradingStatus(Enum):
    """Paper trading system status"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class PaperTradingConfig:
    """Configuration for paper trading system"""
    initial_capital: Decimal = Decimal('1000000')  # 1M RUB
    commission_rate: float = 0.0005  # 0.05% commission
    slippage_rate: float = 0.001     # 0.1% slippage
    max_position_size: float = 0.1   # 10% max position
    min_confidence: float = 0.6      # Minimum signal confidence
    
    # Risk management
    stop_loss_pct: float = 0.05      # 5% stop loss
    take_profit_pct: float = 0.15    # 15% take profit
    max_drawdown_limit: float = 0.2  # 20% max drawdown
    max_daily_trades: int = 10       # Max trades per day
    
    # Timing settings
    update_interval: int = 30        # Seconds between updates
    market_hours_only: bool = True   # Trade only during MOEX hours
    
    # Strategy settings
    position_sizing_method: str = "equal_weight"  # equal_weight, confidence_weighted
    auto_execute: bool = True        # Auto-execute signals or require approval
    
    # Logging and reporting
    log_all_signals: bool = True     # Log all signals, not just executed ones
    daily_reports: bool = True       # Generate daily performance reports
    
    currency: str = "RUB"


@dataclass
class PaperTrade:
    """Individual paper trade record"""
    trade_id: str
    timestamp: datetime
    symbol: str
    action: OrderAction
    quantity: int
    price: Decimal
    commission: Decimal
    slippage: Decimal
    signal_confidence: float
    reasoning: str
    
    # Execution details
    execution_time: Optional[datetime] = None
    execution_price: Optional[Decimal] = None
    status: str = "pending"  # pending, executed, cancelled
    
    # Exit details (for tracking open positions)
    exit_time: Optional[datetime] = None
    exit_price: Optional[Decimal] = None
    exit_reason: str = ""  # stop_loss, take_profit, signal, manual
    
    # P&L tracking
    unrealized_pnl: Optional[Decimal] = None
    realized_pnl: Optional[Decimal] = None
    
    def calculate_pnl(self, current_price: Decimal) -> Decimal:
        """Calculate current P&L for the trade"""
        if self.status != "executed" or not self.execution_price:
            return Decimal('0')
        
        if self.exit_price:
            # Realized P&L
            if self.action == OrderAction.BUY:
                pnl = (self.exit_price - self.execution_price) * self.quantity
            else:  # SELL (short)
                pnl = (self.execution_price - self.exit_price) * self.quantity
            
            self.realized_pnl = pnl - self.commission - self.slippage
            return self.realized_pnl
        else:
            # Unrealized P&L
            if self.action == OrderAction.BUY:
                pnl = (current_price - self.execution_price) * self.quantity
            else:  # SELL (short)
                pnl = (self.execution_price - current_price) * self.quantity
            
            self.unrealized_pnl = pnl - self.commission - self.slippage
            return self.unrealized_pnl


@dataclass
class PaperTradingSession:
    """Paper trading session information"""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    config: Optional[PaperTradingConfig] = None
    
    # Performance tracking
    initial_capital: Decimal = Decimal('0')
    current_capital: Decimal = Decimal('0')
    total_pnl: Decimal = Decimal('0')
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    # Trade history
    trades: List[PaperTrade] = field(default_factory=list)
    daily_snapshots: List[Dict] = field(default_factory=list)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get session summary"""
        duration = (self.end_time or datetime.now()) - self.start_time
        
        return {
            'session_id': self.session_id,
            'duration_hours': duration.total_seconds() / 3600,
            'initial_capital': float(self.initial_capital),
            'current_capital': float(self.current_capital),
            'total_return': float((self.current_capital - self.initial_capital) / self.initial_capital) if self.initial_capital > 0 else 0.0,
            'total_pnl': float(self.total_pnl),
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.winning_trades / self.total_trades if self.total_trades > 0 else 0.0,
            'trades_per_hour': self.total_trades / (duration.total_seconds() / 3600) if duration.total_seconds() > 0 else 0.0
        }


class PaperTradingEngine:
    """
    Paper trading engine for Russian stock market.
    Simulates real trading with live data but without actual money.
    """
    
    def __init__(self, ai_engine: AIDecisionEngine, config: Optional[PaperTradingConfig] = None):
        self.ai_engine = ai_engine
        self.config = config or PaperTradingConfig()
        
        # System state
        self.status = PaperTradingStatus.STOPPED
        self.current_session: Optional[PaperTradingSession] = None
        self.portfolio_manager: Optional[PortfolioManager] = None
        
        # Data and execution
        self.market_data_provider: Optional[Callable] = None
        self.symbols: List[str] = []
        self.open_positions: Dict[str, PaperTrade] = {}
        self.pending_orders: Dict[str, PaperTrade] = {}
        
        # Threading for real-time operation
        self.trading_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Performance tracking
        self.daily_trades_count = 0
        self.last_trade_date: Optional[datetime] = None
        
        # Event callbacks
        self.on_trade_executed: Optional[Callable] = None
        self.on_position_closed: Optional[Callable] = None
        self.on_signal_generated: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        logger.info("Paper trading engine initialized")
    
    def set_market_data_provider(self, provider: Callable[[List[str]], Dict[str, MarketData]]):
        """
        Set market data provider function
        
        Args:
            provider: Function that takes symbol list and returns market data dict
        """
        self.market_data_provider = provider
        logger.info("Market data provider set")
    
    def set_symbols(self, symbols: List[str]):
        """Set symbols to trade"""
        self.symbols = symbols
        logger.info(f"Trading symbols set: {symbols}")
    
    def start_session(self, session_name: Optional[str] = None) -> str:
        """
        Start a new paper trading session
        
        Args:
            session_name: Optional session name
            
        Returns:
            Session ID
        """
        if self.status == PaperTradingStatus.RUNNING:
            raise ValueError("Trading session already running")
        
        if not self.market_data_provider:
            raise ValueError("Market data provider not set")
        
        if not self.symbols:
            raise ValueError("No symbols set for trading")
        
        # Create new session
        session_id = session_name or f"paper_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.current_session = PaperTradingSession(
            session_id=session_id,
            start_time=datetime.now(),
            config=self.config,
            initial_capital=self.config.initial_capital,
            current_capital=self.config.initial_capital
        )
        
        # Initialize portfolio manager
        self.portfolio_manager = PortfolioManager(self.config.initial_capital)
        
        # Reset counters
        self.daily_trades_count = 0
        self.last_trade_date = None
        self.open_positions.clear()
        self.pending_orders.clear()
        
        # Start trading thread
        self.stop_event.clear()
        self.trading_thread = threading.Thread(target=self._trading_loop, daemon=True)
        self.trading_thread.start()
        
        self.status = PaperTradingStatus.RUNNING
        
        logger.info(f"Paper trading session started: {session_id}")
        return session_id
    
    def stop_session(self):
        """Stop the current trading session"""
        if self.status != PaperTradingStatus.RUNNING:
            logger.warning("No active trading session to stop")
            return
        
        # Signal stop to trading thread
        self.stop_event.set()
        
        # Wait for thread to finish
        if self.trading_thread and self.trading_thread.is_alive():
            self.trading_thread.join(timeout=10)
        
        # Close all open positions
        if self.open_positions:
            self._close_all_positions("session_end")
        
        # Finalize session
        if self.current_session:
            self.current_session.end_time = datetime.now()
            self.current_session.current_capital = self.portfolio_manager.get_total_value()
            self.current_session.total_pnl = self.current_session.current_capital - self.current_session.initial_capital
        
        self.status = PaperTradingStatus.STOPPED
        
        logger.info("Paper trading session stopped")
    
    def pause_session(self):
        """Pause the current trading session"""
        if self.status == PaperTradingStatus.RUNNING:
            self.status = PaperTradingStatus.PAUSED
            logger.info("Paper trading session paused")
    
    def resume_session(self):
        """Resume the paused trading session"""
        if self.status == PaperTradingStatus.PAUSED:
            self.status = PaperTradingStatus.RUNNING
            logger.info("Paper trading session resumed")
    
    def _trading_loop(self):
        """Main trading loop running in separate thread"""
        logger.info("Trading loop started")
        
        try:
            while not self.stop_event.is_set():
                if self.status == PaperTradingStatus.RUNNING:
                    try:
                        # Check if we're in market hours
                        if self.config.market_hours_only and not self._is_market_hours():
                            time.sleep(60)  # Check every minute during off-hours
                            continue
                        
                        # Reset daily trade counter if new day
                        self._check_new_trading_day()
                        
                        # Get current market data
                        market_data = self._get_current_market_data()
                        
                        if not market_data:
                            time.sleep(self.config.update_interval)
                            continue
                        
                        # Update portfolio with current prices
                        self.portfolio_manager.update_market_prices(market_data)
                        
                        # Check exit conditions for open positions
                        self._check_exit_conditions(market_data)
                        
                        # Generate and process trading signals
                        if self.daily_trades_count < self.config.max_daily_trades:
                            self._process_trading_signals(market_data)
                        
                        # Update session statistics
                        self._update_session_stats()
                        
                        # Take portfolio snapshot
                        self.portfolio_manager.take_snapshot()
                        
                    except Exception as e:
                        logger.error(f"Error in trading loop: {e}")
                        if self.on_error:
                            self.on_error(e)
                        
                        # Set error status but continue running
                        self.status = PaperTradingStatus.ERROR
                        time.sleep(self.config.update_interval * 2)  # Wait longer on error
                        self.status = PaperTradingStatus.RUNNING
                
                # Sleep until next update
                time.sleep(self.config.update_interval)
                
        except Exception as e:
            logger.error(f"Fatal error in trading loop: {e}")
            self.status = PaperTradingStatus.ERROR
            if self.on_error:
                self.on_error(e)
        
        logger.info("Trading loop ended")
    
    def _is_market_hours(self) -> bool:
        """Check if current time is within MOEX trading hours"""
        now = datetime.now()
        
        # MOEX trading hours: 10:00 - 18:45 MSK, Monday-Friday
        if now.weekday() >= 5:  # Weekend
            return False
        
        # Convert to Moscow time (simplified - assumes local time is MSK)
        hour = now.hour
        minute = now.minute
        
        # Market opens at 10:00
        if hour < 10:
            return False
        
        # Market closes at 18:45
        if hour > 18 or (hour == 18 and minute > 45):
            return False
        
        return True
    
    def _check_new_trading_day(self):
        """Check if it's a new trading day and reset counters"""
        today = datetime.now().date()
        
        if self.last_trade_date != today:
            self.daily_trades_count = 0
            self.last_trade_date = today
            
            # Generate daily report if enabled
            if self.config.daily_reports and self.current_session:
                self._generate_daily_report()
    
    def _get_current_market_data(self) -> Optional[Dict[str, MarketData]]:
        """Get current market data for all symbols"""
        try:
            if self.market_data_provider:
                return self.market_data_provider(self.symbols)
            return None
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return None
    
    def _process_trading_signals(self, market_data: Dict[str, MarketData]):
        """Generate and process trading signals"""
        
        # Create mock market conditions (in real implementation, this would be calculated)
        market_conditions = MarketConditions(
            market_volatility=0.3,
            ruble_volatility=0.2,
            geopolitical_risk=0.4,
            market_trend="SIDEWAYS",
            trading_volume_ratio=1.0
        )
        
        for symbol in self.symbols:
            if symbol not in market_data:
                continue
            
            # Skip if we already have a position in this symbol
            if symbol in self.open_positions:
                continue
            
            try:
                # Generate signal using AI engine
                signal = self._generate_signal_for_symbol(symbol, market_data[symbol], market_conditions)
                
                if signal and signal.confidence >= self.config.min_confidence:
                    # Log signal if enabled
                    if self.config.log_all_signals and self.on_signal_generated:
                        self.on_signal_generated(signal)
                    
                    # Execute signal if auto-execution is enabled
                    if self.config.auto_execute:
                        self._execute_signal(signal, market_data[symbol])
                
            except Exception as e:
                logger.error(f"Error processing signal for {symbol}: {e}")
    
    def _generate_signal_for_symbol(self, symbol: str, market_data: MarketData, 
                                  market_conditions: MarketConditions) -> Optional[TradingSignal]:
        """Generate trading signal for a specific symbol"""
        
        # Mock technical indicators (in real implementation, calculate from historical data)
        from services.technical_analyzer import TechnicalIndicators
        import numpy as np
        
        indicators = TechnicalIndicators(
            rsi=50.0 + np.random.normal(0, 15),
            macd=np.random.normal(0, 0.5),
            macd_signal=np.random.normal(0, 0.5),
            sma_20=float(market_data.price) * (1 + np.random.normal(0, 0.02)),
            sma_50=float(market_data.price) * (1 + np.random.normal(0, 0.05)),
            bollinger_upper=float(market_data.price) * 1.02,
            bollinger_lower=float(market_data.price) * 0.98,
            bollinger_middle=float(market_data.price),
            stochastic_k=50.0 + np.random.normal(0, 20)
        )
        
        # Mock Russian stock info
        stock = RussianStock(
            symbol=symbol,
            name=f"Russian Company {symbol}",
            sector="GENERAL",
            currency="RUB"
        )
        
        # Generate signal
        return self.ai_engine.generate_trading_signal(
            symbol=symbol,
            stock=stock,
            market_data=market_data,
            technical_indicators=indicators,
            sentiments=[],  # No sentiment data in paper trading
            market_conditions=market_conditions,
            historical_volume=[market_data.volume] * 20  # Mock historical volume
        )
    
    def _execute_signal(self, signal: TradingSignal, market_data: MarketData):
        """Execute a trading signal"""
        
        # Calculate position size
        position_size = self._calculate_position_size(signal)
        
        if position_size <= 0:
            return
        
        # Calculate execution price with slippage
        slippage = market_data.price * Decimal(str(self.config.slippage_rate))
        
        if signal.action == OrderAction.BUY:
            execution_price = market_data.price + slippage
        else:
            execution_price = market_data.price - slippage
        
        # Calculate commission
        trade_value = execution_price * position_size
        commission = trade_value * Decimal(str(self.config.commission_rate))
        
        # Check if we have enough cash for buy orders
        total_cost = trade_value + commission
        if signal.action == OrderAction.BUY and total_cost > self.portfolio_manager.get_available_cash():
            logger.warning(f"Insufficient cash for {signal.symbol} trade: need {total_cost}, have {self.portfolio_manager.get_available_cash()}")
            return
        
        # Create paper trade
        trade_id = f"{signal.symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        paper_trade = PaperTrade(
            trade_id=trade_id,
            timestamp=datetime.now(),
            symbol=signal.symbol,
            action=signal.action,
            quantity=position_size,
            price=market_data.price,
            commission=commission,
            slippage=slippage,
            signal_confidence=signal.confidence,
            reasoning=signal.reasoning,
            execution_time=datetime.now(),
            execution_price=execution_price,
            status="executed"
        )
        
        # Execute in portfolio manager
        execution_result = ExecutionResult(
            order_id=trade_id,
            status="filled",
            filled_quantity=position_size,
            average_price=execution_price,
            commission=commission,
            timestamp=datetime.now()
        )
        
        order_details = {
            'symbol': signal.symbol,
            'action': signal.action,
            'quantity': position_size
        }
        
        self.portfolio_manager.update_position(execution_result, order_details)
        
        # Track the trade
        self.open_positions[signal.symbol] = paper_trade
        self.daily_trades_count += 1
        
        # Update session stats
        if self.current_session:
            self.current_session.trades.append(paper_trade)
            self.current_session.total_trades += 1
        
        # Trigger callback
        if self.on_trade_executed:
            self.on_trade_executed(paper_trade)
        
        logger.info(f"Executed paper trade: {signal.action.value} {position_size} {signal.symbol} at {execution_price} RUB")
    
    def _calculate_position_size(self, signal: TradingSignal) -> int:
        """Calculate position size based on configuration"""
        
        total_value = self.portfolio_manager.get_total_value()
        
        if self.config.position_sizing_method == "equal_weight":
            position_value = total_value * Decimal(str(self.config.max_position_size))
        elif self.config.position_sizing_method == "confidence_weighted":
            base_weight = self.config.max_position_size
            confidence_weight = base_weight * signal.confidence
            position_value = total_value * Decimal(str(confidence_weight))
        else:
            position_value = total_value * Decimal(str(self.config.max_position_size))
        
        # Convert to number of shares (assume 1 share per lot for simplicity)
        market_price = Decimal('100')  # This should come from market data
        position_size = int(position_value / market_price)
        
        return max(1, position_size)
    
    def _check_exit_conditions(self, market_data: Dict[str, MarketData]):
        """Check stop loss and take profit conditions for open positions"""
        
        positions_to_close = []
        
        for symbol, trade in self.open_positions.items():
            if symbol not in market_data:
                continue
            
            current_price = market_data[symbol].price
            entry_price = trade.execution_price
            
            if not entry_price:
                continue
            
            should_close = False
            exit_reason = ""
            
            if trade.action == OrderAction.BUY:
                # Long position
                pnl_pct = float((current_price - entry_price) / entry_price)
                
                if pnl_pct <= -self.config.stop_loss_pct:
                    should_close = True
                    exit_reason = "stop_loss"
                elif pnl_pct >= self.config.take_profit_pct:
                    should_close = True
                    exit_reason = "take_profit"
            else:
                # Short position
                pnl_pct = float((entry_price - current_price) / entry_price)
                
                if pnl_pct <= -self.config.stop_loss_pct:
                    should_close = True
                    exit_reason = "stop_loss"
                elif pnl_pct >= self.config.take_profit_pct:
                    should_close = True
                    exit_reason = "take_profit"
            
            if should_close:
                positions_to_close.append((symbol, exit_reason))
        
        # Close positions
        for symbol, exit_reason in positions_to_close:
            self._close_position(symbol, market_data[symbol], exit_reason)
    
    def _close_position(self, symbol: str, market_data: MarketData, exit_reason: str):
        """Close a specific position"""
        
        if symbol not in self.open_positions:
            return
        
        trade = self.open_positions[symbol]
        
        # Calculate exit price with slippage
        slippage = market_data.price * Decimal(str(self.config.slippage_rate))
        
        if trade.action == OrderAction.BUY:
            exit_price = market_data.price - slippage
        else:
            exit_price = market_data.price + slippage
        
        # Update trade record
        trade.exit_time = datetime.now()
        trade.exit_price = exit_price
        trade.exit_reason = exit_reason
        
        # Calculate final P&L
        final_pnl = trade.calculate_pnl(exit_price)
        
        # Update session stats
        if self.current_session:
            if final_pnl > 0:
                self.current_session.winning_trades += 1
            else:
                self.current_session.losing_trades += 1
        
        # Remove from open positions
        del self.open_positions[symbol]
        
        # Trigger callback
        if self.on_position_closed:
            self.on_position_closed(trade)
        
        logger.info(f"Closed {symbol} position: {final_pnl} RUB ({exit_reason})")
    
    def _close_all_positions(self, exit_reason: str):
        """Close all open positions"""
        
        if not self.market_data_provider:
            logger.warning("Cannot close positions: no market data provider")
            return
        
        try:
            market_data = self.market_data_provider(list(self.open_positions.keys()))
            
            symbols_to_close = list(self.open_positions.keys())
            for symbol in symbols_to_close:
                if symbol in market_data:
                    self._close_position(symbol, market_data[symbol], exit_reason)
                
        except Exception as e:
            logger.error(f"Error closing all positions: {e}")
    
    def _update_session_stats(self):
        """Update current session statistics"""
        if not self.current_session or not self.portfolio_manager:
            return
        
        self.current_session.current_capital = self.portfolio_manager.get_total_value()
        self.current_session.total_pnl = (
            self.current_session.current_capital - self.current_session.initial_capital
        )
    
    def _generate_daily_report(self):
        """Generate daily performance report"""
        if not self.current_session or not self.portfolio_manager:
            return
        
        try:
            # Get performance metrics
            performance = self.portfolio_manager.calculate_performance_metrics()
            
            # Create daily snapshot
            snapshot = {
                'date': datetime.now().date().isoformat(),
                'total_value': float(self.current_session.current_capital),
                'daily_pnl': float(self.current_session.total_pnl),
                'trades_today': self.daily_trades_count,
                'open_positions': len(self.open_positions),
                'performance_metrics': {
                    'total_return': performance.total_return,
                    'daily_return': performance.daily_return,
                    'sharpe_ratio': performance.sharpe_ratio,
                    'max_drawdown': performance.max_drawdown,
                    'win_rate': performance.win_rate
                }
            }
            
            self.current_session.daily_snapshots.append(snapshot)
            
            logger.info(f"Daily report generated: {snapshot['daily_pnl']:.2f} RUB P&L, {self.daily_trades_count} trades")
            
        except Exception as e:
            logger.error(f"Error generating daily report: {e}")
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current paper trading status"""
        
        status_info = {
            'status': self.status.value,
            'session_active': self.current_session is not None,
            'symbols_count': len(self.symbols),
            'open_positions': len(self.open_positions),
            'daily_trades': self.daily_trades_count,
            'max_daily_trades': self.config.max_daily_trades
        }
        
        if self.current_session and self.portfolio_manager:
            session_summary = self.current_session.get_summary()
            status_info.update(session_summary)
            
            # Add current portfolio info
            portfolio_summary = self.portfolio_manager.get_portfolio_summary()
            status_info['portfolio'] = portfolio_summary
        
        return status_info
    
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get information about open positions"""
        
        positions = []
        
        for symbol, trade in self.open_positions.items():
            # Get current market data for P&L calculation
            try:
                if self.market_data_provider:
                    market_data = self.market_data_provider([symbol])
                    current_price = market_data.get(symbol, {}).price if market_data else None
                else:
                    current_price = None
                
                current_pnl = trade.calculate_pnl(current_price) if current_price else Decimal('0')
                
                position_info = {
                    'trade_id': trade.trade_id,
                    'symbol': trade.symbol,
                    'action': trade.action.value,
                    'quantity': trade.quantity,
                    'entry_price': float(trade.execution_price) if trade.execution_price else None,
                    'current_price': float(current_price) if current_price else None,
                    'unrealized_pnl': float(current_pnl),
                    'entry_time': trade.execution_time.isoformat() if trade.execution_time else None,
                    'confidence': trade.signal_confidence,
                    'reasoning': trade.reasoning
                }
                
                positions.append(position_info)
                
            except Exception as e:
                logger.error(f"Error getting position info for {symbol}: {e}")
        
        return positions
    
    def get_trade_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get trade history"""
        
        if not self.current_session:
            return []
        
        trades = self.current_session.trades
        if limit:
            trades = trades[-limit:]
        
        trade_history = []
        
        for trade in trades:
            trade_info = {
                'trade_id': trade.trade_id,
                'timestamp': trade.timestamp.isoformat(),
                'symbol': trade.symbol,
                'action': trade.action.value,
                'quantity': trade.quantity,
                'entry_price': float(trade.execution_price) if trade.execution_price else None,
                'exit_price': float(trade.exit_price) if trade.exit_price else None,
                'exit_time': trade.exit_time.isoformat() if trade.exit_time else None,
                'exit_reason': trade.exit_reason,
                'realized_pnl': float(trade.realized_pnl) if trade.realized_pnl else None,
                'confidence': trade.signal_confidence,
                'status': trade.status
            }
            
            trade_history.append(trade_info)
        
        return trade_history
    
    def export_session_data(self, filename: Optional[str] = None) -> str:
        """Export current session data to JSON file"""
        
        if not self.current_session:
            raise ValueError("No active session to export")
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"paper_trading_session_{timestamp}.json"
        
        # Prepare export data
        export_data = {
            'session_info': self.current_session.get_summary(),
            'config': {
                'initial_capital': float(self.config.initial_capital),
                'commission_rate': self.config.commission_rate,
                'slippage_rate': self.config.slippage_rate,
                'max_position_size': self.config.max_position_size,
                'min_confidence': self.config.min_confidence,
                'stop_loss_pct': self.config.stop_loss_pct,
                'take_profit_pct': self.config.take_profit_pct
            },
            'trade_history': self.get_trade_history(),
            'daily_snapshots': self.current_session.daily_snapshots,
            'symbols': self.symbols
        }
        
        # Save to file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Session data exported to {filename}")
        return filename
    
    def manual_close_position(self, symbol: str, reason: str = "manual") -> bool:
        """Manually close a specific position"""
        
        if symbol not in self.open_positions:
            logger.warning(f"No open position for {symbol}")
            return False
        
        try:
            if self.market_data_provider:
                market_data = self.market_data_provider([symbol])
                if symbol in market_data:
                    self._close_position(symbol, market_data[symbol], reason)
                    return True
            
            logger.error(f"Could not get market data to close {symbol}")
            return False
            
        except Exception as e:
            logger.error(f"Error manually closing {symbol}: {e}")
            return False
    
    def manual_execute_signal(self, signal: TradingSignal) -> bool:
        """Manually execute a trading signal"""
        
        try:
            if self.market_data_provider:
                market_data = self.market_data_provider([signal.symbol])
                if signal.symbol in market_data:
                    self._execute_signal(signal, market_data[signal.symbol])
                    return True
            
            logger.error(f"Could not get market data to execute signal for {signal.symbol}")
            return False
            
        except Exception as e:
            logger.error(f"Error manually executing signal for {signal.symbol}: {e}")
            return False