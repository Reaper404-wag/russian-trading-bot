"""
Configuration for Russian market alert system
"""

from typing import Dict, List, Any
from dataclasses import dataclass
from ..models.notifications import NotificationChannel, NotificationPriority


@dataclass
class AlertConfig:
    """Configuration for alert system"""
    
    # Email configuration
    email_smtp_server: str = "smtp.gmail.com"
    email_smtp_port: int = 587
    email_username: str = ""
    email_password: str = ""
    email_from_address: str = ""
    
    # Telegram configuration
    telegram_bot_token: str = ""
    telegram_api_url: str = "https://api.telegram.org/bot"
    
    # SMS configuration (SMS.ru)
    sms_api_key: str = ""
    sms_api_url: str = "https://sms.ru/sms/send"
    
    # Alert thresholds
    trading_signal_confidence_threshold: float = 0.7
    portfolio_loss_threshold: float = 0.05  # 5%
    portfolio_gain_threshold: float = 0.10  # 10%
    market_volatility_threshold: float = 0.03  # 3%
    volume_spike_threshold: float = 2.0  # 2x average
    price_movement_threshold: float = 0.05  # 5%
    
    # Alert cooldown periods (minutes)
    trading_signal_cooldown: int = 15
    portfolio_alert_cooldown: int = 30
    market_alert_cooldown: int = 30
    geopolitical_alert_cooldown: int = 60
    
    # Quiet hours (Moscow time)
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "08:00"
    
    # Priority settings
    critical_alert_channels: List[NotificationChannel] = None
    high_priority_channels: List[NotificationChannel] = None
    medium_priority_channels: List[NotificationChannel] = None
    low_priority_channels: List[NotificationChannel] = None
    
    def __post_init__(self):
        """Initialize default channel priorities"""
        if self.critical_alert_channels is None:
            self.critical_alert_channels = [
                NotificationChannel.EMAIL,
                NotificationChannel.TELEGRAM,
                NotificationChannel.SMS
            ]
        
        if self.high_priority_channels is None:
            self.high_priority_channels = [
                NotificationChannel.EMAIL,
                NotificationChannel.TELEGRAM
            ]
        
        if self.medium_priority_channels is None:
            self.medium_priority_channels = [
                NotificationChannel.EMAIL,
                NotificationChannel.TELEGRAM
            ]
        
        if self.low_priority_channels is None:
            self.low_priority_channels = [
                NotificationChannel.EMAIL
            ]
    
    def get_channels_for_priority(self, priority: NotificationPriority) -> List[NotificationChannel]:
        """Get notification channels for priority level"""
        if priority == NotificationPriority.CRITICAL:
            return self.critical_alert_channels
        elif priority == NotificationPriority.HIGH:
            return self.high_priority_channels
        elif priority == NotificationPriority.MEDIUM:
            return self.medium_priority_channels
        else:
            return self.low_priority_channels
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for service initialization"""
        return {
            'email': {
                'smtp_server': self.email_smtp_server,
                'smtp_port': self.email_smtp_port,
                'username': self.email_username,
                'password': self.email_password,
                'from_email': self.email_from_address
            },
            'telegram': {
                'bot_token': self.telegram_bot_token,
                'api_url': self.telegram_api_url
            },
            'sms': {
                'api_key': self.sms_api_key,
                'api_url': self.sms_api_url
            },
            'thresholds': {
                'trading_signal_confidence': self.trading_signal_confidence_threshold,
                'portfolio_loss': self.portfolio_loss_threshold,
                'portfolio_gain': self.portfolio_gain_threshold,
                'market_volatility': self.market_volatility_threshold,
                'volume_spike': self.volume_spike_threshold,
                'price_movement': self.price_movement_threshold
            },
            'cooldowns': {
                'trading_signal': self.trading_signal_cooldown,
                'portfolio_alert': self.portfolio_alert_cooldown,
                'market_alert': self.market_alert_cooldown,
                'geopolitical_alert': self.geopolitical_alert_cooldown
            },
            'quiet_hours': {
                'start': self.quiet_hours_start,
                'end': self.quiet_hours_end
            }
        }


# Default Russian market alert templates
RUSSIAN_ALERT_TEMPLATES = {
    "trading_signal_email": {
        "subject": "🔔 Торговый сигнал: {action} {symbol}",
        "body": """
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
        """.strip()
    },
    
    "trading_signal_telegram": {
        "subject": "🔔 Торговый сигнал: {action} {symbol}",
        "body": """
🔔 *Торговый сигнал*

📈 *Акция:* `{symbol}`
🎯 *Действие:* *{action}*
📊 *Уверенность:* `{confidence}`
💰 *Цена:* `{current_price}`
🎯 *Цель:* `{target_price}`
🛡️ *Стоп-лосс:* `{stop_loss}`

💡 *Обоснование:*
_{reasoning}_

⏰ {timestamp}
        """.strip()
    },
    
    "trading_signal_sms": {
        "subject": "Сигнал: {action} {symbol}",
        "body": "🔔 {action} {symbol} по {current_price}. Уверенность: {confidence}. Цель: {target_price}"
    },
    
    "portfolio_alert_email": {
        "subject": "⚠️ Портфель: {alert_type}",
        "body": """
Уведомление по портфелю:

📊 Тип уведомления: {alert_type}
💰 Текущая стоимость: {current_value}
📈 Изменение: {change_amount} ({change_percent})
🎯 Пороговое значение: {threshold_value}
📋 Затронутые позиции: {affected_positions}

Время: {timestamp}
        """.strip()
    },
    
    "portfolio_alert_telegram": {
        "subject": "⚠️ Портфель: {alert_type}",
        "body": """
⚠️ *Уведомление по портфелю*

📊 *Тип:* {alert_type}
💰 *Стоимость:* `{current_value}`
📈 *Изменение:* `{change_amount} ({change_percent})`
📋 *Позиции:* {affected_positions}

⏰ {timestamp}
        """.strip()
    },
    
    "portfolio_alert_sms": {
        "subject": "Портфель: {alert_type}",
        "body": "⚠️ {alert_type}: {current_value} ({change_percent})"
    },
    
    "market_alert_email": {
        "subject": "📊 Рынок: {alert_type} - {symbol}",
        "body": """
Уведомление о состоянии рынка:

📊 Тип события: {alert_type}
📈 Акция: {symbol}
💰 Текущее значение: {current_value}
📈 Изменение: {change_percent}
🎯 Пороговое значение: {threshold_value}
🌡️ Состояние рынка: {market_condition}

Время: {timestamp}
        """.strip()
    },
    
    "market_alert_telegram": {
        "subject": "📊 Рынок: {alert_type}",
        "body": """
📊 *Рыночное уведомление*

🔔 *Событие:* {alert_type}
📈 *Акция:* `{symbol}`
💰 *Значение:* `{current_value}`
📈 *Изменение:* `{change_percent}`
🌡️ *Состояние:* {market_condition}

⏰ {timestamp}
        """.strip()
    },
    
    "geopolitical_alert_email": {
        "subject": "🌍 Геополитика: {event_type}",
        "body": """
Обнаружено важное геополитическое событие:

🌍 Тип события: {event_type}
⚠️ Серьезность: {severity}
📝 Описание: {description}
🏭 Затронутые секторы: {affected_sectors}
📊 Влияние на рынок: {market_impact}

Время: {timestamp}
        """.strip()
    },
    
    "geopolitical_alert_telegram": {
        "subject": "🌍 Геополитика: {event_type}",
        "body": """
🌍 *Геополитическое событие*

🔔 *Тип:* {event_type}
⚠️ *Серьезность:* {severity}
📝 *Описание:* {description}
🏭 *Секторы:* {affected_sectors}
📊 *Влияние:* {market_impact}

⏰ {timestamp}
        """.strip()
    }
}


# Russian market specific alert keywords
RUSSIAN_MARKET_KEYWORDS = {
    'high_volatility': [
        'высокая волатильность', 'резкие колебания', 'нестабильность',
        'сильные движения', 'повышенный риск'
    ],
    'volume_spike': [
        'всплеск объема', 'необычная активность', 'повышенные объемы',
        'активная торговля', 'большие объемы'
    ],
    'price_movement': [
        'значительный рост', 'значительное падение', 'резкое движение',
        'сильное изменение', 'скачок цены'
    ],
    'portfolio_loss': [
        'превышен порог убытков', 'большие потери', 'критические убытки',
        'значительное снижение', 'падение портфеля'
    ],
    'portfolio_gain': [
        'достигнут порог прибыли', 'значительная прибыль', 'хорошая доходность',
        'рост портфеля', 'положительная динамика'
    ],
    'geopolitical_risk': [
        'санкции', 'геополитические риски', 'политическая нестабильность',
        'международные ограничения', 'экономические меры'
    ]
}


def load_alert_config_from_env() -> AlertConfig:
    """Load alert configuration from environment variables"""
    import os
    
    return AlertConfig(
        email_smtp_server=os.getenv('ALERT_EMAIL_SMTP_SERVER', 'smtp.gmail.com'),
        email_smtp_port=int(os.getenv('ALERT_EMAIL_SMTP_PORT', '587')),
        email_username=os.getenv('ALERT_EMAIL_USERNAME', ''),
        email_password=os.getenv('ALERT_EMAIL_PASSWORD', ''),
        email_from_address=os.getenv('ALERT_EMAIL_FROM', ''),
        
        telegram_bot_token=os.getenv('ALERT_TELEGRAM_BOT_TOKEN', ''),
        
        sms_api_key=os.getenv('ALERT_SMS_API_KEY', ''),
        
        trading_signal_confidence_threshold=float(os.getenv('ALERT_SIGNAL_CONFIDENCE_THRESHOLD', '0.7')),
        portfolio_loss_threshold=float(os.getenv('ALERT_PORTFOLIO_LOSS_THRESHOLD', '0.05')),
        portfolio_gain_threshold=float(os.getenv('ALERT_PORTFOLIO_GAIN_THRESHOLD', '0.10')),
        market_volatility_threshold=float(os.getenv('ALERT_MARKET_VOLATILITY_THRESHOLD', '0.03')),
        
        quiet_hours_start=os.getenv('ALERT_QUIET_HOURS_START', '22:00'),
        quiet_hours_end=os.getenv('ALERT_QUIET_HOURS_END', '08:00')
    )