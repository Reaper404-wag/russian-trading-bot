"""
Tests for the paper trading engine
"""

import pytest
import time
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch
import threading

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.paper_trading_engine import (
    PaperTradingEngine, PaperTradingConfig, PaperTradingStatus,
    PaperTrade, PaperTradingSession
)
from services.ai_decision_engine import AIDecisionEngine
from models.trading import TradingSignal, OrderAction
from models.market_data import MarketData


class TestPaperTradingEngine:
    """Test cases for paper trading engine"""
    
    @pytest.fixture
    def ai_engine(self):
        """Create mock AI decision engine"""
        return Mock(spec=AIDecisionEngine)
    
    @pytest.fixture
    def paper_config(self):
        """Create paper trading configuration"""
        return PaperTradingConfig(
            initial_capital=Decimal('1000000'),
            commission_rate=0.0005,
            slippage_rate=0.001,
            max_position_size=0.1,
            min_confidence=0.6,
            update_interval=1,  # 1 second for testing
            market_hours_only=False,  # Allow trading anytime for tests
            auto_execute=True
        )
    
    @pytest.fixture
    def paper_engine(self, ai_engine, paper_config):
        """Create paper trading engine instance"""
        return PaperTradingEngine(ai_engine, paper_config)
    
    @pytest.fixture
    def mock_market_data_provider(self):
        """Create mock market data provider"""
        def provider(symbols):
            data = {}
            for symbol in symbols:
                data[symbol] = MarketData(
                    symbol=symbol,
                    timestamp=datetime.now(),
                    price=Decimal('250.0'),
                    volume=100000,
                    bid=Decimal('249.5'),
                    ask=Decimal('250.5'),
                    currency="RUB"
                )
            return data
        return provider
    
    def test_engine_initialization(self, ai_engine, paper_config):
        """Test paper trading engine initialization"""
        engine = PaperTradingEngine(ai_engine, paper_config)
        
        assert engine.ai_engine == ai_engine
        assert engine.config == paper_config
        assert engine.status == PaperTradingStatus.STOPPED
        assert engine.current_session is None
        assert engine.portfolio_manager is None
        assert engine.symbols == []
        assert engine.open_positions == {}
    
    def test_config_validation(self):
        """Test paper trading configuration"""
        config = PaperTradingConfig(
            initial_capital=Decimal('500000'),
            commission_rate=0.001,
            max_position_size=0.15
        )
        
        assert config.initial_capital == Decimal('500000')
        assert config.commission_rate == 0.001
        assert config.max_position_size == 0.15
        assert config.currency == "RUB"
        assert config.stop_loss_pct == 0.05
        assert config.take_profit_pct == 0.15
    
    def test_market_data_provider_setup(self, paper_engine, mock_market_data_provider):
        """Test setting up market data provider"""
        paper_engine.set_market_data_provider(mock_market_data_provider)
        
        assert paper_engine.market_data_provider == mock_market_data_provider
        
        # Test data retrieval
        symbols = ['SBER', 'GAZP']
        data = paper_engine.market_data_provider(symbols)
        
        assert len(data) == 2
        assert 'SBER' in data
        assert 'GAZP' in data
        assert data['SBER'].price == Decimal('250.0')
    
    def test_symbols_setup(self, paper_engine):
        """Test setting trading symbols"""
        symbols = ['SBER', 'GAZP', 'LKOH']
        paper_engine.set_symbols(symbols)
        
        assert paper_engine.symbols == symbols
    
    def test_session_start_validation(self, paper_engine):
        """Test session start validation"""
        # Should fail without market data provider
        with pytest.raises(ValueError, match="Market data provider not set"):
            paper_engine.start_session()
        
        # Should fail without symbols
        paper_engine.set_market_data_provider(Mock())
        with pytest.raises(ValueError, match="No symbols set"):
            paper_engine.start_session()
    
    def test_session_lifecycle(self, paper_engine, mock_market_data_provider):
        """Test complete session lifecycle"""
        # Setup
        paper_engine.set_market_data_provider(mock_market_data_provider)
        paper_engine.set_symbols(['SBER', 'GAZP'])
        
        # Start session
        session_id = paper_engine.start_session("test_session")
        
        assert session_id == "test_session"
        assert paper_engine.status == PaperTradingStatus.RUNNING
        assert paper_engine.current_session is not None
        assert paper_engine.current_session.session_id == "test_session"
        assert paper_engine.portfolio_manager is not None
        
        # Wait a moment for thread to start
        time.sleep(0.1)
        
        # Pause session
        paper_engine.pause_session()
        assert paper_engine.status == PaperTradingStatus.PAUSED
        
        # Resume session
        paper_engine.resume_session()
        assert paper_engine.status == PaperTradingStatus.RUNNING
        
        # Stop session
        paper_engine.stop_session()
        assert paper_engine.status == PaperTradingStatus.STOPPED
        assert paper_engine.current_session.end_time is not None
    
    def test_paper_trade_creation(self):
        """Test paper trade object creation and P&L calculation"""
        trade = PaperTrade(
            trade_id="test_trade_001",
            timestamp=datetime.now(),
            symbol="SBER",
            action=OrderAction.BUY,
            quantity=100,
            price=Decimal('250.0'),
            commission=Decimal('12.5'),
            slippage=Decimal('2.5'),
            signal_confidence=0.8,
            reasoning="Test trade",
            execution_time=datetime.now(),
            execution_price=Decimal('252.5'),
            status="executed"
        )
        
        # Test unrealized P&L calculation
        current_price = Decimal('260.0')
        pnl = trade.calculate_pnl(current_price)
        
        # P&L = (260 - 252.5) * 100 - 12.5 - 2.5 = 750 - 15 = 735
        expected_pnl = Decimal('735.0')
        assert abs(pnl - expected_pnl) < Decimal('0.01')
        
        # Test realized P&L calculation
        trade.exit_price = Decimal('270.0')
        trade.exit_time = datetime.now()
        
        realized_pnl = trade.calculate_pnl(Decimal('270.0'))
        # P&L = (270 - 252.5) * 100 - 12.5 - 2.5 = 1750 - 15 = 1735
        expected_realized = Decimal('1735.0')
        assert abs(realized_pnl - expected_realized) < Decimal('0.01')
    
    def test_position_size_calculation(self, paper_engine, mock_market_data_provider):
        """Test position size calculation methods"""
        # Setup engine
        paper_engine.set_market_data_provider(mock_market_data_provider)
        paper_engine.set_symbols(['SBER'])
        session_id = paper_engine.start_session()
        
        # Test equal weight sizing
        signal = TradingSignal(
            symbol="SBER",
            action=OrderAction.BUY,
            confidence=0.8,
            reasoning="Test signal"
        )
        
        position_size = paper_engine._calculate_position_size(signal)
        assert position_size > 0
        assert isinstance(position_size, int)
        
        # Test confidence weighted sizing
        paper_engine.config.position_sizing_method = "confidence_weighted"
        
        high_conf_signal = TradingSignal(
            symbol="SBER",
            action=OrderAction.BUY,
            confidence=0.9,
            reasoning="High confidence signal"
        )
        
        low_conf_signal = TradingSignal(
            symbol="SBER",
            action=OrderAction.BUY,
            confidence=0.6,
            reasoning="Low confidence signal"
        )
        
        high_size = paper_engine._calculate_position_size(high_conf_signal)
        low_size = paper_engine._calculate_position_size(low_conf_signal)
        
        # High confidence should result in larger position
        assert high_size >= low_size
        
        paper_engine.stop_session()
    
    def test_market_hours_check(self, paper_engine):
        """Test market hours validation"""
        # Mock datetime to test different times
        with patch('services.paper_trading_engine.datetime') as mock_datetime:
            # Test during market hours (Wednesday 14:00)
            mock_datetime.now.return_value = datetime(2023, 6, 14, 14, 0)  # Wednesday 2PM
            assert paper_engine._is_market_hours() == True
            
            # Test before market hours (Wednesday 9:00)
            mock_datetime.now.return_value = datetime(2023, 6, 14, 9, 0)   # Wednesday 9AM
            assert paper_engine._is_market_hours() == False
            
            # Test after market hours (Wednesday 19:00)
            mock_datetime.now.return_value = datetime(2023, 6, 14, 19, 0)  # Wednesday 7PM
            assert paper_engine._is_market_hours() == False
            
            # Test weekend (Saturday 14:00)
            mock_datetime.now.return_value = datetime(2023, 6, 17, 14, 0)  # Saturday 2PM
            assert paper_engine._is_market_hours() == False
    
    def test_signal_execution(self, paper_engine, mock_market_data_provider, ai_engine):
        """Test trading signal execution"""
        # Setup
        paper_engine.set_market_data_provider(mock_market_data_provider)
        paper_engine.set_symbols(['SBER'])
        
        # Mock AI engine to return a signal
        mock_signal = TradingSignal(
            symbol="SBER",
            action=OrderAction.BUY,
            confidence=0.8,
            reasoning="Test buy signal"
        )
        ai_engine.generate_trading_signal.return_value = mock_signal
        
        session_id = paper_engine.start_session()
        
        # Create market data
        market_data = mock_market_data_provider(['SBER'])
        
        # Execute signal manually
        paper_engine._execute_signal(mock_signal, market_data['SBER'])
        
        # Verify trade was executed
        assert len(paper_engine.open_positions) == 1
        assert 'SBER' in paper_engine.open_positions
        
        trade = paper_engine.open_positions['SBER']
        assert trade.symbol == 'SBER'
        assert trade.action == OrderAction.BUY
        assert trade.status == 'executed'
        assert trade.signal_confidence == 0.8
        
        paper_engine.stop_session()
    
    def test_stop_loss_execution(self, paper_engine, mock_market_data_provider):
        """Test stop loss execution"""
        # Setup
        paper_engine.set_market_data_provider(mock_market_data_provider)
        paper_engine.set_symbols(['SBER'])
        session_id = paper_engine.start_session()
        
        # Create a position manually
        trade = PaperTrade(
            trade_id="test_001",
            timestamp=datetime.now(),
            symbol="SBER",
            action=OrderAction.BUY,
            quantity=100,
            price=Decimal('250.0'),
            commission=Decimal('12.5'),
            slippage=Decimal('2.5'),
            signal_confidence=0.8,
            reasoning="Test trade",
            execution_time=datetime.now(),
            execution_price=Decimal('250.0'),
            status="executed"
        )
        
        paper_engine.open_positions['SBER'] = trade
        
        # Create market data with price drop triggering stop loss
        def stop_loss_provider(symbols):
            return {
                'SBER': MarketData(
                    symbol='SBER',
                    timestamp=datetime.now(),
                    price=Decimal('230.0'),  # 8% drop - should trigger 5% stop loss
                    volume=100000,
                    bid=Decimal('229.5'),
                    ask=Decimal('230.5'),
                    currency="RUB"
                )
            }
        
        market_data = stop_loss_provider(['SBER'])
        
        # Check exit conditions
        paper_engine._check_exit_conditions(market_data)
        
        # Position should be closed
        assert len(paper_engine.open_positions) == 0
        assert trade.exit_reason == "stop_loss"
        assert trade.exit_price is not None
        
        paper_engine.stop_session()
    
    def test_take_profit_execution(self, paper_engine, mock_market_data_provider):
        """Test take profit execution"""
        # Setup
        paper_engine.set_market_data_provider(mock_market_data_provider)
        paper_engine.set_symbols(['SBER'])
        session_id = paper_engine.start_session()
        
        # Create a position manually
        trade = PaperTrade(
            trade_id="test_001",
            timestamp=datetime.now(),
            symbol="SBER",
            action=OrderAction.BUY,
            quantity=100,
            price=Decimal('250.0'),
            commission=Decimal('12.5'),
            slippage=Decimal('2.5'),
            signal_confidence=0.8,
            reasoning="Test trade",
            execution_time=datetime.now(),
            execution_price=Decimal('250.0'),
            status="executed"
        )
        
        paper_engine.open_positions['SBER'] = trade
        
        # Create market data with price increase triggering take profit
        def take_profit_provider(symbols):
            return {
                'SBER': MarketData(
                    symbol='SBER',
                    timestamp=datetime.now(),
                    price=Decimal('290.0'),  # 16% gain - should trigger 15% take profit
                    volume=100000,
                    bid=Decimal('289.5'),
                    ask=Decimal('290.5'),
                    currency="RUB"
                )
            }
        
        market_data = take_profit_provider(['SBER'])
        
        # Check exit conditions
        paper_engine._check_exit_conditions(market_data)
        
        # Position should be closed
        assert len(paper_engine.open_positions) == 0
        assert trade.exit_reason == "take_profit"
        assert trade.exit_price is not None
        
        paper_engine.stop_session()
    
    def test_daily_trade_limit(self, paper_engine, mock_market_data_provider):
        """Test daily trade limit enforcement"""
        # Set low daily limit for testing
        paper_engine.config.max_daily_trades = 2
        
        # Setup
        paper_engine.set_market_data_provider(mock_market_data_provider)
        paper_engine.set_symbols(['SBER', 'GAZP', 'LKOH'])
        
        # Simulate reaching daily limit
        paper_engine.daily_trades_count = 2
        
        # Should not execute more trades
        signal = TradingSignal(
            symbol="LKOH",
            action=OrderAction.BUY,
            confidence=0.8,
            reasoning="Test signal"
        )
        
        market_data = mock_market_data_provider(['LKOH'])
        
        # This should not execute due to daily limit
        initial_positions = len(paper_engine.open_positions)
        paper_engine._execute_signal(signal, market_data['LKOH'])
        
        # No new position should be created
        assert len(paper_engine.open_positions) == initial_positions
    
    def test_session_summary(self, paper_engine, mock_market_data_provider):
        """Test session summary generation"""
        # Setup and start session
        paper_engine.set_market_data_provider(mock_market_data_provider)
        paper_engine.set_symbols(['SBER'])
        session_id = paper_engine.start_session()
        
        # Add some mock trades to session
        paper_engine.current_session.total_trades = 5
        paper_engine.current_session.winning_trades = 3
        paper_engine.current_session.losing_trades = 2
        paper_engine.current_session.current_capital = Decimal('1050000')
        
        summary = paper_engine.current_session.get_summary()
        
        assert summary['session_id'] == session_id
        assert summary['total_trades'] == 5
        assert summary['winning_trades'] == 3
        assert summary['losing_trades'] == 2
        assert summary['win_rate'] == 0.6
        assert summary['total_return'] == 0.05  # 5% return
        assert 'duration_hours' in summary
        
        paper_engine.stop_session()
    
    def test_status_reporting(self, paper_engine, mock_market_data_provider):
        """Test status reporting functionality"""
        # Initial status
        status = paper_engine.get_current_status()
        
        assert status['status'] == 'stopped'
        assert status['session_active'] == False
        assert status['open_positions'] == 0
        
        # Start session and check status
        paper_engine.set_market_data_provider(mock_market_data_provider)
        paper_engine.set_symbols(['SBER', 'GAZP'])
        session_id = paper_engine.start_session()
        
        status = paper_engine.get_current_status()
        
        assert status['status'] == 'running'
        assert status['session_active'] == True
        assert status['symbols_count'] == 2
        assert 'portfolio' in status
        
        paper_engine.stop_session()
    
    def test_manual_operations(self, paper_engine, mock_market_data_provider):
        """Test manual trading operations"""
        # Setup
        paper_engine.set_market_data_provider(mock_market_data_provider)
        paper_engine.set_symbols(['SBER'])
        session_id = paper_engine.start_session()
        
        # Manual signal execution
        signal = TradingSignal(
            symbol="SBER",
            action=OrderAction.BUY,
            confidence=0.8,
            reasoning="Manual test signal"
        )
        
        success = paper_engine.manual_execute_signal(signal)
        assert success == True
        assert len(paper_engine.open_positions) == 1
        
        # Manual position closing
        success = paper_engine.manual_close_position('SBER', 'manual_test')
        assert success == True
        assert len(paper_engine.open_positions) == 0
        
        paper_engine.stop_session()
    
    def test_data_export(self, paper_engine, mock_market_data_provider, tmp_path):
        """Test session data export"""
        # Setup and run session
        paper_engine.set_market_data_provider(mock_market_data_provider)
        paper_engine.set_symbols(['SBER'])
        session_id = paper_engine.start_session()
        
        # Add some mock data
        paper_engine.current_session.total_trades = 3
        paper_engine.current_session.winning_trades = 2
        paper_engine.current_session.losing_trades = 1
        
        # Export data
        filename = str(tmp_path / "test_session.json")
        exported_file = paper_engine.export_session_data(filename)
        
        assert exported_file == filename
        
        # Verify file exists and contains expected data
        import json
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert 'session_info' in data
        assert 'config' in data
        assert 'trade_history' in data
        assert 'symbols' in data
        assert data['session_info']['total_trades'] == 3
        assert data['symbols'] == ['SBER']
        
        paper_engine.stop_session()
    
    def test_error_handling(self, paper_engine):
        """Test error handling in paper trading"""
        # Test with invalid market data provider
        def failing_provider(symbols):
            raise Exception("Market data error")
        
        paper_engine.set_market_data_provider(failing_provider)
        paper_engine.set_symbols(['SBER'])
        
        # Should handle errors gracefully
        session_id = paper_engine.start_session()
        
        # Wait a moment for thread to encounter error
        time.sleep(0.2)
        
        # Engine should still be running despite errors
        assert paper_engine.status in [PaperTradingStatus.RUNNING, PaperTradingStatus.ERROR]
        
        paper_engine.stop_session()
    
    def test_callback_system(self, paper_engine, mock_market_data_provider):
        """Test callback system for events"""
        # Setup callbacks
        trade_executed_calls = []
        position_closed_calls = []
        signal_generated_calls = []
        error_calls = []
        
        def on_trade_executed(trade):
            trade_executed_calls.append(trade)
        
        def on_position_closed(trade):
            position_closed_calls.append(trade)
        
        def on_signal_generated(signal):
            signal_generated_calls.append(signal)
        
        def on_error(error):
            error_calls.append(error)
        
        paper_engine.on_trade_executed = on_trade_executed
        paper_engine.on_position_closed = on_position_closed
        paper_engine.on_signal_generated = on_signal_generated
        paper_engine.on_error = on_error
        
        # Setup and start session
        paper_engine.set_market_data_provider(mock_market_data_provider)
        paper_engine.set_symbols(['SBER'])
        session_id = paper_engine.start_session()
        
        # Execute a trade manually to trigger callback
        signal = TradingSignal(
            symbol="SBER",
            action=OrderAction.BUY,
            confidence=0.8,
            reasoning="Callback test"
        )
        
        market_data = mock_market_data_provider(['SBER'])
        paper_engine._execute_signal(signal, market_data['SBER'])
        
        # Verify callback was called
        assert len(trade_executed_calls) == 1
        assert trade_executed_calls[0].symbol == 'SBER'
        
        paper_engine.stop_session()
    
    @pytest.mark.integration
    def test_full_paper_trading_workflow(self, paper_engine, mock_market_data_provider, ai_engine):
        """Integration test for full paper trading workflow"""
        # Mock AI engine to return predictable signals
        def mock_generate_signal(*args, **kwargs):
            symbol = kwargs.get('symbol', 'SBER')
            return TradingSignal(
                symbol=symbol,
                action=OrderAction.BUY,
                confidence=0.7,
                reasoning=f"Mock signal for {symbol}"
            )
        
        ai_engine.generate_trading_signal = Mock(side_effect=mock_generate_signal)
        
        # Setup
        paper_engine.set_market_data_provider(mock_market_data_provider)
        paper_engine.set_symbols(['SBER', 'GAZP'])
        
        # Start session
        session_id = paper_engine.start_session()
        
        # Let it run for a short time
        time.sleep(2)
        
        # Check that system is working
        status = paper_engine.get_current_status()
        assert status['status'] == 'running'
        assert status['session_active'] == True
        
        # Stop session
        paper_engine.stop_session()
        
        # Verify session completed
        assert paper_engine.status == PaperTradingStatus.STOPPED
        assert paper_engine.current_session.end_time is not None
        
        # Get final summary
        summary = paper_engine.current_session.get_summary()
        assert isinstance(summary, dict)
        assert 'total_return' in summary