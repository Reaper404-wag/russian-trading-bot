"""
Notification service for Russian trading bot alerts
Handles email, Telegram, and SMS notifications in Russian
"""

import smtplib
import asyncio
import logging
from datetime import datetime, time
from typing import List, Dict, Optional, Any
import email.mime.text
import email.mime.multipart
import email.header
import uuid
import pytz
import requests
import json

from ..models.notifications import (
    Notification, NotificationTemplate, NotificationPreferences,
    NotificationType, NotificationChannel, NotificationPriority, NotificationStatus,
    TradingSignalAlert, PortfolioAlert, MarketAlert, GeopoliticalAlert,
    RUSSIAN_TEMPLATES
)


class NotificationService:
    """Service for sending notifications in Russian"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize notification service with configuration"""
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.moscow_tz = pytz.timezone('Europe/Moscow')
        
        # Email configuration
        self.smtp_server = config.get('email', {}).get('smtp_server', 'smtp.gmail.com')
        self.smtp_port = config.get('email', {}).get('smtp_port', 587)
        self.email_user = config.get('email', {}).get('username')
        self.email_password = config.get('email', {}).get('password')
        self.from_email = config.get('email', {}).get('from_email', self.email_user)
        
        # Telegram configuration
        self.telegram_token = config.get('telegram', {}).get('bot_token')
        self.telegram_api_url = f"https://api.telegram.org/bot{self.telegram_token}"
        
        # SMS configuration (using SMS.ru as example)
        self.sms_api_key = config.get('sms', {}).get('api_key')
        self.sms_api_url = config.get('sms', {}).get('api_url', 'https://sms.ru/sms/send')
        
        # Templates
        self.templates = RUSSIAN_TEMPLATES.copy()
        
        # Notification queue
        self.notification_queue = []
        self.failed_notifications = []
    
    def add_template(self, template: NotificationTemplate) -> None:
        """Add custom notification template"""
        self.templates[template.template_id] = template
    
    def create_notification(
        self,
        notification_type: NotificationType,
        priority: NotificationPriority,
        channel: NotificationChannel,
        recipient: str,
        data: Dict[str, Any],
        template_id: Optional[str] = None
    ) -> Notification:
        """Create notification from template and data"""
        
        # Select template
        if template_id and template_id in self.templates:
            template = self.templates[template_id]
        else:
            # Find default template for type and channel
            template_key = f"{notification_type.value}_{channel.value}"
            template = self.templates.get(template_key)
            
            if not template:
                # Fallback to first available template for type
                for t in self.templates.values():
                    if t.notification_type == notification_type:
                        template = t
                        break
        
        if not template:
            raise ValueError(f"No template found for {notification_type.value}")
        
        # Add timestamp to data
        data['timestamp'] = datetime.now(self.moscow_tz).strftime('%d.%m.%Y %H:%M MSK')
        
        # Format message
        try:
            formatted = template.format_message(**data)
        except ValueError as e:
            self.logger.error(f"Template formatting error: {e}")
            raise
        
        # Create notification
        notification = Notification(
            notification_id=str(uuid.uuid4()),
            notification_type=notification_type,
            priority=priority,
            channel=channel,
            recipient=recipient,
            subject=formatted['subject'],
            message=formatted['body'],
            data=data
        )
        
        return notification
    
    async def send_notification(self, notification: Notification) -> bool:
        """Send notification via appropriate channel"""
        try:
            if notification.channel == NotificationChannel.EMAIL:
                success = await self._send_email(notification)
            elif notification.channel == NotificationChannel.TELEGRAM:
                success = await self._send_telegram(notification)
            elif notification.channel == NotificationChannel.SMS:
                success = await self._send_sms(notification)
            else:
                self.logger.error(f"Unsupported channel: {notification.channel}")
                return False
            
            if success:
                notification.status = NotificationStatus.SENT
                notification.sent_at = datetime.now()
                self.logger.info(f"Notification {notification.notification_id} sent successfully")
            else:
                notification.status = NotificationStatus.FAILED
                notification.retry_count += 1
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error sending notification {notification.notification_id}: {e}")
            notification.status = NotificationStatus.FAILED
            notification.error_message = str(e)
            notification.retry_count += 1
            return False
    
    async def _send_email(self, notification: Notification) -> bool:
        """Send email notification"""
        if not self.email_user or not self.email_password:
            self.logger.error("Email credentials not configured")
            return False
        
        try:
            # Create message
            msg = email.mime.multipart.MIMEMultipart('alternative')
            msg['From'] = email.header.Header(f"Russian Trading Bot <{self.from_email}>", 'utf-8')
            msg['To'] = email.header.Header(notification.recipient, 'utf-8')
            msg['Subject'] = email.header.Header(notification.subject, 'utf-8')
            
            # Add body
            body = email.mime.text.MIMEText(notification.message, 'plain', 'utf-8')
            msg.attach(body)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_user, self.email_password)
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Email sending failed: {e}")
            return False
    
    async def _send_telegram(self, notification: Notification) -> bool:
        """Send Telegram notification"""
        if not self.telegram_token:
            self.logger.error("Telegram token not configured")
            return False
        
        try:
            # Prepare message
            message_text = f"*{notification.subject}*\n\n{notification.message}"
            
            # Send message
            url = f"{self.telegram_api_url}/sendMessage"
            payload = {
                'chat_id': notification.recipient,
                'text': message_text,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get('ok'):
                return True
            else:
                self.logger.error(f"Telegram API error: {result}")
                return False
                
        except Exception as e:
            self.logger.error(f"Telegram sending failed: {e}")
            return False
    
    async def _send_sms(self, notification: Notification) -> bool:
        """Send SMS notification"""
        if not self.sms_api_key:
            self.logger.error("SMS API key not configured")
            return False
        
        try:
            # Prepare SMS text (limit to 160 characters)
            sms_text = notification.message[:160]
            
            # Send SMS using SMS.ru API
            payload = {
                'api_id': self.sms_api_key,
                'to': notification.recipient,
                'msg': sms_text,
                'json': 1
            }
            
            response = requests.post(self.sms_api_url, data=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            if result.get('status') == 'OK':
                return True
            else:
                self.logger.error(f"SMS API error: {result}")
                return False
                
        except Exception as e:
            self.logger.error(f"SMS sending failed: {e}")
            return False
    
    def is_quiet_hours(self, preferences: NotificationPreferences) -> bool:
        """Check if current time is within quiet hours"""
        if not preferences.quiet_hours_start or not preferences.quiet_hours_end:
            return False
        
        now = datetime.now(self.moscow_tz).time()
        start_time = time.fromisoformat(preferences.quiet_hours_start)
        end_time = time.fromisoformat(preferences.quiet_hours_end)
        
        # Handle overnight quiet hours (e.g., 22:00 to 08:00)
        if start_time > end_time:
            return now >= start_time or now <= end_time
        else:
            return start_time <= now <= end_time
    
    async def send_trading_signal_alert(
        self,
        signal_data: TradingSignalAlert,
        preferences: NotificationPreferences
    ) -> List[Notification]:
        """Send trading signal alert"""
        notifications = []
        
        # Check confidence threshold
        if signal_data.confidence < preferences.min_trading_signal_confidence:
            self.logger.info(f"Signal confidence {signal_data.confidence} below threshold")
            return notifications
        
        # Check quiet hours for non-critical alerts
        if self.is_quiet_hours(preferences):
            self.logger.info("Skipping trading signal during quiet hours")
            return notifications
        
        # Get preferred channels
        channels = preferences.get_channels_for_type(NotificationType.TRADING_SIGNAL)
        
        for channel in channels:
            try:
                # Determine recipient
                recipient = self._get_recipient_for_channel(channel, preferences)
                if not recipient:
                    continue
                
                # Create notification
                notification = self.create_notification(
                    notification_type=NotificationType.TRADING_SIGNAL,
                    priority=NotificationPriority.MEDIUM,
                    channel=channel,
                    recipient=recipient,
                    data=signal_data.to_dict()
                )
                
                # Send notification
                success = await self.send_notification(notification)
                notifications.append(notification)
                
                if not success and notification.retry_count < notification.max_retries:
                    self.notification_queue.append(notification)
                    
            except Exception as e:
                self.logger.error(f"Error sending trading signal alert: {e}")
        
        return notifications
    
    async def send_portfolio_alert(
        self,
        portfolio_data: PortfolioAlert,
        preferences: NotificationPreferences
    ) -> List[Notification]:
        """Send portfolio alert"""
        notifications = []
        
        # Get preferred channels
        channels = preferences.get_channels_for_type(NotificationType.PORTFOLIO_ALERT)
        
        for channel in channels:
            try:
                # Determine recipient
                recipient = self._get_recipient_for_channel(channel, preferences)
                if not recipient:
                    continue
                
                # Create notification
                notification = self.create_notification(
                    notification_type=NotificationType.PORTFOLIO_ALERT,
                    priority=NotificationPriority.HIGH,
                    channel=channel,
                    recipient=recipient,
                    data=portfolio_data.to_dict()
                )
                
                # Send notification
                success = await self.send_notification(notification)
                notifications.append(notification)
                
                if not success and notification.retry_count < notification.max_retries:
                    self.notification_queue.append(notification)
                    
            except Exception as e:
                self.logger.error(f"Error sending portfolio alert: {e}")
        
        return notifications
    
    async def send_market_alert(
        self,
        market_data: MarketAlert,
        preferences: NotificationPreferences
    ) -> List[Notification]:
        """Send market condition alert"""
        notifications = []
        
        # Get preferred channels
        channels = preferences.get_channels_for_type(NotificationType.MARKET_ALERT)
        
        for channel in channels:
            try:
                # Determine recipient
                recipient = self._get_recipient_for_channel(channel, preferences)
                if not recipient:
                    continue
                
                # Create notification
                notification = self.create_notification(
                    notification_type=NotificationType.MARKET_ALERT,
                    priority=NotificationPriority.MEDIUM,
                    channel=channel,
                    recipient=recipient,
                    data=market_data.to_dict()
                )
                
                # Send notification
                success = await self.send_notification(notification)
                notifications.append(notification)
                
                if not success and notification.retry_count < notification.max_retries:
                    self.notification_queue.append(notification)
                    
            except Exception as e:
                self.logger.error(f"Error sending market alert: {e}")
        
        return notifications
    
    async def send_geopolitical_alert(
        self,
        geo_data: GeopoliticalAlert,
        preferences: NotificationPreferences
    ) -> List[Notification]:
        """Send geopolitical event alert"""
        notifications = []
        
        # Get preferred channels
        channels = preferences.get_channels_for_type(NotificationType.GEOPOLITICAL_ALERT)
        
        for channel in channels:
            try:
                # Determine recipient
                recipient = self._get_recipient_for_channel(channel, preferences)
                if not recipient:
                    continue
                
                # Create notification
                notification = self.create_notification(
                    notification_type=NotificationType.GEOPOLITICAL_ALERT,
                    priority=NotificationPriority.HIGH,
                    channel=channel,
                    recipient=recipient,
                    data=geo_data.to_dict()
                )
                
                # Send notification
                success = await self.send_notification(notification)
                notifications.append(notification)
                
                if not success and notification.retry_count < notification.max_retries:
                    self.notification_queue.append(notification)
                    
            except Exception as e:
                self.logger.error(f"Error sending geopolitical alert: {e}")
        
        return notifications
    
    def _get_recipient_for_channel(
        self,
        channel: NotificationChannel,
        preferences: NotificationPreferences
    ) -> Optional[str]:
        """Get recipient address for notification channel"""
        if channel == NotificationChannel.EMAIL:
            return preferences.email
        elif channel == NotificationChannel.TELEGRAM:
            return preferences.telegram_chat_id
        elif channel == NotificationChannel.SMS:
            return preferences.phone_number
        else:
            return None
    
    async def process_notification_queue(self) -> None:
        """Process queued notifications for retry"""
        retry_notifications = []
        
        for notification in self.notification_queue:
            if notification.retry_count < notification.max_retries:
                success = await self.send_notification(notification)
                if not success:
                    retry_notifications.append(notification)
            else:
                # Max retries reached, move to failed
                notification.status = NotificationStatus.FAILED
                self.failed_notifications.append(notification)
                self.logger.error(f"Notification {notification.notification_id} failed after max retries")
        
        self.notification_queue = retry_notifications
    
    def get_notification_stats(self) -> Dict[str, int]:
        """Get notification statistics"""
        return {
            'queued': len(self.notification_queue),
            'failed': len(self.failed_notifications)
        }


class TelegramBot:
    """Telegram bot for Russian trading alerts"""
    
    def __init__(self, token: str):
        """Initialize Telegram bot"""
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{token}"
        self.logger = logging.getLogger(__name__)
    
    async def send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = 'Markdown'
    ) -> bool:
        """Send message to Telegram chat"""
        try:
            url = f"{self.api_url}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': text,
                'parse_mode': parse_mode
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            return result.get('ok', False)
            
        except Exception as e:
            self.logger.error(f"Telegram message failed: {e}")
            return False
    
    async def send_trading_signal(
        self,
        chat_id: str,
        signal_data: TradingSignalAlert
    ) -> bool:
        """Send formatted trading signal to Telegram"""
        
        # Format signal message
        action_emoji = "🟢" if signal_data.action == "BUY" else "🔴" if signal_data.action == "SELL" else "🟡"
        confidence_emoji = "🔥" if signal_data.confidence > 0.8 else "⚡" if signal_data.confidence > 0.6 else "💡"
        
        message = f"""
{action_emoji} *Торговый сигнал*

📈 *Акция:* `{signal_data.symbol}`
🎯 *Действие:* *{signal_data.action}*
{confidence_emoji} *Уверенность:* `{signal_data.confidence:.1%}`
💰 *Цена:* `{signal_data.current_price:.2f} ₽`

🎯 *Цель:* `{signal_data.target_price:.2f} ₽` если указана
🛡️ *Стоп-лосс:* `{signal_data.stop_loss:.2f} ₽` если указан

💡 *Обоснование:*
_{signal_data.reasoning}_
        """.strip()
        
        return await self.send_message(chat_id, message)
    
    async def send_portfolio_update(
        self,
        chat_id: str,
        portfolio_data: PortfolioAlert
    ) -> bool:
        """Send portfolio update to Telegram"""
        
        alert_emoji = "⚠️" if "LOSS" in portfolio_data.alert_type else "📈" if "GAIN" in portfolio_data.alert_type else "📊"
        
        message = f"""
{alert_emoji} *Уведомление по портфелю*

📊 *Тип:* `{portfolio_data.alert_type}`
💰 *Стоимость:* `{portfolio_data.current_value:.2f} ₽`
📈 *Изменение:* `{portfolio_data.change_amount:.2f} ₽ ({portfolio_data.change_percent:.1%})`

⏰ _{datetime.now().strftime('%d.%m.%Y %H:%M MSK')}_
        """.strip()
        
        return await self.send_message(chat_id, message)