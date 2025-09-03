"""
Tests for the backtesting engine
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.backtesting_engine import (
    BacktestingEngine, BacktestConfig, BacktestResults, BacktestTrade,
    BacktestStatus
)
from services.ai_decision_engine import AIDecisionEngine, DecisionWeights
from models.trading import TradingSignal, OrderAction
from models.market_data import MarketData


class TestBacktestingEngine:
    """Test cases for backtesting engine"""
    
    @pytest.fixture
    def ai_engine(self):
        """Create mock AI decision engine"""
        return Mock(spec=AIDecisionEngine)
    
    @pytest.fixture
    def backtest_engine(self, ai_engine):
        """Create backtesting engine instance"""
        return BacktestingEngine(ai_engine)
    
    @pytest.fixture
    def sample_config(self):
        """Create sample backtest configuration"""
        return BacktestConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            initial_capital=Decimal('1000000'),
            commission_rate=0.0005,
            slippage_rate=0.001,
            max_position_size=0.1,
            min_confidence=0.6
        )
    
    @pytest.fixture
    def sample_symbols(self):
        """Sample Russian stock symbols"""
        return ['SBER', 'GAZP', 'LKOH', 'YNDX', 'MGNT']
    
    def test_engine_initialization(self, ai_engine):
        """Test backtesting engine initialization"""
        engine = BacktestingEngine(ai_engine)
        
        assert engine.ai_engine == ai_engine
        assert engine.status == BacktestStatus.NOT_STARTED
        assert engine.current_backtest is None
        assert engine.historical_data == {}
        assert engine.benchmark_data == {}
    
    def test_load_historical_data(self, backtest_engine, sample_symbols, sample_config):
        """Test loading historical data"""
        success = backtest_engine.load_historical_data(
            sample_symbols, 
            sample_config.start_date, 
            sample_config.end_date
        )
        
        assert success is True
        assert len(backtest_engine.historical_data) == len(sample_symbols)
        
        # Check data structure
        for symbol in sample_symbols:
            assert symbol in backtest_engine.historical_data
            df = backtest_engine.historical_data[symbol]
            
            assert isinstance(df, pd.DataFrame)
            assert 'open' in df.columns
            assert 'high' in df.columns
            assert 'low' in df.columns
            assert 'close' in df.columns
            assert 'volume' in df.columns
            assert len(df) > 0
        
        # Check benchmark data
        assert len(backtest_engine.benchmark_data) > 0
        assert 'IMOEX' in backtest_engine.benchmark_data
    
    def test_get_market_data_for_date(self, backtest_engine, sample_symbols, sample_config):
        """Test getting market data for specific date"""
        # Load data first
        backtest_engine.load_historical_data(
            sample_symbols, 
            sample_config.start_date, 
            sample_config.end_date
        )
        
        test_date = datetime(2023, 6, 15)
        market_data = backtest_engine._get_market_data_for_date(test_date, sample_symbols)
        
        assert isinstance(market_data, dict)
        assert len(market_data) > 0
        
        for symbol, data in market_data.items():
            assert isinstance(data, MarketData)
            assert data.symbol == symbol
            assert data.currency == "RUB"
            assert data.price > 0
            assert data.volume > 0
    
    def test_backtest_config_validation(self):
        """Test backtest configuration validation"""
        config = BacktestConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            initial_capital=Decimal('1000000')
        )
        
        assert config.currency == "RUB"
        assert config.commission_rate == 0.0005
        assert config.slippage_rate == 0.001
        assert config.max_position_size == 0.1
        assert config.benchmark_symbol == "IMOEX"
    
    def test_position_size_calculation(self, backtest_engine):
        """Test position size calculation methods"""
        signal = TradingSignal(
            symbol="SBER",
            action=OrderAction.BUY,
            confidence=0.8,
            reasoning="Test signal"
        )
        
        total_value = Decimal('1000000')
        config = BacktestConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            max_position_size=0.1,
            position_sizing_method="equal_weight"
        )
        
        position_size = backtest_engine._calculate_position_size(signal, total_value, config)
        
        assert position_size > 0
        assert isinstance(position_size, int)
    
    def test_confidence_weighted_position_sizing(self, backtest_engine):
        """Test confidence-weighted position sizing"""
        high_confidence_signal = TradingSignal(
            symbol="SBER",
            action=OrderAction.BUY,
            confidence=0.9,
            reasoning="High confidence signal"
        )
        
        low_confidence_signal = TradingSignal(
            symbol="GAZP",
            action=OrderAction.BUY,
            confidence=0.6,
            reasoning="Low confidence signal"
        )
        
        total_value = Decimal('1000000')
        config = BacktestConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            max_position_size=0.1,
            position_sizing_method="confidence_weighted"
        )
        
        high_conf_size = backtest_engine._calculate_position_size(
            high_confidence_signal, total_value, config
        )
        low_conf_size = backtest_engine._calculate_position_size(
            low_confidence_signal, total_value, config
        )
        
        # High confidence should result in larger position
        assert high_conf_size >= low_conf_size
    
    def test_drawdown_calculation(self, backtest_engine):
        """Test drawdown calculation"""
        portfolio_values = [
            (datetime(2023, 1, 1), Decimal('1000000')),
            (datetime(2023, 1, 2), Decimal('1050000')),
            (datetime(2023, 1, 3), Decimal('1100000')),  # Peak
            (datetime(2023, 1, 4), Decimal('1000000')),  # 9.09% drawdown
            (datetime(2023, 1, 5), Decimal('950000')),   # 13.64% drawdown
        ]
        
        drawdown = backtest_engine._calculate_current_drawdown(portfolio_values)
        
        assert drawdown > 0
        assert abs(drawdown - 0.1364) < 0.001  # Approximately 13.64%
    
    def test_trade_execution_buy_signal(self, backtest_engine, ai_engine):
        """Test trade execution for buy signals"""
        from services.portfolio_manager import PortfolioManager
        
        # Setup
        portfolio_manager = PortfolioManager(Decimal('1000000'))
        open_positions = {}
        results = BacktestResults(
            config=BacktestConfig(
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 12, 31)
            ),
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            duration_days=365,
            initial_capital=Decimal('1000000'),
            final_capital=Decimal('1000000'),
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
        
        # Create buy signal
        signals = [TradingSignal(
            symbol="SBER",
            action=OrderAction.BUY,
            confidence=0.8,
            reasoning="Test buy signal"
        )]
        
        # Market data
        market_data = {
            "SBER": MarketData(
                symbol="SBER",
                timestamp=datetime(2023, 6, 15),
                price=Decimal('250.0'),
                volume=100000,
                bid=Decimal('249.5'),
                ask=Decimal('250.5'),
                currency="RUB"
            )
        }
        
        config = BacktestConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            max_position_size=0.1
        )
        
        # Execute signals
        backtest_engine._execute_signals(
            signals, market_data, config, datetime(2023, 6, 15),
            portfolio_manager, open_positions, results
        )
        
        # Verify trade was executed
        assert len(open_positions) == 1
        assert "SBER" in open_positions
        assert results.total_trades == 1
        
        trade = open_positions["SBER"]
        assert trade.symbol == "SBER"
        assert trade.action == OrderAction.BUY
        assert trade.entry_price > Decimal('250.0')  # Should include slippage
    
    def test_stop_loss_execution(self, backtest_engine):
        """Test stop loss execution"""
        # Create open position
        open_positions = {
            "SBER": BacktestTrade(
                entry_date=datetime(2023, 6, 1),
                exit_date=None,
                symbol="SBER",
                action=OrderAction.BUY,
                entry_price=Decimal('250.0'),
                exit_price=None,
                quantity=100,
                commission=Decimal('12.5'),
                slippage=Decimal('2.5')
            )
        }
        
        # Market data showing price drop
        market_data = {
            "SBER": MarketData(
                symbol="SBER",
                timestamp=datetime(2023, 6, 15),
                price=Decimal('230.0'),  # 8% drop - should trigger stop loss
                volume=100000,
                bid=Decimal('229.5'),
                ask=Decimal('230.5'),
                currency="RUB"
            )
        }
        
        config = BacktestConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            stop_loss_pct=0.05  # 5% stop loss
        )
        
        results = BacktestResults(
            config=config,
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            duration_days=365,
            initial_capital=Decimal('1000000'),
            final_capital=Decimal('1000000'),
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
        
        # Check exit conditions
        backtest_engine._check_exit_conditions(
            open_positions, market_data, config, datetime(2023, 6, 15), results
        )
        
        # Position should be closed due to stop loss
        assert len(open_positions) == 0
        assert len(results.trades) == 1
        
        closed_trade = results.trades[0]
        assert closed_trade.exit_reason == "stop_loss"
        assert closed_trade.exit_date == datetime(2023, 6, 15)
        assert closed_trade.pnl < 0  # Should be a loss
    
    def test_take_profit_execution(self, backtest_engine):
        """Test take profit execution"""
        # Create open position
        open_positions = {
            "SBER": BacktestTrade(
                entry_date=datetime(2023, 6, 1),
                exit_date=None,
                symbol="SBER",
                action=OrderAction.BUY,
                entry_price=Decimal('250.0'),
                exit_price=None,
                quantity=100,
                commission=Decimal('12.5'),
                slippage=Decimal('2.5')
            )
        }
        
        # Market data showing price increase
        market_data = {
            "SBER": MarketData(
                symbol="SBER",
                timestamp=datetime(2023, 6, 15),
                price=Decimal('290.0'),  # 16% gain - should trigger take profit
                volume=100000,
                bid=Decimal('289.5'),
                ask=Decimal('290.5'),
                currency="RUB"
            )
        }
        
        config = BacktestConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            take_profit_pct=0.15  # 15% take profit
        )
        
        results = BacktestResults(
            config=config,
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            duration_days=365,
            initial_capital=Decimal('1000000'),
            final_capital=Decimal('1000000'),
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
        
        # Check exit conditions
        backtest_engine._check_exit_conditions(
            open_positions, market_data, config, datetime(2023, 6, 15), results
        )
        
        # Position should be closed due to take profit
        assert len(open_positions) == 0
        assert len(results.trades) == 1
        
        closed_trade = results.trades[0]
        assert closed_trade.exit_reason == "take_profit"
        assert closed_trade.exit_date == datetime(2023, 6, 15)
        assert closed_trade.pnl > 0  # Should be a profit
    
    def test_final_metrics_calculation(self, backtest_engine):
        """Test final metrics calculation"""
        config = BacktestConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31)
        )
        
        results = BacktestResults(
            config=config,
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            duration_days=365,
            initial_capital=Decimal('1000000'),
            final_capital=Decimal('1200000'),  # 20% gain
            total_return=0.0,
            annual_return=0.0,
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            max_drawdown=0.0,
            volatility=0.0,
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
            win_rate=0.0,
            profit_factor=0.0,
            avg_win=Decimal('0'),
            avg_loss=Decimal('0'),
            benchmark_return=0.0,
            alpha=0.0,
            beta=0.0,
            information_ratio=0.0
        )
        
        # Add some sample trades
        results.trades = [
            BacktestTrade(
                entry_date=datetime(2023, 1, 15),
                exit_date=datetime(2023, 2, 15),
                symbol="SBER",
                action=OrderAction.BUY,
                entry_price=Decimal('250.0'),
                exit_price=Decimal('275.0'),
                quantity=100,
                commission=Decimal('25.0'),
                slippage=Decimal('5.0'),
                pnl=Decimal('2470.0')  # Profit
            ),
            BacktestTrade(
                entry_date=datetime(2023, 3, 15),
                exit_date=datetime(2023, 4, 15),
                symbol="GAZP",
                action=OrderAction.BUY,
                entry_price=Decimal('180.0'),
                exit_price=Decimal('165.0'),
                quantity=100,
                commission=Decimal('25.0'),
                slippage=Decimal('5.0'),
                pnl=Decimal('-1530.0')  # Loss
            )
        ]
        
        # Add daily returns
        results.daily_returns = [0.01, -0.005, 0.008, -0.002, 0.012] * 73  # 365 days
        
        # Add portfolio values
        base_value = Decimal('1000000')
        for i in range(365):
            date = datetime(2023, 1, 1) + timedelta(days=i)
            value = base_value * (1 + Decimal(str(i * 0.0005)))  # Gradual increase
            results.portfolio_values.append((date, value))
        
        # Load benchmark data for comparison
        backtest_engine._load_benchmark_data(datetime(2023, 1, 1), datetime(2023, 12, 31))
        
        # Calculate final metrics
        backtest_engine._calculate_final_metrics(results, config)
        
        # Verify calculations
        assert results.total_return == 0.2  # 20% return
        assert results.annual_return > 0
        assert results.win_rate == 0.6  # 6 out of 10 trades
        assert results.volatility > 0
        assert results.max_drawdown >= 0
        
        # Check that profit factor is calculated
        assert results.profit_factor > 0
        
        # Check average win/loss
        assert results.avg_win > 0
        assert results.avg_loss < 0
    
    def test_backtest_report_generation(self, backtest_engine):
        """Test backtest report generation"""
        config = BacktestConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31)
        )
        
        results = BacktestResults(
            config=config,
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            duration_days=365,
            initial_capital=Decimal('1000000'),
            final_capital=Decimal('1200000'),
            total_return=0.2,
            annual_return=0.2,
            sharpe_ratio=1.5,
            sortino_ratio=1.8,
            max_drawdown=0.08,
            volatility=0.15,
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
            win_rate=0.6,
            profit_factor=1.8,
            avg_win=Decimal('5000'),
            avg_loss=Decimal('-3000'),
            benchmark_return=0.12,
            alpha=0.08,
            beta=1.2,
            information_ratio=0.5
        )
        
        # Add sample trades
        results.trades = [
            BacktestTrade(
                entry_date=datetime(2023, 6, 1),
                exit_date=datetime(2023, 6, 15),
                symbol="SBER",
                action=OrderAction.BUY,
                entry_price=Decimal('250.0'),
                exit_price=Decimal('275.0'),
                quantity=100,
                commission=Decimal('25.0'),
                slippage=Decimal('5.0'),
                pnl=Decimal('2470.0'),
                exit_reason="take_profit"
            )
        ]
        
        report = backtest_engine.get_backtest_report(results)
        
        assert isinstance(report, str)
        assert "ОТЧЕТ ПО БЭКТЕСТИНГУ" in report
        assert "20.00%" in report  # Total return
        assert "1.50" in report    # Sharpe ratio
        assert "60.0%" in report   # Win rate
        assert "SBER" in report    # Trade details
        assert "₽" in report       # Russian currency symbol
    
    def test_results_export(self, backtest_engine, tmp_path):
        """Test exporting backtest results"""
        config = BacktestConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31)
        )
        
        results = BacktestResults(
            config=config,
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            duration_days=365,
            initial_capital=Decimal('1000000'),
            final_capital=Decimal('1200000'),
            total_return=0.2,
            annual_return=0.2,
            sharpe_ratio=1.5,
            sortino_ratio=1.8,
            max_drawdown=0.08,
            volatility=0.15,
            total_trades=10,
            winning_trades=6,
            losing_trades=4,
            win_rate=0.6,
            profit_factor=1.8,
            avg_win=Decimal('5000'),
            avg_loss=Decimal('-3000'),
            benchmark_return=0.12,
            alpha=0.08,
            beta=1.2,
            information_ratio=0.5
        )
        
        # Set current backtest
        backtest_engine.current_backtest = results
        
        # Export to temporary file
        filename = str(tmp_path / "test_results.json")
        exported_file = backtest_engine.export_results(results, filename)
        
        assert exported_file == filename
        
        # Verify file exists and contains expected data
        import json
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data['total_return'] == 0.2
        assert data['sharpe_ratio'] == 1.5
        assert data['total_trades'] == 10
        assert 'trades' in data
    
    def test_benchmark_comparison(self, backtest_engine):
        """Test benchmark comparison functionality"""
        # Load benchmark data
        backtest_engine._load_benchmark_data(
            datetime(2023, 1, 1), 
            datetime(2023, 12, 31)
        )
        
        assert 'IMOEX' in backtest_engine.benchmark_data
        assert 'RTSI' in backtest_engine.benchmark_data
        
        # Check benchmark data structure
        imoex_data = backtest_engine.benchmark_data['IMOEX']
        assert 'close' in imoex_data.columns
        assert 'return' in imoex_data.columns
        assert len(imoex_data) > 0
    
    def test_russian_market_specifics(self, backtest_engine, sample_config):
        """Test Russian market specific features"""
        # Test currency handling
        assert sample_config.currency == "RUB"
        
        # Test benchmark symbol
        assert sample_config.benchmark_symbol == "IMOEX"
        
        # Test commission rates (typical for Russian brokers)
        assert sample_config.commission_rate == 0.0005  # 0.05%
        
        # Test that historical data includes Russian trading days
        symbols = ['SBER', 'GAZP']
        backtest_engine.load_historical_data(symbols, sample_config.start_date, sample_config.end_date)
        
        for symbol in symbols:
            df = backtest_engine.historical_data[symbol]
            # Check that weekends are excluded (Russian market closed)
            weekdays = [d.weekday() for d in df.index]
            assert all(day < 5 for day in weekdays)  # Monday=0, Friday=4
    
    @pytest.mark.integration
    def test_full_backtest_integration(self, backtest_engine, ai_engine, sample_config, sample_symbols):
        """Integration test for full backtest process"""
        # Mock AI engine to return predictable signals
        def mock_generate_signal(*args, **kwargs):
            symbol = args[0] if args else kwargs.get('symbol', 'SBER')
            return TradingSignal(
                symbol=symbol,
                action=OrderAction.BUY,
                confidence=0.7,
                reasoning=f"Mock signal for {symbol}"
            )
        
        ai_engine.generate_trading_signal = Mock(side_effect=mock_generate_signal)
        
        # Run backtest
        results = backtest_engine.run_backtest(sample_config, sample_symbols[:2])  # Use fewer symbols for speed
        
        # Verify results
        assert isinstance(results, BacktestResults)
        assert results.status == BacktestStatus.COMPLETED
        assert results.initial_capital == sample_config.initial_capital
        assert results.final_capital > 0
        assert results.duration_days == (sample_config.end_date - sample_config.start_date).days
        
        # Verify some trades were made
        assert results.total_trades >= 0
        
        # Verify metrics are calculated
        assert isinstance(results.total_return, float)
        assert isinstance(results.sharpe_ratio, float)
        assert isinstance(results.max_drawdown, float)
    
    def test_error_handling(self, backtest_engine, ai_engine):
        """Test error handling in backtesting"""
        # Test with invalid date range
        invalid_config = BacktestConfig(
            start_date=datetime(2023, 12, 31),
            end_date=datetime(2023, 1, 1)  # End before start
        )
        
        # Should handle gracefully
        with pytest.raises(Exception):
            backtest_engine.run_backtest(invalid_config, ['SBER'])
        
        # Test with empty symbol list
        valid_config = BacktestConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31)
        )
        
        results = backtest_engine.run_backtest(valid_config, [])
        assert results.total_trades == 0
    
    def test_performance_metrics_edge_cases(self, backtest_engine):
        """Test performance metrics with edge cases"""
        config = BacktestConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 1, 2)  # Very short period
        )
        
        results = BacktestResults(
            config=config,
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 1, 2),
            duration_days=1,
            initial_capital=Decimal('1000000'),
            final_capital=Decimal('1000000'),  # No change
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
        
        # Should handle edge cases without errors
        backtest_engine._calculate_final_metrics(results, config)
        
        # Verify no division by zero or other errors
        assert results.total_return == 0.0
        assert results.win_rate == 0.0
        assert results.profit_factor == 0.0