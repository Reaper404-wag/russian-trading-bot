"""
Unit tests for Russian market performance analytics service
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
import math

from russian_trading_bot.services.performance_analytics import (
    PerformanceAnalyticsService,
    RussianIndex,
    RussianSector,
    BenchmarkData,
    SectorPerformance,
    BenchmarkComparison,
    PerformanceAnalytics
)


class TestPerformanceAnalyticsService:
    """Test performance analytics service"""
    
    @pytest.fixture
    def analytics_service(self):
        """Create performance analytics service"""
        return PerformanceAnalyticsService()
    
    @pytest.fixture
    def sample_portfolio_data(self):
        """Sample portfolio data for testing"""
        # Generate 30 days of sample data
        base_date = datetime(2024, 1, 1)
        timestamps = [base_date + timedelta(days=i) for i in range(30)]
        
        # Portfolio returns (daily)
        portfolio_returns = [
            0.01, -0.005, 0.02, 0.015, -0.01,
            0.008, 0.012, -0.003, 0.005, 0.018,
            -0.007, 0.009, 0.014, -0.002, 0.011,
            0.006, -0.008, 0.013, 0.007, -0.004,
            0.016, 0.003, -0.009, 0.012, 0.008,
            -0.006, 0.015, 0.004, -0.001, 0.010
        ]
        
        # Portfolio values
        initial_value = 1000000.0  # 1M RUB
        portfolio_values = [initial_value]
        for ret in portfolio_returns:
            portfolio_values.append(portfolio_values[-1] * (1 + ret))
        
        # MOEX returns (slightly different pattern)
        moex_returns = [
            0.008, -0.003, 0.015, 0.012, -0.008,
            0.006, 0.010, -0.001, 0.003, 0.014,
            -0.005, 0.007, 0.011, 0.001, 0.009,
            0.004, -0.006, 0.010, 0.005, -0.002,
            0.013, 0.001, -0.007, 0.009, 0.006,
            -0.004, 0.012, 0.002, 0.001, 0.008
        ]
        
        # RTS returns (more volatile)
        rts_returns = [
            0.012, -0.008, 0.025, 0.018, -0.015,
            0.010, 0.016, -0.005, 0.008, 0.022,
            -0.010, 0.011, 0.018, -0.003, 0.014,
            0.008, -0.012, 0.016, 0.009, -0.006,
            0.020, 0.004, -0.013, 0.015, 0.010,
            -0.008, 0.019, 0.006, -0.002, 0.013
        ]
        
        # Sample positions
        positions = {
            "SBER": 300000.0,  # Banking
            "GAZP": 250000.0,  # Oil & Gas
            "LKOH": 200000.0,  # Oil & Gas
            "GMKN": 150000.0,  # Metals & Mining
            "YNDX": 100000.0,  # Technology
        }
        
        return {
            "portfolio_returns": portfolio_returns,
            "portfolio_values": portfolio_values,
            "positions": positions,
            "moex_returns": moex_returns,
            "rts_returns": rts_returns,
            "timestamps": timestamps
        }
    
    def test_calculate_comprehensive_analytics(self, analytics_service, sample_portfolio_data):
        """Test comprehensive analytics calculation"""
        analytics = analytics_service.calculate_comprehensive_analytics(
            portfolio_returns=sample_portfolio_data["portfolio_returns"],
            portfolio_values=sample_portfolio_data["portfolio_values"],
            positions=sample_portfolio_data["positions"],
            moex_returns=sample_portfolio_data["moex_returns"],
            rts_returns=sample_portfolio_data["rts_returns"],
            timestamps=sample_portfolio_data["timestamps"]
        )
        
        # Check that analytics object is created
        assert isinstance(analytics, PerformanceAnalytics)
        
        # Check basic metrics
        assert analytics.total_return != 0
        assert analytics.annualized_return != 0
        assert analytics.volatility >= 0
        assert analytics.sharpe_ratio != 0
        assert analytics.max_drawdown <= 0  # Should be negative
        
        # Check benchmark comparisons
        assert isinstance(analytics.moex_comparison, BenchmarkComparison)
        assert isinstance(analytics.rts_comparison, BenchmarkComparison)
        assert analytics.moex_comparison.beta != 0
        assert analytics.rts_comparison.beta != 0
        
        # Check sector performance
        assert len(analytics.sector_performance) > 0
        assert RussianSector.BANKING in analytics.sector_performance
        assert RussianSector.OIL_GAS in analytics.sector_performance
        
        # Check risk metrics
        assert "jensen_alpha_moex" in analytics.risk_adjusted_metrics
        assert "var_95" in analytics.risk_adjusted_metrics
    
    def test_empty_analytics_for_insufficient_data(self, analytics_service):
        """Test empty analytics when insufficient data"""
        analytics = analytics_service.calculate_comprehensive_analytics(
            portfolio_returns=[],
            portfolio_values=[],
            positions={},
            moex_returns=[],
            rts_returns=[],
            timestamps=[]
        )
        
        assert analytics.total_return == 0.0
        assert analytics.annualized_return == 0.0
        assert analytics.volatility == 0.0
        assert analytics.sharpe_ratio == 0.0
        assert len(analytics.sector_performance) == 0
    
    def test_calculate_annualized_return(self, analytics_service):
        """Test annualized return calculation"""
        # Test with positive returns
        returns = [0.01, 0.02, 0.015, -0.005, 0.008]  # 5 days
        annualized = analytics_service._calculate_annualized_return(returns)
        
        # Should be positive and reasonable
        assert annualized > 0
        assert annualized < 50  # Less than 5000% annually (reasonable for short period extrapolation)
        
        # Test with empty returns
        assert analytics_service._calculate_annualized_return([]) == 0.0
    
    def test_calculate_volatility(self, analytics_service):
        """Test volatility calculation"""
        returns = [0.01, -0.02, 0.015, -0.005, 0.008, 0.012, -0.007]
        volatility = analytics_service._calculate_volatility(returns)
        
        # Should be positive
        assert volatility > 0
        
        # Test with insufficient data
        assert analytics_service._calculate_volatility([0.01]) == 0.0
        assert analytics_service._calculate_volatility([]) == 0.0
    
    def test_calculate_sharpe_ratio(self, analytics_service):
        """Test Sharpe ratio calculation"""
        returns = [0.01, 0.02, 0.015, -0.005, 0.008]
        volatility = analytics_service._calculate_volatility(returns)
        sharpe = analytics_service._calculate_sharpe_ratio(returns, volatility)
        
        # Should be reasonable
        assert isinstance(sharpe, float)
        
        # Test with zero volatility
        assert analytics_service._calculate_sharpe_ratio(returns, 0.0) == 0.0
    
    def test_calculate_max_drawdown(self, analytics_service):
        """Test maximum drawdown calculation"""
        # Values that go up then down
        values = [1000, 1100, 1200, 1050, 900, 950, 1100]
        max_dd = analytics_service._calculate_max_drawdown(values)
        
        # Should be negative (drawdown from peak of 1200 to trough of 900)
        expected_dd = -(1200 - 900) / 1200  # -25%
        assert abs(max_dd - expected_dd) < 0.001
        
        # Test with insufficient data
        assert analytics_service._calculate_max_drawdown([1000]) == 0.0
        assert analytics_service._calculate_max_drawdown([]) == 0.0
    
    def test_calculate_sortino_ratio(self, analytics_service):
        """Test Sortino ratio calculation"""
        returns = [0.01, -0.02, 0.015, -0.005, 0.008, 0.012, -0.007]
        sortino = analytics_service._calculate_sortino_ratio(returns)
        
        assert isinstance(sortino, float)
        
        # Test with no negative returns
        positive_returns = [0.01, 0.02, 0.015, 0.008, 0.012]
        sortino_positive = analytics_service._calculate_sortino_ratio(positive_returns)
        assert sortino_positive > 0  # Should be positive or inf
        
        # Test with empty returns
        assert analytics_service._calculate_sortino_ratio([]) == 0.0
    
    def test_calculate_win_rate(self, analytics_service):
        """Test win rate calculation"""
        returns = [0.01, -0.02, 0.015, -0.005, 0.008]  # 3 positive, 2 negative
        win_rate = analytics_service._calculate_win_rate(returns)
        
        assert win_rate == 0.6  # 3/5 = 60%
        
        # Test with all positive
        assert analytics_service._calculate_win_rate([0.01, 0.02, 0.03]) == 1.0
        
        # Test with all negative
        assert analytics_service._calculate_win_rate([-0.01, -0.02, -0.03]) == 0.0
        
        # Test with empty
        assert analytics_service._calculate_win_rate([]) == 0.0
    
    def test_calculate_profit_factor(self, analytics_service):
        """Test profit factor calculation"""
        returns = [0.02, -0.01, 0.03, -0.015, 0.01]  # Profit: 0.06, Loss: 0.025
        profit_factor = analytics_service._calculate_profit_factor(returns)
        
        expected = 0.06 / 0.025  # 2.4
        assert abs(profit_factor - expected) < 0.001
        
        # Test with no losses
        assert analytics_service._calculate_profit_factor([0.01, 0.02, 0.03]) == float('inf')
        
        # Test with no profits
        assert analytics_service._calculate_profit_factor([-0.01, -0.02, -0.03]) == 0.0
        
        # Test with empty
        assert analytics_service._calculate_profit_factor([]) == 0.0
    
    def test_calculate_beta(self, analytics_service):
        """Test beta calculation"""
        portfolio_returns = [0.01, -0.02, 0.015, -0.005, 0.008]
        benchmark_returns = [0.008, -0.015, 0.012, -0.003, 0.006]
        
        beta = analytics_service._calculate_beta(portfolio_returns, benchmark_returns)
        
        # Beta should be reasonable
        assert isinstance(beta, float)
        assert beta > 0  # Positive correlation expected
        
        # Test with mismatched lengths
        assert analytics_service._calculate_beta([0.01], [0.01, 0.02]) == 0.0
        
        # Test with insufficient data
        assert analytics_service._calculate_beta([0.01], [0.01]) == 0.0
    
    def test_calculate_correlation(self, analytics_service):
        """Test correlation calculation"""
        returns1 = [0.01, -0.02, 0.015, -0.005, 0.008]
        returns2 = [0.008, -0.015, 0.012, -0.003, 0.006]
        
        correlation = analytics_service._calculate_correlation(returns1, returns2)
        
        # Correlation should be between -1 and 1
        assert -1 <= correlation <= 1
        
        # Test perfect correlation
        perfect_corr = analytics_service._calculate_correlation(returns1, returns1)
        assert abs(perfect_corr - 1.0) < 0.001
        
        # Test with insufficient data
        assert analytics_service._calculate_correlation([0.01], [0.01]) == 0.0
    
    def test_calculate_var_and_cvar(self, analytics_service):
        """Test VaR and CVaR calculations"""
        returns = [-0.05, -0.03, -0.01, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08]
        
        var_95 = analytics_service._calculate_var(returns, 0.95)
        cvar_95 = analytics_service._calculate_cvar(returns, 0.95)
        
        # VaR should be negative (worst 5% of returns)
        assert var_95 < 0
        
        # CVaR should be worse (more negative) than VaR
        assert cvar_95 <= var_95
        
        # Test with empty returns
        assert analytics_service._calculate_var([], 0.95) == 0.0
        assert analytics_service._calculate_cvar([], 0.95) == 0.0
    
    def test_sector_mappings(self, analytics_service):
        """Test Russian sector mappings"""
        # Test known mappings
        assert analytics_service.sector_mappings["SBER"] == RussianSector.BANKING
        assert analytics_service.sector_mappings["GAZP"] == RussianSector.OIL_GAS
        assert analytics_service.sector_mappings["YNDX"] == RussianSector.TECHNOLOGY
        assert analytics_service.sector_mappings["GMKN"] == RussianSector.METALS_MINING
    
    def test_calculate_sector_performance(self, analytics_service, sample_portfolio_data):
        """Test sector performance calculation"""
        sector_perf = analytics_service._calculate_sector_performance(
            positions=sample_portfolio_data["positions"],
            portfolio_returns=sample_portfolio_data["portfolio_returns"],
            timestamps=sample_portfolio_data["timestamps"]
        )
        
        # Should have multiple sectors
        assert len(sector_perf) > 0
        
        # Check that banking sector exists (SBER)
        assert RussianSector.BANKING in sector_perf
        banking_perf = sector_perf[RussianSector.BANKING]
        
        assert isinstance(banking_perf, SectorPerformance)
        assert banking_perf.sector == RussianSector.BANKING
        assert banking_perf.weight_in_portfolio > 0
        assert "SBER" in banking_perf.stocks
        
        # Check oil & gas sector (GAZP, LKOH)
        assert RussianSector.OIL_GAS in sector_perf
        oil_gas_perf = sector_perf[RussianSector.OIL_GAS]
        assert len(oil_gas_perf.stocks) == 2  # GAZP and LKOH
        assert "GAZP" in oil_gas_perf.stocks
        assert "LKOH" in oil_gas_perf.stocks
    
    def test_benchmark_comparison(self, analytics_service, sample_portfolio_data):
        """Test benchmark comparison calculation"""
        comparison = analytics_service._calculate_benchmark_comparison(
            portfolio_returns=sample_portfolio_data["portfolio_returns"],
            benchmark_returns=sample_portfolio_data["moex_returns"],
            benchmark_name="MOEX"
        )
        
        assert isinstance(comparison, BenchmarkComparison)
        assert comparison.beta != 0
        assert -1 <= comparison.correlation <= 1
        assert comparison.tracking_error >= 0
        
        # Test with empty data
        empty_comparison = analytics_service._calculate_benchmark_comparison([], [], "TEST")
        assert empty_comparison.alpha == 0
        assert empty_comparison.beta == 0
    
    def test_generate_performance_report(self, analytics_service, sample_portfolio_data):
        """Test performance report generation"""
        analytics = analytics_service.calculate_comprehensive_analytics(
            portfolio_returns=sample_portfolio_data["portfolio_returns"],
            portfolio_values=sample_portfolio_data["portfolio_values"],
            positions=sample_portfolio_data["positions"],
            moex_returns=sample_portfolio_data["moex_returns"],
            rts_returns=sample_portfolio_data["rts_returns"],
            timestamps=sample_portfolio_data["timestamps"]
        )
        
        report = analytics_service.generate_performance_report(analytics)
        
        # Check that report is generated
        assert isinstance(report, str)
        assert len(report) > 0
        
        # Check for Russian text
        assert "ОТЧЕТ О ПРОИЗВОДИТЕЛЬНОСТИ ПОРТФЕЛЯ" in report
        assert "ОСНОВНЫЕ ПОКАЗАТЕЛИ" in report
        assert "СРАВНЕНИЕ С БЕНЧМАРКАМИ" in report
        assert "MOEX Russia Index" in report
        assert "RTS Index" in report
        
        # Check for metrics
        assert "Коэффициент Шарпа" in report
        assert "Волатильность" in report
        assert "Максимальная просадка" in report
    
    def test_risk_free_rate_and_constants(self, analytics_service):
        """Test risk-free rate and trading constants"""
        assert analytics_service.risk_free_rate == 0.075  # 7.5% CBR rate
        assert analytics_service.trading_days_per_year == 252
    
    def test_jensen_alpha_calculation(self, analytics_service):
        """Test Jensen's alpha calculation"""
        portfolio_returns = [0.01, 0.02, -0.01, 0.015, 0.008]
        benchmark_returns = [0.008, 0.015, -0.005, 0.012, 0.006]
        
        alpha = analytics_service._calculate_jensen_alpha(portfolio_returns, benchmark_returns)
        
        # Alpha should be a reasonable number
        assert isinstance(alpha, float)
        
        # Test with empty data
        assert analytics_service._calculate_jensen_alpha([], []) == 0.0
    
    def test_treynor_ratio_calculation(self, analytics_service):
        """Test Treynor ratio calculation"""
        portfolio_returns = [0.01, 0.02, -0.01, 0.015, 0.008]
        benchmark_returns = [0.008, 0.015, -0.005, 0.012, 0.006]
        
        treynor = analytics_service._calculate_treynor_ratio(portfolio_returns, benchmark_returns)
        
        # Treynor ratio should be a reasonable number
        assert isinstance(treynor, float)
        
        # Test with zero beta
        zero_benchmark = [0.0] * len(portfolio_returns)
        treynor_zero = analytics_service._calculate_treynor_ratio(portfolio_returns, zero_benchmark)
        assert treynor_zero == 0.0


class TestRussianEnums:
    """Test Russian market enums"""
    
    def test_russian_index_enum(self):
        """Test Russian index enumeration"""
        assert RussianIndex.MOEX_RUSSIA.value == "MOEX Russia Index"
        assert RussianIndex.RTS.value == "RTS Index"
        assert RussianIndex.IMOEX.value == "IMOEX"
        assert RussianIndex.RTSI.value == "RTSI"
    
    def test_russian_sector_enum(self):
        """Test Russian sector enumeration"""
        assert RussianSector.OIL_GAS.value == "oil_gas"
        assert RussianSector.BANKING.value == "banking"
        assert RussianSector.METALS_MINING.value == "metals_mining"
        assert RussianSector.TELECOM.value == "telecom"
        assert RussianSector.UTILITIES.value == "utilities"
        assert RussianSector.CONSUMER.value == "consumer"
        assert RussianSector.TECHNOLOGY.value == "technology"
        assert RussianSector.REAL_ESTATE.value == "real_estate"
        assert RussianSector.INDUSTRIALS.value == "industrials"


class TestDataClasses:
    """Test data classes"""
    
    def test_benchmark_data(self):
        """Test BenchmarkData dataclass"""
        data = BenchmarkData(
            index=RussianIndex.MOEX_RUSSIA,
            timestamp=datetime.now(),
            value=Decimal("3500.50"),
            daily_return=0.015,
            volume=1000000
        )
        
        assert data.index == RussianIndex.MOEX_RUSSIA
        assert data.value == Decimal("3500.50")
        assert data.daily_return == 0.015
        assert data.volume == 1000000
    
    def test_sector_performance(self):
        """Test SectorPerformance dataclass"""
        perf = SectorPerformance(
            sector=RussianSector.BANKING,
            total_return=0.15,
            daily_return=0.01,
            weekly_return=0.03,
            monthly_return=0.12,
            volatility=0.25,
            sharpe_ratio=0.8,
            weight_in_portfolio=0.3,
            stocks=["SBER", "VTBR"]
        )
        
        assert perf.sector == RussianSector.BANKING
        assert perf.total_return == 0.15
        assert perf.weight_in_portfolio == 0.3
        assert "SBER" in perf.stocks
        assert "VTBR" in perf.stocks
    
    def test_benchmark_comparison(self):
        """Test BenchmarkComparison dataclass"""
        comparison = BenchmarkComparison(
            portfolio_return=0.12,
            benchmark_return=0.10,
            alpha=0.02,
            beta=1.1,
            correlation=0.85,
            tracking_error=0.05,
            information_ratio=0.4
        )
        
        assert comparison.portfolio_return == 0.12
        assert comparison.benchmark_return == 0.10
        assert comparison.alpha == 0.02
        assert comparison.beta == 1.1
        assert comparison.correlation == 0.85
    
    def test_performance_analytics(self):
        """Test PerformanceAnalytics dataclass"""
        analytics = PerformanceAnalytics(
            total_return=0.15,
            annualized_return=0.18,
            volatility=0.20,
            sharpe_ratio=0.9,
            max_drawdown=-0.08,
            calmar_ratio=2.25,
            sortino_ratio=1.2,
            win_rate=0.65,
            profit_factor=1.8,
            moex_comparison=BenchmarkComparison(0.15, 0.12, 0.03, 1.1, 0.85, 0.05, 0.6),
            rts_comparison=BenchmarkComparison(0.15, 0.14, 0.01, 1.2, 0.80, 0.06, 0.17),
            sector_performance={},
            risk_adjusted_metrics={"var_95": -0.03, "cvar_95": -0.045}
        )
        
        assert analytics.total_return == 0.15
        assert analytics.sharpe_ratio == 0.9
        assert analytics.max_drawdown == -0.08
        assert analytics.win_rate == 0.65
        assert analytics.risk_adjusted_metrics["var_95"] == -0.03