"""
Performance analytics service for Russian stock market
Handles benchmark comparisons, Sharpe ratio, and sector analysis
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
import logging
from enum import Enum
import math

from .portfolio_manager import PortfolioSnapshot, PerformanceMetrics


logger = logging.getLogger(__name__)


class RussianIndex(Enum):
    """Russian market indices"""
    MOEX_RUSSIA = "MOEX Russia Index"
    RTS = "RTS Index"
    IMOEX = "IMOEX"
    RTSI = "RTSI"


class RussianSector(Enum):
    """Russian market sectors"""
    OIL_GAS = "oil_gas"
    BANKING = "banking"
    METALS_MINING = "metals_mining"
    TELECOM = "telecom"
    UTILITIES = "utilities"
    CONSUMER = "consumer"
    TECHNOLOGY = "technology"
    REAL_ESTATE = "real_estate"
    INDUSTRIALS = "industrials"


@dataclass
class BenchmarkData:
    """Benchmark index data"""
    index: RussianIndex
    timestamp: datetime
    value: Decimal
    daily_return: Optional[float] = None
    volume: Optional[int] = None


@dataclass
class SectorPerformance:
    """Sector performance metrics"""
    sector: RussianSector
    total_return: float
    daily_return: float
    weekly_return: float
    monthly_return: float
    volatility: float
    sharpe_ratio: float
    weight_in_portfolio: float
    stocks: List[str]


@dataclass
class BenchmarkComparison:
    """Comparison with Russian market benchmarks"""
    portfolio_return: float
    benchmark_return: float
    alpha: float  # Excess return over benchmark
    beta: float   # Portfolio sensitivity to benchmark
    correlation: float
    tracking_error: float
    information_ratio: float


@dataclass
class PerformanceAnalytics:
    """Comprehensive performance analytics"""
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    calmar_ratio: float
    sortino_ratio: float
    win_rate: float
    profit_factor: float
    moex_comparison: BenchmarkComparison
    rts_comparison: BenchmarkComparison
    sector_performance: Dict[RussianSector, SectorPerformance]
    risk_adjusted_metrics: Dict[str, float]


class PerformanceAnalyticsService:
    """
    Service for calculating comprehensive performance analytics
    for Russian stock market portfolios
    """
    
    def __init__(self):
        self.risk_free_rate = 0.075  # Russian CBR key rate (7.5%)
        self.trading_days_per_year = 252
        
        # Russian sector mappings
        self.sector_mappings = {
            "SBER": RussianSector.BANKING,
            "VTBR": RussianSector.BANKING,
            "GAZP": RussianSector.OIL_GAS,
            "LKOH": RussianSector.OIL_GAS,
            "ROSN": RussianSector.OIL_GAS,
            "NVTK": RussianSector.OIL_GAS,
            "GMKN": RussianSector.METALS_MINING,
            "NLMK": RussianSector.METALS_MINING,
            "MAGN": RussianSector.METALS_MINING,
            "MTSS": RussianSector.TELECOM,
            "MGNT": RussianSector.CONSUMER,
            "YNDX": RussianSector.TECHNOLOGY,
            "MAIL": RussianSector.TECHNOLOGY,
            "IRAO": RussianSector.UTILITIES,
            "FEES": RussianSector.UTILITIES,
            "LSR": RussianSector.REAL_ESTATE,
            "PIK": RussianSector.REAL_ESTATE,
        }
    
    def calculate_comprehensive_analytics(
        self,
        portfolio_returns: List[float],
        portfolio_values: List[float],
        positions: Dict[str, float],
        moex_returns: List[float],
        rts_returns: List[float],
        timestamps: List[datetime]
    ) -> PerformanceAnalytics:
        """
        Calculate comprehensive performance analytics
        
        Args:
            portfolio_returns: Daily portfolio returns
            portfolio_values: Portfolio values over time
            positions: Current positions {symbol: value}
            moex_returns: MOEX Russia Index returns
            rts_returns: RTS Index returns
            timestamps: Timestamps for returns
            
        Returns:
            PerformanceAnalytics object with all metrics
        """
        if not portfolio_returns or len(portfolio_returns) < 2:
            return self._empty_analytics()
        
        # Basic performance metrics
        total_return = (portfolio_values[-1] - portfolio_values[0]) / portfolio_values[0]
        annualized_return = self._calculate_annualized_return(portfolio_returns)
        volatility = self._calculate_volatility(portfolio_returns)
        sharpe_ratio = self._calculate_sharpe_ratio(portfolio_returns, volatility)
        max_drawdown = self._calculate_max_drawdown(portfolio_values)
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
        sortino_ratio = self._calculate_sortino_ratio(portfolio_returns)
        win_rate = self._calculate_win_rate(portfolio_returns)
        profit_factor = self._calculate_profit_factor(portfolio_returns)
        
        # Benchmark comparisons
        moex_comparison = self._calculate_benchmark_comparison(
            portfolio_returns, moex_returns, "MOEX"
        )
        rts_comparison = self._calculate_benchmark_comparison(
            portfolio_returns, rts_returns, "RTS"
        )
        
        # Sector performance analysis
        sector_performance = self._calculate_sector_performance(
            positions, portfolio_returns, timestamps
        )
        
        # Risk-adjusted metrics
        risk_adjusted_metrics = {
            "jensen_alpha_moex": self._calculate_jensen_alpha(portfolio_returns, moex_returns),
            "jensen_alpha_rts": self._calculate_jensen_alpha(portfolio_returns, rts_returns),
            "treynor_ratio_moex": self._calculate_treynor_ratio(portfolio_returns, moex_returns),
            "treynor_ratio_rts": self._calculate_treynor_ratio(portfolio_returns, rts_returns),
            "var_95": self._calculate_var(portfolio_returns, 0.95),
            "cvar_95": self._calculate_cvar(portfolio_returns, 0.95),
        }
        
        return PerformanceAnalytics(
            total_return=total_return,
            annualized_return=annualized_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            calmar_ratio=calmar_ratio,
            sortino_ratio=sortino_ratio,
            win_rate=win_rate,
            profit_factor=profit_factor,
            moex_comparison=moex_comparison,
            rts_comparison=rts_comparison,
            sector_performance=sector_performance,
            risk_adjusted_metrics=risk_adjusted_metrics
        )
    
    def _calculate_annualized_return(self, returns: List[float]) -> float:
        """Calculate annualized return"""
        if not returns:
            return 0.0
        
        total_return = 1.0
        for r in returns:
            total_return *= (1 + r)
        
        periods = len(returns)
        if periods == 0:
            return 0.0
        
        annualized = (total_return ** (self.trading_days_per_year / periods)) - 1
        return annualized
    
    def _calculate_volatility(self, returns: List[float]) -> float:
        """Calculate annualized volatility"""
        if len(returns) < 2:
            return 0.0
        
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        daily_vol = math.sqrt(variance)
        annualized_vol = daily_vol * math.sqrt(self.trading_days_per_year)
        
        return annualized_vol
    
    def _calculate_sharpe_ratio(self, returns: List[float], volatility: float) -> float:
        """Calculate Sharpe ratio"""
        if volatility == 0:
            return 0.0
        
        mean_return = sum(returns) / len(returns) if returns else 0
        annualized_mean = mean_return * self.trading_days_per_year
        excess_return = annualized_mean - self.risk_free_rate
        
        return excess_return / volatility
    
    def _calculate_max_drawdown(self, values: List[float]) -> float:
        """Calculate maximum drawdown"""
        if len(values) < 2:
            return 0.0
        
        peak = values[0]
        max_dd = 0.0
        
        for value in values[1:]:
            if value > peak:
                peak = value
            else:
                drawdown = (peak - value) / peak
                max_dd = max(max_dd, drawdown)
        
        return -max_dd  # Return as negative value
    
    def _calculate_sortino_ratio(self, returns: List[float]) -> float:
        """Calculate Sortino ratio (downside deviation)"""
        if not returns:
            return 0.0
        
        mean_return = sum(returns) / len(returns)
        downside_returns = [r for r in returns if r < 0]
        
        if not downside_returns:
            return float('inf') if mean_return > 0 else 0.0
        
        downside_variance = sum(r ** 2 for r in downside_returns) / len(downside_returns)
        downside_deviation = math.sqrt(downside_variance) * math.sqrt(self.trading_days_per_year)
        
        if downside_deviation == 0:
            return 0.0
        
        annualized_mean = mean_return * self.trading_days_per_year
        excess_return = annualized_mean - self.risk_free_rate
        
        return excess_return / downside_deviation
    
    def _calculate_win_rate(self, returns: List[float]) -> float:
        """Calculate win rate (percentage of positive returns)"""
        if not returns:
            return 0.0
        
        winning_periods = sum(1 for r in returns if r > 0)
        return winning_periods / len(returns)
    
    def _calculate_profit_factor(self, returns: List[float]) -> float:
        """Calculate profit factor (gross profit / gross loss)"""
        if not returns:
            return 0.0
        
        gross_profit = sum(r for r in returns if r > 0)
        gross_loss = abs(sum(r for r in returns if r < 0))
        
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
        
        return gross_profit / gross_loss
    
    def _calculate_benchmark_comparison(
        self, 
        portfolio_returns: List[float], 
        benchmark_returns: List[float],
        benchmark_name: str
    ) -> BenchmarkComparison:
        """Calculate comparison metrics against benchmark"""
        if len(portfolio_returns) != len(benchmark_returns) or not portfolio_returns:
            return BenchmarkComparison(0, 0, 0, 0, 0, 0, 0)
        
        # Calculate returns
        portfolio_total = sum(portfolio_returns)
        benchmark_total = sum(benchmark_returns)
        
        # Calculate beta (portfolio sensitivity to benchmark)
        beta = self._calculate_beta(portfolio_returns, benchmark_returns)
        
        # Calculate alpha (excess return)
        alpha = portfolio_total - (self.risk_free_rate + beta * (benchmark_total - self.risk_free_rate))
        
        # Calculate correlation
        correlation = self._calculate_correlation(portfolio_returns, benchmark_returns)
        
        # Calculate tracking error
        tracking_error = self._calculate_tracking_error(portfolio_returns, benchmark_returns)
        
        # Calculate information ratio
        information_ratio = alpha / tracking_error if tracking_error != 0 else 0
        
        return BenchmarkComparison(
            portfolio_return=portfolio_total,
            benchmark_return=benchmark_total,
            alpha=alpha,
            beta=beta,
            correlation=correlation,
            tracking_error=tracking_error,
            information_ratio=information_ratio
        )
    
    def _calculate_beta(self, portfolio_returns: List[float], benchmark_returns: List[float]) -> float:
        """Calculate portfolio beta"""
        if len(portfolio_returns) != len(benchmark_returns) or len(portfolio_returns) < 2:
            return 0.0
        
        # Calculate covariance and variance
        port_mean = sum(portfolio_returns) / len(portfolio_returns)
        bench_mean = sum(benchmark_returns) / len(benchmark_returns)
        
        covariance = sum(
            (p - port_mean) * (b - bench_mean) 
            for p, b in zip(portfolio_returns, benchmark_returns)
        ) / (len(portfolio_returns) - 1)
        
        benchmark_variance = sum(
            (b - bench_mean) ** 2 for b in benchmark_returns
        ) / (len(benchmark_returns) - 1)
        
        if benchmark_variance == 0:
            return 0.0
        
        return covariance / benchmark_variance
    
    def _calculate_correlation(self, returns1: List[float], returns2: List[float]) -> float:
        """Calculate correlation between two return series"""
        if len(returns1) != len(returns2) or len(returns1) < 2:
            return 0.0
        
        mean1 = sum(returns1) / len(returns1)
        mean2 = sum(returns2) / len(returns2)
        
        numerator = sum((r1 - mean1) * (r2 - mean2) for r1, r2 in zip(returns1, returns2))
        
        sum_sq1 = sum((r1 - mean1) ** 2 for r1 in returns1)
        sum_sq2 = sum((r2 - mean2) ** 2 for r2 in returns2)
        
        denominator = math.sqrt(sum_sq1 * sum_sq2)
        
        if denominator == 0:
            return 0.0
        
        return numerator / denominator
    
    def _calculate_tracking_error(self, portfolio_returns: List[float], benchmark_returns: List[float]) -> float:
        """Calculate tracking error (volatility of excess returns)"""
        if len(portfolio_returns) != len(benchmark_returns) or len(portfolio_returns) < 2:
            return 0.0
        
        excess_returns = [p - b for p, b in zip(portfolio_returns, benchmark_returns)]
        return self._calculate_volatility(excess_returns)
    
    def _calculate_jensen_alpha(self, portfolio_returns: List[float], benchmark_returns: List[float]) -> float:
        """Calculate Jensen's alpha"""
        if not portfolio_returns or not benchmark_returns:
            return 0.0
        
        beta = self._calculate_beta(portfolio_returns, benchmark_returns)
        portfolio_mean = sum(portfolio_returns) / len(portfolio_returns) * self.trading_days_per_year
        benchmark_mean = sum(benchmark_returns) / len(benchmark_returns) * self.trading_days_per_year
        
        expected_return = self.risk_free_rate + beta * (benchmark_mean - self.risk_free_rate)
        return portfolio_mean - expected_return
    
    def _calculate_treynor_ratio(self, portfolio_returns: List[float], benchmark_returns: List[float]) -> float:
        """Calculate Treynor ratio"""
        beta = self._calculate_beta(portfolio_returns, benchmark_returns)
        if beta == 0:
            return 0.0
        
        portfolio_mean = sum(portfolio_returns) / len(portfolio_returns) * self.trading_days_per_year
        excess_return = portfolio_mean - self.risk_free_rate
        
        return excess_return / beta
    
    def _calculate_var(self, returns: List[float], confidence_level: float) -> float:
        """Calculate Value at Risk"""
        if not returns:
            return 0.0
        
        sorted_returns = sorted(returns)
        index = int((1 - confidence_level) * len(sorted_returns))
        return sorted_returns[index] if index < len(sorted_returns) else 0.0
    
    def _calculate_cvar(self, returns: List[float], confidence_level: float) -> float:
        """Calculate Conditional Value at Risk (Expected Shortfall)"""
        if not returns:
            return 0.0
        
        var = self._calculate_var(returns, confidence_level)
        tail_returns = [r for r in returns if r <= var]
        
        if not tail_returns:
            return 0.0
        
        return sum(tail_returns) / len(tail_returns)
    
    def _calculate_sector_performance(
        self, 
        positions: Dict[str, float], 
        portfolio_returns: List[float],
        timestamps: List[datetime]
    ) -> Dict[RussianSector, SectorPerformance]:
        """Calculate performance by Russian market sectors"""
        sector_performance = {}
        total_portfolio_value = sum(positions.values())
        
        # Group positions by sector
        sector_positions = {}
        for symbol, value in positions.items():
            sector = self.sector_mappings.get(symbol, RussianSector.INDUSTRIALS)
            if sector not in sector_positions:
                sector_positions[sector] = []
            sector_positions[sector].append((symbol, value))
        
        # Calculate performance for each sector
        for sector, sector_stocks in sector_positions.items():
            sector_value = sum(value for _, value in sector_stocks)
            sector_weight = sector_value / total_portfolio_value if total_portfolio_value > 0 else 0
            
            # For simplicity, assume sector returns are proportional to portfolio returns
            # In a real implementation, you'd calculate actual sector-specific returns
            sector_returns = [r * sector_weight for r in portfolio_returns]
            
            sector_performance[sector] = SectorPerformance(
                sector=sector,
                total_return=sum(sector_returns),
                daily_return=sector_returns[-1] if sector_returns else 0,
                weekly_return=sum(sector_returns[-7:]) if len(sector_returns) >= 7 else sum(sector_returns),
                monthly_return=sum(sector_returns[-30:]) if len(sector_returns) >= 30 else sum(sector_returns),
                volatility=self._calculate_volatility(sector_returns),
                sharpe_ratio=self._calculate_sharpe_ratio(sector_returns, self._calculate_volatility(sector_returns)),
                weight_in_portfolio=sector_weight,
                stocks=[symbol for symbol, _ in sector_stocks]
            )
        
        return sector_performance
    
    def _empty_analytics(self) -> PerformanceAnalytics:
        """Return empty analytics for insufficient data"""
        return PerformanceAnalytics(
            total_return=0.0,
            annualized_return=0.0,
            volatility=0.0,
            sharpe_ratio=0.0,
            max_drawdown=0.0,
            calmar_ratio=0.0,
            sortino_ratio=0.0,
            win_rate=0.0,
            profit_factor=0.0,
            moex_comparison=BenchmarkComparison(0, 0, 0, 0, 0, 0, 0),
            rts_comparison=BenchmarkComparison(0, 0, 0, 0, 0, 0, 0),
            sector_performance={},
            risk_adjusted_metrics={}
        )
    
    def generate_performance_report(self, analytics: PerformanceAnalytics) -> str:
        """Generate a comprehensive performance report in Russian"""
        report = []
        report.append("=== ОТЧЕТ О ПРОИЗВОДИТЕЛЬНОСТИ ПОРТФЕЛЯ ===\n")
        
        # Basic metrics
        report.append("ОСНОВНЫЕ ПОКАЗАТЕЛИ:")
        report.append(f"  Общая доходность: {analytics.total_return:.2%}")
        report.append(f"  Годовая доходность: {analytics.annualized_return:.2%}")
        report.append(f"  Волатильность: {analytics.volatility:.2%}")
        report.append(f"  Коэффициент Шарпа: {analytics.sharpe_ratio:.3f}")
        report.append(f"  Максимальная просадка: {analytics.max_drawdown:.2%}")
        report.append(f"  Коэффициент Кальмара: {analytics.calmar_ratio:.3f}")
        report.append(f"  Коэффициент Сортино: {analytics.sortino_ratio:.3f}")
        report.append(f"  Доля прибыльных периодов: {analytics.win_rate:.2%}")
        report.append(f"  Фактор прибыли: {analytics.profit_factor:.3f}\n")
        
        # Benchmark comparisons
        report.append("СРАВНЕНИЕ С БЕНЧМАРКАМИ:")
        report.append(f"  MOEX Russia Index:")
        report.append(f"    Альфа: {analytics.moex_comparison.alpha:.2%}")
        report.append(f"    Бета: {analytics.moex_comparison.beta:.3f}")
        report.append(f"    Корреляция: {analytics.moex_comparison.correlation:.3f}")
        report.append(f"    Коэффициент информации: {analytics.moex_comparison.information_ratio:.3f}")
        
        report.append(f"  RTS Index:")
        report.append(f"    Альфа: {analytics.rts_comparison.alpha:.2%}")
        report.append(f"    Бета: {analytics.rts_comparison.beta:.3f}")
        report.append(f"    Корреляция: {analytics.rts_comparison.correlation:.3f}")
        report.append(f"    Коэффициент информации: {analytics.rts_comparison.information_ratio:.3f}\n")
        
        # Sector performance
        if analytics.sector_performance:
            report.append("ПРОИЗВОДИТЕЛЬНОСТЬ ПО СЕКТОРАМ:")
            for sector, perf in analytics.sector_performance.items():
                report.append(f"  {sector.value.replace('_', ' ').title()}:")
                report.append(f"    Доля в портфеле: {perf.weight_in_portfolio:.2%}")
                report.append(f"    Доходность: {perf.total_return:.2%}")
                report.append(f"    Коэффициент Шарпа: {perf.sharpe_ratio:.3f}")
                report.append(f"    Акции: {', '.join(perf.stocks)}")
        
        # Risk metrics
        report.append("\nРИСК-МЕТРИКИ:")
        for metric, value in analytics.risk_adjusted_metrics.items():
            metric_name = metric.replace('_', ' ').title()
            if 'var' in metric.lower():
                report.append(f"  {metric_name}: {value:.2%}")
            else:
                report.append(f"  {metric_name}: {value:.3f}")
        
        return "\n".join(report)