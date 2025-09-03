#!/usr/bin/env python3
"""
System Health Monitor for Russian Trading Bot
Comprehensive monitoring and alerting for production system
"""

import os
import logging
import asyncio
import psutil
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import aiohttp
import redis
import psycopg2

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class HealthMetric:
    """Health metric data structure"""
    name: str
    value: float
    unit: str
    status: str  # 'healthy', 'warning', 'critical'
    threshold_warning: float
    threshold_critical: float
    timestamp: datetime

@dataclass
class SystemAlert:
    """System alert data structure"""
    alert_id: str
    severity: str  # 'info', 'warning', 'critical'
    component: str
    message: str
    details: Dict
    timestamp: datetime
    resolved: bool = False

class RussianTradingSystemMonitor:
    """Comprehensive system health monitor"""
    
    def __init__(self, config: Dict = None):
        self.config = config or self._default_config()
        self.session: Optional[aiohttp.ClientSession] = None
        self.redis_client: Optional[redis.Redis] = None
        self.db_connection: Optional[psycopg2.connection] = None
        
        # Monitoring state
        self.metrics_history = {}
        self.active_alerts = {}
        self.alert_history = []
        self.monitoring_enabled = True
        
    def _default_config(self) -> Dict:
        """Default monitoring configuration"""
        return {
            'check_interval': 30,  # seconds
            'metrics_retention': 3600,  # 1 hour
            'alert_cooldown': 300,  # 5 minutes
            'thresholds': {
                'cpu_warning': 70.0,
                'cpu_critical': 90.0,
                'memory_warning': 80.0,
                'memory_critical': 95.0,
                'disk_warning': 85.0,
                'disk_critical': 95.0,
                'response_time_warning': 5.0,
                'response_time_critical': 10.0,
                'error_rate_warning': 0.05,
                'error_rate_critical': 0.10
            },
            'notification_channels': {
                'telegram': True,
                'email': True,
                'webhook': True
            }
        }
        
    async def __aenter__(self):
        """Async context manager entry"""
        # Initialize HTTP session
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
        # Initialize Redis connection
        try:
            self.redis_client = redis.Redis(
                host=os.getenv('REDIS_HOST', 'redis'),
                port=int(os.getenv('REDIS_PORT', '6379')),
                password=os.getenv('REDIS_PASSWORD'),
                decode_responses=True
            )
            self.redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            
        # Initialize database connection
        try:
            self.db_connection = psycopg2.connect(
                host=os.getenv('DB_HOST', 'postgres'),
                port=int(os.getenv('DB_PORT', '5432')),
                database=os.getenv('DB_NAME', 'russian_trading'),
                user=os.getenv('DB_USER', 'trading_user'),
                password=os.getenv('DB_PASSWORD')
            )
        except Exception as e:
            logger.warning(f"Database connection failed: {e}")
            
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
        if self.db_connection:
            self.db_connection.close()
            
    def collect_system_metrics(self) -> List[HealthMetric]:
        """Collect system performance metrics"""
        metrics = []
        timestamp = datetime.now(timezone.utc)
        
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_status = self._get_status(
            cpu_percent,
            self.config['thresholds']['cpu_warning'],
            self.config['thresholds']['cpu_critical']
        )
        
        metrics.append(HealthMetric(
            name='cpu_usage',
            value=cpu_percent,
            unit='%',
            status=cpu_status,
            threshold_warning=self.config['thresholds']['cpu_warning'],
            threshold_critical=self.config['thresholds']['cpu_critical'],
            timestamp=timestamp
        ))
        
        # Memory metrics
        memory = psutil.virtual_memory()
        memory_status = self._get_status(
            memory.percent,
            self.config['thresholds']['memory_warning'],
            self.config['thresholds']['memory_critical']
        )
        
        metrics.append(HealthMetric(
            name='memory_usage',
            value=memory.percent,
            unit='%',
            status=memory_status,
            threshold_warning=self.config['thresholds']['memory_warning'],
            threshold_critical=self.config['thresholds']['memory_critical'],
            timestamp=timestamp
        ))
        
        # Disk metrics
        disk = psutil.disk_usage('/')
        disk_status = self._get_status(
            disk.percent,
            self.config['thresholds']['disk_warning'],
            self.config['thresholds']['disk_critical']
        )
        
        metrics.append(HealthMetric(
            name='disk_usage',
            value=disk.percent,
            unit='%',
            status=disk_status,
            threshold_warning=self.config['thresholds']['disk_warning'],
            threshold_critical=self.config['thresholds']['disk_critical'],
            timestamp=timestamp
        ))
        
        # Network metrics
        network = psutil.net_io_counters()
        metrics.append(HealthMetric(
            name='network_bytes_sent',
            value=network.bytes_sent,
            unit='bytes',
            status='healthy',
            threshold_warning=0,
            threshold_critical=0,
            timestamp=timestamp
        ))
        
        metrics.append(HealthMetric(
            name='network_bytes_recv',
            value=network.bytes_recv,
            unit='bytes',
            status='healthy',
            threshold_warning=0,
            threshold_critical=0,
            timestamp=timestamp
        ))
        
        return metrics
        
    async def check_application_health(self) -> List[HealthMetric]:
        """Check application-specific health metrics"""
        metrics = []
        timestamp = datetime.now(timezone.utc)
        
        # Check main application endpoint
        try:
            start_time = time.time()
            async with self.session.get('http://trading-bot:8000/health') as response:
                response_time = time.time() - start_time
                
                response_status = self._get_status(
                    response_time,
                    self.config['thresholds']['response_time_warning'],
                    self.config['thresholds']['response_time_critical']
                )
                
                metrics.append(HealthMetric(
                    name='app_response_time',
                    value=response_time,
                    unit='seconds',
                    status=response_status,
                    threshold_warning=self.config['thresholds']['response_time_warning'],
                    threshold_critical=self.config['thresholds']['response_time_critical'],
                    timestamp=timestamp
                ))
                
                # Check if response is successful
                app_status = 'healthy' if response.status == 200 else 'critical'
                metrics.append(HealthMetric(
                    name='app_availability',
                    value=1.0 if response.status == 200 else 0.0,
                    unit='boolean',
                    status=app_status,
                    threshold_warning=0.95,
                    threshold_critical=0.90,
                    timestamp=timestamp
                ))
                
        except Exception as e:
            logger.error(f"Application health check failed: {e}")
            metrics.append(HealthMetric(
                name='app_availability',
                value=0.0,
                unit='boolean',
                status='critical',
                threshold_warning=0.95,
                threshold_critical=0.90,
                timestamp=timestamp
            ))
            
        return metrics
        
    async def check_database_health(self) -> List[HealthMetric]:
        """Check database health metrics"""
        metrics = []
        timestamp = datetime.now(timezone.utc)
        
        if not self.db_connection:
            metrics.append(HealthMetric(
                name='db_availability',
                value=0.0,
                unit='boolean',
                status='critical',
                threshold_warning=0.95,
                threshold_critical=0.90,
                timestamp=timestamp
            ))
            return metrics
            
        try:
            cursor = self.db_connection.cursor()
            
            # Test basic connectivity
            start_time = time.time()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            response_time = time.time() - start_time
            
            response_status = self._get_status(
                response_time,
                1.0,  # 1 second warning
                5.0   # 5 seconds critical
            )
            
            metrics.append(HealthMetric(
                name='db_response_time',
                value=response_time,
                unit='seconds',
                status=response_status,
                threshold_warning=1.0,
                threshold_critical=5.0,
                timestamp=timestamp
            ))
            
            # Check database size
            cursor.execute("""
                SELECT pg_size_pretty(pg_database_size(current_database()))
            """)
            db_size = cursor.fetchone()[0]
            
            # Check active connections
            cursor.execute("""
                SELECT count(*) FROM pg_stat_activity 
                WHERE state = 'active'
            """)
            active_connections = cursor.fetchone()[0]
            
            metrics.append(HealthMetric(
                name='db_active_connections',
                value=active_connections,
                unit='count',
                status='healthy' if active_connections < 50 else 'warning',
                threshold_warning=50,
                threshold_critical=100,
                timestamp=timestamp
            ))
            
            # Check recent data
            cursor.execute("""
                SELECT COUNT(*) FROM market_data 
                WHERE timestamp > NOW() - INTERVAL '1 hour'
            """)
            recent_data = cursor.fetchone()[0]
            
            metrics.append(HealthMetric(
                name='db_recent_data_points',
                value=recent_data,
                unit='count',
                status='healthy' if recent_data > 0 else 'warning',
                threshold_warning=1,
                threshold_critical=0,
                timestamp=timestamp
            ))
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            metrics.append(HealthMetric(
                name='db_availability',
                value=0.0,
                unit='boolean',
                status='critical',
                threshold_warning=0.95,
                threshold_critical=0.90,
                timestamp=timestamp
            ))
            
        return metrics
        
    async def check_redis_health(self) -> List[HealthMetric]:
        """Check Redis health metrics"""
        metrics = []
        timestamp = datetime.now(timezone.utc)
        
        if not self.redis_client:
            metrics.append(HealthMetric(
                name='redis_availability',
                value=0.0,
                unit='boolean',
                status='critical',
                threshold_warning=0.95,
                threshold_critical=0.90,
                timestamp=timestamp
            ))
            return metrics
            
        try:
            # Test basic connectivity
            start_time = time.time()
            self.redis_client.ping()
            response_time = time.time() - start_time
            
            response_status = self._get_status(
                response_time,
                0.1,  # 100ms warning
                1.0   # 1 second critical
            )
            
            metrics.append(HealthMetric(
                name='redis_response_time',
                value=response_time,
                unit='seconds',
                status=response_status,
                threshold_warning=0.1,
                threshold_critical=1.0,
                timestamp=timestamp
            ))
            
            # Get Redis info
            info = self.redis_client.info()
            
            # Memory usage
            used_memory = info.get('used_memory', 0)
            max_memory = info.get('maxmemory', 0)
            
            if max_memory > 0:
                memory_percent = (used_memory / max_memory) * 100
                memory_status = self._get_status(memory_percent, 80.0, 95.0)
                
                metrics.append(HealthMetric(
                    name='redis_memory_usage',
                    value=memory_percent,
                    unit='%',
                    status=memory_status,
                    threshold_warning=80.0,
                    threshold_critical=95.0,
                    timestamp=timestamp
                ))
                
            # Connected clients
            connected_clients = info.get('connected_clients', 0)
            metrics.append(HealthMetric(
                name='redis_connected_clients',
                value=connected_clients,
                unit='count',
                status='healthy' if connected_clients < 100 else 'warning',
                threshold_warning=100,
                threshold_critical=200,
                timestamp=timestamp
            ))
            
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            metrics.append(HealthMetric(
                name='redis_availability',
                value=0.0,
                unit='boolean',
                status='critical',
                threshold_warning=0.95,
                threshold_critical=0.90,
                timestamp=timestamp
            ))
            
        return metrics
        
    async def check_external_services(self) -> List[HealthMetric]:
        """Check external services health"""
        metrics = []
        timestamp = datetime.now(timezone.utc)
        
        # Check MOEX API
        try:
            start_time = time.time()
            async with self.session.get(
                'https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.json',
                params={'iss.meta': 'off', 'start': '0', 'limit': '1'}
            ) as response:
                response_time = time.time() - start_time
                
                response_status = self._get_status(
                    response_time,
                    self.config['thresholds']['response_time_warning'],
                    self.config['thresholds']['response_time_critical']
                )
                
                metrics.append(HealthMetric(
                    name='moex_api_response_time',
                    value=response_time,
                    unit='seconds',
                    status=response_status,
                    threshold_warning=self.config['thresholds']['response_time_warning'],
                    threshold_critical=self.config['thresholds']['response_time_critical'],
                    timestamp=timestamp
                ))
                
                moex_status = 'healthy' if response.status == 200 else 'critical'
                metrics.append(HealthMetric(
                    name='moex_api_availability',
                    value=1.0 if response.status == 200 else 0.0,
                    unit='boolean',
                    status=moex_status,
                    threshold_warning=0.95,
                    threshold_critical=0.90,
                    timestamp=timestamp
                ))
                
        except Exception as e:
            logger.error(f"MOEX API health check failed: {e}")
            metrics.append(HealthMetric(
                name='moex_api_availability',
                value=0.0,
                unit='boolean',
                status='critical',
                threshold_warning=0.95,
                threshold_critical=0.90,
                timestamp=timestamp
            ))
            
        return metrics
        
    def _get_status(self, value: float, warning_threshold: float, critical_threshold: float) -> str:
        """Determine status based on thresholds"""
        if value >= critical_threshold:
            return 'critical'
        elif value >= warning_threshold:
            return 'warning'
        else:
            return 'healthy'
            
    async def collect_all_metrics(self) -> List[HealthMetric]:
        """Collect all health metrics"""
        all_metrics = []
        
        # System metrics
        all_metrics.extend(self.collect_system_metrics())
        
        # Application metrics
        all_metrics.extend(await self.check_application_health())
        
        # Database metrics
        all_metrics.extend(await self.check_database_health())
        
        # Redis metrics
        all_metrics.extend(await self.check_redis_health())
        
        # External services metrics
        all_metrics.extend(await self.check_external_services())
        
        return all_metrics
        
    def store_metrics(self, metrics: List[HealthMetric]):
        """Store metrics in history"""
        current_time = time.time()
        
        for metric in metrics:
            metric_name = metric.name
            
            if metric_name not in self.metrics_history:
                self.metrics_history[metric_name] = []
                
            # Add new metric
            self.metrics_history[metric_name].append({
                'timestamp': current_time,
                'value': metric.value,
                'status': metric.status
            })
            
            # Clean old metrics
            retention_time = current_time - self.config['metrics_retention']
            self.metrics_history[metric_name] = [
                m for m in self.metrics_history[metric_name]
                if m['timestamp'] > retention_time
            ]
            
        # Store in Redis if available
        if self.redis_client:
            try:
                metrics_data = {
                    'timestamp': current_time,
                    'metrics': [asdict(m) for m in metrics]
                }
                self.redis_client.set(
                    'system_health_metrics',
                    json.dumps(metrics_data, default=str),
                    ex=3600  # Expire after 1 hour
                )
            except Exception as e:
                logger.error(f"Failed to store metrics in Redis: {e}")
                
    def check_for_alerts(self, metrics: List[HealthMetric]) -> List[SystemAlert]:
        """Check metrics for alert conditions"""
        new_alerts = []
        current_time = datetime.now(timezone.utc)
        
        for metric in metrics:
            if metric.status in ['warning', 'critical']:
                alert_id = f"{metric.name}_{metric.status}"
                
                # Check if alert already exists and is within cooldown
                if alert_id in self.active_alerts:
                    last_alert_time = self.active_alerts[alert_id]['timestamp']
                    time_diff = (current_time - last_alert_time).total_seconds()
                    
                    if time_diff < self.config['alert_cooldown']:
                        continue  # Skip alert due to cooldown
                        
                # Create new alert
                alert = SystemAlert(
                    alert_id=alert_id,
                    severity=metric.status,
                    component=metric.name,
                    message=f"{metric.name} is {metric.status}: {metric.value}{metric.unit}",
                    details={
                        'metric_name': metric.name,
                        'current_value': metric.value,
                        'unit': metric.unit,
                        'threshold_warning': metric.threshold_warning,
                        'threshold_critical': metric.threshold_critical,
                        'status': metric.status
                    },
                    timestamp=current_time
                )
                
                new_alerts.append(alert)
                self.active_alerts[alert_id] = asdict(alert)
                self.alert_history.append(alert)
                
        return new_alerts
        
    async def send_alerts(self, alerts: List[SystemAlert]):
        """Send alerts through configured channels"""
        for alert in alerts:
            alert_message = self._format_alert_message(alert)
            
            # Send to Telegram
            if self.config['notification_channels']['telegram']:
                await self._send_telegram_alert(alert_message, alert.severity)
                
            # Send to webhook
            if self.config['notification_channels']['webhook']:
                await self._send_webhook_alert(alert)
                
            logger.warning(f"Alert sent: {alert.message}")
            
    def _format_alert_message(self, alert: SystemAlert) -> str:
        """Format alert message for notifications"""
        severity_emoji = {
            'info': 'ℹ️',
            'warning': '⚠️',
            'critical': '🚨'
        }
        
        emoji = severity_emoji.get(alert.severity, '❓')
        
        message = f"{emoji} Система торговли - {alert.severity.upper()}\n\n"
        message += f"Компонент: {alert.component}\n"
        message += f"Сообщение: {alert.message}\n"
        message += f"Время: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        
        if alert.details:
            message += f"\nДетали:\n"
            for key, value in alert.details.items():
                message += f"  {key}: {value}\n"
                
        return message
        
    async def _send_telegram_alert(self, message: str, severity: str):
        """Send alert to Telegram"""
        telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not telegram_token or not telegram_chat_id:
            return
            
        try:
            url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
            data = {
                'chat_id': telegram_chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    logger.info("Telegram alert sent successfully")
                else:
                    logger.error(f"Failed to send Telegram alert: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")
            
    async def _send_webhook_alert(self, alert: SystemAlert):
        """Send alert to webhook"""
        webhook_url = os.getenv('ALERT_WEBHOOK_URL')
        
        if not webhook_url:
            return
            
        try:
            alert_data = asdict(alert)
            alert_data['timestamp'] = alert.timestamp.isoformat()
            
            async with self.session.post(webhook_url, json=alert_data) as response:
                if response.status == 200:
                    logger.info("Webhook alert sent successfully")
                else:
                    logger.error(f"Failed to send webhook alert: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error sending webhook alert: {e}")
            
    async def run_monitoring_cycle(self):
        """Run a single monitoring cycle"""
        try:
            # Collect all metrics
            metrics = await self.collect_all_metrics()
            
            # Store metrics
            self.store_metrics(metrics)
            
            # Check for alerts
            new_alerts = self.check_for_alerts(metrics)
            
            # Send alerts
            if new_alerts:
                await self.send_alerts(new_alerts)
                
            # Log summary
            critical_count = sum(1 for m in metrics if m.status == 'critical')
            warning_count = sum(1 for m in metrics if m.status == 'warning')
            healthy_count = sum(1 for m in metrics if m.status == 'healthy')
            
            logger.info(f"Monitoring cycle completed: {healthy_count} healthy, {warning_count} warnings, {critical_count} critical")
            
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'metrics_count': len(metrics),
                'healthy': healthy_count,
                'warnings': warning_count,
                'critical': critical_count,
                'new_alerts': len(new_alerts)
            }
            
        except Exception as e:
            logger.error(f"Error in monitoring cycle: {e}")
            return None
            
    async def start_monitoring(self):
        """Start continuous monitoring"""
        logger.info("Starting system health monitoring...")
        
        while self.monitoring_enabled:
            try:
                await self.run_monitoring_cycle()
                await asyncio.sleep(self.config['check_interval'])
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)  # Shorter wait on error
                
    def get_health_summary(self) -> Dict:
        """Get current health summary"""
        summary = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'overall_status': 'unknown',
            'active_alerts': len(self.active_alerts),
            'metrics_summary': {},
            'recent_alerts': []
        }
        
        # Get recent metrics summary
        for metric_name, history in self.metrics_history.items():
            if history:
                latest = history[-1]
                summary['metrics_summary'][metric_name] = {
                    'current_value': latest['value'],
                    'status': latest['status'],
                    'last_updated': latest['timestamp']
                }
                
        # Get recent alerts
        recent_alerts = sorted(self.alert_history[-10:], key=lambda x: x.timestamp, reverse=True)
        summary['recent_alerts'] = [asdict(alert) for alert in recent_alerts]
        
        # Determine overall status
        if any(alert['severity'] == 'critical' for alert in self.active_alerts.values()):
            summary['overall_status'] = 'critical'
        elif any(alert['severity'] == 'warning' for alert in self.active_alerts.values()):
            summary['overall_status'] = 'warning'
        else:
            summary['overall_status'] = 'healthy'
            
        return summary

async def main():
    """Main monitoring function"""
    logger.info("🔍 Starting Russian Trading Bot System Health Monitor")
    
    async with RussianTradingSystemMonitor() as monitor:
        # Run a single monitoring cycle for testing
        result = await monitor.run_monitoring_cycle()
        
        if result:
            logger.info(f"Monitoring test completed successfully: {result}")
            
            # Get health summary
            summary = monitor.get_health_summary()
            logger.info(f"Overall system status: {summary['overall_status']}")
            logger.info(f"Active alerts: {summary['active_alerts']}")
            
        else:
            logger.error("Monitoring test failed")

if __name__ == "__main__":
    asyncio.run(main())