"""
Notification models for Russian trading bot alerts
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List, Any
from enum import Enum
from decimal import Decimal


class NotificationType(Enum):
    """Types of notifications"""
    TRADING_SIGNAL = "trading_signal"
    PORTFOLIO_ALERT = "portfolio_alert"
    MARKET_ALERT = "market_alert"
    RISK_ALERT = "risk_alert"
    SYSTEM_ALERT = "system_alert"
    GEOPOLITICAL_ALERT = "geopolitical_alert"


class NotificationPriority(Enum):
    """Notification priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationChannel(Enum):
    """Notification delivery channels"""
    EMAIL = "email"
    TELEGRAM = "telegram"
    SMS = "sms"
    PUSH = "push"
    WEB = "web"


class NotificationStatus(Enum):
    """Notification delivery status"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRY = "retry"


@dataclass
class NotificationTemplate:
    """Template for Russian language notifications"""
    template_id: str
    notification_type: NotificationType
    subject_template: str  # Russian subject template
    body_template: str     # Russian body template
    channel: NotificationChannel
    priority: NotificationPriority = NotificationPriority.MEDIUM
    
    def format_message(self, **kwargs) -> Dict[str, str]:
        """Format notification message with provided data"""
        try:
            subject = self.subject_template.format(**kwargs)
            body = self.body_template.format(**kwargs)
            return {"subject": subject, "body": body}
        except KeyError as e:
            raise ValueError(f"Missing template parameter: {e}")


@dataclass
class Notification:
    """Individual notification instance"""
    notification_id: str
    notification_type: NotificationType
    priority: NotificationPriority
    channel: NotificationChannel
    recipient: str
    subject: str
    message: str
    data: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    status: NotificationStatus = NotificationStatus.PENDING
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    
    def __post_init__(self):
        """Initialize notification"""
        if self.created_at is None:
            self.created_at = datetime.now()


@dataclass
class TradingSignalAlert:
    """Trading signal notification data"""
    symbol: str
    action: str  # BUY/SELL/HOLD
    confidence: float
    current_price: Decimal
    target_price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None
    reasoning: str = ""
    expected_return: Optional[float] = None
    risk_score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for template formatting"""
        return {
            'symbol': self.symbol,
            'action': self.action,
            'confidence': f"{self.confidence:.1%}",
            'current_price': f"{self.current_price:.2f} ₽",
            'target_price': f"{self.target_price:.2f} ₽" if self.target_price else "Не указана",
            'stop_loss': f"{self.stop_loss:.2f} ₽" if self.stop_loss else "Не указан",
            'reasoning': self.reasoning,
            'expected_return': f"{self.expected_return:.1%}" if self.expected_return else "Не указана",
            'risk_score': f"{self.risk_score:.1%}" if self.risk_score else "Не указан"
        }


@dataclass
class PortfolioAlert:
    """Portfolio-related notification data"""
    alert_type: str  # LOSS_THRESHOLD, GAIN_THRESHOLD, POSITION_SIZE, etc.
    current_value: Decimal
    threshold_value: Optional[Decimal] = None
    change_amount: Optional[Decimal] = None
    change_percent: Optional[float] = None
    affected_positions: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for template formatting"""
        return {
            'alert_type': self.alert_type,
            'current_value': f"{self.current_value:.2f} ₽",
            'threshold_value': f"{self.threshold_value:.2f} ₽" if self.threshold_value else "Не указан",
            'change_amount': f"{self.change_amount:.2f} ₽" if self.change_amount else "Не указано",
            'change_percent': f"{self.change_percent:.1%}" if self.change_percent else "Не указано",
            'affected_positions': ", ".join(self.affected_positions) if self.affected_positions else "Нет"
        }


@dataclass
class MarketAlert:
    """Market condition notification data"""
    alert_type: str  # VOLATILITY, VOLUME_SPIKE, PRICE_MOVEMENT, etc.
    symbol: Optional[str] = None
    current_value: Optional[Decimal] = None
    threshold_value: Optional[Decimal] = None
    change_percent: Optional[float] = None
    market_condition: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for template formatting"""
        return {
            'alert_type': self.alert_type,
            'symbol': self.symbol or "Общий рынок",
            'current_value': f"{self.current_value:.2f}" if self.current_value else "Не указано",
            'threshold_value': f"{self.threshold_value:.2f}" if self.threshold_value else "Не указан",
            'change_percent': f"{self.change_percent:.1%}" if self.change_percent else "Не указано",
            'market_condition': self.market_condition or "Нормальное"
        }


@dataclass
class GeopoliticalAlert:
    """Geopolitical event notification data"""
    event_type: str  # SANCTIONS, POLICY_CHANGE, ECONOMIC_NEWS, etc.
    severity: str    # LOW, MEDIUM, HIGH, CRITICAL
    description: str
    affected_sectors: Optional[List[str]] = None
    market_impact: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for template formatting"""
        return {
            'event_type': self.event_type,
            'severity': self.severity,
            'description': self.description,
            'affected_sectors': ", ".join(self.affected_sectors) if self.affected_sectors else "Все секторы",
            'market_impact': self.market_impact or "Оценивается"
        }


@dataclass
class NotificationPreferences:
    """User notification preferences"""
    user_id: str
    email: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    phone_number: Optional[str] = None
    
    # Channel preferences by notification type
    trading_signals: List[NotificationChannel] = None
    portfolio_alerts: List[NotificationChannel] = None
    market_alerts: List[NotificationChannel] = None
    risk_alerts: List[NotificationChannel] = None
    system_alerts: List[NotificationChannel] = None
    geopolitical_alerts: List[NotificationChannel] = None
    
    # Priority thresholds
    min_trading_signal_confidence: float = 0.7
    portfolio_loss_threshold: float = 0.05  # 5%
    portfolio_gain_threshold: float = 0.10  # 10%
    market_volatility_threshold: float = 0.03  # 3%
    
    # Quiet hours (Moscow time)
    quiet_hours_start: Optional[str] = "22:00"  # 22:00 MSK
    quiet_hours_end: Optional[str] = "08:00"    # 08:00 MSK
    
    def __post_init__(self):
        """Initialize default preferences"""
        if self.trading_signals is None:
            self.trading_signals = [NotificationChannel.EMAIL, NotificationChannel.TELEGRAM]
        if self.portfolio_alerts is None:
            self.portfolio_alerts = [NotificationChannel.EMAIL, NotificationChannel.TELEGRAM, NotificationChannel.SMS]
        if self.market_alerts is None:
            self.market_alerts = [NotificationChannel.EMAIL, NotificationChannel.TELEGRAM]
        if self.risk_alerts is None:
            self.risk_alerts = [NotificationChannel.EMAIL, NotificationChannel.TELEGRAM, NotificationChannel.SMS]
        if self.system_alerts is None:
            self.system_alerts = [NotificationChannel.EMAIL]
        if self.geopolitical_alerts is None:
            self.geopolitical_alerts = [NotificationChannel.EMAIL, NotificationChannel.TELEGRAM]
    
    def get_channels_for_type(self, notification_type: NotificationType) -> List[NotificationChannel]:
        """Get preferred channels for notification type"""
        channel_map = {
            NotificationType.TRADING_SIGNAL: self.trading_signals,
            NotificationType.PORTFOLIO_ALERT: self.portfolio_alerts,
            NotificationType.MARKET_ALERT: self.market_alerts,
            NotificationType.RISK_ALERT: self.risk_alerts,
            NotificationType.SYSTEM_ALERT: self.system_alerts,
            NotificationType.GEOPOLITICAL_ALERT: self.geopolitical_alerts
        }
        return channel_map.get(notification_type, [NotificationChannel.EMAIL])


# Russian notification templates
RUSSIAN_TEMPLATES = {
    "trading_signal_email": NotificationTemplate(
        template_id="trading_signal_email",
        notification_type=NotificationType.TRADING_SIGNAL,
        subject_template="🔔 Торговый сигнал: {action} {symbol}",
        body_template="""
Получен новый торговый сигнал:

📈 Акция: {symbol}
🎯 Действие: {action}
📊 Уверенность: {confidence}
💰 Текущая цена: {current_price}
🎯 Целевая цена: {target_price}
🛡️ Стоп-лосс: {stop_loss}
📈 Ожидаемая доходность: {expected_return}
⚠️ Риск: {risk_score}

💡 Обоснование:
{reasoning}

Время: {timestamp}
        """.strip(),
        channel=NotificationChannel.EMAIL,
        priority=NotificationPriority.MEDIUM
    ),
    
    "portfolio_alert_telegram": NotificationTemplate(
        template_id="portfolio_alert_telegram",
        notification_type=NotificationType.PORTFOLIO_ALERT,
        subject_template="⚠️ Портфель: {alert_type}",
        body_template="""
🔔 Уведомление по портфелю

📊 Тип: {alert_type}
💰 Текущая стоимость: {current_value}
📈 Изменение: {change_amount} ({change_percent})
🎯 Пороговое значение: {threshold_value}
📋 Затронутые позиции: {affected_positions}

⏰ {timestamp}
        """.strip(),
        channel=NotificationChannel.TELEGRAM,
        priority=NotificationPriority.HIGH
    ),
    
    "market_alert_sms": NotificationTemplate(
        template_id="market_alert_sms",
        notification_type=NotificationType.MARKET_ALERT,
        subject_template="Рынок: {alert_type}",
        body_template="🔔 {alert_type}: {symbol} {change_percent}. Условия: {market_condition}",
        channel=NotificationChannel.SMS,
        priority=NotificationPriority.HIGH
    ),
    
    "geopolitical_alert_email": NotificationTemplate(
        template_id="geopolitical_alert_email",
        notification_type=NotificationType.GEOPOLITICAL_ALERT,
        subject_template="🌍 Геополитическое событие: {event_type}",
        body_template="""
Обнаружено важное геополитическое событие:

🌍 Тип события: {event_type}
⚠️ Серьезность: {severity}
📝 Описание: {description}
🏭 Затронутые секторы: {affected_sectors}
📊 Влияние на рынок: {market_impact}

⏰ Время: {timestamp}
        """.strip(),
        channel=NotificationChannel.EMAIL,
        priority=NotificationPriority.HIGH
    )
}