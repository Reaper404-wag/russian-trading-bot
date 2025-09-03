#!/usr/bin/env python3
"""
Automated Alert System for Russian Trading Bot
Handles system failures and market-specific alerts
"""

import os
import logging
import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from enum import Enum
import aiohttp
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class AlertCategory(Enum):
    SYSTEM = "system"
    MARKET = "market"
    TRADING = "trading"
    SECURITY = "security"
    COMPLIANCE = "compliance"

@dataclass
class Alert:
    """Alert data structure"""
    alert_id: str
    severity: AlertSeverity
    category: AlertCategory
    title: str
    message: str
    details: Dict
    timestamp: datetime
    source: str
    resolved: bool = False
    resolution_time: Optional[datetime] = None
    escalated: bool = False

class RussianTradingAlertManager:
    """Comprehensive alert management system"""
    
    def __init__(self, config: Dict = None):
        self.config = config or self._default_config()
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Alert state
        self.active_alerts = {}
        self.alert_history = []
        self.escalation_rules = self._setup_escalation_rules()
        self.notification_channels = self._setup_notification_channels()
        
    def _default_config(self) -> Dict:
        """Default alert configuration"""
        return {
            'alert_retention_days': 30,
            'escalation_timeout': 1800,  # 30 minutes
            'rate_limiting': {
                'max_alerts_per_hour': 50,
                'cooldown_period': 300  # 5 minutes
            },
            'notification_preferences': {
                'telegram': {
                    'enabled': True,
                    'severities': ['warning', 'critical', 'emergency']
                },
                'email': {
                    'enabled': True,
                    'severities': ['critical', 'emergency']
                },
                'webhook': {
                    'enabled': True,
                    'severities': ['info', 'warning', 'critical', 'emergency']
                },
                'sms': {
                    'enabled': False,
                    'severities': ['emergency']
                }
            },
            'russian_market_hours': {
                'start': '10:00',
                'end': '18:45',
                'timezone': 'Europe/Moscow'
            }
        }
        
    def _setup_escalation_rules(self) -> Dict:
        """Setup alert escalation rules"""
        return {
            AlertSeverity.INFO: {
                'escalate_after': None,
                'escalate_to': None
            },
            AlertSeverity.WARNING: {
                'escalate_after': 3600,  # 1 hour
                'escalate_to': AlertSeverity.CRITICAL
            },
            AlertSeverity.CRITICAL: {
                'escalate_after': 1800,  # 30 minutes
                'escalate_to': AlertSeverity.EMERGENCY
            },
            AlertSeverity.EMERGENCY: {
                'escalate_after': None,
                'escalate_to': None
            }
        }
        
    def _setup_notification_channels(self) -> Dict:
        """Setup notification channels"""
        return {
            'telegram': {
                'token': os.getenv('TELEGRAM_BOT_TOKEN'),
                'chat_id': os.getenv('TELEGRAM_CHAT_ID'),
                'enabled': bool(os.getenv('TELEGRAM_BOT_TOKEN'))
            },
            'email': {
                'smtp_host': os.getenv('EMAIL_SMTP_HOST', 'smtp.gmail.com'),
                'smtp_port': int(os.getenv('EMAIL_SMTP_PORT', '587')),
                'username': os.getenv('EMAIL_USERNAME'),
                'password': os.getenv('EMAIL_PASSWORD'),
                'to_addresses': os.getenv('ALERT_EMAIL_RECIPIENTS', '').split(','),
                'enabled': bool(os.getenv('EMAIL_USERNAME'))
            },
            'webhook': {
                'url': os.getenv('ALERT_WEBHOOK_URL'),
                'enabled': bool(os.getenv('ALERT_WEBHOOK_URL'))
            }
        }
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            
    def create_alert(self, 
                    severity: AlertSeverity,
                    category: AlertCategory,
                    title: str,
                    message: str,
                    details: Dict = None,
                    source: str = "system") -> Alert:
        """Create a new alert"""
        
        alert_id = f"{category.value}_{severity.value}_{int(time.time())}"
        
        alert = Alert(
            alert_id=alert_id,
            severity=severity,
            category=category,
            title=title,
            message=message,
            details=details or {},
            timestamp=datetime.now(timezone.utc),
            source=source
        )
        
        return alert
        
    async def send_alert(self, alert: Alert) -> bool:
        """Send alert through configured channels"""
        try:
            # Check rate limiting
            if not self._check_rate_limit(alert):
                logger.warning(f"Alert rate limited: {alert.alert_id}")
                return False
                
            # Store alert
            self.active_alerts[alert.alert_id] = alert
            self.alert_history.append(alert)
            
            # Send notifications
            success = await self._send_notifications(alert)
            
            logger.info(f"Alert sent: {alert.title} ({alert.severity.value})")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send alert {alert.alert_id}: {e}")
            return False
            
    def _check_rate_limit(self, alert: Alert) -> bool:
        """Check if alert should be rate limited"""
        current_time = time.time()
        hour_ago = current_time - 3600
        
        # Count alerts in the last hour
        recent_alerts = [
            a for a in self.alert_history
            if a.timestamp.timestamp() > hour_ago
        ]
        
        if len(recent_alerts) >= self.config['rate_limiting']['max_alerts_per_hour']:
            return False
            
        # Check cooldown for similar alerts
        cooldown_period = self.config['rate_limiting']['cooldown_period']
        similar_alerts = [
            a for a in self.alert_history
            if (a.category == alert.category and 
                a.severity == alert.severity and
                (current_time - a.timestamp.timestamp()) < cooldown_period)
        ]
        
        return len(similar_alerts) == 0
        
    async def _send_notifications(self, alert: Alert) -> bool:
        """Send notifications through all configured channels"""
        success = True
        
        # Get notification preferences for this severity
        severity_str = alert.severity.value
        
        # Telegram notification
        if (self.notification_channels['telegram']['enabled'] and
            severity_str in self.config['notification_preferences']['telegram']['severities']):
            telegram_success = await self._send_telegram_notification(alert)
            success = success and telegram_success
            
        # Email notification
        if (self.notification_channels['email']['enabled'] and
            severity_str in self.config['notification_preferences']['email']['severities']):
            email_success = await self._send_email_notification(alert)
            success = success and email_success
            
        # Webhook notification
        if (self.notification_channels['webhook']['enabled'] and
            severity_str in self.config['notification_preferences']['webhook']['severities']):
            webhook_success = await self._send_webhook_notification(alert)
            success = success and webhook_success
            
        return success
        
    async def _send_telegram_notification(self, alert: Alert) -> bool:
        """Send Telegram notification"""
        try:
            token = self.notification_channels['telegram']['token']
            chat_id = self.notification_channels['telegram']['chat_id']
            
            if not token or not chat_id:
                return False
                
            message = self._format_telegram_message(alert)
            
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }
            
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    logger.info(f"Telegram notification sent for alert {alert.alert_id}")
                    return True
                else:
                    logger.error(f"Telegram notification failed: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")
            return False
            
    def _format_telegram_message(self, alert: Alert) -> str:
        """Format alert message for Telegram"""
        severity_emoji = {
            AlertSeverity.INFO: 'ℹ️',
            AlertSeverity.WARNING: '⚠️',
            AlertSeverity.CRITICAL: '🚨',
            AlertSeverity.EMERGENCY: '🆘'
        }
        
        category_emoji = {
            AlertCategory.SYSTEM: '🖥️',
            AlertCategory.MARKET: '📈',
            AlertCategory.TRADING: '💰',
            AlertCategory.SECURITY: '🔒',
            AlertCategory.COMPLIANCE: '📋'
        }
        
        emoji = severity_emoji.get(alert.severity, '❓')
        cat_emoji = category_emoji.get(alert.category, '📌')
        
        message = f"{emoji} <b>Система торговли - {alert.severity.value.upper()}</b>\n\n"
        message += f"{cat_emoji} <b>Категория:</b> {alert.category.value}\n"
        message += f"📝 <b>Заголовок:</b> {alert.title}\n"
        message += f"💬 <b>Сообщение:</b> {alert.message}\n"
        message += f"🕐 <b>Время:</b> {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        message += f"🔍 <b>Источник:</b> {alert.source}\n"
        
        if alert.details:
            message += f"\n📊 <b>Детали:</b>\n"
            for key, value in alert.details.items():
                message += f"  • {key}: {value}\n"
                
        message += f"\n🆔 ID: <code>{alert.alert_id}</code>"
        
        return message
        
    async def _send_email_notification(self, alert: Alert) -> bool:
        """Send email notification"""
        try:
            email_config = self.notification_channels['email']
            
            if not email_config['username'] or not email_config['to_addresses']:
                return False
                
            # Create message
            msg = MIMEMultipart()
            msg['From'] = email_config['username']
            msg['To'] = ', '.join(email_config['to_addresses'])
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.title}"
            
            # Create email body
            body = self._format_email_message(alert)
            msg.attach(MIMEText(body, 'html', 'utf-8'))
            
            # Send email
            with smtplib.SMTP(email_config['smtp_host'], email_config['smtp_port']) as server:
                server.starttls()
                server.login(email_config['username'], email_config['password'])
                server.send_message(msg)
                
            logger.info(f"Email notification sent for alert {alert.alert_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
            return False
            
    def _format_email_message(self, alert: Alert) -> str:
        """Format alert message for email"""
        severity_colors = {
            AlertSeverity.INFO: '#17a2b8',
            AlertSeverity.WARNING: '#ffc107',
            AlertSeverity.CRITICAL: '#dc3545',
            AlertSeverity.EMERGENCY: '#6f42c1'
        }
        
        color = severity_colors.get(alert.severity, '#6c757d')
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 20px;">
            <div style="border-left: 4px solid {color}; padding-left: 20px;">
                <h2 style="color: {color}; margin-top: 0;">
                    Система торговли - {alert.severity.value.upper()}
                </h2>
                
                <table style="border-collapse: collapse; width: 100%; margin-top: 20px;">
                    <tr>
                        <td style="padding: 8px; font-weight: bold; width: 120px;">Категория:</td>
                        <td style="padding: 8px;">{alert.category.value}</td>
                    </tr>
                    <tr style="background-color: #f8f9fa;">
                        <td style="padding: 8px; font-weight: bold;">Заголовок:</td>
                        <td style="padding: 8px;">{alert.title}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold;">Сообщение:</td>
                        <td style="padding: 8px;">{alert.message}</td>
                    </tr>
                    <tr style="background-color: #f8f9fa;">
                        <td style="padding: 8px; font-weight: bold;">Время:</td>
                        <td style="padding: 8px;">{alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold;">Источник:</td>
                        <td style="padding: 8px;">{alert.source}</td>
                    </tr>
                    <tr style="background-color: #f8f9fa;">
                        <td style="padding: 8px; font-weight: bold;">ID:</td>
                        <td style="padding: 8px; font-family: monospace;">{alert.alert_id}</td>
                    </tr>
                </table>
        """
        
        if alert.details:
            html += """
                <h3 style="margin-top: 30px; color: #495057;">Детали:</h3>
                <table style="border-collapse: collapse; width: 100%; border: 1px solid #dee2e6;">
            """
            
            for key, value in alert.details.items():
                html += f"""
                    <tr>
                        <td style="padding: 8px; border: 1px solid #dee2e6; font-weight: bold; background-color: #f8f9fa;">{key}:</td>
                        <td style="padding: 8px; border: 1px solid #dee2e6;">{value}</td>
                    </tr>
                """
                
            html += "</table>"
            
        html += """
            </div>
            
            <div style="margin-top: 30px; padding: 15px; background-color: #e9ecef; border-radius: 5px;">
                <p style="margin: 0; font-size: 12px; color: #6c757d;">
                    Это автоматическое уведомление от системы торговли на российском рынке.
                    Для получения дополнительной информации обратитесь к системному администратору.
                </p>
            </div>
        </body>
        </html>
        """
        
        return html
        
    async def _send_webhook_notification(self, alert: Alert) -> bool:
        """Send webhook notification"""
        try:
            webhook_url = self.notification_channels['webhook']['url']
            
            if not webhook_url:
                return False
                
            # Prepare webhook payload
            payload = {
                'alert_id': alert.alert_id,
                'severity': alert.severity.value,
                'category': alert.category.value,
                'title': alert.title,
                'message': alert.message,
                'details': alert.details,
                'timestamp': alert.timestamp.isoformat(),
                'source': alert.source,
                'resolved': alert.resolved
            }
            
            async with self.session.post(webhook_url, json=payload) as response:
                if response.status == 200:
                    logger.info(f"Webhook notification sent for alert {alert.alert_id}")
                    return True
                else:
                    logger.error(f"Webhook notification failed: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error sending webhook notification: {e}")
            return False
            
    async def resolve_alert(self, alert_id: str, resolution_message: str = None) -> bool:
        """Resolve an active alert"""
        if alert_id not in self.active_alerts:
            logger.warning(f"Alert {alert_id} not found in active alerts")
            return False
            
        alert = self.active_alerts[alert_id]
        alert.resolved = True
        alert.resolution_time = datetime.now(timezone.utc)
        
        # Remove from active alerts
        del self.active_alerts[alert_id]
        
        # Send resolution notification
        resolution_alert = self.create_alert(
            severity=AlertSeverity.INFO,
            category=alert.category,
            title=f"Resolved: {alert.title}",
            message=resolution_message or f"Alert {alert_id} has been resolved",
            details={'original_alert_id': alert_id, 'resolution_time': alert.resolution_time.isoformat()},
            source="alert_manager"
        )
        
        await self.send_alert(resolution_alert)
        
        logger.info(f"Alert {alert_id} resolved")
        return True
        
    async def check_escalations(self):
        """Check for alerts that need escalation"""
        current_time = datetime.now(timezone.utc)
        
        for alert_id, alert in list(self.active_alerts.items()):
            if alert.escalated:
                continue
                
            escalation_rule = self.escalation_rules.get(alert.severity)
            if not escalation_rule or not escalation_rule['escalate_after']:
                continue
                
            # Check if escalation time has passed
            time_since_alert = (current_time - alert.timestamp).total_seconds()
            
            if time_since_alert >= escalation_rule['escalate_after']:
                # Escalate alert
                escalated_alert = self.create_alert(
                    severity=escalation_rule['escalate_to'],
                    category=alert.category,
                    title=f"ESCALATED: {alert.title}",
                    message=f"Alert escalated due to no resolution: {alert.message}",
                    details={
                        'original_alert_id': alert_id,
                        'original_severity': alert.severity.value,
                        'escalation_time': current_time.isoformat(),
                        'time_since_original': time_since_alert
                    },
                    source="alert_escalation"
                )
                
                await self.send_alert(escalated_alert)
                
                # Mark original alert as escalated
                alert.escalated = True
                
                logger.warning(f"Alert {alert_id} escalated from {alert.severity.value} to {escalation_rule['escalate_to'].value}")
                
    def get_alert_summary(self) -> Dict:
        """Get summary of current alert status"""
        current_time = datetime.now(timezone.utc)
        
        summary = {
            'timestamp': current_time.isoformat(),
            'active_alerts': len(self.active_alerts),
            'total_alerts_today': 0,
            'alerts_by_severity': {},
            'alerts_by_category': {},
            'recent_alerts': []
        }
        
        # Count alerts by severity and category
        for severity in AlertSeverity:
            summary['alerts_by_severity'][severity.value] = 0
            
        for category in AlertCategory:
            summary['alerts_by_category'][category.value] = 0
            
        # Count active alerts
        for alert in self.active_alerts.values():
            summary['alerts_by_severity'][alert.severity.value] += 1
            summary['alerts_by_category'][alert.category.value] += 1
            
        # Count today's alerts
        today_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        today_alerts = [
            alert for alert in self.alert_history
            if alert.timestamp >= today_start
        ]
        summary['total_alerts_today'] = len(today_alerts)
        
        # Get recent alerts
        recent_alerts = sorted(self.alert_history[-10:], key=lambda x: x.timestamp, reverse=True)
        summary['recent_alerts'] = [
            {
                'alert_id': alert.alert_id,
                'severity': alert.severity.value,
                'category': alert.category.value,
                'title': alert.title,
                'timestamp': alert.timestamp.isoformat(),
                'resolved': alert.resolved
            }
            for alert in recent_alerts
        ]
        
        return summary

# Predefined alert templates for common scenarios
class RussianMarketAlerts:
    """Predefined alerts for Russian market scenarios"""
    
    @staticmethod
    def moex_api_down():
        return Alert(
            alert_id=f"moex_api_down_{int(time.time())}",
            severity=AlertSeverity.CRITICAL,
            category=AlertCategory.MARKET,
            title="MOEX API недоступен",
            message="Московская биржа API не отвечает. Торговые операции могут быть нарушены.",
            details={
                'api_endpoint': 'https://iss.moex.com/iss',
                'impact': 'Невозможно получить рыночные данные',
                'recommended_action': 'Проверить статус MOEX API и переключиться на резервные источники данных'
            },
            timestamp=datetime.now(timezone.utc),
            source="moex_monitor"
        )
        
    @staticmethod
    def high_volatility_detected(symbol: str, volatility: float):
        return Alert(
            alert_id=f"high_volatility_{symbol}_{int(time.time())}",
            severity=AlertSeverity.WARNING,
            category=AlertCategory.MARKET,
            title=f"Высокая волатильность: {symbol}",
            message=f"Обнаружена высокая волатильность для {symbol}: {volatility:.2%}",
            details={
                'symbol': symbol,
                'volatility': volatility,
                'threshold': 0.05,
                'recommended_action': 'Пересмотреть позиции и риск-менеджмент'
            },
            timestamp=datetime.now(timezone.utc),
            source="volatility_monitor"
        )
        
    @staticmethod
    def trading_halt(symbol: str, reason: str):
        return Alert(
            alert_id=f"trading_halt_{symbol}_{int(time.time())}",
            severity=AlertSeverity.CRITICAL,
            category=AlertCategory.TRADING,
            title=f"Торги приостановлены: {symbol}",
            message=f"Торги по {symbol} приостановлены. Причина: {reason}",
            details={
                'symbol': symbol,
                'reason': reason,
                'impact': 'Невозможно торговать данным инструментом',
                'recommended_action': 'Дождаться возобновления торгов или закрыть позиции'
            },
            timestamp=datetime.now(timezone.utc),
            source="trading_monitor"
        )

async def test_alert_system():
    """Test the alert system"""
    logger.info("🚨 Testing Russian Trading Bot Alert System")
    
    async with RussianTradingAlertManager() as alert_manager:
        # Test different types of alerts
        test_alerts = [
            alert_manager.create_alert(
                AlertSeverity.INFO,
                AlertCategory.SYSTEM,
                "Система запущена",
                "Система торговли успешно запущена и готова к работе",
                {'startup_time': datetime.now(timezone.utc).isoformat()}
            ),
            
            alert_manager.create_alert(
                AlertSeverity.WARNING,
                AlertCategory.MARKET,
                "Высокая волатильность",
                "Обнаружена повышенная волатильность на рынке",
                {'volatility_level': '15%', 'affected_symbols': ['SBER', 'GAZP']}
            ),
            
            RussianMarketAlerts.moex_api_down()
        ]
        
        # Send test alerts
        for alert in test_alerts:
            success = await alert_manager.send_alert(alert)
            logger.info(f"Alert sent: {alert.title} - {'✅' if success else '❌'}")
            
        # Get summary
        summary = alert_manager.get_alert_summary()
        logger.info(f"Alert summary: {summary['active_alerts']} active alerts")
        
        # Test resolution
        if alert_manager.active_alerts:
            first_alert_id = list(alert_manager.active_alerts.keys())[0]
            await alert_manager.resolve_alert(first_alert_id, "Test resolution")
            
        logger.info("Alert system test completed")

if __name__ == "__main__":
    asyncio.run(test_alert_system())