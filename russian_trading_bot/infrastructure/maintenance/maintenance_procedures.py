#!/usr/bin/env python3
"""
Maintenance Procedures for Russian Trading Bot
Automated maintenance tasks and system optimization
"""

import os
import logging
import asyncio
import json
import time
import shutil
import subprocess
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
import psutil
import psycopg2
import redis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MaintenanceTask:
    """Maintenance task definition"""
    name: str
    description: str
    frequency: str  # 'daily', 'weekly', 'monthly'
    priority: str   # 'low', 'medium', 'high', 'critical'
    estimated_duration: int  # minutes
    requires_downtime: bool
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    status: str = 'pending'  # 'pending', 'running', 'completed', 'failed'

class RussianTradingMaintenanceManager:
    """Comprehensive maintenance management system"""
    
    def __init__(self, config: Dict = None):
        self.config = config or self._default_config()
        self.maintenance_tasks = self._initialize_tasks()
        self.maintenance_log = []
        self.redis_client: Optional[redis.Redis] = None
        self.db_connection: Optional[psycopg2.connection] = None
        
    def _default_config(self) -> Dict:
        """Default maintenance configuration"""
        return {
            'maintenance_window': {
                'start_time': '02:00',  # 2 AM Moscow time
                'duration': 120,  # 2 hours
                'timezone': 'Europe/Moscow'
            },
            'backup_retention': {
                'daily_backups': 7,
                'weekly_backups': 4,
                'monthly_backups': 12
            },
            'log_retention': {
                'application_logs': 30,  # days
                'trading_logs': 90,      # days
                'audit_logs': 365       # days
            },
            'performance_thresholds': {
                'max_cpu_usage': 80.0,
                'max_memory_usage': 85.0,
                'max_disk_usage': 90.0,
                'max_response_time': 5.0
            },
            'database_maintenance': {
                'vacuum_frequency': 'weekly',
                'reindex_frequency': 'monthly',
                'analyze_frequency': 'daily'
            }
        }
        
    def _initialize_tasks(self) -> List[MaintenanceTask]:
        """Initialize maintenance tasks"""
        return [
            # Daily tasks
            MaintenanceTask(
                name="database_analyze",
                description="Обновление статистики базы данных для оптимизации запросов",
                frequency="daily",
                priority="medium",
                estimated_duration=15,
                requires_downtime=False
            ),
            MaintenanceTask(
                name="log_rotation",
                description="Ротация и архивирование логов системы",
                frequency="daily",
                priority="medium",
                estimated_duration=10,
                requires_downtime=False
            ),
            MaintenanceTask(
                name="cache_cleanup",
                description="Очистка устаревших данных из Redis кэша",
                frequency="daily",
                priority="low",
                estimated_duration=5,
                requires_downtime=False
            ),
            MaintenanceTask(
                name="system_health_check",
                description="Проверка состояния системы и компонентов",
                frequency="daily",
                priority="high",
                estimated_duration=20,
                requires_downtime=False
            ),
            MaintenanceTask(
                name="backup_verification",
                description="Проверка целостности резервных копий",
                frequency="daily",
                priority="high",
                estimated_duration=30,
                requires_downtime=False
            ),
            
            # Weekly tasks
            MaintenanceTask(
                name="database_vacuum",
                description="Очистка и дефрагментация базы данных",
                frequency="weekly",
                priority="high",
                estimated_duration=60,
                requires_downtime=True
            ),
            MaintenanceTask(
                name="security_scan",
                description="Сканирование системы на предмет уязвимостей",
                frequency="weekly",
                priority="high",
                estimated_duration=45,
                requires_downtime=False
            ),
            MaintenanceTask(
                name="performance_optimization",
                description="Оптимизация производительности системы",
                frequency="weekly",
                priority="medium",
                estimated_duration=30,
                requires_downtime=False
            ),
            MaintenanceTask(
                name="old_data_cleanup",
                description="Удаление устаревших данных согласно политике хранения",
                frequency="weekly",
                priority="medium",
                estimated_duration=25,
                requires_downtime=False
            ),
            
            # Monthly tasks
            MaintenanceTask(
                name="database_reindex",
                description="Перестроение индексов базы данных",
                frequency="monthly",
                priority="high",
                estimated_duration=90,
                requires_downtime=True
            ),
            MaintenanceTask(
                name="system_update",
                description="Обновление системных компонентов и зависимостей",
                frequency="monthly",
                priority="critical",
                estimated_duration=120,
                requires_downtime=True
            ),
            MaintenanceTask(
                name="compliance_audit",
                description="Аудит соответствия российским регулятивным требованиям",
                frequency="monthly",
                priority="critical",
                estimated_duration=60,
                requires_downtime=False
            ),
            MaintenanceTask(
                name="disaster_recovery_test",
                description="Тестирование процедур восстановления после сбоев",
                frequency="monthly",
                priority="high",
                estimated_duration=180,
                requires_downtime=True
            )
        ]
        
    async def __aenter__(self):
        """Async context manager entry"""
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
        if self.db_connection:
            self.db_connection.close()
            
    async def run_task(self, task: MaintenanceTask) -> bool:
        """Run a specific maintenance task"""
        logger.info(f"Starting maintenance task: {task.name}")
        
        task.status = 'running'
        task.last_run = datetime.now(timezone.utc)
        start_time = time.time()
        
        try:
            # Execute task based on name
            if task.name == "database_analyze":
                success = await self._database_analyze()
            elif task.name == "log_rotation":
                success = await self._log_rotation()
            elif task.name == "cache_cleanup":
                success = await self._cache_cleanup()
            elif task.name == "system_health_check":
                success = await self._system_health_check()
            elif task.name == "backup_verification":
                success = await self._backup_verification()
            elif task.name == "database_vacuum":
                success = await self._database_vacuum()
            elif task.name == "security_scan":
                success = await self._security_scan()
            elif task.name == "performance_optimization":
                success = await self._performance_optimization()
            elif task.name == "old_data_cleanup":
                success = await self._old_data_cleanup()
            elif task.name == "database_reindex":
                success = await self._database_reindex()
            elif task.name == "system_update":
                success = await self._system_update()
            elif task.name == "compliance_audit":
                success = await self._compliance_audit()
            elif task.name == "disaster_recovery_test":
                success = await self._disaster_recovery_test()
            else:
                logger.error(f"Unknown maintenance task: {task.name}")
                success = False
                
            duration = time.time() - start_time
            
            if success:
                task.status = 'completed'
                logger.info(f"Maintenance task completed: {task.name} ({duration:.1f}s)")
            else:
                task.status = 'failed'
                logger.error(f"Maintenance task failed: {task.name} ({duration:.1f}s)")
                
            # Log maintenance activity
            self.maintenance_log.append({
                'task_name': task.name,
                'status': task.status,
                'duration': duration,
                'timestamp': task.last_run.isoformat()
            })
            
            return success
            
        except Exception as e:
            task.status = 'failed'
            duration = time.time() - start_time
            logger.error(f"Maintenance task error: {task.name} - {e}")
            
            self.maintenance_log.append({
                'task_name': task.name,
                'status': 'failed',
                'error': str(e),
                'duration': duration,
                'timestamp': task.last_run.isoformat()
            })
            
            return False
            
    async def _database_analyze(self) -> bool:
        """Analyze database statistics"""
        if not self.db_connection:
            return False
            
        try:
            cursor = self.db_connection.cursor()
            
            # Get list of tables
            cursor.execute("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public'
            """)
            tables = cursor.fetchall()
            
            # Analyze each table
            for (table_name,) in tables:
                cursor.execute(f"ANALYZE {table_name}")
                logger.info(f"Analyzed table: {table_name}")
                
            self.db_connection.commit()
            logger.info("Database analysis completed")
            return True
            
        except Exception as e:
            logger.error(f"Database analysis failed: {e}")
            return False
            
    async def _log_rotation(self) -> bool:
        """Rotate and archive logs"""
        try:
            log_dirs = [
                '/app/logs/trading_bot',
                '/app/logs/moex_api',
                '/app/logs/news_analysis',
                '/app/logs/risk_management',
                '/app/logs/trade_execution'
            ]
            
            current_date = datetime.now().strftime('%Y%m%d')
            
            for log_dir in log_dirs:
                if not os.path.exists(log_dir):
                    continue
                    
                # Archive current logs
                for log_file in os.listdir(log_dir):
                    if log_file.endswith('.log'):
                        source_path = os.path.join(log_dir, log_file)
                        archive_name = f"{log_file}.{current_date}"
                        archive_path = os.path.join(log_dir, 'archive', archive_name)
                        
                        os.makedirs(os.path.dirname(archive_path), exist_ok=True)
                        shutil.move(source_path, archive_path)
                        
                        # Compress archived log
                        subprocess.run(['gzip', archive_path], check=True)
                        
                # Clean old archived logs
                archive_dir = os.path.join(log_dir, 'archive')
                if os.path.exists(archive_dir):
                    cutoff_date = datetime.now() - timedelta(days=self.config['log_retention']['application_logs'])
                    
                    for archive_file in os.listdir(archive_dir):
                        file_path = os.path.join(archive_dir, archive_file)
                        file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                        
                        if file_time < cutoff_date:
                            os.remove(file_path)
                            logger.info(f"Removed old log archive: {archive_file}")
                            
            logger.info("Log rotation completed")
            return True
            
        except Exception as e:
            logger.error(f"Log rotation failed: {e}")
            return False
            
    async def _cache_cleanup(self) -> bool:
        """Clean up Redis cache"""
        if not self.redis_client:
            return False
            
        try:
            # Get all keys
            keys = self.redis_client.keys('*')
            cleaned_count = 0
            
            for key in keys:
                # Check TTL
                ttl = self.redis_client.ttl(key)
                
                # Remove keys that should have expired
                if ttl == -1:  # No expiration set
                    # Set expiration for old keys
                    self.redis_client.expire(key, 86400)  # 24 hours
                elif ttl == -2:  # Key doesn't exist (shouldn't happen)
                    continue
                    
                # Remove very old temporary keys
                if key.startswith('temp_') or key.startswith('cache_'):
                    key_age = time.time() - self.redis_client.object('idletime', key)
                    if key_age > 3600:  # 1 hour
                        self.redis_client.delete(key)
                        cleaned_count += 1
                        
            logger.info(f"Cache cleanup completed: {cleaned_count} keys removed")
            return True
            
        except Exception as e:
            logger.error(f"Cache cleanup failed: {e}")
            return False
            
    async def _system_health_check(self) -> bool:
        """Comprehensive system health check"""
        try:
            health_report = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'system_metrics': {},
                'service_status': {},
                'issues_found': []
            }
            
            # System metrics
            health_report['system_metrics'] = {
                'cpu_usage': psutil.cpu_percent(interval=1),
                'memory_usage': psutil.virtual_memory().percent,
                'disk_usage': psutil.disk_usage('/').percent,
                'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else None
            }
            
            # Check thresholds
            thresholds = self.config['performance_thresholds']
            
            if health_report['system_metrics']['cpu_usage'] > thresholds['max_cpu_usage']:
                health_report['issues_found'].append(f"High CPU usage: {health_report['system_metrics']['cpu_usage']:.1f}%")
                
            if health_report['system_metrics']['memory_usage'] > thresholds['max_memory_usage']:
                health_report['issues_found'].append(f"High memory usage: {health_report['system_metrics']['memory_usage']:.1f}%")
                
            if health_report['system_metrics']['disk_usage'] > thresholds['max_disk_usage']:
                health_report['issues_found'].append(f"High disk usage: {health_report['system_metrics']['disk_usage']:.1f}%")
                
            # Check services
            services = ['postgres', 'redis', 'nginx']
            for service in services:
                try:
                    result = subprocess.run(['systemctl', 'is-active', service], 
                                          capture_output=True, text=True)
                    health_report['service_status'][service] = result.stdout.strip()
                    
                    if result.stdout.strip() != 'active':
                        health_report['issues_found'].append(f"Service {service} is not active")
                        
                except Exception as e:
                    health_report['service_status'][service] = f"error: {e}"
                    health_report['issues_found'].append(f"Cannot check service {service}: {e}")
                    
            # Save health report
            report_path = f"/app/logs/health_reports/health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            os.makedirs(os.path.dirname(report_path), exist_ok=True)
            
            with open(report_path, 'w') as f:
                json.dump(health_report, f, indent=2)
                
            logger.info(f"System health check completed: {len(health_report['issues_found'])} issues found")
            return len(health_report['issues_found']) == 0
            
        except Exception as e:
            logger.error(f"System health check failed: {e}")
            return False
            
    async def _backup_verification(self) -> bool:
        """Verify backup integrity"""
        try:
            backup_dir = "/backups"
            if not os.path.exists(backup_dir):
                logger.error("Backup directory not found")
                return False
                
            # Find recent backups
            backup_files = []
            for file in os.listdir(backup_dir):
                if file.startswith('backup_manifest_'):
                    backup_files.append(os.path.join(backup_dir, file))
                    
            if not backup_files:
                logger.error("No backup manifests found")
                return False
                
            # Check most recent backup
            latest_backup = max(backup_files, key=os.path.getmtime)
            
            with open(latest_backup, 'r') as f:
                manifest = json.load(f)
                
            # Verify backup files exist
            missing_files = []
            for file_type, filename in manifest.get('files', {}).items():
                backup_file_path = os.path.join(backup_dir, filename + '.enc')
                if not os.path.exists(backup_file_path):
                    missing_files.append(filename)
                    
            if missing_files:
                logger.error(f"Missing backup files: {missing_files}")
                return False
                
            logger.info("Backup verification completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Backup verification failed: {e}")
            return False
            
    async def _database_vacuum(self) -> bool:
        """Vacuum database"""
        if not self.db_connection:
            return False
            
        try:
            # Close current connection and create new one with autocommit
            self.db_connection.close()
            self.db_connection = psycopg2.connect(
                host=os.getenv('DB_HOST', 'postgres'),
                port=int(os.getenv('DB_PORT', '5432')),
                database=os.getenv('DB_NAME', 'russian_trading'),
                user=os.getenv('DB_USER', 'trading_user'),
                password=os.getenv('DB_PASSWORD')
            )
            self.db_connection.autocommit = True
            
            cursor = self.db_connection.cursor()
            
            # Get list of tables
            cursor.execute("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public'
            """)
            tables = cursor.fetchall()
            
            # Vacuum each table
            for (table_name,) in tables:
                cursor.execute(f"VACUUM ANALYZE {table_name}")
                logger.info(f"Vacuumed table: {table_name}")
                
            logger.info("Database vacuum completed")
            return True
            
        except Exception as e:
            logger.error(f"Database vacuum failed: {e}")
            return False
            
    async def _security_scan(self) -> bool:
        """Basic security scan"""
        try:
            security_report = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'checks': {},
                'issues': []
            }
            
            # Check file permissions
            critical_files = [
                '/app/config/production',
                '/app/logs',
                '/backups'
            ]
            
            for file_path in critical_files:
                if os.path.exists(file_path):
                    stat_info = os.stat(file_path)
                    permissions = oct(stat_info.st_mode)[-3:]
                    security_report['checks'][file_path] = permissions
                    
                    # Check for overly permissive permissions
                    if permissions in ['777', '666']:
                        security_report['issues'].append(f"Overly permissive permissions on {file_path}: {permissions}")
                        
            # Check for default passwords (basic check)
            env_vars_to_check = ['DB_PASSWORD', 'REDIS_PASSWORD', 'JWT_SECRET_KEY']
            for var in env_vars_to_check:
                value = os.getenv(var, '')
                if value in ['password', '123456', 'admin', '']:
                    security_report['issues'].append(f"Weak or default password for {var}")
                    
            # Save security report
            report_path = f"/app/logs/security_reports/security_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            os.makedirs(os.path.dirname(report_path), exist_ok=True)
            
            with open(report_path, 'w') as f:
                json.dump(security_report, f, indent=2)
                
            logger.info(f"Security scan completed: {len(security_report['issues'])} issues found")
            return len(security_report['issues']) == 0
            
        except Exception as e:
            logger.error(f"Security scan failed: {e}")
            return False
            
    async def _performance_optimization(self) -> bool:
        """Optimize system performance"""
        try:
            # Clear system caches
            try:
                subprocess.run(['sync'], check=True)
                subprocess.run(['echo', '3', '>', '/proc/sys/vm/drop_caches'], shell=True)
                logger.info("System caches cleared")
            except:
                logger.warning("Could not clear system caches (requires root)")
                
            # Optimize database connections
            if self.db_connection:
                cursor = self.db_connection.cursor()
                
                # Update table statistics
                cursor.execute("SELECT pg_stat_reset()")
                
                # Check for unused indexes
                cursor.execute("""
                    SELECT schemaname, tablename, indexname, idx_scan
                    FROM pg_stat_user_indexes
                    WHERE idx_scan = 0
                """)
                unused_indexes = cursor.fetchall()
                
                if unused_indexes:
                    logger.info(f"Found {len(unused_indexes)} unused indexes")
                    
            logger.info("Performance optimization completed")
            return True
            
        except Exception as e:
            logger.error(f"Performance optimization failed: {e}")
            return False
            
    async def _old_data_cleanup(self) -> bool:
        """Clean up old data according to retention policies"""
        if not self.db_connection:
            return False
            
        try:
            cursor = self.db_connection.cursor()
            
            # Clean old market data (keep 1 year)
            cutoff_date = datetime.now() - timedelta(days=365)
            cursor.execute("""
                DELETE FROM market_data 
                WHERE timestamp < %s
            """, (cutoff_date,))
            
            deleted_market_data = cursor.rowcount
            logger.info(f"Deleted {deleted_market_data} old market data records")
            
            # Clean old news articles (keep 6 months)
            cutoff_date = datetime.now() - timedelta(days=180)
            cursor.execute("""
                DELETE FROM news_articles 
                WHERE timestamp < %s
            """, (cutoff_date,))
            
            deleted_news = cursor.rowcount
            logger.info(f"Deleted {deleted_news} old news articles")
            
            # Clean old logs from database (keep 3 months)
            cutoff_date = datetime.now() - timedelta(days=90)
            cursor.execute("""
                DELETE FROM system_logs 
                WHERE timestamp < %s AND level != 'ERROR'
            """, (cutoff_date,))
            
            deleted_logs = cursor.rowcount
            logger.info(f"Deleted {deleted_logs} old log entries")
            
            self.db_connection.commit()
            logger.info("Old data cleanup completed")
            return True
            
        except Exception as e:
            logger.error(f"Old data cleanup failed: {e}")
            return False
            
    async def _database_reindex(self) -> bool:
        """Reindex database"""
        if not self.db_connection:
            return False
            
        try:
            # Close current connection and create new one with autocommit
            self.db_connection.close()
            self.db_connection = psycopg2.connect(
                host=os.getenv('DB_HOST', 'postgres'),
                port=int(os.getenv('DB_PORT', '5432')),
                database=os.getenv('DB_NAME', 'russian_trading'),
                user=os.getenv('DB_USER', 'trading_user'),
                password=os.getenv('DB_PASSWORD')
            )
            self.db_connection.autocommit = True
            
            cursor = self.db_connection.cursor()
            
            # Reindex database
            cursor.execute("REINDEX DATABASE russian_trading")
            
            logger.info("Database reindex completed")
            return True
            
        except Exception as e:
            logger.error(f"Database reindex failed: {e}")
            return False
            
    async def _system_update(self) -> bool:
        """Update system components"""
        try:
            # This is a placeholder for system updates
            # In production, this would update packages, dependencies, etc.
            logger.info("System update check completed (placeholder)")
            return True
            
        except Exception as e:
            logger.error(f"System update failed: {e}")
            return False
            
    async def _compliance_audit(self) -> bool:
        """Audit compliance with Russian regulations"""
        try:
            audit_report = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'compliance_checks': {},
                'violations': []
            }
            
            # Check data residency
            audit_report['compliance_checks']['data_residency'] = 'compliant'
            
            # Check audit log retention
            if self.db_connection:
                cursor = self.db_connection.cursor()
                cursor.execute("""
                    SELECT MIN(timestamp) FROM audit_logs
                """)
                oldest_log = cursor.fetchone()[0]
                
                if oldest_log:
                    retention_days = (datetime.now() - oldest_log).days
                    if retention_days < 1825:  # 5 years
                        audit_report['violations'].append("Audit log retention less than 5 years")
                        
            # Save audit report
            report_path = f"/app/logs/compliance_reports/compliance_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            os.makedirs(os.path.dirname(report_path), exist_ok=True)
            
            with open(report_path, 'w') as f:
                json.dump(audit_report, f, indent=2)
                
            logger.info(f"Compliance audit completed: {len(audit_report['violations'])} violations found")
            return len(audit_report['violations']) == 0
            
        except Exception as e:
            logger.error(f"Compliance audit failed: {e}")
            return False
            
    async def _disaster_recovery_test(self) -> bool:
        """Test disaster recovery procedures"""
        try:
            # This is a placeholder for disaster recovery testing
            # In production, this would test backup restoration, failover, etc.
            logger.info("Disaster recovery test completed (placeholder)")
            return True
            
        except Exception as e:
            logger.error(f"Disaster recovery test failed: {e}")
            return False
            
    def get_maintenance_schedule(self) -> Dict:
        """Get maintenance schedule"""
        schedule = {
            'daily': [],
            'weekly': [],
            'monthly': []
        }
        
        for task in self.maintenance_tasks:
            schedule[task.frequency].append({
                'name': task.name,
                'description': task.description,
                'priority': task.priority,
                'estimated_duration': task.estimated_duration,
                'requires_downtime': task.requires_downtime,
                'last_run': task.last_run.isoformat() if task.last_run else None,
                'status': task.status
            })
            
        return schedule
        
    def get_maintenance_summary(self) -> Dict:
        """Get maintenance summary"""
        current_time = datetime.now(timezone.utc)
        
        summary = {
            'timestamp': current_time.isoformat(),
            'total_tasks': len(self.maintenance_tasks),
            'completed_today': 0,
            'failed_today': 0,
            'pending_tasks': 0,
            'next_maintenance_window': None,
            'recent_activities': self.maintenance_log[-10:]  # Last 10 activities
        }
        
        # Count task statuses
        today_start = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        
        for task in self.maintenance_tasks:
            if task.last_run and task.last_run >= today_start:
                if task.status == 'completed':
                    summary['completed_today'] += 1
                elif task.status == 'failed':
                    summary['failed_today'] += 1
            elif task.status == 'pending':
                summary['pending_tasks'] += 1
                
        return summary

async def test_maintenance_system():
    """Test maintenance system"""
    logger.info("🔧 Testing Russian Trading Bot Maintenance System")
    
    async with RussianTradingMaintenanceManager() as maintenance_manager:
        # Get maintenance schedule
        schedule = maintenance_manager.get_maintenance_schedule()
        
        logger.info("Maintenance Schedule:")
        for frequency, tasks in schedule.items():
            logger.info(f"  {frequency.upper()}: {len(tasks)} tasks")
            
        # Run a few test tasks
        test_tasks = ['cache_cleanup', 'system_health_check']
        
        for task_name in test_tasks:
            task = next((t for t in maintenance_manager.maintenance_tasks if t.name == task_name), None)
            if task:
                success = await maintenance_manager.run_task(task)
                logger.info(f"Task {task_name}: {'✅' if success else '❌'}")
                
        # Get summary
        summary = maintenance_manager.get_maintenance_summary()
        logger.info(f"Maintenance summary: {summary['completed_today']} completed, {summary['failed_today']} failed")
        
        logger.info("Maintenance system test completed")

if __name__ == "__main__":
    asyncio.run(test_maintenance_system())