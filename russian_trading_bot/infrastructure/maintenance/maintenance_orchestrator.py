#!/usr/bin/env python3
"""
Maintenance Orchestrator for Russian Trading Bot
Coordinates all maintenance activities and monitoring
"""

import asyncio
import logging
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .system_health_monitor import RussianTradingSystemMonitor
from .automated_alerts import RussianTradingAlertManager, AlertSeverity, AlertCategory
from .maintenance_procedures import RussianTradingMaintenanceManager
from .system_documentation import RussianTradingDocumentationGenerator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RussianTradingMaintenanceOrchestrator:
    """Orchestrates all maintenance and monitoring activities"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.health_monitor = None
        self.alert_manager = None
        self.maintenance_manager = None
        self.doc_generator = None
        self.running = False
        
    async def __aenter__(self):
        """Initialize all components"""
        logger.info("🚀 Initializing Russian Trading Bot Maintenance System")
        
        # Initialize health monitor
        self.health_monitor = RussianTradingSystemMonitor(self.config.get('health_monitor'))
        await self.health_monitor.__aenter__()
        
        # Initialize alert manager
        self.alert_manager = RussianTradingAlertManager(self.config.get('alert_manager'))
        await self.alert_manager.__aenter__()
        
        # Initialize maintenance manager
        self.maintenance_manager = RussianTradingMaintenanceManager(self.config.get('maintenance'))
        await self.maintenance_manager.__aenter__()
        
        # Initialize documentation generator
        self.doc_generator = RussianTradingDocumentationGenerator()
        
        logger.info("✅ All maintenance components initialized")
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup all components"""
        self.running = False
        
        if self.health_monitor:
            await self.health_monitor.__aexit__(exc_type, exc_val, exc_tb)
        if self.alert_manager:
            await self.alert_manager.__aexit__(exc_type, exc_val, exc_tb)
        if self.maintenance_manager:
            await self.maintenance_manager.__aexit__(exc_type, exc_val, exc_tb)
            
        logger.info("🔄 Maintenance system shutdown complete")
        
    async def start_monitoring(self):
        """Start continuous monitoring and maintenance"""
        logger.info("🔍 Starting continuous monitoring and maintenance...")
        self.running = True
        
        # Start monitoring tasks
        tasks = [
            asyncio.create_task(self._health_monitoring_loop()),
            asyncio.create_task(self._maintenance_scheduling_loop()),
            asyncio.create_task(self._alert_escalation_loop())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Error in monitoring loops: {e}")
        finally:
            self.running = False
            
    async def _health_monitoring_loop(self):
        """Continuous health monitoring loop"""
        while self.running:
            try:
                # Run health monitoring cycle
                result = await self.health_monitor.run_monitoring_cycle()
                
                if result and result.get('critical', 0) > 0:
                    # Send critical system alert
                    alert = self.alert_manager.create_alert(
                        severity=AlertSeverity.CRITICAL,
                        category=AlertCategory.SYSTEM,
                        title="Критические проблемы системы",
                        message=f"Обнаружено {result['critical']} критических проблем",
                        details=result,
                        source="health_monitor"
                    )
                    await self.alert_manager.send_alert(alert)
                    
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(30)
                
    async def _maintenance_scheduling_loop(self):
        """Maintenance scheduling loop"""
        while self.running:
            try:
                # Check if it's maintenance window
                current_time = datetime.now(timezone.utc)
                
                # Run daily maintenance tasks
                if current_time.hour == 2:  # 2 AM UTC (5 AM Moscow)
                    await self._run_daily_maintenance()
                    
                # Run weekly maintenance (Sundays)
                if current_time.weekday() == 6 and current_time.hour == 3:
                    await self._run_weekly_maintenance()
                    
                # Run monthly maintenance (1st of month)
                if current_time.day == 1 and current_time.hour == 4:
                    await self._run_monthly_maintenance()
                    
                # Wait before next check
                await asyncio.sleep(3600)  # Check every hour
                
            except Exception as e:
                logger.error(f"Error in maintenance scheduling loop: {e}")
                await asyncio.sleep(1800)  # Wait 30 minutes on error
                
    async def _alert_escalation_loop(self):
        """Alert escalation monitoring loop"""
        while self.running:
            try:
                # Check for alerts that need escalation
                await self.alert_manager.check_escalations()
                
                # Wait before next check
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in alert escalation loop: {e}")
                await asyncio.sleep(60)
                
    async def _run_daily_maintenance(self):
        """Run daily maintenance tasks"""
        logger.info("🔧 Starting daily maintenance tasks...")
        
        daily_tasks = [
            task for task in self.maintenance_manager.maintenance_tasks
            if task.frequency == 'daily'
        ]
        
        for task in daily_tasks:
            try:
                success = await self.maintenance_manager.run_task(task)
                
                if not success:
                    # Send maintenance failure alert
                    alert = self.alert_manager.create_alert(
                        severity=AlertSeverity.WARNING,
                        category=AlertCategory.SYSTEM,
                        title=f"Ошибка обслуживания: {task.name}",
                        message=f"Задача обслуживания {task.name} завершилась с ошибкой",
                        details={'task_name': task.name, 'description': task.description},
                        source="maintenance_scheduler"
                    )
                    await self.alert_manager.send_alert(alert)
                    
            except Exception as e:
                logger.error(f"Error running daily task {task.name}: {e}")
                
        logger.info("✅ Daily maintenance tasks completed")
        
    async def _run_weekly_maintenance(self):
        """Run weekly maintenance tasks"""
        logger.info("🔧 Starting weekly maintenance tasks...")
        
        weekly_tasks = [
            task for task in self.maintenance_manager.maintenance_tasks
            if task.frequency == 'weekly'
        ]
        
        # Send maintenance window notification
        alert = self.alert_manager.create_alert(
            severity=AlertSeverity.INFO,
            category=AlertCategory.SYSTEM,
            title="Еженедельное обслуживание",
            message="Начинается еженедельное обслуживание системы",
            details={'tasks_count': len(weekly_tasks)},
            source="maintenance_scheduler"
        )
        await self.alert_manager.send_alert(alert)
        
        for task in weekly_tasks:
            try:
                success = await self.maintenance_manager.run_task(task)
                
                if not success and task.priority in ['high', 'critical']:
                    # Send critical maintenance failure alert
                    alert = self.alert_manager.create_alert(
                        severity=AlertSeverity.CRITICAL,
                        category=AlertCategory.SYSTEM,
                        title=f"Критическая ошибка обслуживания: {task.name}",
                        message=f"Критическая задача обслуживания {task.name} завершилась с ошибкой",
                        details={'task_name': task.name, 'priority': task.priority},
                        source="maintenance_scheduler"
                    )
                    await self.alert_manager.send_alert(alert)
                    
            except Exception as e:
                logger.error(f"Error running weekly task {task.name}: {e}")
                
        logger.info("✅ Weekly maintenance tasks completed")
        
    async def _run_monthly_maintenance(self):
        """Run monthly maintenance tasks"""
        logger.info("🔧 Starting monthly maintenance tasks...")
        
        monthly_tasks = [
            task for task in self.maintenance_manager.maintenance_tasks
            if task.frequency == 'monthly'
        ]
        
        # Generate system documentation
        try:
            self.doc_generator.generate_all_documentation()
            logger.info("📚 System documentation updated")
        except Exception as e:
            logger.error(f"Error generating documentation: {e}")
            
        for task in monthly_tasks:
            try:
                success = await self.maintenance_manager.run_task(task)
                
                if not success:
                    # Send maintenance failure alert
                    alert = self.alert_manager.create_alert(
                        severity=AlertSeverity.CRITICAL if task.priority == 'critical' else AlertSeverity.WARNING,
                        category=AlertCategory.SYSTEM,
                        title=f"Ошибка месячного обслуживания: {task.name}",
                        message=f"Месячная задача обслуживания {task.name} завершилась с ошибкой",
                        details={'task_name': task.name, 'priority': task.priority},
                        source="maintenance_scheduler"
                    )
                    await self.alert_manager.send_alert(alert)
                    
            except Exception as e:
                logger.error(f"Error running monthly task {task.name}: {e}")
                
        logger.info("✅ Monthly maintenance tasks completed")
        
    def get_system_status(self) -> Dict:
        """Get comprehensive system status"""
        status = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'system_health': None,
            'active_alerts': None,
            'maintenance_summary': None,
            'overall_status': 'unknown'
        }
        
        # Get health status
        if self.health_monitor:
            status['system_health'] = self.health_monitor.get_health_summary()
            
        # Get alert status
        if self.alert_manager:
            status['active_alerts'] = self.alert_manager.get_alert_summary()
            
        # Get maintenance status
        if self.maintenance_manager:
            status['maintenance_summary'] = self.maintenance_manager.get_maintenance_summary()
            
        # Determine overall status
        if status['system_health']:
            health_status = status['system_health']['overall_status']
            if health_status == 'critical':
                status['overall_status'] = 'critical'
            elif health_status == 'warning':
                status['overall_status'] = 'degraded'
            else:
                status['overall_status'] = 'healthy'
                
        return status

async def main():
    """Main function for testing the maintenance orchestrator"""
    logger.info("🇷🇺 Russian Trading Bot - Maintenance Orchestrator Test")
    
    config = {
        'health_monitor': {'check_interval': 30},
        'alert_manager': {},
        'maintenance': {}
    }
    
    async with RussianTradingMaintenanceOrchestrator(config) as orchestrator:
        # Get system status
        status = orchestrator.get_system_status()
        
        logger.info("📊 System Status Summary:")
        logger.info(f"  Overall Status: {status['overall_status']}")
        
        if status['system_health']:
            logger.info(f"  System Health: {status['system_health']['overall_status']}")
            logger.info(f"  Active Alerts: {status['system_health']['active_alerts']}")
            
        if status['maintenance_summary']:
            logger.info(f"  Completed Today: {status['maintenance_summary']['completed_today']}")
            logger.info(f"  Failed Today: {status['maintenance_summary']['failed_today']}")
            logger.info(f"  Pending Tasks: {status['maintenance_summary']['pending_tasks']}")
            
        # Run a single monitoring cycle for testing
        logger.info("🔍 Running test monitoring cycle...")
        
        # Test health monitoring
        if orchestrator.health_monitor:
            health_result = await orchestrator.health_monitor.run_monitoring_cycle()
            if health_result:
                logger.info(f"  Health Check: {health_result['healthy']} healthy, {health_result['warnings']} warnings, {health_result['critical']} critical")
                
        # Test maintenance tasks
        if orchestrator.maintenance_manager:
            test_task = next((t for t in orchestrator.maintenance_manager.maintenance_tasks if t.name == 'cache_cleanup'), None)
            if test_task:
                success = await orchestrator.maintenance_manager.run_task(test_task)
                logger.info(f"  Test Maintenance Task: {'✅' if success else '❌'}")
                
        logger.info("✅ Maintenance orchestrator test completed")

if __name__ == "__main__":
    asyncio.run(main())