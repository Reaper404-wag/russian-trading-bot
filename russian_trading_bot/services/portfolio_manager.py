"""
Portfolio management service for Russian stock trading bot
Handles portfolio tracking, P&L calculations, and performance metrics
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP
import logging
from enum import Enum

from ..models.trading import Portfolio, Position, ExecutionResult, OrderAction
from ..models.market_data import RussianStock, MarketData


logger = logging.getLogger(__name__)


class PerformanceMetric(Enum):
    """Performance metrics for Russian market"""
    TOTAL_RETURN = "total_return"
    DAILY_RETURN = "daily_return"
    WEEKLY_RETURN = "weekly_return"
    MONTHLY_RETURN = "monthly_return"
    ANNUAL_RETURN = "annual_return"
    SHARPE_RATIO = "sharpe_ratio"
    MAX_DRAWDOWN = "max_drawdown"
    WIN_RATE = "win_rate"
    PROFIT_FACTOR = "profit_factor"


@dataclass
class PortfolioSnapshot:
    """Portfolio snapshot at a specific point in time"""
    timestamp: datetime
    total_value: Decimal
    cash_balance: Decimal
    positions_value: Decimal
    daily_pnl: Decimal
    total_pnl: Decimal
    positions_count: int
    currency: str = "RUB"


@dataclass
class PerformanceMetrics:
    """Performance metrics for Russian portfolio"""
    total_return: float
    daily_return: float
    weekly_return: float
    monthly_return: float
    annual_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    volatility: float
    moex_correlation: Optional[float] = None
    rts_correlation: Optional[float] = None
    currency: str = "RUB"


@dataclass
class TaxCalculation:
    """Russian tax calculation results"""
    capital_gains: Decimal
    capital_losses: Decimal
    net_capital_gains: Decimal
    dividend_income: Decimal
    total_taxable_income: Decimal
    estimated_tax: Decimal
    currency: str = "RUB"
    tax_year: int = field(default_factory=lambda: datetime.now().year)


class PortfolioManager:
    """Portfolio management service for Russian market"""
    
    def __init__(self, initial_cash: Decimal = Decimal('1000000')):
        """
        Initialize portfolio manager
        
        Args:
            initial_cash: Initial cash balance in RUB
        """
        self.portfolio = Portfolio(
            positions={},
            cash_balance=initial_cash,
            currency="RUB"
        )
        self.snapshots: List[PortfolioSnapshot] = []
        self.trade_history: List[Dict] = []
        self.dividend_history: List[Dict] = []
        self.initial_value = initial_cash
        
        logger.info(f"Portfolio manager initialized with {initial_cash} RUB")
    
    def update_position(self, execution: ExecutionResult, order_details: Dict) -> None:
        """
        Update portfolio position based on trade execution
        
        Args:
            execution: Trade execution result
            order_details: Original order details
        """
        if not execution.is_successful:
            logger.warning(f"Skipping position update for failed execution: {execution.order_id}")
            return
        
        symbol = order_details['symbol']
        action = order_details['action']
        quantity = execution.filled_quantity
        price = execution.average_price
        commission = execution.commission or Decimal('0')
        
        # Calculate total cost including commission
        total_cost = price * quantity + commission
        
        if action == OrderAction.BUY:
            self._handle_buy_order(symbol, quantity, price, total_cost)
        elif action == OrderAction.SELL:
            self._handle_sell_order(symbol, quantity, price, total_cost, commission)
        
        # Record trade in history
        self.trade_history.append({
            'timestamp': execution.timestamp or datetime.now(),
            'symbol': symbol,
            'action': action.value,
            'quantity': quantity,
            'price': price,
            'commission': commission,
            'total_cost': total_cost,
            'order_id': execution.order_id
        })
        
        logger.info(f"Position updated: {action.value} {quantity} {symbol} at {price} RUB")
    
    def _handle_buy_order(self, symbol: str, quantity: int, price: Decimal, total_cost: Decimal) -> None:
        """Handle buy order execution"""
        if symbol in self.portfolio.positions:
            # Update existing position
            position = self.portfolio.positions[symbol]
            total_quantity = position.quantity + quantity
            total_value = position.average_price * position.quantity + price * quantity
            new_average_price = total_value / total_quantity
            
            position.quantity = total_quantity
            position.average_price = new_average_price
        else:
            # Create new position
            self.portfolio.positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                average_price=price,
                currency="RUB"
            )
        
        # Deduct cash
        self.portfolio.cash_balance -= total_cost
    
    def _handle_sell_order(self, symbol: str, quantity: int, price: Decimal, 
                          total_cost: Decimal, commission: Decimal) -> None:
        """Handle sell order execution"""
        if symbol not in self.portfolio.positions:
            raise ValueError(f"Cannot sell {symbol}: no position exists")
        
        position = self.portfolio.positions[symbol]
        if position.quantity < quantity:
            raise ValueError(f"Cannot sell {quantity} {symbol}: only {position.quantity} available")
        
        # Calculate realized P&L
        cost_basis = position.average_price * quantity
        proceeds = price * quantity - commission
        realized_pnl = proceeds - cost_basis
        
        # Update position
        position.quantity -= quantity
        if position.realized_pnl is None:
            position.realized_pnl = Decimal('0')
        position.realized_pnl += realized_pnl
        
        # Remove position if fully sold
        if position.quantity == 0:
            del self.portfolio.positions[symbol]
        
        # Add cash proceeds
        self.portfolio.cash_balance += proceeds
    
    def update_market_prices(self, market_data: Dict[str, MarketData]) -> None:
        """
        Update current market prices for all positions
        
        Args:
            market_data: Dictionary of symbol -> MarketData
        """
        for symbol, position in self.portfolio.positions.items():
            if symbol in market_data:
                position.current_price = market_data[symbol].price
                position.market_value = position.current_price * position.quantity
                position.unrealized_pnl = (
                    position.current_price - position.average_price
                ) * position.quantity
        
        # Recalculate portfolio totals
        self.portfolio.__post_init__()
        
        logger.debug(f"Updated market prices for {len(market_data)} symbols")
    
    def calculate_pnl(self) -> Dict[str, Decimal]:
        """
        Calculate profit and loss metrics
        
        Returns:
            Dictionary with P&L metrics
        """
        total_unrealized = sum(
            pos.unrealized_pnl or Decimal('0') 
            for pos in self.portfolio.positions.values()
        )
        
        total_realized = sum(
            pos.realized_pnl or Decimal('0') 
            for pos in self.portfolio.positions.values()
        )
        
        total_pnl = total_unrealized + total_realized
        
        # Calculate daily P&L if we have snapshots
        daily_pnl = Decimal('0')
        if self.snapshots:
            yesterday_value = self.snapshots[-1].total_value
            today_value = self.portfolio.total_value or Decimal('0')
            daily_pnl = today_value - yesterday_value
        
        return {
            'unrealized_pnl': total_unrealized,
            'realized_pnl': total_realized,
            'total_pnl': total_pnl,
            'daily_pnl': daily_pnl,
            'total_return_pct': float(total_pnl / self.initial_value * 100) if self.initial_value > 0 else 0.0
        }
    
    def calculate_performance_metrics(self, benchmark_returns: Optional[List[float]] = None) -> PerformanceMetrics:
        """
        Calculate comprehensive performance metrics
        
        Args:
            benchmark_returns: Optional benchmark returns for comparison (MOEX/RTS)
            
        Returns:
            PerformanceMetrics object
        """
        if len(self.snapshots) < 2:
            # Not enough data for meaningful metrics
            return PerformanceMetrics(
                total_return=0.0,
                daily_return=0.0,
                weekly_return=0.0,
                monthly_return=0.0,
                annual_return=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                win_rate=0.0,
                profit_factor=0.0,
                volatility=0.0
            )
        
        # Calculate returns
        returns = self._calculate_returns()
        
        # Total return
        total_return = float((self.portfolio.total_value - self.initial_value) / self.initial_value)
        
        # Period returns
        daily_return = returns[-1] if returns else 0.0
        weekly_return = self._calculate_period_return(7)
        monthly_return = self._calculate_period_return(30)
        annual_return = self._calculate_annualized_return(returns)
        
        # Risk metrics
        volatility = self._calculate_volatility(returns)
        sharpe_ratio = self._calculate_sharpe_ratio(returns, volatility)
        max_drawdown = self._calculate_max_drawdown()
        
        # Trading metrics
        win_rate = self._calculate_win_rate()
        profit_factor = self._calculate_profit_factor()
        
        # Correlation with benchmarks
        moex_correlation = None
        rts_correlation = None
        if benchmark_returns and len(benchmark_returns) == len(returns):
            moex_correlation = self._calculate_correlation(returns, benchmark_returns)
        
        return PerformanceMetrics(
            total_return=total_return,
            daily_return=daily_return,
            weekly_return=weekly_return,
            monthly_return=monthly_return,
            annual_return=annual_return,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            volatility=volatility,
            moex_correlation=moex_correlation,
            rts_correlation=rts_correlation
        )
    
    def _calculate_returns(self) -> List[float]:
        """Calculate daily returns from snapshots"""
        if len(self.snapshots) < 2:
            return []
        
        returns = []
        for i in range(1, len(self.snapshots)):
            prev_value = float(self.snapshots[i-1].total_value)
            curr_value = float(self.snapshots[i].total_value)
            
            if prev_value > 0:
                daily_return = (curr_value - prev_value) / prev_value
                returns.append(daily_return)
        
        return returns
    
    def _calculate_period_return(self, days: int) -> float:
        """Calculate return for specific period"""
        if len(self.snapshots) < days:
            return 0.0
        
        start_value = float(self.snapshots[-days].total_value)
        end_value = float(self.snapshots[-1].total_value)
        
        if start_value > 0:
            return (end_value - start_value) / start_value
        return 0.0
    
    def _calculate_annualized_return(self, returns: List[float]) -> float:
        """Calculate annualized return"""
        if not returns:
            return 0.0
        
        # Compound daily returns to get total return
        total_return = 1.0
        for r in returns:
            total_return *= (1 + r)
        
        # Annualize based on number of trading days
        trading_days_per_year = 252
        periods = len(returns)
        
        if periods > 0:
            return (total_return ** (trading_days_per_year / periods)) - 1
        return 0.0
    
    def _calculate_volatility(self, returns: List[float]) -> float:
        """Calculate volatility (standard deviation of returns)"""
        if len(returns) < 2:
            return 0.0
        
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        
        # Annualize volatility
        return (variance ** 0.5) * (252 ** 0.5)
    
    def _calculate_sharpe_ratio(self, returns: List[float], volatility: float, 
                               risk_free_rate: float = 0.075) -> float:
        """
        Calculate Sharpe ratio
        
        Args:
            returns: List of daily returns
            volatility: Annualized volatility
            risk_free_rate: Russian risk-free rate (CBR key rate ~7.5%)
        """
        if volatility == 0 or not returns:
            return 0.0
        
        # Calculate annualized return
        annual_return = self._calculate_annualized_return(returns)
        
        return (annual_return - risk_free_rate) / volatility
    
    def _calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown"""
        if len(self.snapshots) < 2:
            return 0.0
        
        peak = float(self.snapshots[0].total_value)
        max_drawdown = 0.0
        
        for snapshot in self.snapshots[1:]:
            value = float(snapshot.total_value)
            
            if value > peak:
                peak = value
            else:
                drawdown = (peak - value) / peak
                max_drawdown = max(max_drawdown, drawdown)
        
        return max_drawdown
    
    def _calculate_win_rate(self) -> float:
        """Calculate win rate from trade history"""
        if not self.trade_history:
            return 0.0
        
        # Group trades by symbol to calculate position P&L
        position_pnl = {}
        
        for trade in self.trade_history:
            symbol = trade['symbol']
            if symbol not in position_pnl:
                position_pnl[symbol] = []
            
            if trade['action'] == 'buy':
                position_pnl[symbol].append(-float(trade['total_cost']))
            else:  # sell
                position_pnl[symbol].append(float(trade['total_cost']))
        
        # Calculate win rate
        wins = 0
        total_positions = 0
        
        for symbol, pnl_list in position_pnl.items():
            if len(pnl_list) >= 2:  # At least one buy and one sell
                total_pnl = sum(pnl_list)
                if total_pnl > 0:
                    wins += 1
                total_positions += 1
        
        return wins / total_positions if total_positions > 0 else 0.0
    
    def _calculate_profit_factor(self) -> float:
        """Calculate profit factor (gross profit / gross loss)"""
        gross_profit = Decimal('0')
        gross_loss = Decimal('0')
        
        for position in self.portfolio.positions.values():
            if position.realized_pnl:
                if position.realized_pnl > 0:
                    gross_profit += position.realized_pnl
                else:
                    gross_loss += abs(position.realized_pnl)
        
        return float(gross_profit / gross_loss) if gross_loss > 0 else 0.0
    
    def _calculate_correlation(self, returns1: List[float], returns2: List[float]) -> float:
        """Calculate correlation between two return series"""
        if len(returns1) != len(returns2) or len(returns1) < 2:
            return 0.0
        
        n = len(returns1)
        mean1 = sum(returns1) / n
        mean2 = sum(returns2) / n
        
        numerator = sum((returns1[i] - mean1) * (returns2[i] - mean2) for i in range(n))
        
        sum_sq1 = sum((r - mean1) ** 2 for r in returns1)
        sum_sq2 = sum((r - mean2) ** 2 for r in returns2)
        
        denominator = (sum_sq1 * sum_sq2) ** 0.5
        
        return numerator / denominator if denominator > 0 else 0.0
    
    def take_snapshot(self) -> PortfolioSnapshot:
        """
        Take a snapshot of current portfolio state
        
        Returns:
            PortfolioSnapshot object
        """
        positions_value = sum(
            pos.market_value or Decimal('0') 
            for pos in self.portfolio.positions.values()
        )
        
        total_value = self.portfolio.cash_balance + positions_value
        
        # Calculate daily P&L
        daily_pnl = Decimal('0')
        if self.snapshots:
            daily_pnl = total_value - self.snapshots[-1].total_value
        
        # Calculate total P&L
        total_pnl = total_value - self.initial_value
        
        snapshot = PortfolioSnapshot(
            timestamp=datetime.now(),
            total_value=total_value,
            cash_balance=self.portfolio.cash_balance,
            positions_value=positions_value,
            daily_pnl=daily_pnl,
            total_pnl=total_pnl,
            positions_count=len(self.portfolio.positions)
        )
        
        self.snapshots.append(snapshot)
        
        # Keep only last 365 snapshots to manage memory
        if len(self.snapshots) > 365:
            self.snapshots = self.snapshots[-365:]
        
        logger.debug(f"Portfolio snapshot taken: {total_value} RUB total value")
        
        return snapshot
    
    def get_portfolio_summary(self) -> Dict:
        """
        Get comprehensive portfolio summary
        
        Returns:
            Dictionary with portfolio summary
        """
        pnl_metrics = self.calculate_pnl()
        
        # Position details
        positions_summary = []
        for symbol, position in self.portfolio.positions.items():
            positions_summary.append({
                'symbol': symbol,
                'quantity': position.quantity,
                'average_price': float(position.average_price),
                'current_price': float(position.current_price) if position.current_price else None,
                'market_value': float(position.market_value) if position.market_value else None,
                'unrealized_pnl': float(position.unrealized_pnl) if position.unrealized_pnl else None,
                'unrealized_pnl_pct': float(
                    position.unrealized_pnl / (position.average_price * position.quantity) * 100
                ) if position.unrealized_pnl and position.average_price > 0 else None
            })
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_value': float(self.portfolio.total_value or 0),
            'cash_balance': float(self.portfolio.cash_balance),
            'positions_count': len(self.portfolio.positions),
            'currency': self.portfolio.currency,
            'pnl_metrics': {k: float(v) for k, v in pnl_metrics.items()},
            'positions': positions_summary,
            'snapshots_count': len(self.snapshots)
        }
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """
        Get position for specific symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Position object or None if not found
        """
        return self.portfolio.positions.get(symbol.upper())
    
    def get_available_cash(self) -> Decimal:
        """Get available cash balance"""
        return self.portfolio.cash_balance
    
    def get_total_value(self) -> Decimal:
        """Get total portfolio value"""
        return self.portfolio.total_value or Decimal('0')