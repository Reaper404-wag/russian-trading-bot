#!/usr/bin/env python3
"""
Russian Broker APIs Configuration and Management
Production-ready configuration for Russian broker integrations
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

class BrokerType(Enum):
    TINKOFF = "tinkoff"
    FINAM = "finam"
    SBERBANK = "sberbank"
    VTB = "vtb"

@dataclass
class BrokerConfig:
    """Configuration for a broker API"""
    name: str
    broker_type: BrokerType
    api_url: str
    api_token: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    sandbox_mode: bool = True
    timeout: int = 30
    rate_limit: int = 120  # requests per minute
    retry_attempts: int = 3
    enabled: bool = True
    
    # Trading parameters
    default_currency: str = "RUB"
    min_order_value: float = 1000.0  # Minimum order value in RUB
    max_position_size: float = 0.05  # Maximum position size as fraction of portfolio
    
    # Compliance settings
    requires_qualification: bool = False
    supports_margin: bool = False
    supports_options: bool = False

class RussianBrokerManager:
    """Manages Russian broker API connections"""
    
    def __init__(self):
        self.brokers = self._initialize_brokers()
        self.session: Optional[aiohttp.ClientSession] = None
        self.last_request_times = {}
        self.request_counts = {}
        self.error_counts = {}
        self.connection_status = {}
        
    def _initialize_brokers(self) -> Dict[str, BrokerConfig]:
        """Initialize Russian broker configurations"""
        return {
            'tinkoff': BrokerConfig(
                name='Tinkoff Invest',
                broker_type=BrokerType.TINKOFF,
                api_url=os.getenv('TINKOFF_API_URL', 'https://invest-public-api.tinkoff.ru/rest'),
                api_token=os.getenv('TINKOFF_API_TOKEN'),
                sandbox_mode=os.getenv('TINKOFF_SANDBOX_MODE', 'true').lower() == 'true',
                rate_limit=120,  # 120 requests per minute
                supports_margin=True,
                supports_options=True
            ),
            'finam': BrokerConfig(
                name='Finam',
                broker_type=BrokerType.FINAM,
                api_url=os.getenv('FINAM_API_URL', 'https://trade-api.finam.ru'),
                api_key=os.getenv('FINAM_API_KEY'),
                api_secret=os.getenv('FINAM_API_SECRET'),
                sandbox_mode=os.getenv('FINAM_SANDBOX_MODE', 'true').lower() == 'true',
                rate_limit=60,  # 60 requests per minute
                supports_margin=True
            ),
            'sberbank': BrokerConfig(
                name='Sberbank Investments',
                broker_type=BrokerType.SBERBANK,
                api_url=os.getenv('SBERBANK_API_URL', 'https://api.sberbank-investments.ru'),
                api_token=os.getenv('SBERBANK_API_TOKEN'),
                sandbox_mode=os.getenv('SBERBANK_SANDBOX_MODE', 'true').lower() == 'true',
                rate_limit=100,
                requires_qualification=True
            ),
            'vtb': BrokerConfig(
                name='VTB Investments',
                broker_type=BrokerType.VTB,
                api_url=os.getenv('VTB_API_URL', 'https://api.vtb-investments.ru'),
                api_token=os.getenv('VTB_API_TOKEN'),
                sandbox_mode=os.getenv('VTB_SANDBOX_MODE', 'true').lower() == 'true',
                rate_limit=80,
                requires_qualification=True
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
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'User-Agent': 'RussianTradingBot/1.0',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        )
        
        # Test connections to all enabled brokers
        await self._test_all_connections()
        
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            
    async def _rate_limit(self, broker_name: str, rate_limit: int):
        """Implement rate limiting per broker"""
        current_time = time.time()
        last_request = self.last_request_times.get(broker_name, 0)
        time_since_last = current_time - last_request
        
        min_interval = 60.0 / rate_limit  # Convert rate limit to minimum interval
        
        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            await asyncio.sleep(sleep_time)
            
        self.last_request_times[broker_name] = time.time()
        
    async def _make_authenticated_request(self, broker: BrokerConfig, method: str, endpoint: str, 
                                        data: Dict = None, params: Dict = None) -> Optional[Dict]:
        """Make authenticated request to broker API"""
        await self._rate_limit(broker.name, broker.rate_limit)
        
        url = f"{broker.api_url.rstrip('/')}/{endpoint.lstrip('/')}"
        headers = {}
        
        # Set authentication headers based on broker type
        if broker.broker_type == BrokerType.TINKOFF:
            if broker.api_token:
                headers['Authorization'] = f'Bearer {broker.api_token}'
            if broker.sandbox_mode:
                url = url.replace('invest-public-api', 'invest-public-api/sandbox')
                
        elif broker.broker_type == BrokerType.FINAM:
            if broker.api_key:
                headers['X-API-Key'] = broker.api_key
            if broker.api_secret:
                headers['X-API-Secret'] = broker.api_secret
                
        elif broker.broker_type in [BrokerType.SBERBANK, BrokerType.VTB]:
            if broker.api_token:
                headers['Authorization'] = f'Bearer {broker.api_token}'
                
        for attempt in range(broker.retry_attempts):
            try:
                self.request_counts[broker.name] = self.request_counts.get(broker.name, 0) + 1
                
                if method.upper() == 'GET':
                    async with self.session.get(url, headers=headers, params=params) as response:
                        return await self._handle_response(broker, response)
                elif method.upper() == 'POST':
                    async with self.session.post(url, headers=headers, json=data, params=params) as response:
                        return await self._handle_response(broker, response)
                elif method.upper() == 'PUT':
                    async with self.session.put(url, headers=headers, json=data, params=params) as response:
                        return await self._handle_response(broker, response)
                elif method.upper() == 'DELETE':
                    async with self.session.delete(url, headers=headers, params=params) as response:
                        return await self._handle_response(broker, response)
                        
            except asyncio.TimeoutError:
                logger.warning(f"{broker.name} API timeout, attempt {attempt + 1}")
                await asyncio.sleep(1 * (attempt + 1))
                continue
                
            except Exception as e:
                logger.error(f"{broker.name} API request failed: {e}")
                self.error_counts[broker.name] = self.error_counts.get(broker.name, 0) + 1
                await asyncio.sleep(1 * (attempt + 1))
                continue
                
        return None
        
    async def _handle_response(self, broker: BrokerConfig, response: aiohttp.ClientResponse) -> Optional[Dict]:
        """Handle broker API response"""
        if response.status == 200:
            try:
                return await response.json()
            except Exception as e:
                logger.error(f"Failed to parse {broker.name} response: {e}")
                return None
        elif response.status == 401:
            logger.error(f"{broker.name} authentication failed")
            self.connection_status[broker.name] = 'auth_failed'
        elif response.status == 429:
            logger.warning(f"{broker.name} rate limit exceeded")
            await asyncio.sleep(60)  # Wait 1 minute
        else:
            logger.error(f"{broker.name} API error {response.status}: {await response.text()}")
            
        self.error_counts[broker.name] = self.error_counts.get(broker.name, 0) + 1
        return None
        
    async def _test_connection(self, broker_name: str) -> bool:
        """Test connection to a specific broker"""
        if broker_name not in self.brokers:
            return False
            
        broker = self.brokers[broker_name]
        
        if not broker.enabled:
            self.connection_status[broker_name] = 'disabled'
            return False
            
        try:
            # Test endpoint varies by broker
            if broker.broker_type == BrokerType.TINKOFF:
                endpoint = 'tinkoff.public.invest.api.contract.v1.InstrumentsService/Currencies'
            elif broker.broker_type == BrokerType.FINAM:
                endpoint = 'api/v1/securities'
            else:
                endpoint = 'api/v1/ping'
                
            result = await self._make_authenticated_request(broker, 'GET', endpoint)
            
            if result is not None:
                self.connection_status[broker_name] = 'connected'
                logger.info(f"{broker.name} connection established")
                return True
            else:
                self.connection_status[broker_name] = 'failed'
                logger.error(f"{broker.name} connection failed")
                return False
                
        except Exception as e:
            logger.error(f"Error testing {broker.name} connection: {e}")
            self.connection_status[broker_name] = 'error'
            return False
            
    async def _test_all_connections(self):
        """Test connections to all enabled brokers"""
        tasks = []
        
        for broker_name, broker in self.brokers.items():
            if broker.enabled:
                task = asyncio.create_task(
                    self._test_connection(broker_name),
                    name=f"test_{broker_name}"
                )
                tasks.append(task)
                
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            
    async def get_account_info(self, broker_name: str) -> Optional[Dict]:
        """Get account information from broker"""
        if broker_name not in self.brokers:
            return None
            
        broker = self.brokers[broker_name]
        
        if broker.broker_type == BrokerType.TINKOFF:
            endpoint = 'tinkoff.public.invest.api.contract.v1.UsersService/GetAccounts'
        elif broker.broker_type == BrokerType.FINAM:
            endpoint = 'api/v1/portfolio'
        else:
            endpoint = 'api/v1/account'
            
        return await self._make_authenticated_request(broker, 'GET', endpoint)
        
    async def get_portfolio(self, broker_name: str, account_id: str = None) -> Optional[Dict]:
        """Get portfolio information from broker"""
        if broker_name not in self.brokers:
            return None
            
        broker = self.brokers[broker_name]
        
        if broker.broker_type == BrokerType.TINKOFF:
            endpoint = 'tinkoff.public.invest.api.contract.v1.OperationsService/GetPortfolio'
            data = {'account_id': account_id} if account_id else {}
        elif broker.broker_type == BrokerType.FINAM:
            endpoint = f'api/v1/portfolio/{account_id}' if account_id else 'api/v1/portfolio'
            data = None
        else:
            endpoint = 'api/v1/portfolio'
            data = {'account_id': account_id} if account_id else None
            
        return await self._make_authenticated_request(broker, 'GET', endpoint, data=data)
        
    async def place_order(self, broker_name: str, order_data: Dict) -> Optional[Dict]:
        """Place order through broker API"""
        if broker_name not in self.brokers:
            return None
            
        broker = self.brokers[broker_name]
        
        # Validate order data
        if not self._validate_order(broker, order_data):
            return None
            
        if broker.broker_type == BrokerType.TINKOFF:
            endpoint = 'tinkoff.public.invest.api.contract.v1.OrdersService/PostOrder'
        elif broker.broker_type == BrokerType.FINAM:
            endpoint = 'api/v1/orders'
        else:
            endpoint = 'api/v1/orders'
            
        return await self._make_authenticated_request(broker, 'POST', endpoint, data=order_data)
        
    def _validate_order(self, broker: BrokerConfig, order_data: Dict) -> bool:
        """Validate order data before submission"""
        required_fields = ['symbol', 'quantity', 'side', 'type']
        
        for field in required_fields:
            if field not in order_data:
                logger.error(f"Missing required order field: {field}")
                return False
                
        # Validate order value
        price = order_data.get('price', 0)
        quantity = order_data.get('quantity', 0)
        order_value = price * quantity
        
        if order_value < broker.min_order_value:
            logger.error(f"Order value {order_value} below minimum {broker.min_order_value}")
            return False
            
        return True
        
    async def get_order_status(self, broker_name: str, order_id: str) -> Optional[Dict]:
        """Get order status from broker"""
        if broker_name not in self.brokers:
            return None
            
        broker = self.brokers[broker_name]
        
        if broker.broker_type == BrokerType.TINKOFF:
            endpoint = f'tinkoff.public.invest.api.contract.v1.OrdersService/GetOrderState'
            data = {'order_id': order_id}
        elif broker.broker_type == BrokerType.FINAM:
            endpoint = f'api/v1/orders/{order_id}'
            data = None
        else:
            endpoint = f'api/v1/orders/{order_id}'
            data = None
            
        return await self._make_authenticated_request(broker, 'GET', endpoint, data=data)
        
    def get_broker_stats(self) -> Dict:
        """Get statistics for all brokers"""
        stats = {}
        
        for broker_name, broker in self.brokers.items():
            stats[broker_name] = {
                'enabled': broker.enabled,
                'broker_type': broker.broker_type.value,
                'sandbox_mode': broker.sandbox_mode,
                'connection_status': self.connection_status.get(broker_name, 'unknown'),
                'request_count': self.request_counts.get(broker_name, 0),
                'error_count': self.error_counts.get(broker_name, 0),
                'error_rate': self.error_counts.get(broker_name, 0) / max(self.request_counts.get(broker_name, 1), 1),
                'last_request': self.last_request_times.get(broker_name, 0),
                'supports_margin': broker.supports_margin,
                'supports_options': broker.supports_options
            }
            
        return stats
        
    def get_connected_brokers(self) -> List[str]:
        """Get list of successfully connected brokers"""
        return [
            name for name, status in self.connection_status.items()
            if status == 'connected'
        ]

class BrokerConfigManager:
    """Manages broker configuration"""
    
    def __init__(self, config_file: str = None):
        self.config_file = config_file or "/app/config/production/brokers.json"
        
    def save_config(self, broker_manager: RussianBrokerManager):
        """Save broker configuration to file"""
        try:
            config_data = {}
            
            for broker_name, broker in broker_manager.brokers.items():
                broker_dict = asdict(broker)
                # Don't save sensitive credentials to file
                broker_dict.pop('api_token', None)
                broker_dict.pop('api_key', None)
                broker_dict.pop('api_secret', None)
                broker_dict['broker_type'] = broker.broker_type.value
                config_data[broker_name] = broker_dict
                
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Broker configuration saved to {self.config_file}")
            
        except Exception as e:
            logger.error(f"Failed to save broker configuration: {e}")

async def test_broker_connections():
    """Test all Russian broker connections"""
    logger.info("Testing Russian broker connections...")
    
    async with RussianBrokerManager() as broker_manager:
        # Get connection statistics
        stats = broker_manager.get_broker_stats()
        
        logger.info("Broker connection results:")
        for broker_name, broker_stats in stats.items():
            status = broker_stats['connection_status']
            enabled = broker_stats['enabled']
            sandbox = broker_stats['sandbox_mode']
            
            status_msg = f"{'✅' if status == 'connected' else '❌'} {broker_name}: {status}"
            if enabled:
                status_msg += f" (sandbox: {sandbox})"
            else:
                status_msg += " (disabled)"
                
            logger.info(f"  {status_msg}")
            
        # Test account info for connected brokers
        connected_brokers = broker_manager.get_connected_brokers()
        
        for broker_name in connected_brokers:
            logger.info(f"Testing account info for {broker_name}...")
            account_info = await broker_manager.get_account_info(broker_name)
            
            if account_info:
                logger.info(f"  ✅ Account info retrieved successfully")
            else:
                logger.warning(f"  ⚠️ Could not retrieve account info")
                
        logger.info(f"Connected brokers: {len(connected_brokers)}/{len(stats)}")

if __name__ == "__main__":
    asyncio.run(test_broker_connections())