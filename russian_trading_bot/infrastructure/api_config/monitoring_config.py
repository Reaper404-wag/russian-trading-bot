#!/usr/bin/env python3
"""
External API Monitoring Configuration
Monitors all external Russian market data sources and APIs
"""

import os
import logging
import asyncio
import aiohttp
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ServiceType(Enum):
    MARKET_DATA = "market_data"
    NEWS_FEED = "news_feed"
    BROKER_API = "broker_api"
    NOTIFICATION = "notification"

@dataclass
class MonitoringTarget:
    """Configuration for monitoring target"""
    name: str
    service_type: ServiceType
    url: str
    check_interval: int = 60  # seconds
    timeout: int = 30
    expected_status: int = 200
    critical: bool = True
    headers: Optional[Dict] = None
    auth_required: bool = False
    
    # Health check parameters
    response_time_threshold: float = 5.0  # seconds
    availability_threshold: float = 0.95  # 95% uptime
    
    # Alert parameters
    alert_after_failures: int = 3
    recovery_notification: bool = True

class ExternalAPIMonitor:
    """Monitors external APIs and services for Russian trading bot"""
    
    def __init__(self):
        self.targets = self._initialize_targets()
        self.session: Optional[aiohttp.ClientSession] = None
        self.monitoring_data = {}
        self.alert_states = {}
        self.running = False
        
    def _initialize_targets(self) -> Dict[str, MonitoringTarget]:
        """Initialize monitoring targets"""
        return {
            # MOEX API endpoints
            'moex_securities': MonitoringTarget(
                name='MOEX Securities API',
                service_type=ServiceType.MARKET_DATA,
                url='https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.json',
                check_interval=60,
                timeout=15,
                critical=True,
                headers={'User-Agent': 'RussianTradingBot/1.0'}
            ),
            'moex_marketdata': MonitoringTarget(
                name='MOEX Market Data API',
                service_type=ServiceType.MARKET_DATA,
                url='https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities/SBER.json',
                check_interval=30,
                timeout=10,
                critical=True,
                headers={'User-Agent': 'RussianTradingBot/1.0'}
            ),
            'moex_history': MonitoringTarget(
                name='MOEX Historical Data API',
                service_type=ServiceType.MARKET_DATA,
                url='https://iss.moex.com/iss/history/engines/stock/markets/shares/boards/TQBR/securities/SBER.json',
                check_interval=300,  # 5 minutes
                timeout=20,
                critical=False,
                headers={'User-Agent': 'RussianTradingBot/1.0'}
            ),
            
            # Russian news sources
            'rbc_news': MonitoringTarget(
                name='RBC News',
                service_type=ServiceType.NEWS_FEED,
                url='https://www.rbc.ru',
                check_interval=180,  # 3 minutes
                timeout=15,
                critical=False,
                headers={'User-Agent': 'RussianTradingBot/1.0'}
            ),
            'vedomosti_rss': MonitoringTarget(
                name='Vedomosti RSS',
                service_type=ServiceType.NEWS_FEED,
                url='https://www.vedomosti.ru/rss/news',
                check_interval=300,  # 5 minutes
                timeout=15,
                critical=False,
                headers={'User-Agent': 'RussianTradingBot/1.0'}
            ),
            'kommersant_rss': MonitoringTarget(
                name='Kommersant RSS',
                service_type=ServiceType.NEWS_FEED,
                url='https://www.kommersant.ru/RSS/news.xml',
                check_interval=300,  # 5 minutes
                timeout=15,
                critical=False,
                headers={'User-Agent': 'RussianTradingBot/1.0'}
            ),
            'cbr_news': MonitoringTarget(
                name='Central Bank RSS',
                service_type=ServiceType.NEWS_FEED,
                url='https://cbr.ru/rss/RssPress/',
                check_interval=1800,  # 30 minutes
                timeout=20,
                critical=False,
                headers={'User-Agent': 'RussianTradingBot/1.0'}
            ),
            
            # Broker APIs (if configured)
            'tinkoff_api': MonitoringTarget(
                name='Tinkoff Invest API',
                service_type=ServiceType.BROKER_API,
                url='https://invest-public-api.tinkoff.ru/rest',
                check_interval=120,  # 2 minutes
                timeout=10,
                critical=True,
                auth_required=True,
                headers={'User-Agent': 'RussianTradingBot/1.0'}
            ),
            
            # Notification services
            'telegram_api': MonitoringTarget(
                name='Telegram Bot API',
                service_type=ServiceType.NOTIFICATION,
                url='https://api.telegram.org',
                check_interval=300,  # 5 minutes
                timeout=10,
                critical=False,
                headers={'User-Agent': 'RussianTradingBot/1.0'}
            )
        }
        
    async def __aenter__(self):
        """Async context manager entry"""
        connector = aiohttp.TCPConnector(
            limit=50,
            limit_per_host=10,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
        # Initialize monitoring data
        for target_name in self.targets:
            self.monitoring_data[target_name] = {
                'status': 'unknown',
                'last_check': None,
                'response_time': None,
                'consecutive_failures': 0,
                'total_checks': 0,
                'successful_checks': 0,
                'availability': 0.0,
                'last_error': None
            }
            self.alert_states[target_name] = {
                'alert_sent': False,
                'last_alert_time': None,
                'recovery_sent': False
            }
            
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        self.running = False
        if self.session:
            await self.session.close()
            
    async def check_target(self, target_name: str) -> Dict:
        """Check a specific monitoring target"""
        if target_name not in self.targets:
            return {'status': 'error', 'message': f'Unknown target: {target_name}'}
            
        target = self.targets[target_name]
        start_time = time.time()
        
        try:
            headers = target.headers or {}
            
            # Add authentication if required
            if target.auth_required:
                if target.service_type == ServiceType.BROKER_API and target_name == 'tinkoff_api':
                    token = os.getenv('TINKOFF_API_TOKEN')
                    if token:
                        headers['Authorization'] = f'Bearer {token}'
                        
            async with self.session.get(
                target.url, 
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=target.timeout)
            ) as response:
                response_time = time.time() - start_time
                
                # Update monitoring data
                data = self.monitoring_data[target_name]
                data['last_check'] = datetime.now(timezone.utc)
                data['response_time'] = response_time
                data['total_checks'] += 1
                
                if response.status == target.expected_status:
                    data['status'] = 'healthy'
                    data['successful_checks'] += 1
                    data['consecutive_failures'] = 0
                    data['last_error'] = None
                    
                    # Send recovery notification if needed
                    if self.alert_states[target_name]['alert_sent'] and target.recovery_notification:
                        await self._send_recovery_notification(target_name, target)
                        
                else:
                    data['status'] = 'unhealthy'
                    data['consecutive_failures'] += 1
                    data['last_error'] = f'HTTP {response.status}'
                    
                    # Send alert if threshold reached
                    if data['consecutive_failures'] >= target.alert_after_failures:
                        await self._send_alert(target_name, target, data['last_error'])
                        
                # Calculate availability
                data['availability'] = data['successful_checks'] / data['total_checks']
                
                # Check response time threshold
                if response_time > target.response_time_threshold:
                    data['status'] = 'degraded'
                    
                return {
                    'status': data['status'],
                    'response_time': response_time,
                    'status_code': response.status,
                    'availability': data['availability']
                }
                
        except asyncio.TimeoutError:
            return await self._handle_check_error(target_name, target, 'Timeout')
        except aiohttp.ClientError as e:
            return await self._handle_check_error(target_name, target, f'Connection error: {e}')
        except Exception as e:
            return await self._handle_check_error(target_name, target, f'Unexpected error: {e}')
            
    async def _handle_check_error(self, target_name: str, target: MonitoringTarget, error_msg: str) -> Dict:
        """Handle check error"""
        response_time = time.time() - time.time()  # This will be 0, but we need to track it
        
        data = self.monitoring_data[target_name]
        data['last_check'] = datetime.now(timezone.utc)
        data['response_time'] = None
        data['total_checks'] += 1
        data['status'] = 'unhealthy'
        data['consecutive_failures'] += 1
        data['last_error'] = error_msg
        
        # Calculate availability
        data['availability'] = data['successful_checks'] / data['total_checks']
        
        # Send alert if threshold reached
        if data['consecutive_failures'] >= target.alert_after_failures:
            await self._send_alert(target_name, target, error_msg)
            
        return {
            'status': 'unhealthy',
            'response_time': None,
            'error': error_msg,
            'availability': data['availability']
        }
        
    async def _send_alert(self, target_name: str, target: MonitoringTarget, error_msg: str):
        """Send alert for failed service"""
        alert_state = self.alert_states[target_name]
        
        if alert_state['alert_sent']:
            return  # Alert already sent
            
        alert_message = f"🚨 Сервис недоступен: {target.name}\n"
        alert_message += f"Ошибка: {error_msg}\n"
        alert_message += f"Количество неудачных попыток: {self.monitoring_data[target_name]['consecutive_failures']}\n"
        alert_message += f"Критичность: {'Высокая' if target.critical else 'Низкая'}\n"
        alert_message += f"Время: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
        
        try:
            # Send to notification service
            notification_url = "http://trading-bot:8000/api/notifications/alert"
            async with self.session.post(
                notification_url,
                json={
                    'type': 'service_down',
                    'severity': 'high' if target.critical else 'medium',
                    'service': target_name,
                    'message': alert_message,
                    'details': {
                        'target': target.name,
                        'url': target.url,
                        'error': error_msg,
                        'consecutive_failures': self.monitoring_data[target_name]['consecutive_failures']
                    }
                }
            ) as response:
                if response.status == 200:
                    alert_state['alert_sent'] = True
                    alert_state['last_alert_time'] = datetime.now(timezone.utc)
                    logger.info(f"Alert sent for {target_name}")
                    
        except Exception as e:
            logger.error(f"Failed to send alert for {target_name}: {e}")
            
    async def _send_recovery_notification(self, target_name: str, target: MonitoringTarget):
        """Send recovery notification"""
        alert_state = self.alert_states[target_name]
        
        if alert_state['recovery_sent']:
            return  # Recovery notification already sent
            
        recovery_message = f"✅ Сервис восстановлен: {target.name}\n"
        recovery_message += f"Время восстановления: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
        recovery_message += f"Доступность: {self.monitoring_data[target_name]['availability']:.2%}"
        
        try:
            # Send to notification service
            notification_url = "http://trading-bot:8000/api/notifications/alert"
            async with self.session.post(
                notification_url,
                json={
                    'type': 'service_recovery',
                    'severity': 'info',
                    'service': target_name,
                    'message': recovery_message,
                    'details': {
                        'target': target.name,
                        'availability': self.monitoring_data[target_name]['availability']
                    }
                }
            ) as response:
                if response.status == 200:
                    alert_state['alert_sent'] = False
                    alert_state['recovery_sent'] = True
                    logger.info(f"Recovery notification sent for {target_name}")
                    
        except Exception as e:
            logger.error(f"Failed to send recovery notification for {target_name}: {e}")
            
    async def check_all_targets(self) -> Dict:
        """Check all monitoring targets"""
        results = {}
        
        tasks = []
        for target_name in self.targets:
            task = asyncio.create_task(
                self.check_target(target_name),
                name=f"check_{target_name}"
            )
            tasks.append((target_name, task))
            
        for target_name, task in tasks:
            try:
                result = await task
                results[target_name] = result
            except Exception as e:
                logger.error(f"Error checking {target_name}: {e}")
                results[target_name] = {'status': 'error', 'error': str(e)}
                
        return results
        
    async def start_monitoring(self):
        """Start continuous monitoring"""
        self.running = True
        logger.info("Starting external API monitoring...")
        
        while self.running:
            try:
                # Check all targets
                results = await self.check_all_targets()
                
                # Log summary
                healthy_count = sum(1 for r in results.values() if r.get('status') == 'healthy')
                total_count = len(results)
                
                logger.info(f"Monitoring check completed: {healthy_count}/{total_count} services healthy")
                
                # Wait for next check cycle
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)  # Shorter wait on error
                
    def get_monitoring_summary(self) -> Dict:
        """Get monitoring summary"""
        summary = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_targets': len(self.targets),
            'by_service_type': {},
            'critical_services': {},
            'overall_health': 'unknown'
        }
        
        # Group by service type
        for target_name, target in self.targets.items():
            service_type = target.service_type.value
            if service_type not in summary['by_service_type']:
                summary['by_service_type'][service_type] = {
                    'total': 0,
                    'healthy': 0,
                    'degraded': 0,
                    'unhealthy': 0
                }
                
            summary['by_service_type'][service_type]['total'] += 1
            
            data = self.monitoring_data.get(target_name, {})
            status = data.get('status', 'unknown')
            
            if status == 'healthy':
                summary['by_service_type'][service_type]['healthy'] += 1
            elif status == 'degraded':
                summary['by_service_type'][service_type]['degraded'] += 1
            elif status == 'unhealthy':
                summary['by_service_type'][service_type]['unhealthy'] += 1
                
            # Track critical services
            if target.critical:
                summary['critical_services'][target_name] = {
                    'name': target.name,
                    'status': status,
                    'availability': data.get('availability', 0.0),
                    'last_check': data.get('last_check')
                }
                
        # Determine overall health
        critical_unhealthy = sum(
            1 for service in summary['critical_services'].values()
            if service['status'] == 'unhealthy'
        )
        
        if critical_unhealthy > 0:
            summary['overall_health'] = 'critical'
        elif any(
            service['status'] in ['degraded', 'unhealthy']
            for service in summary['critical_services'].values()
        ):
            summary['overall_health'] = 'degraded'
        else:
            summary['overall_health'] = 'healthy'
            
        return summary
        
    def get_detailed_status(self) -> Dict:
        """Get detailed status for all targets"""
        detailed_status = {}
        
        for target_name, target in self.targets.items():
            data = self.monitoring_data.get(target_name, {})
            
            detailed_status[target_name] = {
                'name': target.name,
                'service_type': target.service_type.value,
                'url': target.url,
                'critical': target.critical,
                'status': data.get('status', 'unknown'),
                'last_check': data.get('last_check'),
                'response_time': data.get('response_time'),
                'availability': data.get('availability', 0.0),
                'total_checks': data.get('total_checks', 0),
                'successful_checks': data.get('successful_checks', 0),
                'consecutive_failures': data.get('consecutive_failures', 0),
                'last_error': data.get('last_error')
            }
            
        return detailed_status

async def test_monitoring():
    """Test external API monitoring"""
    logger.info("Testing external API monitoring...")
    
    async with ExternalAPIMonitor() as monitor:
        # Run a single check cycle
        results = await monitor.check_all_targets()
        
        logger.info("Monitoring results:")
        for target_name, result in results.items():
            status = result.get('status', 'unknown')
            response_time = result.get('response_time')
            
            status_icon = {
                'healthy': '✅',
                'degraded': '⚠️',
                'unhealthy': '❌',
                'unknown': '❓'
            }.get(status, '❓')
            
            time_str = f" ({response_time:.2f}s)" if response_time else ""
            logger.info(f"  {status_icon} {target_name}: {status}{time_str}")
            
        # Get summary
        summary = monitor.get_monitoring_summary()
        logger.info(f"Overall health: {summary['overall_health']}")
        logger.info(f"Critical services: {len(summary['critical_services'])}")

if __name__ == "__main__":
    asyncio.run(test_monitoring())