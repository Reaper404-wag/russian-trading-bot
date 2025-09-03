"""
Backtesting Engine for Russian Stock Market

This module implements a comprehensive backtesting system using historical MOEX data
to validate trading strategies and compare performance against Russian market indices.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import pandas as pd
import numpy as np
from enum import Enum

from models.trading import TradingSignal, OrderAction, TradeOrder, ExecutionResult, Portfolio, Position
from models.market_data import RussianStock, MarketData
from services.portfolio_manager import PortfolioManager, PerformanceMetrics
from services.ai_decision_engine import AIDecisionEngine, MarketConditions

logger = logging.getLogger(__name__)


class BacktestStatus(Enum):
    """Backtesting status"""
    NOT_STARTED = "not_started"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class BacktestConfig:
    """Configuration for backtesting"""
    start_date: datetime
    end_date: datetime
    initial_capital: Decimal = Decimal('1000000')  # 1M RUB
    commission_rate: float = 0.0005  # 0.05% commission
    slippage_rate: float = 0.001     # 0.1% slippage
    max_position_size: float = 0.1   # 10% max position
    rebalance_frequency: str = "daily"  # daily, weekly, monthly
    benchmark_symbol: str = "IMOEX"  # MOEX Russia Index
    currency: str = "RUB"
    
    # Risk management settings
    stop_loss_pct: float = 0.05      # 5% stop loss
    take_profit_pct: float = 0.15    # 15% take profit
    max_drawdown_limit: float = 0.2  # 20% max drawdown
    
    # Strategy settings
    min_confidence: float = 0.6      # Minimum signal confidence
    position_sizing_method: str = "equal_weight"  # equal_weight, risk_parity, kelly


@dataclass
class BacktestTrade:
    """Individual trade in backtest"""
    entry_date: datetime
    exit_date: Optional[datetime]
    symbol: str
    action: OrderAction
    entry_price: Decimal
    exit_price: Optional[Decimal]
    quantity: int
    commission: Decimal
    slippage: Decimal
    pnl: Optional[Decimal] = None
    pnl_pct: Optional[float] = None
    duration_days: Optional[int] = None
    exit_reason: str = ""  # stop_loss, take_profit, signal, end_of_backtest
    
    def __post_init__(self):
        """Calculate derived values"""
        if self.exit_price and self.exit_date:
            if self.action == OrderAction.BUY:
                self.pnl = (self.exit_price - self.entry_price) * self.quantity - self.commission - self.slippage
                self.pnl_pct = float((self.exit_price - self.entry_price) / self.entry_price)
            else:  # SELL (short)
                self.pnl = (self.entry_price - self.exit_price) * self.quantity - self.commission - self.slippage
                self.pnl_pct = float((self.entry_price - self.exit_price) / self.entry_price)
            
            self.duration_days = (self.exit_date - self.entry_date).days


@dataclass
class BacktestResults:
    """Comprehensive backtesting results"""
    config: BacktestConfig
    start_date: datetime
    end_date: datetime
    duration_days: int
    
    # Portfolio metrics
    initial_capital: Decimal
    final_capital: Decimal
    total_return: float
    annual_return: float
    
    # Performance metrics
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    volatility: float
    
    # Trading metrics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    avg_win: Decimal
    avg_loss: Decimal
    
    # Benchmark comparison
    benchmark_return: float
    alpha: float
    beta: float
    information_ratio: float
    
    # Trade details
    trades: List[BacktestTrade] = field(default_factory=list)
    daily_returns: List[float] = field(default_factory=list)
    portfolio_values: List[Tuple[datetime, Decimal]] = field(default_factory=list)
    
    # Russian market specific
    ruble_adjusted_return: Optional[float] = None
    sector_performance: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert results to dictionary for serialization"""
        return {
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'duration_days': self.duration_days,
            'initial_capital': float(self.initial_capital),
            'final_capital': float(self.final_capital),
            'total_return': self.total_return,
            'annual_return': self.annual_return,
            'sharpe_ratio': self.sharpe_ratio,
            'sortino_ratio': self.sortino_ratio,
            'max_drawdown': self.max_drawdown,
            'volatility': self.volatility,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'profit_factor': self.profit_factor,
            'avg_win': float(self.avg_win),
            'avg_loss': float(self.avg_loss),
            'benchmark_return': self.benchmark_return,
            'alpha': self.alpha,
            'beta': self.beta,
            'information_ratio': self.information_ratio,
            'ruble_adjusted_return': self.ruble_adjusted_return,
            'sector_performance': self.sector_performance,
            'trade_count': len(self.trades)
        }


class BacktestingEngine:
    """
    Comprehensive backtesting engine for Russian stock market strategies.
    Supports historical MOEX data, multiple strategies, and detailed performance analysis.
    """
    
    def __init__(self, ai_engine: AIDecisionEngine):
        self.ai_engine = ai_engine
        self.status = BacktestStatus.NOT_STARTED
        self.current_backtest: Optional[BacktestResults] = None
        
        # Historical data cache
        self.historical_data: Dict[str, pd.DataFrame] = {}
        self.benchmark_data: Dict[str, pd.DataFrame] = {}
        
        logger.info("Backtesting engine initialized")
    
    def load_historical_data(self, symbols: List[str], start_date: datetime, 
                           end_date: datetime) -> bool:
        """
        Load historical MOEX data for backtesting
        
        Args:
            symbols: List of stock symbols
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            True if data loaded successfully
        """
        try:
            # In a real implementation, this would load from MOEX API or database
            # For now, we'll simulate the data structure
            
            for symbol in symbols:
                # Generate sample historical data
                date_range = pd.date_range(start=start_date, end=end_date, freq='D')
                
                # Filter for Russian trading days (Monday-Friday, excluding holidays)
                trading_days = [d for d in date_range if d.weekday() < 5]
                
                # Simulate price data with realistic Russian market characteristics
                np.random.seed(hash(symbol) % 2**32)  # Consistent seed per symbol
                
                base_price = 100.0
                returns = np.random.normal(0.0005, 0.025, len(trading_days))  # Higher volatility for Russian market
                prices = [base_price]
                
                for ret in returns:
                    prices.append(prices[-1] * (1 + ret))
                
                # Create DataFrame with OHLCV data
                df = pd.DataFrame({
                    'date': trading_days,
                    'open': prices[:-1],
                    'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices[:-1]],
                    'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices[:-1]],
                    'close': prices[1:],
                    'volume': np.random.randint(10000, 1000000, len(trading_days)),
                    'currency': 'RUB'
                })
                
                df.set_index('date', inplace=True)
                self.historical_data[symbol] = df
                
                logger.debug(f"Loaded {len(df)} days of data for {symbol}")
            
            # Load benchmark data (MOEX indices)
            self._load_benchmark_data(start_date, end_date)
            
            logger.info(f"Historical data loaded for {len(symbols)} symbols")
            return True
            
        except Exception as e:
            logger.error(f"Error loading historical data: {e}")
            return False
    
    def _load_benchmark_data(self, start_date: datetime, end_date: datetime):
        """Load Russian market benchmark data"""
        benchmarks = ['IMOEX', 'RTSI', 'MOEXBMI']  # MOEX Russia, RTS, MOEX BMI
        
        for benchmark in benchmarks:
            date_range = pd.date_range(start=start_date, end=end_date, freq='D')
            trading_days = [d for d in date_range if d.weekday() < 5]
            
            # Simulate benchmark returns (typically lower volatility than individual stocks)
            np.random.seed(hash(benchmark) % 2**32)
            returns = np.random.normal(0.0003, 0.015, len(trading_days))
            
            base_value = 3000.0  # Typical MOEX index level
            values = [base_value]
            
            for ret in returns:
                values.append(values[-1] * (1 + ret))
            
            df = pd.DataFrame({
                'date': trading_days,
                'close': values[1:],
                'return': returns
            })
            
            df.set_index('date', inplace=True)
            self.benchmark_data[benchmark] = df
    
    def run_backtest(self, config: BacktestConfig, symbols: List[str],
                    strategy_name: str = "AI_Multi_Factor") -> BacktestResults:
        """
        Run comprehensive backtest with given configuration
        
        Args:
            config: Backtesting configuration
            symbols: List of symbols to trade
            strategy_name: Name of the strategy being tested
            
        Returns:
            BacktestResults with comprehensive analysis
        """
        try:
            self.status = BacktestStatus.RUNNING
            logger.info(f"Starting backtest: {strategy_name} from {config.start_date} to {config.end_date}")
            
            # Load historical data if not already loaded
            if not self.historical_data:
                if not self.load_historical_data(symbols, config.start_date, config.end_date):
                    raise ValueError("Failed to load historical data")
            
            # Initialize portfolio manager
            portfolio_manager = PortfolioManager(config.initial_capital)
            
            # Initialize results tracking
            results = BacktestResults(
                config=config,
                start_date=config.start_date,
                end_date=config.end_date,
                duration_days=(config.end_date - config.start_date).days,
                initial_capital=config.initial_capital,
                final_capital=config.initial_capital,
                total_return=0.0,
                annual_return=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                max_drawdown=0.0,
                volatility=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                profit_factor=0.0,
                avg_win=Decimal('0'),
                avg_loss=Decimal('0'),
                benchmark_return=0.0,
                alpha=0.0,
                beta=0.0,
                information_ratio=0.0
            )
            
            # Get trading dates
            all_dates = set()
            for symbol_data in self.historical_data.values():
                all_dates.update(symbol_data.index)
            
            trading_dates = sorted(list(all_dates))
            trading_dates = [d for d in trading_dates if config.start_date <= d <= config.end_date]
            
            # Track open positions
            open_positions: Dict[str, BacktestTrade] = {}
            
            # Main backtesting loop
            for i, current_date in enumerate(trading_dates):
                try:
                    # Get market data for current date
                    current_market_data = self._get_market_data_for_date(current_date, symbols)
                    
                    if not current_market_data:
                        continue
                    
                    # Update portfolio with current prices
                    portfolio_manager.update_market_prices(current_market_data)
                    
                    # Take portfolio snapshot
                    snapshot = portfolio_manager.take_snapshot()
                    results.portfolio_values.append((current_date, snapshot.total_value))
                    
                    # Calculate daily return
                    if i > 0:
                        prev_value = results.portfolio_values[i-1][1]
                        daily_return = float((snapshot.total_value - prev_value) / prev_value)
                        results.daily_returns.append(daily_return)
                    
                    # Check stop losses and take profits for open positions
                    self._check_exit_conditions(open_positions, current_market_data, 
                                              config, current_date, results)
                    
                    # Generate trading signals
                    if i >= 20:  # Need some history for indicators
                        signals = self._generate_signals_for_date(
                            current_date, symbols, current_market_data, config
                        )
                        
                        # Execute trades based on signals
                        self._execute_signals(signals, current_market_data, config, 
                                            current_date, portfolio_manager, 
                                            open_positions, results)
                    
                    # Risk management: check max drawdown
                    current_drawdown = self._calculate_current_drawdown(results.portfolio_values)
                    if current_drawdown > config.max_drawdown_limit:
                        logger.warning(f"Max drawdown limit reached: {current_drawdown:.2%}")
                        # Close all positions
                        self._close_all_positions(open_positions, current_market_data, 
                                                current_date, results, "max_drawdown")
                
                except Exception as e:
                    logger.error(f"Error processing date {current_date}: {e}")
                    continue
            
            # Close any remaining open positions at end of backtest
            if open_positions:
                final_market_data = self._get_market_data_for_date(trading_dates[-1], symbols)
                self._close_all_positions(open_positions, final_market_data, 
                                        trading_dates[-1], results, "end_of_backtest")
            
            # Calculate final results
            results.final_capital = portfolio_manager.get_total_value()
            self._calculate_final_metrics(results, config)
            
            self.current_backtest = results
            self.status = BacktestStatus.COMPLETED
            
            logger.info(f"Backtest completed. Total return: {results.total_return:.2%}, "
                       f"Sharpe ratio: {results.sharpe_ratio:.2f}")
            
            return results
            
        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            self.status = BacktestStatus.FAILED
            raise
    
    def _get_market_data_for_date(self, date: datetime, symbols: List[str]) -> Dict[str, MarketData]:
        """Get market data for all symbols on a specific date"""
        market_data = {}
        
        for symbol in symbols:
            if symbol in self.historical_data:
                df = self.historical_data[symbol]
                
                # Find the closest trading date
                available_dates = df.index
                closest_date = min(available_dates, key=lambda x: abs((x - date).days))
                
                if abs((closest_date - date).days) <= 3:  # Within 3 days
                    row = df.loc[closest_date]
                    
                    market_data[symbol] = MarketData(
                        symbol=symbol,
                        timestamp=closest_date,
                        price=Decimal(str(row['close'])),
                        volume=int(row['volume']),
                        bid=Decimal(str(row['close'] * 0.999)),  # Approximate bid
                        ask=Decimal(str(row['close'] * 1.001)),  # Approximate ask
                        currency="RUB"
                    )
        
        return market_data
    
    def _generate_signals_for_date(self, date: datetime, symbols: List[str],
                                 market_data: Dict[str, MarketData],
                                 config: BacktestConfig) -> List[TradingSignal]:
        """Generate trading signals for a specific date"""
        signals = []
        
        # Create mock market conditions (in real implementation, this would be calculated)
        market_conditions = MarketConditions(
            market_volatility=0.3,
            ruble_volatility=0.2,
            geopolitical_risk=0.4,
            market_trend="SIDEWAYS",
            trading_volume_ratio=1.0
        )
        
        for symbol in symbols:
            if symbol not in market_data:
                continue
            
            try:
                # Get historical data for technical analysis
                historical_data = self.historical_data[symbol]
                recent_data = historical_data[historical_data.index <= date].tail(50)
                
                if len(recent_data) < 20:
                    continue
                
                # Calculate technical indicators (simplified)
                from services.technical_analyzer import TechnicalIndicators
                
                # Mock technical indicators (in real implementation, calculate from data)
                indicators = TechnicalIndicators(
                    rsi=50.0 + np.random.normal(0, 15),
                    macd=np.random.normal(0, 0.5),
                    macd_signal=np.random.normal(0, 0.5),
                    sma_20=float(recent_data['close'].rolling(20).mean().iloc[-1]),
                    sma_50=float(recent_data['close'].rolling(50).mean().iloc[-1]) if len(recent_data) >= 50 else None,
                    bollinger_upper=float(recent_data['close'].rolling(20).mean().iloc[-1] * 1.02),
                    bollinger_lower=float(recent_data['close'].rolling(20).mean().iloc[-1] * 0.98),
                    bollinger_middle=float(recent_data['close'].rolling(20).mean().iloc[-1]),
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
                signal = self.ai_engine.generate_trading_signal(
                    symbol=symbol,
                    stock=stock,
                    market_data=market_data[symbol],
                    technical_indicators=indicators,
                    sentiments=[],  # No sentiment data in backtest
                    market_conditions=market_conditions,
                    historical_volume=recent_data['volume'].tolist()
                )
                
                # Only include signals above minimum confidence
                if signal.confidence >= config.min_confidence:
                    signals.append(signal)
                
            except Exception as e:
                logger.error(f"Error generating signal for {symbol} on {date}: {e}")
                continue
        
        return signals
    
    def _execute_signals(self, signals: List[TradingSignal], 
                        market_data: Dict[str, MarketData],
                        config: BacktestConfig, date: datetime,
                        portfolio_manager: PortfolioManager,
                        open_positions: Dict[str, BacktestTrade],
                        results: BacktestResults):
        """Execute trading signals"""
        
        for signal in signals:
            symbol = signal.symbol
            
            if symbol not in market_data:
                continue
            
            # Skip if we already have a position in this symbol
            if symbol in open_positions:
                continue
            
            # Calculate position size
            position_size = self._calculate_position_size(
                signal, portfolio_manager.get_total_value(), config
            )
            
            if position_size <= 0:
                continue
            
            # Calculate execution price with slippage
            market_price = market_data[symbol].price
            slippage = market_price * Decimal(str(config.slippage_rate))
            
            if signal.action == OrderAction.BUY:
                execution_price = market_price + slippage
            else:
                execution_price = market_price - slippage
            
            # Calculate commission
            trade_value = execution_price * position_size
            commission = trade_value * Decimal(str(config.commission_rate))
            
            # Check if we have enough cash
            total_cost = trade_value + commission
            if signal.action == OrderAction.BUY and total_cost > portfolio_manager.get_available_cash():
                continue
            
            # Create trade record
            trade = BacktestTrade(
                entry_date=date,
                exit_date=None,
                symbol=symbol,
                action=signal.action,
                entry_price=execution_price,
                exit_price=None,
                quantity=position_size,
                commission=commission,
                slippage=slippage
            )
            
            # Execute trade in portfolio
            execution_result = ExecutionResult(
                order_id=f"backtest_{symbol}_{date.strftime('%Y%m%d')}",
                status="filled",
                filled_quantity=position_size,
                average_price=execution_price,
                commission=commission,
                timestamp=date
            )
            
            order_details = {
                'symbol': symbol,
                'action': signal.action,
                'quantity': position_size
            }
            
            portfolio_manager.update_position(execution_result, order_details)
            
            # Track open position
            open_positions[symbol] = trade
            results.total_trades += 1
            
            logger.debug(f"Executed {signal.action.value} {position_size} {symbol} at {execution_price}")
    
    def _calculate_position_size(self, signal: TradingSignal, total_value: Decimal,
                               config: BacktestConfig) -> int:
        """Calculate position size based on configuration"""
        
        if config.position_sizing_method == "equal_weight":
            # Equal weight across all positions
            position_value = total_value * Decimal(str(config.max_position_size))
            
        elif config.position_sizing_method == "confidence_weighted":
            # Weight by signal confidence
            base_weight = config.max_position_size
            confidence_weight = base_weight * signal.confidence
            position_value = total_value * Decimal(str(confidence_weight))
            
        else:
            # Default to equal weight
            position_value = total_value * Decimal(str(config.max_position_size))
        
        # Convert to number of shares (Russian stocks trade in lots)
        # Assume 1 share per lot for simplicity
        market_price = Decimal('100')  # This should come from market data
        position_size = int(position_value / market_price)
        
        return max(1, position_size)  # At least 1 share
    
    def _check_exit_conditions(self, open_positions: Dict[str, BacktestTrade],
                             market_data: Dict[str, MarketData],
                             config: BacktestConfig, date: datetime,
                             results: BacktestResults):
        """Check stop loss and take profit conditions"""
        
        positions_to_close = []
        
        for symbol, trade in open_positions.items():
            if symbol not in market_data:
                continue
            
            current_price = market_data[symbol].price
            entry_price = trade.entry_price
            
            should_close = False
            exit_reason = ""
            
            if trade.action == OrderAction.BUY:
                # Long position
                pnl_pct = float((current_price - entry_price) / entry_price)
                
                if pnl_pct <= -config.stop_loss_pct:
                    should_close = True
                    exit_reason = "stop_loss"
                elif pnl_pct >= config.take_profit_pct:
                    should_close = True
                    exit_reason = "take_profit"
            
            else:
                # Short position
                pnl_pct = float((entry_price - current_price) / entry_price)
                
                if pnl_pct <= -config.stop_loss_pct:
                    should_close = True
                    exit_reason = "stop_loss"
                elif pnl_pct >= config.take_profit_pct:
                    should_close = True
                    exit_reason = "take_profit"
            
            if should_close:
                positions_to_close.append((symbol, exit_reason))
        
        # Close positions
        for symbol, exit_reason in positions_to_close:
            self._close_position(symbol, open_positions, market_data, 
                               date, results, exit_reason)
    
    def _close_position(self, symbol: str, open_positions: Dict[str, BacktestTrade],
                       market_data: Dict[str, MarketData], date: datetime,
                       results: BacktestResults, exit_reason: str):
        """Close a specific position"""
        
        if symbol not in open_positions or symbol not in market_data:
            return
        
        trade = open_positions[symbol]
        current_price = market_data[symbol].price
        
        # Calculate slippage and commission for exit
        slippage = current_price * Decimal(str(0.001))  # 0.1% slippage
        if trade.action == OrderAction.BUY:
            exit_price = current_price - slippage
        else:
            exit_price = current_price + slippage
        
        trade_value = exit_price * trade.quantity
        commission = trade_value * Decimal(str(0.0005))  # 0.05% commission
        
        # Update trade record
        trade.exit_date = date
        trade.exit_price = exit_price
        trade.commission += commission
        trade.slippage += slippage
        trade.exit_reason = exit_reason
        trade.__post_init__()  # Recalculate P&L
        
        # Update results
        results.trades.append(trade)
        
        if trade.pnl > 0:
            results.winning_trades += 1
        else:
            results.losing_trades += 1
        
        # Remove from open positions
        del open_positions[symbol]
        
        logger.debug(f"Closed {symbol} position: {trade.pnl} RUB ({exit_reason})")
    
    def _close_all_positions(self, open_positions: Dict[str, BacktestTrade],
                           market_data: Dict[str, MarketData], date: datetime,
                           results: BacktestResults, exit_reason: str):
        """Close all open positions"""
        
        symbols_to_close = list(open_positions.keys())
        for symbol in symbols_to_close:
            self._close_position(symbol, open_positions, market_data, 
                               date, results, exit_reason)
    
    def _calculate_current_drawdown(self, portfolio_values: List[Tuple[datetime, Decimal]]) -> float:
        """Calculate current drawdown from peak"""
        if len(portfolio_values) < 2:
            return 0.0
        
        values = [float(v[1]) for v in portfolio_values]
        peak = max(values)
        current = values[-1]
        
        return (peak - current) / peak if peak > 0 else 0.0
    
    def _calculate_final_metrics(self, results: BacktestResults, config: BacktestConfig):
        """Calculate final performance metrics"""
        
        # Basic returns
        results.total_return = float((results.final_capital - results.initial_capital) / results.initial_capital)
        
        if results.duration_days > 0:
            results.annual_return = (1 + results.total_return) ** (365.25 / results.duration_days) - 1
        
        # Trading metrics
        if results.total_trades > 0:
            results.win_rate = results.winning_trades / results.total_trades
        
        # Calculate profit factor
        gross_profit = sum(float(t.pnl) for t in results.trades if t.pnl and t.pnl > 0)
        gross_loss = abs(sum(float(t.pnl) for t in results.trades if t.pnl and t.pnl < 0))
        
        if gross_loss > 0:
            results.profit_factor = gross_profit / gross_loss
        
        # Average win/loss
        winning_trades = [t for t in results.trades if t.pnl and t.pnl > 0]
        losing_trades = [t for t in results.trades if t.pnl and t.pnl < 0]
        
        if winning_trades:
            results.avg_win = Decimal(str(np.mean([float(t.pnl) for t in winning_trades])))
        
        if losing_trades:
            results.avg_loss = Decimal(str(np.mean([float(t.pnl) for t in losing_trades])))
        
        # Risk metrics
        if results.daily_returns:
            returns_array = np.array(results.daily_returns)
            results.volatility = float(np.std(returns_array) * np.sqrt(252))  # Annualized
            
            # Sharpe ratio (assuming 7.5% Russian risk-free rate)
            risk_free_rate = 0.075
            if results.volatility > 0:
                results.sharpe_ratio = (results.annual_return - risk_free_rate) / results.volatility
            
            # Sortino ratio (downside deviation)
            downside_returns = returns_array[returns_array < 0]
            if len(downside_returns) > 0:
                downside_deviation = float(np.std(downside_returns) * np.sqrt(252))
                if downside_deviation > 0:
                    results.sortino_ratio = (results.annual_return - risk_free_rate) / downside_deviation
        
        # Max drawdown
        if results.portfolio_values:
            values = [float(v[1]) for v in results.portfolio_values]
            peak = values[0]
            max_dd = 0.0
            
            for value in values:
                if value > peak:
                    peak = value
                else:
                    drawdown = (peak - value) / peak
                    max_dd = max(max_dd, drawdown)
            
            results.max_drawdown = max_dd
        
        # Benchmark comparison
        benchmark_symbol = config.benchmark_symbol
        if benchmark_symbol in self.benchmark_data:
            benchmark_df = self.benchmark_data[benchmark_symbol]
            benchmark_period = benchmark_df[
                (benchmark_df.index >= config.start_date) & 
                (benchmark_df.index <= config.end_date)
            ]
            
            if len(benchmark_period) > 1:
                benchmark_start = benchmark_period['close'].iloc[0]
                benchmark_end = benchmark_period['close'].iloc[-1]
                results.benchmark_return = float((benchmark_end - benchmark_start) / benchmark_start)
                
                # Alpha and Beta calculation
                if len(benchmark_period) == len(results.daily_returns):
                    benchmark_returns = benchmark_period['return'].values
                    portfolio_returns = np.array(results.daily_returns)
                    
                    # Beta
                    covariance = np.cov(portfolio_returns, benchmark_returns)[0, 1]
                    benchmark_variance = np.var(benchmark_returns)
                    
                    if benchmark_variance > 0:
                        results.beta = covariance / benchmark_variance
                        
                        # Alpha
                        results.alpha = results.annual_return - (risk_free_rate + results.beta * (np.mean(benchmark_returns) * 252 - risk_free_rate))
                        
                        # Information ratio
                        excess_returns = portfolio_returns - benchmark_returns
                        tracking_error = np.std(excess_returns) * np.sqrt(252)
                        
                        if tracking_error > 0:
                            results.information_ratio = np.mean(excess_returns) * 252 / tracking_error
        
        logger.info(f"Final metrics calculated: Return={results.total_return:.2%}, "
                   f"Sharpe={results.sharpe_ratio:.2f}, MaxDD={results.max_drawdown:.2%}")
    
    def get_backtest_report(self, results: Optional[BacktestResults] = None) -> str:
        """Generate comprehensive backtest report in Russian"""
        
        if results is None:
            results = self.current_backtest
        
        if results is None:
            return "Нет результатов бэктестинга для отображения"
        
        report = f"""
ОТЧЕТ ПО БЭКТЕСТИНГУ
{'='*50}

ПЕРИОД ТЕСТИРОВАНИЯ
Начало: {results.start_date.strftime('%d.%m.%Y')}
Конец: {results.end_date.strftime('%d.%m.%Y')}
Продолжительность: {results.duration_days} дней

РЕЗУЛЬТАТЫ ПОРТФЕЛЯ
Начальный капитал: {results.initial_capital:,.0f} ₽
Конечный капитал: {results.final_capital:,.0f} ₽
Общая доходность: {results.total_return:.2%}
Годовая доходность: {results.annual_return:.2%}

МЕТРИКИ РИСКА
Коэффициент Шарпа: {results.sharpe_ratio:.2f}
Коэффициент Сортино: {results.sortino_ratio:.2f}
Максимальная просадка: {results.max_drawdown:.2%}
Волатильность: {results.volatility:.2%}

ТОРГОВЫЕ МЕТРИКИ
Всего сделок: {results.total_trades}
Прибыльных сделок: {results.winning_trades}
Убыточных сделок: {results.losing_trades}
Процент прибыльных: {results.win_rate:.1%}
Фактор прибыли: {results.profit_factor:.2f}
Средняя прибыль: {results.avg_win:,.0f} ₽
Средний убыток: {results.avg_loss:,.0f} ₽

СРАВНЕНИЕ С БЕНЧМАРКОМ
Доходность бенчмарка: {results.benchmark_return:.2%}
Альфа: {results.alpha:.2%}
Бета: {results.beta:.2f}
Информационный коэффициент: {results.information_ratio:.2f}

ДЕТАЛИ СДЕЛОК
"""
        
        if results.trades:
            report += "\nПоследние 10 сделок:\n"
            report += f"{'Дата':<12} {'Символ':<8} {'Действие':<8} {'P&L':<12} {'Причина закрытия':<15}\n"
            report += "-" * 70 + "\n"
            
            for trade in results.trades[-10:]:
                pnl_str = f"{trade.pnl:,.0f} ₽" if trade.pnl else "N/A"
                report += f"{trade.entry_date.strftime('%d.%m.%Y'):<12} "
                report += f"{trade.symbol:<8} "
                report += f"{trade.action.value:<8} "
                report += f"{pnl_str:<12} "
                report += f"{trade.exit_reason:<15}\n"
        
        return report
    
    def export_results(self, results: Optional[BacktestResults] = None, 
                      filename: Optional[str] = None) -> str:
        """Export backtest results to JSON file"""
        
        if results is None:
            results = self.current_backtest
        
        if results is None:
            raise ValueError("No backtest results to export")
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"backtest_results_{timestamp}.json"
        
        import json
        
        # Convert results to dictionary
        results_dict = results.to_dict()
        
        # Add trade details
        results_dict['trades'] = []
        for trade in results.trades:
            trade_dict = {
                'entry_date': trade.entry_date.isoformat(),
                'exit_date': trade.exit_date.isoformat() if trade.exit_date else None,
                'symbol': trade.symbol,
                'action': trade.action.value,
                'entry_price': float(trade.entry_price),
                'exit_price': float(trade.exit_price) if trade.exit_price else None,
                'quantity': trade.quantity,
                'pnl': float(trade.pnl) if trade.pnl else None,
                'pnl_pct': trade.pnl_pct,
                'duration_days': trade.duration_days,
                'exit_reason': trade.exit_reason
            }
            results_dict['trades'].append(trade_dict)
        
        # Save to file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results_dict, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Backtest results exported to {filename}")
        return filename