"""
Unit tests for enhanced alert manager
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from decimal import Decimal

from russian_trading_bot.models.notifications import (
    NotificationPreferences, NotificationChannel, NotificationPriority,
    TradingSignalAlert, PortfolioAlert, MarketAlert, GeopoliticalAlert
)
from russian_trading_bot.models.trading import TradingSignal, Portfolio, Position
from russian_trading_bot.models.market_data import MOEXMarketData
from russian_trading_bot.services.alert_manager import AlertManager
from russian_trading_bot.config.alert_config import AlertConfig


class TestAlertManager:
    """Test alert manager functionality"""
    
    @pytest.fixture
    def alert_config(self):
        """Test alert configuration"""
        return AlertConfig(
            email_username="test@example.com",
            email_password="test_password",
            telegram_bot_token="test_token",
            sms_api_key="test_sms_key",
            trading_signal_confidence_threshold=0.7,
            portfolio_loss_threshold=0.05,
            portfolio_gain_threshold=0.10
        )
    
    @pytest.fixture
    def alert_manager(self, alert_config):
        """Create alert manager instance"""
        return AlertManager(alert_config)
    
    @pytest.fixture
    def user_preferences(self):
        """Test user preferences"""
        return NotificationPreferences(
            user_id="test_user",
            email="user@example.com",
            telegram_chat_id="123456789",
            phone_number="+79001234567",
            min_trading_signal_confidence=0.75
        )
    
    @pytest.fixture
    def trading_signal(self):
        """Test trading signal"""
        from russian_trading_bot.models.trading import OrderAction
        return TradingSignal(
            symbol="SBER",
            action=OrderAction.BUY,
            confidence=0.85,
            target_price=Decimal("280.00"),
            stop_loss=Decimal("230.00")
        )
    
    @pytest.fixture
    def portfolio(self):
        """Test portfolio"""
        return Portfolio(
            positions={
                "SBER": Position(
                    symbol="SBER",
                    quantity=100,
                    average_price=Decimal("240.00"),
                    current_price=Decimal("250.50"),
                    market_value=Decimal("25050.00"),
                    unrealized_pnl=Decimal("1050.00")
                )
            },
            cash_balance=Decimal("50000.00"),
            total_value=Decimal("75050.00"),
            total_pnl=Decimal("1050.00")
        )
    
    def test_register_user_preferences(self, alert_manager, user_preferences):
        """Test registering user preferences"""
        alert_manager.register_user_preferences("test_user", user_preferences)
        
        assert "test_user" in alert_manager.user_preferences
        assert alert_manager.user_preferences["test_user"] == user_preferences
    
    @pytest.mark.asyncio
    async def test_send_trading_signal_alert_success(self, alert_manager, user_preferences, trading_signal):
        """Test successful trading signal alert"""
        # Register user
        alert_manager.register_user_preferences("test_user", user_preferences)
        
        # Mock notification service
        alert_manager.notification_service.send_trading_signal_alert = AsyncMock(
            return_value=[Mock(), Mock()]  # Two notifications sent
        )
        
        # Send alert
        result = await alert_manager.send_trading_signal_alert(
            "test_user", trading_signal, 0.85, "Test reasoning"
        )
        
        # Verify
        assert result is True
        assert alert_manager.alerts_sent_today == 2
        alert_manager.notification_service.send_trading_signal_alert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_trading_signal_alert_below_threshold(self, alert_manager, user_preferences, trading_signal):
        """Test trading signal alert below confidence threshold"""
        # Register user
        alert_manager.register_user_preferences("test_user", user_preferences)
        
        # Send alert with low confidence
        result = await alert_manager.send_trading_signal_alert(
            "test_user", trading_signal, 0.6, "Test reasoning"  # Below 0.75 threshold
        )
        
        # Verify
        assert result is False
        assert alert_manager.alerts_sent_today == 0
    
    @pytest.mark.asyncio
    async def test_send_trading_signal_alert_no_user(self, alert_manager, trading_signal):
        """Test trading signal alert for non-existent user"""
        result = await alert_manager.send_trading_signal_alert(
            "nonexistent_user", trading_signal, 0.85, "Test reasoning"
        )
        
        assert result is False
        assert alert_manager.alerts_sent_today == 0
    
    @pytest.mark.asyncio
    async def test_send_portfolio_alert_success(self, alert_manager, user_preferences, portfolio):
        """Test successful portfolio alert"""
        # Register user
        alert_manager.register_user_preferences("test_user", user_preferences)
        
        # Mock notification service
        alert_manager.notification_service.send_portfolio_alert = AsyncMock(
            return_value=[Mock()]  # One notification sent
        )
        
        # Send alert
        result = await alert_manager.send_portfolio_alert(
            "test_user", portfolio, "TEST_ALERT", Decimal("70000.00")
        )
        
        # Verify
        assert result is True
        assert alert_manager.alerts_sent_today == 1
        alert_manager.notification_service.send_portfolio_alert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_monitor_market_conditions(self, alert_manager, user_preferences):
        """Test market condition monitoring"""
        # Register user
        alert_manager.register_user_preferences("test_user", user_preferences)
        
        # Create test market data
        market_data = [
            MOEXMarketData(
                symbol="SBER",
                price=Decimal("250.50"),
                volume=1000000,
                timestamp=datetime.now(),
                change_percent=0.08,
                previous_close=Decimal("232.00")
            )
        ]
        
        # Mock market monitor methods
        alert_manager.market_monitor.monitor_market_volatility = AsyncMock(return_value=[])
        alert_manager.market_monitor.monitor_volume_spikes = AsyncMock(return_value=[])
        alert_manager.market_monitor.monitor_price_movements = AsyncMock(return_value=[])
        
        # Monitor market conditions
        results = await alert_manager.monitor_and_alert_market_conditions(
            market_data, ["test_user"]
        )
        
        # Verify
        assert "test_user" in results
        assert isinstance(results["test_user"], list)
        
        # Verify all monitoring methods were called
        alert_manager.market_monitor.monitor_market_volatility.assert_called_once()
        alert_manager.market_monitor.monitor_volume_spikes.assert_called_once()
        alert_manager.market_monitor.monitor_price_movements.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_monitor_geopolitical_events(self, alert_manager, user_preferences):
        """Test geopolitical event monitoring"""
        # Register user
        alert_manager.register_user_preferences("test_user", user_preferences)
        
        # Mock market monitor
        test_alert = GeopoliticalAlert(
            event_type="SANCTIONS",
            severity="HIGH",
            description="New sanctions announced",
            affected_sectors=["BANKING", "ENERGY"]
        )
        
        alert_manager.market_monitor.monitor_geopolitical_events = AsyncMock(
            return_value=[test_alert]
        )
        
        # Monitor geopolitical events
        results = await alert_manager.monitor_and_alert_geopolitical_events(["test_user"])
        
        # Verify
        assert "test_user" in results
        assert len(results["test_user"]) == 1
        assert results["test_user"][0] == test_alert
        assert alert_manager.alerts_sent_today == 1
    
    @pytest.mark.asyncio
    async def test_monitor_portfolio_risks(self, alert_manager, user_preferences, portfolio):
        """Test portfolio risk monitoring"""
        # Register user
        alert_manager.register_user_preferences("test_user", user_preferences)
        
        # Mock market monitor
        test_alert = PortfolioAlert(
            alert_type="RISK_THRESHOLD",
            current_value=portfolio.total_value,
            change_percent=-0.08
        )
        
        alert_manager.market_monitor.monitor_portfolio_risk_thresholds = AsyncMock(
            return_value=[test_alert]
        )
        
        # Monitor portfolio risks
        results = await alert_manager.monitor_portfolio_risks("test_user", portfolio)
        
        # Verify
        assert len(results) == 1
        assert results[0] == test_alert
        assert alert_manager.alerts_sent_today == 1
    
    @pytest.mark.asyncio
    async def test_send_custom_alert(self, alert_manager, user_preferences):
        """Test sending custom alert"""
        # Register user
        alert_manager.register_user_preferences("test_user", user_preferences)
        
        # Mock notification service
        alert_manager.notification_service.create_notification = Mock()
        alert_manager.notification_service.send_notification = AsyncMock(return_value=True)
        alert_manager.notification_service._get_recipient_for_channel = Mock(
            return_value="test@example.com"
        )
        
        # Send custom alert
        result = await alert_manager.send_custom_alert(
            "test_user", "TEST_ALERT", "Test Title", "Test Message"
        )
        
        # Verify
        assert result is True
        assert alert_manager.alerts_sent_today > 0
    
    def test_track_alert(self, alert_manager):
        """Test alert tracking"""
        # Track an alert
        alert_manager._track_alert("test_alert", "test_user", "SBER", 2)
        
        # Verify tracking
        assert len(alert_manager.alert_history) == 1
        
        alert_record = alert_manager.alert_history[0]
        assert alert_record['alert_type'] == "test_alert"
        assert alert_record['user_id'] == "test_user"
        assert alert_record['symbol'] == "SBER"
        assert alert_record['count'] == 2
        
        # Verify active alerts
        alert_key = "test_alert_test_user_SBER"
        assert alert_key in alert_manager.active_alerts
    
    def test_get_alert_statistics(self, alert_manager):
        """Test alert statistics"""
        # Add some test data
        alert_manager.alerts_sent_today = 10
        alert_manager.alerts_failed_today = 2
        alert_manager._track_alert("trading_signal", "user1", "SBER", 1)
        alert_manager._track_alert("portfolio_alert", "user2", "GAZP", 1)
        
        # Get statistics
        stats = alert_manager.get_alert_statistics()
        
        # Verify
        assert stats['alerts_sent_today'] == 10
        assert stats['alerts_failed_today'] == 2
        assert stats['success_rate_today'] == 10/12  # 10/(10+2)
        assert stats['alerts_last_7_days'] == 2
        assert 'trading_signal' in stats['alert_types_last_7_days']
        assert 'portfolio_alert' in stats['alert_types_last_7_days']
    
    @pytest.mark.asyncio
    async def test_health_check(self, alert_manager):
        """Test system health check"""
        # Mock services
        alert_manager.notification_service.get_notification_stats = Mock(
            return_value={'queued': 5, 'failed': 1}
        )
        
        alert_manager.market_monitor.get_market_condition = Mock(
            return_value=Mock(market_phase="NORMAL", volatility_index=0.02)
        )
        
        # Perform health check
        health = await alert_manager.health_check()
        
        # Verify
        assert health['status'] == 'healthy'
        assert 'timestamp' in health
        assert 'services' in health
        assert 'notification_service' in health['services']
        assert 'market_monitor' in health['services']
        assert 'alert_statistics' in health
    
    @pytest.mark.asyncio
    async def test_health_check_degraded(self, alert_manager):
        """Test health check with degraded status"""
        # Set up degraded conditions
        alert_manager.alerts_sent_today = 5
        alert_manager.alerts_failed_today = 10  # High failure rate
        
        # Mock services
        alert_manager.notification_service.get_notification_stats = Mock(
            return_value={'queued': 5, 'failed': 15}  # Many failed notifications
        )
        
        alert_manager.market_monitor.get_market_condition = Mock(
            return_value=Mock(market_phase="VOLATILE", volatility_index=0.12)  # High volatility
        )
        
        # Perform health check
        health = await alert_manager.health_check()
        
        # Verify degraded status
        assert health['status'] == 'degraded'
    
    @pytest.mark.asyncio
    async def test_process_notification_queue(self, alert_manager):
        """Test processing notification queue"""
        # Mock notification service
        alert_manager.notification_service.process_notification_queue = AsyncMock()
        
        # Process queue
        await alert_manager.process_notification_queue()
        
        # Verify
        alert_manager.notification_service.process_notification_queue.assert_called_once()
    
    def test_alert_history_cleanup(self, alert_manager):
        """Test alert history cleanup (keeps last 1000 alerts)"""
        # Add more than 1000 alerts
        for i in range(1200):
            alert_manager._track_alert(f"test_alert_{i}", "test_user", "SBER", 1)
        
        # Verify cleanup
        assert len(alert_manager.alert_history) == 1000
        
        # Verify we kept the most recent ones
        assert alert_manager.alert_history[0]['alert_type'] == "test_alert_200"
        assert alert_manager.alert_history[-1]['alert_type'] == "test_alert_1199"


class TestAlertConfig:
    """Test alert configuration"""
    
    def test_alert_config_defaults(self):
        """Test default alert configuration values"""
        config = AlertConfig()
        
        assert config.email_smtp_server == "smtp.gmail.com"
        assert config.email_smtp_port == 587
        assert config.trading_signal_confidence_threshold == 0.7
        assert config.portfolio_loss_threshold == 0.05
        assert config.quiet_hours_start == "22:00"
        assert config.quiet_hours_end == "08:00"
    
    def test_alert_config_custom_values(self):
        """Test custom alert configuration values"""
        config = AlertConfig(
            email_smtp_server="smtp.custom.com",
            email_smtp_port=465,
            trading_signal_confidence_threshold=0.8,
            portfolio_loss_threshold=0.03
        )
        
        assert config.email_smtp_server == "smtp.custom.com"
        assert config.email_smtp_port == 465
        assert config.trading_signal_confidence_threshold == 0.8
        assert config.portfolio_loss_threshold == 0.03
    
    def test_get_channels_for_priority(self):
        """Test getting channels for priority level"""
        config = AlertConfig()
        
        # Test critical priority
        critical_channels = config.get_channels_for_priority(NotificationPriority.CRITICAL)
        assert NotificationChannel.EMAIL in critical_channels
        assert NotificationChannel.TELEGRAM in critical_channels
        assert NotificationChannel.SMS in critical_channels
        
        # Test low priority
        low_channels = config.get_channels_for_priority(NotificationPriority.LOW)
        assert NotificationChannel.EMAIL in low_channels
        assert len(low_channels) == 1
    
    def test_to_dict(self):
        """Test converting config to dictionary"""
        config = AlertConfig(
            email_username="test@example.com",
            telegram_bot_token="test_token"
        )
        
        config_dict = config.to_dict()
        
        assert 'email' in config_dict
        assert 'telegram' in config_dict
        assert 'sms' in config_dict
        assert 'thresholds' in config_dict
        assert 'cooldowns' in config_dict
        assert 'quiet_hours' in config_dict
        
        assert config_dict['email']['username'] == "test@example.com"
        assert config_dict['telegram']['bot_token'] == "test_token"
    
    @patch.dict('os.environ', {
        'ALERT_EMAIL_USERNAME': 'env_test@example.com',
        'ALERT_TELEGRAM_BOT_TOKEN': 'env_test_token',
        'ALERT_SIGNAL_CONFIDENCE_THRESHOLD': '0.8'
    })
    def test_load_config_from_env(self):
        """Test loading configuration from environment variables"""
        from russian_trading_bot.config.alert_config import load_alert_config_from_env
        
        config = load_alert_config_from_env()
        
        assert config.email_username == 'env_test@example.com'
        assert config.telegram_bot_token == 'env_test_token'
        assert config.trading_signal_confidence_threshold == 0.8


if __name__ == "__main__":
    pytest.main([__file__])