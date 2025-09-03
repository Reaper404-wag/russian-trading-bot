#!/usr/bin/env python3
"""
Comprehensive API Configuration Manager
Manages all external API connections for Russian Trading Bot
"""

import os
import logging
import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from .moex_api_config import MOEXAPIConfigManager
from .news_feeds_config import RussianNewsManager, NewsConfigManager
from .broker_apis_config import RussianBrokerManager, BrokerConfigManager
from .monitoring_config import ExternalAPIMonitor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RussianTradingAPIManager:
    """Comprehensive API manager for Russian Trading Bot"""
    
    def __init__(self, config_dir: str = "/app/config/production"):
        self.config_dir = config_dir
        self.moex_config_manager = MOEXAPIConfigManager()
        self.news_config_manager = NewsConfigManager()
        self.broker_config_manager = BrokerConfigManager()
        
        # API managers
        self.moex_manager = None
        self.news_manager = None
        self.broker_manager = None
        self.monitor = None
        
        # Connection status
        self.connection_status = {
            'moex': 'disconnected',
            'news': 'disconnected',
            'brokers': 'disconnected',
            'monitoring': 'disconnected'
        }
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize_all_connections()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close_all_connections()
        
    async def initialize_all_connections(self):
        """Initialize all API connections"""
        logger.info("Initializing all API connections...")
        
        try:
            # Initialize MOEX API
            self.moex_manager = self.moex_config_manager.get_api_manager()
            await self.moex_manager.__aenter__()
            self.connection_status['moex'] = 'connected'
            logger.info("✅ MOEX API initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize MOEX API: {e}")
            self.connection_status['moex'] = 'error'
            
        try:
            # Initialize News Manager
            self.news_manager = RussianNewsManager()
            await self.news_manager.__aenter__()
            self.connection_status['news'] = 'connected'
            logger.info("✅ News feeds initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize news feeds: {e}")
            self.connection_status['news'] = 'error'
            
        try:
            # Initialize Broker Manager
            self.broker_manager = RussianBrokerManager()
            await self.broker_manager.__aenter__()
            self.connection_status['brokers'] = 'connected'
            logger.info("✅ Broker APIs initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize broker APIs: {e}")
            self.connection_status['brokers'] = 'error'
            
        try:
            # Initialize Monitoring
            self.monitor = ExternalAPIMonitor()
            await self.monitor.__aenter__()
            self.connection_status['monitoring'] = 'connected'
            logger.info("✅ API monitoring initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize API monitoring: {e}")
            self.connection_status['monitoring'] = 'error'
            
    async def close_all_connections(self):
        """Close all API connections"""
        logger.info("Closing all API connections...")
        
        if self.moex_manager:
            try:
                await self.moex_manager.__aexit__(None, None, None)
                logger.info("✅ MOEX API closed")
            except Exception as e:
                logger.error(f"Error closing MOEX API: {e}")
                
        if self.news_manager:
            try:
                await self.news_manager.__aexit__(None, None, None)
                logger.info("✅ News feeds closed")
            except Exception as e:
                logger.error(f"Error closing news feeds: {e}")
                
        if self.broker_manager:
            try:
                await self.broker_manager.__aexit__(None, None, None)
                logger.info("✅ Broker APIs closed")
            except Exception as e:
                logger.error(f"Error closing broker APIs: {e}")
                
        if self.monitor:
            try:
                await self.monitor.__aexit__(None, None, None)
                logger.info("✅ API monitoring closed")
            except Exception as e:
                logger.error(f"Error closing API monitoring: {e}")
                
    async def test_all_connections(self) -> Dict:
        """Test all API connections"""
        logger.info("Testing all API connections...")
        
        test_results = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'overall_status': 'unknown',
            'services': {}
        }
        
        # Test MOEX API
        if self.moex_manager:
            try:
                stats = self.moex_manager.get_connection_stats()
                securities = await self.moex_manager.get_securities_list()
                
                test_results['services']['moex'] = {
                    'status': 'healthy' if securities else 'unhealthy',
                    'connection_status': stats['status'],
                    'securities_count': len(securities) if securities else 0,
                    'total_requests': stats['total_requests'],
                    'error_count': stats['error_count']
                }
                
            except Exception as e:
                test_results['services']['moex'] = {
                    'status': 'error',
                    'error': str(e)
                }
        else:
            test_results['services']['moex'] = {
                'status': 'not_initialized'
            }
            
        # Test News Feeds
        if self.news_manager:
            try:
                connectivity_results = await self.news_manager.test_all_sources()
                stats = self.news_manager.get_source_stats()
                
                healthy_sources = sum(1 for r in connectivity_results.values() if r['status'] == 'success')
                total_sources = len(connectivity_results)
                
                test_results['services']['news'] = {
                    'status': 'healthy' if healthy_sources > 0 else 'unhealthy',
                    'healthy_sources': healthy_sources,
                    'total_sources': total_sources,
                    'sources': connectivity_results
                }
                
            except Exception as e:
                test_results['services']['news'] = {
                    'status': 'error',
                    'error': str(e)
                }
        else:
            test_results['services']['news'] = {
                'status': 'not_initialized'
            }
            
        # Test Broker APIs
        if self.broker_manager:
            try:
                stats = self.broker_manager.get_broker_stats()
                connected_brokers = self.broker_manager.get_connected_brokers()
                
                test_results['services']['brokers'] = {
                    'status': 'healthy' if connected_brokers else 'unhealthy',
                    'connected_brokers': connected_brokers,
                    'total_brokers': len(stats),
                    'broker_stats': stats
                }
                
            except Exception as e:
                test_results['services']['brokers'] = {
                    'status': 'error',
                    'error': str(e)
                }
        else:
            test_results['services']['brokers'] = {
                'status': 'not_initialized'
            }
            
        # Test Monitoring
        if self.monitor:
            try:
                monitoring_results = await self.monitor.check_all_targets()
                summary = self.monitor.get_monitoring_summary()
                
                test_results['services']['monitoring'] = {
                    'status': 'healthy',
                    'overall_health': summary['overall_health'],
                    'total_targets': summary['total_targets'],
                    'critical_services': summary['critical_services']
                }
                
            except Exception as e:
                test_results['services']['monitoring'] = {
                    'status': 'error',
                    'error': str(e)
                }
        else:
            test_results['services']['monitoring'] = {
                'status': 'not_initialized'
            }
            
        # Determine overall status
        service_statuses = [service.get('status', 'unknown') for service in test_results['services'].values()]
        
        if all(status == 'healthy' for status in service_statuses):
            test_results['overall_status'] = 'healthy'
        elif any(status == 'healthy' for status in service_statuses):
            test_results['overall_status'] = 'degraded'
        else:
            test_results['overall_status'] = 'unhealthy'
            
        return test_results
        
    async def get_market_data_sample(self) -> Dict:
        """Get sample market data from all sources"""
        sample_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'moex_data': None,
            'news_data': None,
            'broker_data': None
        }
        
        # Get MOEX data
        if self.moex_manager:
            try:
                test_symbols = ['SBER', 'GAZP', 'LKOH']
                market_data = await self.moex_manager.get_market_data(test_symbols)
                sample_data['moex_data'] = market_data
                
            except Exception as e:
                logger.error(f"Error getting MOEX sample data: {e}")
                
        # Get news data
        if self.news_manager:
            try:
                news_data = await self.news_manager.fetch_news_from_source('vedomosti')
                if news_data:
                    sample_data['news_data'] = news_data[:3]  # First 3 articles
                    
            except Exception as e:
                logger.error(f"Error getting news sample data: {e}")
                
        # Get broker data
        if self.broker_manager:
            try:
                connected_brokers = self.broker_manager.get_connected_brokers()
                if connected_brokers:
                    broker_name = connected_brokers[0]
                    account_info = await self.broker_manager.get_account_info(broker_name)
                    sample_data['broker_data'] = {
                        'broker': broker_name,
                        'account_info': account_info
                    }
                    
            except Exception as e:
                logger.error(f"Error getting broker sample data: {e}")
                
        return sample_data
        
    def save_all_configurations(self):
        """Save all API configurations"""
        try:
            # Save news configuration
            if self.news_manager:
                self.news_config_manager.save_config(self.news_manager)
                
            # Save broker configuration
            if self.broker_manager:
                self.broker_config_manager.save_config(self.broker_manager)
                
            logger.info("All configurations saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving configurations: {e}")
            
    def get_comprehensive_status(self) -> Dict:
        """Get comprehensive status of all APIs"""
        status = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'connection_status': self.connection_status.copy(),
            'services': {}
        }
        
        # MOEX status
        if self.moex_manager:
            status['services']['moex'] = self.moex_manager.get_connection_stats()
        else:
            status['services']['moex'] = {'status': 'not_initialized'}
            
        # News status
        if self.news_manager:
            status['services']['news'] = self.news_manager.get_source_stats()
        else:
            status['services']['news'] = {'status': 'not_initialized'}
            
        # Broker status
        if self.broker_manager:
            status['services']['brokers'] = self.broker_manager.get_broker_stats()
        else:
            status['services']['brokers'] = {'status': 'not_initialized'}
            
        # Monitoring status
        if self.monitor:
            status['services']['monitoring'] = self.monitor.get_monitoring_summary()
        else:
            status['services']['monitoring'] = {'status': 'not_initialized'}
            
        return status
        
    async def start_monitoring_loop(self):
        """Start continuous monitoring of all APIs"""
        if not self.monitor:
            logger.error("Monitoring not initialized")
            return
            
        logger.info("Starting continuous API monitoring...")
        await self.monitor.start_monitoring()

async def main():
    """Main function to test all API configurations"""
    logger.info("🚀 Starting comprehensive API configuration test...")
    
    async with RussianTradingAPIManager() as api_manager:
        # Test all connections
        test_results = await api_manager.test_all_connections()
        
        logger.info(f"📊 Overall API Status: {test_results['overall_status']}")
        
        # Display service status
        for service_name, service_data in test_results['services'].items():
            status = service_data.get('status', 'unknown')
            status_icon = {
                'healthy': '✅',
                'degraded': '⚠️',
                'unhealthy': '❌',
                'error': '💥',
                'not_initialized': '❓'
            }.get(status, '❓')
            
            logger.info(f"  {status_icon} {service_name.upper()}: {status}")
            
            # Show additional details
            if service_name == 'moex' and 'securities_count' in service_data:
                logger.info(f"    Securities available: {service_data['securities_count']}")
                
            elif service_name == 'news' and 'healthy_sources' in service_data:
                logger.info(f"    News sources: {service_data['healthy_sources']}/{service_data['total_sources']} healthy")
                
            elif service_name == 'brokers' and 'connected_brokers' in service_data:
                logger.info(f"    Connected brokers: {len(service_data['connected_brokers'])}")
                for broker in service_data['connected_brokers']:
                    logger.info(f"      - {broker}")
                    
        # Get sample data
        logger.info("📈 Getting sample market data...")
        sample_data = await api_manager.get_market_data_sample()
        
        if sample_data['moex_data']:
            logger.info("  ✅ MOEX market data retrieved")
            
        if sample_data['news_data']:
            logger.info(f"  ✅ News data retrieved ({len(sample_data['news_data'])} articles)")
            
        if sample_data['broker_data']:
            logger.info(f"  ✅ Broker data retrieved from {sample_data['broker_data']['broker']}")
            
        # Save configurations
        logger.info("💾 Saving configurations...")
        api_manager.save_all_configurations()
        
        # Display comprehensive status
        comprehensive_status = api_manager.get_comprehensive_status()
        
        logger.info("📋 Configuration Summary:")
        logger.info(f"  MOEX API: {comprehensive_status['connection_status']['moex']}")
        logger.info(f"  News Feeds: {comprehensive_status['connection_status']['news']}")
        logger.info(f"  Broker APIs: {comprehensive_status['connection_status']['brokers']}")
        logger.info(f"  Monitoring: {comprehensive_status['connection_status']['monitoring']}")
        
        logger.info("✅ API configuration test completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())