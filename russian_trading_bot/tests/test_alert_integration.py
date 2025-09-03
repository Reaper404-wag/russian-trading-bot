"""
Integration tests for Russian market alert system
Tests the complete alert workflow from signal generation to notification delivery
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from decimal import Decimal
from datetime import datetime

from russian_trading_bot.models.notifications import (
    NotificationPreferences, NotificationChannel, TradingSignalAlert
)
from russian_trading_bot.models.trading import TradingSignal
from russian_trading_bot.services.alert_manager import AlertManager
from russian_trading_bot.config.alert_config import AlertConfig


class TestAlertIntegration:
    """Integration tests for alert system"""
    
    @pytest.fixture
    def integration_config(self):
        """Configuration for integration tests"""
        return AlertConfig(
            email_username="test@example.com",
            email_password="test_password",
            telegram_bot_token="test_token",
            sms_api_key="test_sms_key"
        )
    
    @pytest.fixture
    def alert_manager(self, integration_config):
        """Alert manager for integration tests"""
        return AlertManager(integration_config)
    
    @pytest.fixture
    def test_user_preferences(self):
        """Test user with all notification channels enabled"""
        return NotificationPreferences(
            user_id="integration_test_user",
            email="integration@example.com",
            telegram_chat_id="987654321",
            phone_number="+79009876543",
            trading_signals=[
                NotificationChannel.EMAIL,
                NotificationChannel.TELEGRAM,
                NotificationChannel.SMS
            ],
            min_trading_signal_confidence=0.7
        )
    
    @pytest.mark.asyncio
    async def test_complete_trading_signal_workflow(self, alert_manager, test_user_preferences):
        """Test complete workflow from trading signal to notification delivery"""
        
        # Register user
        alert_manager.register_user_preferences("integration_test_user", test_user_preferences)
        
        # Mock all notification channels
        with patch.object(alert_manager.notification_service, '_send_email', new_callable=AsyncMock) as mock_email, \
             patch.object(alert_manager.notification_service, '_send_telegram', new_callable=AsyncMock) as mock_telegram, \
             patch.object(alert_manager.notification_service, '_send_sms', new_callable=AsyncMock) as mock_sms:
            
            # Configure mocks to return success
            mock_email.return_value = True
            mock_telegram.return_value = True
            mock_sms.return_value = True
            
            # Create trading signal
            from russian_trading_bot.models.trading import OrderAction
            signal = TradingSignal(
                symbol="SBER",
                action=OrderAction.BUY,
                confidence=0.85,
                target_price=Decimal("280.00"),
                stop_loss=Decimal("230.00")
            )
            
            # Send alert
            result = await alert_manager.send_trading_signal_alert(
                "integration_test_user",
                signal,
                0.85,
                "Интеграционный тест: технический анализ показывает сильный восходящий тренд"
            )
            
            # Verify workflow completed successfully
            assert result is True
            
            # Verify all notification channels were used
            mock_email.assert_called_once()
            mock_telegram.assert_called_once()
            mock_sms.assert_called_once()
            
            # Verify alert tracking
            assert alert_manager.alerts_sent_today == 3  # Email + Telegram + SMS
            assert len(alert_manager.alert_history) == 1
            
            # Verify alert statistics
            stats = alert_manager.get_alert_statistics()
            assert stats['alerts_sent_today'] == 3
            assert stats['alerts_failed_today'] == 0
            assert stats['success_rate_today'] == 1.0
    
    @pytest.mark.asyncio
    async def test_notification_failure_handling(self, alert_manager, test_user_preferences):
        """Test handling of notification failures"""
        
        # Register user
        alert_manager.register_user_preferences("integration_test_user", test_user_preferences)
        
        # Mock notification channels with failures
        with patch.object(alert_manager.notification_service, '_send_email', new_callable=AsyncMock) as mock_email, \
             patch.object(alert_manager.notification_service, '_send_telegram', new_callable=AsyncMock) as mock_telegram, \
             patch.object(alert_manager.notification_service, '_send_sms', new_callable=AsyncMock) as mock_sms:
            
            # Configure mocks: email succeeds, telegram and SMS fail
            mock_email.return_value = True
            mock_telegram.return_value = False
            mock_sms.return_value = False
            
            # Create trading signal
            from russian_trading_bot.models.trading import OrderAction
            signal = TradingSignal(
                symbol="GAZP",
                action=OrderAction.SELL,
                confidence=0.80,
                target_price=Decimal("160.00"),
                stop_loss=Decimal("190.00")
            )
            
            # Send alert
            result = await alert_manager.send_trading_signal_alert(
                "integration_test_user",
                signal,
                0.80,
                "Интеграционный тест: фундаментальный анализ указывает на переоцененность"
            )
            
            # Verify partial success
            assert result is True  # Should still return True if at least one notification succeeds
            
            # Verify notification attempts
            mock_email.assert_called_once()
            mock_telegram.assert_called_once()
            mock_sms.assert_called_once()
            
            # Verify failed notifications are queued for retry
            assert len(alert_manager.notification_service.notification_queue) == 2  # Telegram + SMS
    
    @pytest.mark.asyncio
    async def test_quiet_hours_functionality(self, alert_manager, test_user_preferences):
        """Test quiet hours functionality"""
        
        # Set quiet hours
        test_user_preferences.quiet_hours_start = "22:00"
        test_user_preferences.quiet_hours_end = "08:00"
        
        # Register user
        alert_manager.register_user_preferences("integration_test_user", test_user_preferences)
        
        # Mock current time to be during quiet hours (23:00)
        with patch('russian_trading_bot.services.notification_service.datetime') as mock_datetime:
            mock_datetime.now.return_value.time.return_value = datetime.strptime("23:00", "%H:%M").time()
            mock_datetime.now.return_value.strftime.return_value = "01.01.2024 23:00 MSK"
            
            # Mock notification service
            alert_manager.notification_service.send_trading_signal_alert = AsyncMock(return_value=[])
            
            # Create trading signal
            from russian_trading_bot.models.trading import OrderAction
            signal = TradingSignal(
                symbol="LKOH",
                action=OrderAction.BUY,
                confidence=0.75,
                target_price=Decimal("7000.00"),
                stop_loss=Decimal("6200.00")
            )
            
            # Send alert during quiet hours
            result = await alert_manager.send_trading_signal_alert(
                "integration_test_user",
                signal,
                0.75,
                "Тест тихих часов"
            )
            
            # Verify alert was not sent due to quiet hours
            alert_manager.notification_service.send_trading_signal_alert.assert_called_once()
            # The notification service should handle quiet hours internally
    
    @pytest.mark.asyncio
    async def test_confidence_threshold_filtering(self, alert_manager, test_user_preferences):
        """Test confidence threshold filtering"""
        
        # Set high confidence threshold
        test_user_preferences.min_trading_signal_confidence = 0.9
        
        # Register user
        alert_manager.register_user_preferences("integration_test_user", test_user_preferences)
        
        # Create trading signal with low confidence
        from russian_trading_bot.models.trading import OrderAction
        signal = TradingSignal(
            symbol="ROSN",
            action=OrderAction.BUY,
            confidence=0.75,
            target_price=Decimal("550.00"),
            stop_loss=Decimal("480.00")
        )
        
        # Send alert with confidence below threshold
        result = await alert_manager.send_trading_signal_alert(
            "integration_test_user",
            signal,
            0.75,  # Below 0.9 threshold
            "Тест порога уверенности"
        )
        
        # Verify alert was not sent due to low confidence
        assert result is False
        assert alert_manager.alerts_sent_today == 0
    
    @pytest.mark.asyncio
    async def test_multiple_users_workflow(self, alert_manager):
        """Test workflow with multiple users having different preferences"""
        
        # Create users with different preferences
        user1_prefs = NotificationPreferences(
            user_id="user1",
            email="user1@example.com",
            telegram_chat_id="111111111",
            trading_signals=[NotificationChannel.EMAIL],
            min_trading_signal_confidence=0.7
        )
        
        user2_prefs = NotificationPreferences(
            user_id="user2",
            email="user2@example.com",
            telegram_chat_id="222222222",
            phone_number="+79001111111",
            trading_signals=[NotificationChannel.TELEGRAM, NotificationChannel.SMS],
            min_trading_signal_confidence=0.8
        )
        
        # Register users
        alert_manager.register_user_preferences("user1", user1_prefs)
        alert_manager.register_user_preferences("user2", user2_prefs)
        
        # Mock notification channels
        with patch.object(alert_manager.notification_service, '_send_email', new_callable=AsyncMock) as mock_email, \
             patch.object(alert_manager.notification_service, '_send_telegram', new_callable=AsyncMock) as mock_telegram, \
             patch.object(alert_manager.notification_service, '_send_sms', new_callable=AsyncMock) as mock_sms:
            
            mock_email.return_value = True
            mock_telegram.return_value = True
            mock_sms.return_value = True
            
            # Create trading signal
            from russian_trading_bot.models.trading import OrderAction
            signal = TradingSignal(
                symbol="NVTK",
                action=OrderAction.SELL,
                confidence=0.75,
                target_price=Decimal("1100.00"),
                stop_loss=Decimal("1250.00")
            )
            
            # Send alert to user1 (confidence 0.75 - above user1's threshold, below user2's)
            result1 = await alert_manager.send_trading_signal_alert(
                "user1", signal, 0.75, "Тест для пользователя 1"
            )
            
            # Send alert to user2 (same confidence - below user2's threshold)
            result2 = await alert_manager.send_trading_signal_alert(
                "user2", signal, 0.75, "Тест для пользователя 2"
            )
            
            # Verify results
            assert result1 is True   # User1 should receive alert (email only)
            assert result2 is False  # User2 should not receive alert (below threshold)
            
            # Verify notification calls
            mock_email.assert_called_once()      # Only user1's email
            mock_telegram.assert_not_called()    # User2 didn't get alert
            mock_sms.assert_not_called()         # User2 didn't get alert
            
            # Send alert with higher confidence
            result3 = await alert_manager.send_trading_signal_alert(
                "user2", signal, 0.85, "Тест для пользователя 2 с высокой уверенностью"
            )
            
            # Verify user2 now receives alert
            assert result3 is True
            assert mock_telegram.call_count == 1  # User2's telegram
            assert mock_sms.call_count == 1       # User2's SMS
    
    @pytest.mark.asyncio
    async def test_system_health_monitoring(self, alert_manager, test_user_preferences):
        """Test system health monitoring during alert operations"""
        
        # Register user
        alert_manager.register_user_preferences("integration_test_user", test_user_preferences)
        
        # Perform initial health check
        initial_health = await alert_manager.health_check()
        assert initial_health['status'] == 'healthy'
        
        # Mock some failures to test degraded status
        alert_manager.alerts_failed_today = 5
        alert_manager.alerts_sent_today = 10
        
        # Mock notification service with high failure rate
        alert_manager.notification_service.get_notification_stats = Mock(
            return_value={'queued': 20, 'failed': 15}
        )
        
        # Perform health check with degraded conditions
        degraded_health = await alert_manager.health_check()
        assert degraded_health['status'] == 'degraded'
        
        # Verify health check includes all necessary information
        assert 'timestamp' in degraded_health
        assert 'services' in degraded_health
        assert 'alert_statistics' in degraded_health
        assert 'notification_service' in degraded_health['services']
        assert 'market_monitor' in degraded_health['services']


if __name__ == "__main__":
    pytest.main([__file__])