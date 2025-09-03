"""
Enhanced alert manager for Russian trading bot
Coordinates all notification and alerting functionality
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import pytz

from ..models.notifications import (
    NotificationPreferences, TradingSignalAlert, PortfolioAlert, 
    MarketAlert, GeopoliticalAlert, NotificationType, NotificationPriority
)
from ..models.trading import Portfolio, TradingSignal
from ..models.market_data import MOEXMarketData
from .notification_service import NotificationService
from .market_monitor import MarketMonitor
from ..config.alert_config import AlertConfig, load_alert_config_from_env


class AlertManager:
    """
    Enhanced alert manager for Russian market trading bot
    Coordinates notifications, market monitoring, and alert delivery
    """
    
    def __init__(self, config: Optional[AlertConfig] = None):
        """Initialize alert manager"""
        self.config = config or load_alert_config_from_env()
        self.logger = logging.getLogger(__name__)
        self.moscow_tz = pytz.timezone('Europe/Moscow')
        
        # Initialize services
        self.notification_service = NotificationService(self.config.to_dict())
        self.market_monitor = MarketMonitor(
            self.notification_service, 
            self.config.to_dict()
        )
        
        # Alert tracking
        self.active_alerts: Dict[str, datetime] = {}
        self.alert_history: List[Dict[str, Any]] = []
        self.user_preferences: Dict[str, NotificationPreferences] = {}
        
        # Performance metrics
        self.alerts_sent_today = 0
        self.alerts_failed_today = 0
        self.last_reset_date = datetime.now().date()
    
    def register_user_preferences(self, user_id: str, preferences: NotificationPreferences) -> None:
        """Register user notification preferences"""
        self.user_preferences[user_id] = preferences
        self.logger.info(f"Registered preferences for user {user_id}")
    
    async def send_trading_signal_alert(
        self,
        user_id: str,
        signal: TradingSignal,
        confidence: float,
        reasoning: str
    ) -> bool:
        """Send trading signal alert to user"""
        try:
            # Get user preferences
            preferences = self.user_preferences.get(user_id)
            if not preferences:
                self.logger.warning(f"No preferences found for user {user_id}")
                return False
            
            # Check confidence threshold
            if confidence < preferences.min_trading_signal_confidence:
                self.logger.info(f"Signal confidence {confidence} below threshold for user {user_id}")
                return False
            
            # Create signal alert data
            signal_data = TradingSignalAlert(
                symbol=signal.symbol,
                action=signal.action.value,  # Convert enum to string
                confidence=confidence,
                current_price=Decimal("0.00"),  # Will be filled by market data
                target_price=signal.target_price,
                stop_loss=signal.stop_loss,
                reasoning=reasoning,
                expected_return=signal.expected_return,
                risk_score=signal.risk_score
            )
            
            # Send notifications
            notifications = await self.notification_service.send_trading_signal_alert(
                signal_data, preferences
            )
            
            # Track alert
            if notifications:
                self._track_alert('trading_signal', user_id, signal.symbol, len(notifications))
                self.alerts_sent_today += len(notifications)
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error sending trading signal alert: {e}")
            self.alerts_failed_today += 1
            return False
    
    async def send_portfolio_alert(
        self,
        user_id: str,
        portfolio: Portfolio,
        alert_type: str,
        threshold_value: Optional[Decimal] = None
    ) -> bool:
        """Send portfolio alert to user"""
        try:
            # Get user preferences
            preferences = self.user_preferences.get(user_id)
            if not preferences:
                self.logger.warning(f"No preferences found for user {user_id}")
                return False
            
            # Calculate portfolio metrics
            change_amount = portfolio.total_pnl or Decimal('0')
            change_percent = 0.0
            if portfolio.total_value and portfolio.total_value > 0:
                change_percent = float(change_amount / portfolio.total_value)
            
            # Create portfolio alert data
            portfolio_data = PortfolioAlert(
                alert_type=alert_type,
                current_value=portfolio.total_value,
                threshold_value=threshold_value,
                change_amount=change_amount,
                change_percent=change_percent,
                affected_positions=list(portfolio.positions.keys())
            )
            
            # Send notifications
            notifications = await self.notification_service.send_portfolio_alert(
                portfolio_data, preferences
            )
            
            # Track alert
            if notifications:
                self._track_alert('portfolio_alert', user_id, alert_type, len(notifications))
                self.alerts_sent_today += len(notifications)
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error sending portfolio alert: {e}")
            self.alerts_failed_today += 1
            return False
    
    async def monitor_and_alert_market_conditions(
        self,
        market_data: List[MOEXMarketData],
        user_ids: List[str]
    ) -> Dict[str, List[MarketAlert]]:
        """Monitor market conditions and send alerts to users"""
        results = {}
        
        try:
            for user_id in user_ids:
                preferences = self.user_preferences.get(user_id)
                if not preferences:
                    continue
                
                alerts = []
                
                # Monitor volatility
                volatility_alerts = await self.market_monitor.monitor_market_volatility(
                    market_data, preferences
                )
                alerts.extend(volatility_alerts)
                
                # Monitor volume spikes
                volume_alerts = await self.market_monitor.monitor_volume_spikes(
                    market_data, preferences
                )
                alerts.extend(volume_alerts)
                
                # Monitor price movements
                price_alerts = await self.market_monitor.monitor_price_movements(
                    market_data, preferences
                )
                alerts.extend(price_alerts)
                
                # Track alerts
                if alerts:
                    for alert in alerts:
                        self._track_alert('market_alert', user_id, alert.symbol or 'MARKET', 1)
                    
                    self.alerts_sent_today += len(alerts)
                
                results[user_id] = alerts
            
        except Exception as e:
            self.logger.error(f"Error monitoring market conditions: {e}")
            self.alerts_failed_today += 1
        
        return results
    
    async def monitor_and_alert_geopolitical_events(
        self,
        user_ids: List[str]
    ) -> Dict[str, List[GeopoliticalAlert]]:
        """Monitor geopolitical events and send alerts"""
        results = {}
        
        try:
            for user_id in user_ids:
                preferences = self.user_preferences.get(user_id)
                if not preferences:
                    continue
                
                # Monitor geopolitical events
                geo_alerts = await self.market_monitor.monitor_geopolitical_events(preferences)
                
                # Track alerts
                if geo_alerts:
                    for alert in geo_alerts:
                        self._track_alert('geopolitical_alert', user_id, alert.event_type, 1)
                    
                    self.alerts_sent_today += len(geo_alerts)
                
                results[user_id] = geo_alerts
            
        except Exception as e:
            self.logger.error(f"Error monitoring geopolitical events: {e}")
            self.alerts_failed_today += 1
        
        return results
    
    async def monitor_portfolio_risks(
        self,
        user_id: str,
        portfolio: Portfolio
    ) -> List[PortfolioAlert]:
        """Monitor portfolio risk thresholds"""
        try:
            preferences = self.user_preferences.get(user_id)
            if not preferences:
                return []
            
            # Monitor portfolio risks
            risk_alerts = await self.market_monitor.monitor_portfolio_risk_thresholds(
                portfolio, preferences
            )
            
            # Track alerts
            if risk_alerts:
                for alert in risk_alerts:
                    self._track_alert('portfolio_risk', user_id, alert.alert_type, 1)
                
                self.alerts_sent_today += len(risk_alerts)
            
            return risk_alerts
            
        except Exception as e:
            self.logger.error(f"Error monitoring portfolio risks: {e}")
            self.alerts_failed_today += 1
            return []
    
    async def send_custom_alert(
        self,
        user_id: str,
        alert_type: str,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM
    ) -> bool:
        """Send custom alert to user"""
        try:
            preferences = self.user_preferences.get(user_id)
            if not preferences:
                return False
            
            # Get channels for priority
            channels = self.config.get_channels_for_priority(priority)
            
            notifications_sent = 0
            for channel in channels:
                # Get recipient for channel
                recipient = self.notification_service._get_recipient_for_channel(channel, preferences)
                if not recipient:
                    continue
                
                # Create custom notification
                notification = self.notification_service.create_notification(
                    notification_type=NotificationType.SYSTEM_ALERT,
                    priority=priority,
                    channel=channel,
                    recipient=recipient,
                    data={'title': title, 'message': message, 'alert_type': alert_type}
                )
                
                # Send notification
                success = await self.notification_service.send_notification(notification)
                if success:
                    notifications_sent += 1
            
            # Track alert
            if notifications_sent > 0:
                self._track_alert('custom_alert', user_id, alert_type, notifications_sent)
                self.alerts_sent_today += notifications_sent
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error sending custom alert: {e}")
            self.alerts_failed_today += 1
            return False
    
    def _track_alert(self, alert_type: str, user_id: str, symbol: str, count: int) -> None:
        """Track alert for analytics"""
        alert_record = {
            'timestamp': datetime.now(self.moscow_tz),
            'alert_type': alert_type,
            'user_id': user_id,
            'symbol': symbol,
            'count': count
        }
        
        self.alert_history.append(alert_record)
        
        # Keep only last 1000 alerts
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-1000:]
        
        # Track active alerts
        alert_key = f"{alert_type}_{user_id}_{symbol}"
        self.active_alerts[alert_key] = datetime.now()
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics"""
        # Reset daily counters if needed
        today = datetime.now().date()
        if today != self.last_reset_date:
            self.alerts_sent_today = 0
            self.alerts_failed_today = 0
            self.last_reset_date = today
        
        # Calculate statistics from history
        recent_alerts = [
            alert for alert in self.alert_history
            if alert['timestamp'] > datetime.now(self.moscow_tz) - timedelta(days=7)
        ]
        
        alert_types = {}
        for alert in recent_alerts:
            alert_type = alert['alert_type']
            alert_types[alert_type] = alert_types.get(alert_type, 0) + alert['count']
        
        return {
            'alerts_sent_today': self.alerts_sent_today,
            'alerts_failed_today': self.alerts_failed_today,
            'success_rate_today': (
                self.alerts_sent_today / (self.alerts_sent_today + self.alerts_failed_today)
                if (self.alerts_sent_today + self.alerts_failed_today) > 0 else 1.0
            ),
            'alerts_last_7_days': len(recent_alerts),
            'alert_types_last_7_days': alert_types,
            'active_users': len(self.user_preferences),
            'notification_queue_size': len(self.notification_service.notification_queue),
            'failed_notifications': len(self.notification_service.failed_notifications)
        }
    
    async def process_notification_queue(self) -> None:
        """Process queued notifications"""
        await self.notification_service.process_notification_queue()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on alert system"""
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now(self.moscow_tz).isoformat(),
            'services': {}
        }
        
        try:
            # Check notification service
            notification_stats = self.notification_service.get_notification_stats()
            health_status['services']['notification_service'] = {
                'status': 'healthy',
                'queued_notifications': notification_stats['queued'],
                'failed_notifications': notification_stats['failed']
            }
            
            # Check market monitor
            market_condition = self.market_monitor.get_market_condition()
            health_status['services']['market_monitor'] = {
                'status': 'healthy',
                'market_phase': market_condition.market_phase,
                'volatility_index': market_condition.volatility_index
            }
            
            # Check alert statistics
            alert_stats = self.get_alert_statistics()
            health_status['alert_statistics'] = alert_stats
            
            # Determine overall health
            if (alert_stats['success_rate_today'] < 0.9 or 
                notification_stats['failed'] > 10 or
                market_condition.volatility_index > 0.1):
                health_status['status'] = 'degraded'
            
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['error'] = str(e)
            self.logger.error(f"Health check failed: {e}")
        
        return health_status
    
    async def start_monitoring(self, check_interval: int = 60) -> None:
        """Start continuous monitoring loop"""
        self.logger.info("Starting alert manager monitoring loop")
        
        while True:
            try:
                # Process notification queue
                await self.process_notification_queue()
                
                # Wait for next check
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(check_interval)
    
    def stop_monitoring(self) -> None:
        """Stop monitoring loop"""
        self.logger.info("Stopping alert manager monitoring")
        # Implementation would cancel the monitoring task
        pass


# Convenience functions for easy integration
async def create_alert_manager(config_path: Optional[str] = None) -> AlertManager:
    """Create and initialize alert manager"""
    if config_path:
        # Load config from file (implementation would read from file)
        config = load_alert_config_from_env()
    else:
        config = load_alert_config_from_env()
    
    return AlertManager(config)


async def send_test_alerts(alert_manager: AlertManager, user_id: str) -> Dict[str, bool]:
    """Send test alerts to verify system functionality"""
    results = {}
    
    # Test trading signal alert
    from ..models.trading import TradingSignal, OrderAction
    test_signal = TradingSignal(
        symbol="SBER",
        action=OrderAction.BUY,
        confidence=0.85,
        target_price=Decimal("280.00"),
        stop_loss=Decimal("230.00")
    )
    
    results['trading_signal'] = await alert_manager.send_trading_signal_alert(
        user_id, test_signal, 0.85, "Тестовый торговый сигнал"
    )
    
    # Test custom alert
    results['custom_alert'] = await alert_manager.send_custom_alert(
        user_id, "TEST", "Тестовое уведомление", 
        "Это тестовое уведомление для проверки системы оповещений",
        NotificationPriority.LOW
    )
    
    return results