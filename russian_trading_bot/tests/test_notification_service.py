"""
Unit tests for notification service
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, time
from decimal import Decimal

from russian_trading_bot.models.notifications import (
    NotificationTemplate, Notification, NotificationPreferences,
    NotificationType, NotificationChannel, NotificationPriority, NotificationStatus,
    TradingSignalAlert, PortfolioAlert, MarketAlert, GeopoliticalAlert
)
from russian_trading_bot.services.notification_service import NotificationService, TelegramBot


class TestNotificationService:
    """Test notification service functionality"""
    
    @pytest.fixture
    def config(self):
        """Test configuration"""
        return {
            'email': {
                'smtp_server': 'smtp.test.com',
                'smtp_port': 587,
                'username': 'test@example.com',
                'password': 'test_password',
                'from_email': 'bot@example.com'
            },
            'telegram': {
                'bot_token': 'test_token_123'
            },
            'sms': {
                'api_key': 'test_sms_key',
                'api_url': 'https://test.sms.api'
            }
        }
    
    @pytest.fixture
    def notification_service(self, config):
        """Create notification service instance"""
        return NotificationService(config)
    
    @pytest.fixture
    def preferences(self):
        """Test notification preferences"""
        return NotificationPreferences(
            user_id="test_user",
            email="user@example.com",
            telegram_chat_id="123456789",
            phone_number="+79001234567"
        )
    
    def test_create_notification_with_template(self, notification_service):
        """Test creating notification from template"""
        # Test data
        data = {
            'symbol': 'SBER',
            'action': 'BUY',
            'confidence': '85.0%',
            'current_price': '250.50 ₽',
            'target_price': '280.00 ₽',
            'stop_loss': '230.00 ₽',
            'reasoning': 'Технический анализ показывает восходящий тренд',
            'expected_return': '12.0%',
            'risk_score': '3.5%'
        }
        
        # Create notification
        notification = notification_service.create_notification(
            notification_type=NotificationType.TRADING_SIGNAL,
            priority=NotificationPriority.MEDIUM,
            channel=NotificationChannel.EMAIL,
            recipient="test@example.com",
            data=data,
            template_id="trading_signal_email"
        )
        
        # Verify notification
        assert notification.notification_type == NotificationType.TRADING_SIGNAL
        assert notification.priority == NotificationPriority.MEDIUM
        assert notification.channel == NotificationChannel.EMAIL
        assert notification.recipient == "test@example.com"
        assert "SBER" in notification.subject
        assert "BUY" in notification.subject
        assert "250.50 ₽" in notification.message
        assert notification.status == NotificationStatus.PENDING
    
    def test_create_notification_missing_template(self, notification_service):
        """Test creating notification with missing template"""
        data = {'symbol': 'SBER'}
        
        with pytest.raises(ValueError, match="No template found"):
            notification_service.create_notification(
                notification_type=NotificationType.SYSTEM_ALERT,  # No template for this
                priority=NotificationPriority.LOW,
                channel=NotificationChannel.EMAIL,
                recipient="test@example.com",
                data=data
            )
    
    @patch('smtplib.SMTP')
    async def test_send_email_notification(self, mock_smtp, notification_service):
        """Test sending email notification"""
        # Mock SMTP
        mock_server = Mock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        # Create notification
        notification = Notification(
            notification_id="test_123",
            notification_type=NotificationType.TRADING_SIGNAL,
            priority=NotificationPriority.MEDIUM,
            channel=NotificationChannel.EMAIL,
            recipient="test@example.com",
            subject="Test Subject",
            message="Test Message"
        )
        
        # Send notification
        result = await notification_service.send_notification(notification)
        
        # Verify
        assert result is True
        assert notification.status == NotificationStatus.SENT
        assert notification.sent_at is not None
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once()
        mock_server.send_message.assert_called_once()
    
    @patch('requests.post')
    async def test_send_telegram_notification(self, mock_post, notification_service):
        """Test sending Telegram notification"""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {'ok': True}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Create notification
        notification = Notification(
            notification_id="test_123",
            notification_type=NotificationType.PORTFOLIO_ALERT,
            priority=NotificationPriority.HIGH,
            channel=NotificationChannel.TELEGRAM,
            recipient="123456789",
            subject="Test Alert",
            message="Test Message"
        )
        
        # Send notification
        result = await notification_service.send_notification(notification)
        
        # Verify
        assert result is True
        assert notification.status == NotificationStatus.SENT
        mock_post.assert_called_once()
        
        # Check API call
        call_args = mock_post.call_args
        assert 'sendMessage' in call_args[0][0]
        assert call_args[1]['json']['chat_id'] == "123456789"
        assert 'Test Alert' in call_args[1]['json']['text']
    
    @patch('requests.post')
    async def test_send_sms_notification(self, mock_post, notification_service):
        """Test sending SMS notification"""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {'status': 'OK'}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Create notification
        notification = Notification(
            notification_id="test_123",
            notification_type=NotificationType.RISK_ALERT,
            priority=NotificationPriority.CRITICAL,
            channel=NotificationChannel.SMS,
            recipient="+79001234567",
            subject="Risk Alert",
            message="Portfolio loss threshold exceeded"
        )
        
        # Send notification
        result = await notification_service.send_notification(notification)
        
        # Verify
        assert result is True
        assert notification.status == NotificationStatus.SENT
        mock_post.assert_called_once()
        
        # Check API call
        call_args = mock_post.call_args
        assert call_args[1]['data']['to'] == "+79001234567"
        assert len(call_args[1]['data']['msg']) <= 160  # SMS length limit
    
    def test_quiet_hours_check(self, notification_service, preferences):
        """Test quiet hours functionality"""
        # Set quiet hours
        preferences.quiet_hours_start = "22:00"
        preferences.quiet_hours_end = "08:00"
        
        # Mock current time during quiet hours
        with patch('russian_trading_bot.services.notification_service.datetime') as mock_dt:
            # Test during quiet hours (23:00)
            mock_dt.now.return_value.time.return_value = time(23, 0)
            assert notification_service.is_quiet_hours(preferences) is True
            
            # Test during active hours (10:00)
            mock_dt.now.return_value.time.return_value = time(10, 0)
            assert notification_service.is_quiet_hours(preferences) is False
            
            # Test edge case (07:00 - still quiet)
            mock_dt.now.return_value.time.return_value = time(7, 0)
            assert notification_service.is_quiet_hours(preferences) is True
    
    async def test_send_trading_signal_alert(self, notification_service, preferences):
        """Test sending trading signal alert"""
        # Create signal data
        signal_data = TradingSignalAlert(
            symbol="GAZP",
            action="SELL",
            confidence=0.75,
            current_price=Decimal("180.50"),
            target_price=Decimal("160.00"),
            stop_loss=Decimal("190.00"),
            reasoning="Технический анализ показывает нисходящий тренд"
        )
        
        # Mock send_notification
        notification_service.send_notification = AsyncMock(return_value=True)
        
        # Send alert
        notifications = await notification_service.send_trading_signal_alert(
            signal_data, preferences
        )
        
        # Verify
        assert len(notifications) == 2  # Email and Telegram by default
        assert all(n.notification_type == NotificationType.TRADING_SIGNAL for n in notifications)
        assert notification_service.send_notification.call_count == 2
    
    async def test_send_trading_signal_below_threshold(self, notification_service, preferences):
        """Test trading signal below confidence threshold"""
        # Set high threshold
        preferences.min_trading_signal_confidence = 0.8
        
        # Create low confidence signal
        signal_data = TradingSignalAlert(
            symbol="SBER",
            action="BUY",
            confidence=0.6,  # Below threshold
            current_price=Decimal("250.00")
        )
        
        # Send alert
        notifications = await notification_service.send_trading_signal_alert(
            signal_data, preferences
        )
        
        # Verify no notifications sent
        assert len(notifications) == 0
    
    async def test_send_portfolio_alert(self, notification_service, preferences):
        """Test sending portfolio alert"""
        # Create portfolio alert data
        portfolio_data = PortfolioAlert(
            alert_type="ПРЕВЫШЕН_ПОРОГ_УБЫТКОВ",
            current_value=Decimal("950000.00"),
            threshold_value=Decimal("1000000.00"),
            change_amount=Decimal("-50000.00"),
            change_percent=-0.05,
            affected_positions=["SBER", "GAZP", "LKOH"]
        )
        
        # Mock send_notification
        notification_service.send_notification = AsyncMock(return_value=True)
        
        # Send alert
        notifications = await notification_service.send_portfolio_alert(
            portfolio_data, preferences
        )
        
        # Verify
        assert len(notifications) == 3  # Email, Telegram, SMS by default
        assert all(n.notification_type == NotificationType.PORTFOLIO_ALERT for n in notifications)
        assert notification_service.send_notification.call_count == 3
    
    async def test_notification_retry_logic(self, notification_service):
        """Test notification retry logic"""
        # Create failed notification
        notification = Notification(
            notification_id="test_retry",
            notification_type=NotificationType.MARKET_ALERT,
            priority=NotificationPriority.MEDIUM,
            channel=NotificationChannel.EMAIL,
            recipient="test@example.com",
            subject="Test",
            message="Test",
            status=NotificationStatus.FAILED,
            retry_count=1
        )
        
        # Add to queue
        notification_service.notification_queue.append(notification)
        
        # Mock successful retry
        notification_service.send_notification = AsyncMock(return_value=True)
        
        # Process queue
        await notification_service.process_notification_queue()
        
        # Verify
        assert len(notification_service.notification_queue) == 0
        assert notification.status == NotificationStatus.SENT
    
    async def test_notification_max_retries_exceeded(self, notification_service):
        """Test notification with max retries exceeded"""
        # Create notification with max retries
        notification = Notification(
            notification_id="test_max_retry",
            notification_type=NotificationType.SYSTEM_ALERT,
            priority=NotificationPriority.LOW,
            channel=NotificationChannel.EMAIL,
            recipient="test@example.com",
            subject="Test",
            message="Test",
            status=NotificationStatus.FAILED,
            retry_count=3,  # Max retries
            max_retries=3
        )
        
        # Add to queue
        notification_service.notification_queue.append(notification)
        
        # Process queue
        await notification_service.process_notification_queue()
        
        # Verify moved to failed
        assert len(notification_service.notification_queue) == 0
        assert len(notification_service.failed_notifications) == 1
        assert notification.status == NotificationStatus.FAILED
    
    def test_get_recipient_for_channel(self, notification_service, preferences):
        """Test getting recipient for different channels"""
        # Test email
        recipient = notification_service._get_recipient_for_channel(
            NotificationChannel.EMAIL, preferences
        )
        assert recipient == "user@example.com"
        
        # Test Telegram
        recipient = notification_service._get_recipient_for_channel(
            NotificationChannel.TELEGRAM, preferences
        )
        assert recipient == "123456789"
        
        # Test SMS
        recipient = notification_service._get_recipient_for_channel(
            NotificationChannel.SMS, preferences
        )
        assert recipient == "+79001234567"
        
        # Test unsupported channel
        recipient = notification_service._get_recipient_for_channel(
            NotificationChannel.PUSH, preferences
        )
        assert recipient is None


class TestTelegramBot:
    """Test Telegram bot functionality"""
    
    @pytest.fixture
    def telegram_bot(self):
        """Create Telegram bot instance"""
        return TelegramBot("test_token_123")
    
    @patch('requests.post')
    async def test_send_message(self, mock_post, telegram_bot):
        """Test sending Telegram message"""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {'ok': True}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Send message
        result = await telegram_bot.send_message(
            chat_id="123456789",
            text="Test message"
        )
        
        # Verify
        assert result is True
        mock_post.assert_called_once()
        
        # Check API call
        call_args = mock_post.call_args
        assert 'sendMessage' in call_args[0][0]
        assert call_args[1]['json']['chat_id'] == "123456789"
        assert call_args[1]['json']['text'] == "Test message"
    
    @patch('requests.post')
    async def test_send_trading_signal(self, mock_post, telegram_bot):
        """Test sending formatted trading signal"""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {'ok': True}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Create signal data
        signal_data = TradingSignalAlert(
            symbol="SBER",
            action="BUY",
            confidence=0.85,
            current_price=Decimal("250.50"),
            target_price=Decimal("280.00"),
            stop_loss=Decimal("230.00"),
            reasoning="Восходящий тренд"
        )
        
        # Send signal
        result = await telegram_bot.send_trading_signal(
            chat_id="123456789",
            signal_data=signal_data
        )
        
        # Verify
        assert result is True
        mock_post.assert_called_once()
        
        # Check message content
        call_args = mock_post.call_args
        message_text = call_args[1]['json']['text']
        assert "SBER" in message_text
        assert "BUY" in message_text
        assert "85.0%" in message_text
        assert "250.50 ₽" in message_text
    
    @patch('requests.post')
    async def test_send_portfolio_update(self, mock_post, telegram_bot):
        """Test sending portfolio update"""
        # Mock successful response
        mock_response = Mock()
        mock_response.json.return_value = {'ok': True}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Create portfolio data
        portfolio_data = PortfolioAlert(
            alert_type="ПРЕВЫШЕН_ПОРОГ_УБЫТКОВ",
            current_value=Decimal("950000.00"),
            change_amount=Decimal("-50000.00"),
            change_percent=-0.05
        )
        
        # Send update
        result = await telegram_bot.send_portfolio_update(
            chat_id="123456789",
            portfolio_data=portfolio_data
        )
        
        # Verify
        assert result is True
        mock_post.assert_called_once()
        
        # Check message content
        call_args = mock_post.call_args
        message_text = call_args[1]['json']['text']
        assert "ПРЕВЫШЕН_ПОРОГ_УБЫТКОВ" in message_text
        assert "950000.00 ₽" in message_text


class TestNotificationModels:
    """Test notification data models"""
    
    def test_trading_signal_alert_to_dict(self):
        """Test TradingSignalAlert to_dict conversion"""
        alert = TradingSignalAlert(
            symbol="GAZP",
            action="SELL",
            confidence=0.75,
            current_price=Decimal("180.50"),
            target_price=Decimal("160.00"),
            reasoning="Нисходящий тренд"
        )
        
        data = alert.to_dict()
        
        assert data['symbol'] == "GAZP"
        assert data['action'] == "SELL"
        assert data['confidence'] == "75.0%"
        assert data['current_price'] == "180.50 ₽"
        assert data['target_price'] == "160.00 ₽"
        assert data['reasoning'] == "Нисходящий тренд"
    
    def test_portfolio_alert_to_dict(self):
        """Test PortfolioAlert to_dict conversion"""
        alert = PortfolioAlert(
            alert_type="БОЛЬШИЕ_УБЫТКИ",
            current_value=Decimal("900000.00"),
            change_amount=Decimal("-100000.00"),
            change_percent=-0.10,
            affected_positions=["SBER", "GAZP"]
        )
        
        data = alert.to_dict()
        
        assert data['alert_type'] == "БОЛЬШИЕ_УБЫТКИ"
        assert data['current_value'] == "900000.00 ₽"
        assert data['change_amount'] == "-100000.00 ₽"
        assert data['change_percent'] == "-10.0%"
        assert data['affected_positions'] == "SBER, GAZP"
    
    def test_notification_preferences_defaults(self):
        """Test NotificationPreferences default values"""
        prefs = NotificationPreferences(user_id="test_user")
        
        # Check default channels
        assert NotificationChannel.EMAIL in prefs.trading_signals
        assert NotificationChannel.TELEGRAM in prefs.trading_signals
        assert NotificationChannel.SMS in prefs.portfolio_alerts
        
        # Check default thresholds
        assert prefs.min_trading_signal_confidence == 0.7
        assert prefs.portfolio_loss_threshold == 0.05
        assert prefs.portfolio_gain_threshold == 0.10
    
    def test_notification_preferences_get_channels(self):
        """Test getting channels for notification type"""
        prefs = NotificationPreferences(
            user_id="test_user",
            trading_signals=[NotificationChannel.TELEGRAM],
            portfolio_alerts=[NotificationChannel.EMAIL, NotificationChannel.SMS]
        )
        
        # Test trading signals
        channels = prefs.get_channels_for_type(NotificationType.TRADING_SIGNAL)
        assert channels == [NotificationChannel.TELEGRAM]
        
        # Test portfolio alerts
        channels = prefs.get_channels_for_type(NotificationType.PORTFOLIO_ALERT)
        assert channels == [NotificationChannel.EMAIL, NotificationChannel.SMS]
        
        # Test unknown type (should default to email)
        channels = prefs.get_channels_for_type(NotificationType.SYSTEM_ALERT)
        assert NotificationChannel.EMAIL in channels


if __name__ == "__main__":
    pytest.main([__file__])