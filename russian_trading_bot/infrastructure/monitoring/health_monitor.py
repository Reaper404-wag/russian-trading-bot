#!/usr/bin/env python3
"""
Russian Trading Bot Health Monitor
Monitors system health and Russian market-specific components
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
import aiohttp
import psycopg2
import redis
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/app/logs/health_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class HealthStatus:
    """Health status for a component"""
    name: str
    status: str  # 'healthy', 'degraded', 'unhealthy'
    response_time: Optional[float]
    last_check: datetime
    error_message: Optional[str] = None
    metadata: Optional[Dict] = None

class RussianTradingBotHealthMonitor:
    """Comprehensive health monitor for Russian trading bot system"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.redis_client = None
        self.db_connection = None
        self.session = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        
        # Initialize Redis connection
        try:
            self.redis_client = redis.Redis(
                host=self.config.get('redis_host', 'redis'),
                port=self.config.get('redis_port', 6379),
                password=self.config.get('redis_password'),
                decode_responses=True
            )
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
        if self.db_connection:
            self.db_connection.close()
            
    async def check_database_health(self) -> HealthStatus:
        """Check PostgreSQL database health"""
        start_time = time.time()
        
        try:
            if not self.db_connection or self.db_connection.closed:
                self.db_connection = psycopg2.connect(
                    host=self.config.get('db_host', 'postgres'),
                    port=self.config.get('db_port', 5432),
                    database=self.config.get('db_name', 'russian_trading'),
                    user=self.config.get('db_user', 'trading_user'),
                    password=self.config.get('db_password')
                )
            
            cursor = self.db_connection.cursor()
            
            # Check basic connectivity
            cursor.execute("SELECT 1")
            cursor.fetchone()
            
            # Check Russian market data tables
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name IN ('russian_stocks', 'market_data', 'news_articles', 'trades')
            """)
            table_count = cursor.fetchone()[0]
            
            # Check recent data
            cursor.execute("""
                SELECT COUNT(*) FROM market_data 
                WHERE timestamp > NOW() - INTERVAL '1 hour'
            """)
            recent_data_count = cursor.fetchone()[0]
            
            response_time = time.time() - start_time
            
            status = 'healthy'
            metadata = {
                'tables_present': table_count,
                'recent_data_points': recent_data_count,
                'connection_pool_size': self.db_connection.info.backend_pid
            }
            
            if table_count < 4:
                status = 'degraded'
            if recent_data_count == 0:
                status = 'degraded'
                
            return HealthStatus(
                name='database',
                status=status,
                response_time=response_time,
                last_check=datetime.now(timezone.utc),
                metadata=metadata
            )
            
        except Exception as e:
            return HealthStatus(
                name='database',
                status='unhealthy',
                response_time=time.time() - start_time,
                last_check=datetime.now(timezone.utc),
                error_message=str(e)
            )
            
    async def check_redis_health(self) -> HealthStatus:
        """Check Redis cache health"""
        start_time = time.time()
        
        try:
            if not self.redis_client:
                raise Exception("Redis client not initialized")
                
            # Basic ping
            self.redis_client.ping()
            
            # Test set/get operation
            test_key = f"health_check_{int(time.time())}"
            self.redis_client.set(test_key, "test_value", ex=60)
            value = self.redis_client.get(test_key)
            self.redis_client.delete(test_key)
            
            if value != "test_value":
                raise Exception("Redis set/get test failed")
                
            # Get Redis info
            info = self.redis_client.info()
            
            response_time = time.time() - start_time
            
            return HealthStatus(
                name='redis',
                status='healthy',
                response_time=response_time,
                last_check=datetime.now(timezone.utc),
                metadata={
                    'connected_clients': info.get('connected_clients', 0),
                    'used_memory_human': info.get('used_memory_human', 'unknown'),
                    'uptime_in_seconds': info.get('uptime_in_seconds', 0)
                }
            )
            
        except Exception as e:
            return HealthStatus(
                name='redis',
                status='unhealthy',
                response_time=time.time() - start_time,
                last_check=datetime.now(timezone.utc),
                error_message=str(e)
            )
            
    async def check_moex_api_health(self) -> HealthStatus:
        """Check MOEX API connectivity and response"""
        start_time = time.time()
        
        try:
            # Test MOEX API endpoint
            url = "https://iss.moex.com/iss/engines/stock/markets/shares/boards/TQBR/securities.json"
            params = {'iss.meta': 'off', 'iss.only': 'securities', 'securities.columns': 'SECID,SHORTNAME'}
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    raise Exception(f"MOEX API returned status {response.status}")
                    
                data = await response.json()
                securities_count = len(data.get('securities', {}).get('data', []))
                
                response_time = time.time() - start_time
                
                status = 'healthy' if securities_count > 0 else 'degraded'
                
                return HealthStatus(
                    name='moex_api',
                    status=status,
                    response_time=response_time,
                    last_check=datetime.now(timezone.utc),
                    metadata={
                        'securities_count': securities_count,
                        'api_endpoint': url
                    }
                )
                
        except Exception as e:
            return HealthStatus(
                name='moex_api',
                status='unhealthy',
                response_time=time.time() - start_time,
                last_check=datetime.now(timezone.utc),
                error_message=str(e)
            )
            
    async def check_news_sources_health(self) -> List[HealthStatus]:
        """Check Russian news sources availability"""
        news_sources = [
            {'name': 'rbc', 'url': 'https://www.rbc.ru'},
            {'name': 'vedomosti', 'url': 'https://www.vedomosti.ru'},
            {'name': 'kommersant', 'url': 'https://www.kommersant.ru'},
            {'name': 'interfax', 'url': 'https://www.interfax.ru'}
        ]
        
        health_statuses = []
        
        for source in news_sources:
            start_time = time.time()
            
            try:
                async with self.session.get(source['url'], timeout=aiohttp.ClientTimeout(total=10)) as response:
                    response_time = time.time() - start_time
                    
                    status = 'healthy' if response.status == 200 else 'degraded'
                    
                    health_statuses.append(HealthStatus(
                        name=f"news_source_{source['name']}",
                        status=status,
                        response_time=response_time,
                        last_check=datetime.now(timezone.utc),
                        metadata={'url': source['url'], 'status_code': response.status}
                    ))
                    
            except Exception as e:
                health_statuses.append(HealthStatus(
                    name=f"news_source_{source['name']}",
                    status='unhealthy',
                    response_time=time.time() - start_time,
                    last_check=datetime.now(timezone.utc),
                    error_message=str(e),
                    metadata={'url': source['url']}
                ))
                
        return health_statuses
        
    async def check_trading_bot_health(self) -> HealthStatus:
        """Check main trading bot application health"""
        start_time = time.time()
        
        try:
            url = "http://trading-bot:8000/health"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"Trading bot health endpoint returned status {response.status}")
                    
                data = await response.json()
                response_time = time.time() - start_time
                
                return HealthStatus(
                    name='trading_bot',
                    status=data.get('status', 'unknown'),
                    response_time=response_time,
                    last_check=datetime.now(timezone.utc),
                    metadata=data.get('details', {})
                )
                
        except Exception as e:
            return HealthStatus(
                name='trading_bot',
                status='unhealthy',
                response_time=time.time() - start_time,
                last_check=datetime.now(timezone.utc),
                error_message=str(e)
            )
            
    async def check_system_resources(self) -> HealthStatus:
        """Check system resource usage"""
        start_time = time.time()
        
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            response_time = time.time() - start_time
            
            # Determine status based on resource usage
            status = 'healthy'
            if cpu_percent > 80 or memory.percent > 85 or disk.percent > 90:
                status = 'degraded'
            if cpu_percent > 95 or memory.percent > 95 or disk.percent > 95:
                status = 'unhealthy'
                
            return HealthStatus(
                name='system_resources',
                status=status,
                response_time=response_time,
                last_check=datetime.now(timezone.utc),
                metadata={
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory.percent,
                    'memory_available_gb': round(memory.available / (1024**3), 2),
                    'disk_percent': disk.percent,
                    'disk_free_gb': round(disk.free / (1024**3), 2)
                }
            )
            
        except Exception as e:
            return HealthStatus(
                name='system_resources',
                status='unhealthy',
                response_time=time.time() - start_time,
                last_check=datetime.now(timezone.utc),
                error_message=str(e)
            )
            
    async def run_comprehensive_health_check(self) -> Dict:
        """Run all health checks and return comprehensive status"""
        logger.info("Starting comprehensive health check")
        
        health_checks = []
        
        # Core infrastructure checks
        health_checks.append(await self.check_database_health())
        health_checks.append(await self.check_redis_health())
        health_checks.append(await self.check_system_resources())
        
        # Application checks
        health_checks.append(await self.check_trading_bot_health())
        
        # External service checks
        health_checks.append(await self.check_moex_api_health())
        health_checks.extend(await self.check_news_sources_health())
        
        # Calculate overall system health
        healthy_count = sum(1 for check in health_checks if check.status == 'healthy')
        degraded_count = sum(1 for check in health_checks if check.status == 'degraded')
        unhealthy_count = sum(1 for check in health_checks if check.status == 'unhealthy')
        
        total_checks = len(health_checks)
        
        if unhealthy_count > 0:
            overall_status = 'unhealthy'
        elif degraded_count > total_checks * 0.3:  # More than 30% degraded
            overall_status = 'degraded'
        else:
            overall_status = 'healthy'
            
        result = {
            'overall_status': overall_status,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'timezone': 'Europe/Moscow',
            'summary': {
                'total_checks': total_checks,
                'healthy': healthy_count,
                'degraded': degraded_count,
                'unhealthy': unhealthy_count
            },
            'checks': [asdict(check) for check in health_checks]
        }
        
        logger.info(f"Health check completed: {overall_status} ({healthy_count}/{total_checks} healthy)")
        
        return result
        
    async def send_alert_if_needed(self, health_result: Dict):
        """Send alerts for unhealthy components"""
        unhealthy_checks = [
            check for check in health_result['checks'] 
            if check['status'] == 'unhealthy'
        ]
        
        if unhealthy_checks:
            alert_message = f"🚨 Система торговли: обнаружены проблемы\n\n"
            alert_message += f"Время: {health_result['timestamp']}\n"
            alert_message += f"Общий статус: {health_result['overall_status']}\n\n"
            alert_message += "Неисправные компоненты:\n"
            
            for check in unhealthy_checks:
                alert_message += f"• {check['name']}: {check.get('error_message', 'Unknown error')}\n"
                
            # Send to notification service
            try:
                notification_url = "http://trading-bot:8000/api/notifications/alert"
                async with self.session.post(
                    notification_url,
                    json={
                        'type': 'system_health',
                        'severity': 'high',
                        'message': alert_message,
                        'details': health_result
                    }
                ) as response:
                    if response.status == 200:
                        logger.info("Health alert sent successfully")
                    else:
                        logger.error(f"Failed to send health alert: {response.status}")
                        
            except Exception as e:
                logger.error(f"Error sending health alert: {e}")

async def main():
    """Main health monitoring loop"""
    config = {
        'db_host': 'postgres',
        'db_port': 5432,
        'db_name': 'russian_trading',
        'db_user': 'trading_user',
        'db_password': 'your_password_here',  # Should come from environment
        'redis_host': 'redis',
        'redis_port': 6379,
        'redis_password': 'your_redis_password_here'  # Should come from environment
    }
    
    async with RussianTradingBotHealthMonitor(config) as monitor:
        while True:
            try:
                health_result = await monitor.run_comprehensive_health_check()
                
                # Store health result in Redis for API access
                if monitor.redis_client:
                    monitor.redis_client.set(
                        'system_health',
                        json.dumps(health_result),
                        ex=300  # Expire after 5 minutes
                    )
                
                # Send alerts if needed
                await monitor.send_alert_if_needed(health_result)
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(30)  # Shorter wait on error

if __name__ == "__main__":
    asyncio.run(main())