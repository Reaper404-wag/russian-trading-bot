#!/usr/bin/env python3
"""
MOEX API Configuration and Connection Management
Production-ready configuration for Moscow Exchange API
"""

import os
import logging
import asyncio
import aiohttp
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timezone
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MOEXAPIConfig:
    """MOEX API configuration parameters"""
    base_url: str = "https://iss.moex.com/iss"
    timeout: int = 30
    rate_limit: int = 10  # requests per second
    retry_attempts: int = 3
    retry_delay: int = 1
    
    # Market parameters
    market: str = "shares"
    engine: str = "stock"
    board: str = "TQBR"  # Main board for Russian stocks
    
    # Data format
    format: str = "json"
    lang: str = "ru"

class MOEXAPIManager:
    """Production MOEX API connection manager with monitoring"""
    
    def __init__(self, config: MOEXAPIConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.last_request_time = 0
        self.request_count = 0
        self.error_count = 0
        self.connection_status = "disconnected"
        
    async def __aenter__(self):
        """Async context manager entry"""
        connector = aiohttp.TCPConnector(
            limit=100,
            limit_per_host=10,
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': 'RussianTradingBot/1.0',
                'Accept': 'application/json',
                'Accept-Language': 'ru-RU,ru;q=0.9'
            }
        )
        
        # Test connection
        await self._test_connection()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            
    async def _test_connection(self) -> bool:
        """Test MOEX API connection"""
        try:
            url = f"{self.config.base_url}/engines.json"
            async with self.session.get(url) as response:
                if response.status == 200:
                    self.connection_status = "connected"
                    logger.info("MOEX API connection established successfully")
                    return True
                else:
                    self.connection_status = "error"
                    logger.error(f"MOEX API connection failed: {response.status}")
                    return False
                    
        except Exception as e:
            self.connection_status = "error"
            logger.error(f"MOEX API connection test failed: {e}")
            return False
            
    async def _rate_limit(self):
        """Implement rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < (1.0 / self.config.rate_limit):
            sleep_time = (1.0 / self.config.rate_limit) - time_since_last
            await asyncio.sleep(sleep_time)
            
        self.last_request_time = time.time()
        
    async def _make_request(self, url: str, params: Dict = None) -> Optional[Dict]:
        """Make rate-limited request with retry logic"""
        await self._rate_limit()
        
        for attempt in range(self.config.retry_attempts):
            try:
                self.request_count += 1
                
                async with self.session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    elif response.status == 429:  # Rate limited
                        logger.warning(f"MOEX API rate limited, attempt {attempt + 1}")
                        await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                        continue
                    else:
                        logger.error(f"MOEX API error {response.status}: {await response.text()}")
                        self.error_count += 1
                        return None
                        
            except asyncio.TimeoutError:
                logger.warning(f"MOEX API timeout, attempt {attempt + 1}")
                await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                continue
                
            except Exception as e:
                logger.error(f"MOEX API request failed: {e}")
                self.error_count += 1
                await asyncio.sleep(self.config.retry_delay * (attempt + 1))
                continue
                
        return None
        
    async def get_securities_list(self) -> Optional[List[Dict]]:
        """Get list of all securities on MOEX"""
        url = f"{self.config.base_url}/engines/{self.config.engine}/markets/{self.config.market}/boards/{self.config.board}/securities.json"
        
        params = {
            'iss.meta': 'off',
            'iss.only': 'securities',
            'securities.columns': 'SECID,SHORTNAME,REGNUMBER,LOTSIZE,FACEVALUE,STATUS,BOARDID,DECIMALS,SECNAME,REMARKS'
        }
        
        data = await self._make_request(url, params)
        if data and 'securities' in data:
            return data['securities']['data']
        return None
        
    async def get_market_data(self, symbols: List[str]) -> Optional[Dict]:
        """Get current market data for specified symbols"""
        if not symbols:
            return None
            
        # MOEX API can handle multiple symbols in one request
        symbols_str = ','.join(symbols)
        
        url = f"{self.config.base_url}/engines/{self.config.engine}/markets/{self.config.market}/boards/{self.config.board}/securities.json"
        
        params = {
            'securities': symbols_str,
            'iss.meta': 'off',
            'iss.only': 'securities,marketdata',
            'securities.columns': 'SECID,SHORTNAME,PREVPRICE,LOTSIZE',
            'marketdata.columns': 'SECID,LAST,CHANGE,PRCCHANGE,BID,OFFER,HIGH,LOW,OPEN,VOLTODAY,VALTODAY,UPDATETIME,LASTCHANGE'
        }
        
        data = await self._make_request(url, params)
        if data:
            return {
                'securities': data.get('securities', {}),
                'marketdata': data.get('marketdata', {}),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        return None
        
    async def get_historical_data(self, symbol: str, from_date: str, till_date: str) -> Optional[List[Dict]]:
        """Get historical data for a symbol"""
        url = f"{self.config.base_url}/history/engines/{self.config.engine}/markets/{self.config.market}/boards/{self.config.board}/securities/{symbol}.json"
        
        params = {
            'from': from_date,
            'till': till_date,
            'iss.meta': 'off',
            'iss.only': 'history',
            'history.columns': 'TRADEDATE,OPEN,HIGH,LOW,CLOSE,VOLUME,VALUE,NUMTRADES'
        }
        
        data = await self._make_request(url, params)
        if data and 'history' in data:
            return data['history']['data']
        return None
        
    async def get_trading_status(self) -> Optional[Dict]:
        """Get current trading status and market hours"""
        url = f"{self.config.base_url}/engines/{self.config.engine}/markets/{self.config.market}/boards/{self.config.board}/securities.json"
        
        params = {
            'iss.meta': 'off',
            'iss.only': 'marketdata',
            'marketdata.columns': 'SECID,SYSTIME,UPDATETIME',
            'start': '0',
            'limit': '1'
        }
        
        data = await self._make_request(url, params)
        if data and 'marketdata' in data:
            marketdata = data['marketdata']['data']
            if marketdata:
                return {
                    'system_time': marketdata[0][1] if len(marketdata[0]) > 1 else None,
                    'last_update': marketdata[0][2] if len(marketdata[0]) > 2 else None,
                    'market_status': 'open' if marketdata[0][2] else 'closed'
                }
        return None
        
    def get_connection_stats(self) -> Dict:
        """Get connection statistics"""
        return {
            'status': self.connection_status,
            'total_requests': self.request_count,
            'error_count': self.error_count,
            'error_rate': self.error_count / max(self.request_count, 1),
            'last_request_time': self.last_request_time
        }

class MOEXAPIConfigManager:
    """Manages MOEX API configuration and credentials"""
    
    def __init__(self, config_file: str = None):
        self.config_file = config_file or "/app/config/production/moex_api.json"
        self.config = self._load_config()
        
    def _load_config(self) -> Dict:
        """Load MOEX API configuration from file or environment"""
        config = {
            'api_key': os.getenv('MOEX_API_KEY'),
            'base_url': os.getenv('MOEX_API_URL', 'https://iss.moex.com/iss'),
            'rate_limit': int(os.getenv('MOEX_RATE_LIMIT', '10')),
            'timeout': int(os.getenv('MOEX_TIMEOUT', '30')),
            'retry_attempts': int(os.getenv('MOEX_RETRY_ATTEMPTS', '3')),
            'monitoring_enabled': os.getenv('MOEX_MONITORING_ENABLED', 'true').lower() == 'true'
        }
        
        # Try to load from config file
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    config.update(file_config)
            except Exception as e:
                logger.warning(f"Could not load MOEX config file: {e}")
                
        return config
        
    def save_config(self, config: Dict):
        """Save configuration to file"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            logger.info(f"MOEX configuration saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to save MOEX configuration: {e}")
            
    def validate_config(self) -> bool:
        """Validate MOEX API configuration"""
        required_fields = ['base_url', 'rate_limit', 'timeout']
        
        for field in required_fields:
            if not self.config.get(field):
                logger.error(f"Missing required MOEX config field: {field}")
                return False
                
        # Validate URL format
        if not self.config['base_url'].startswith('https://'):
            logger.error("MOEX API URL must use HTTPS")
            return False
            
        # Validate rate limit
        if self.config['rate_limit'] <= 0 or self.config['rate_limit'] > 100:
            logger.error("MOEX rate limit must be between 1 and 100")
            return False
            
        return True
        
    def get_api_manager(self) -> MOEXAPIManager:
        """Get configured MOEX API manager"""
        if not self.validate_config():
            raise ValueError("Invalid MOEX API configuration")
            
        moex_config = MOEXAPIConfig(
            base_url=self.config['base_url'],
            timeout=self.config['timeout'],
            rate_limit=self.config['rate_limit'],
            retry_attempts=self.config['retry_attempts']
        )
        
        return MOEXAPIManager(moex_config)

async def test_moex_connection():
    """Test MOEX API connection and basic functionality"""
    logger.info("Testing MOEX API connection...")
    
    config_manager = MOEXAPIConfigManager()
    
    async with config_manager.get_api_manager() as api:
        # Test basic connection
        stats = api.get_connection_stats()
        logger.info(f"Connection status: {stats['status']}")
        
        # Test securities list
        securities = await api.get_securities_list()
        if securities:
            logger.info(f"Retrieved {len(securities)} securities from MOEX")
            
            # Test market data for popular Russian stocks
            test_symbols = ['SBER', 'GAZP', 'LKOH', 'ROSN', 'NVTK']
            market_data = await api.get_market_data(test_symbols)
            
            if market_data:
                logger.info(f"Retrieved market data for {len(test_symbols)} symbols")
                
                # Display sample data
                if 'marketdata' in market_data and market_data['marketdata']['data']:
                    for row in market_data['marketdata']['data'][:3]:
                        symbol = row[0] if row else 'Unknown'
                        price = row[1] if len(row) > 1 else 'N/A'
                        logger.info(f"  {symbol}: {price} RUB")
                        
        # Test trading status
        status = await api.get_trading_status()
        if status:
            logger.info(f"Market status: {status.get('market_status', 'unknown')}")
            
        # Final stats
        final_stats = api.get_connection_stats()
        logger.info(f"Test completed - Requests: {final_stats['total_requests']}, Errors: {final_stats['error_count']}")

if __name__ == "__main__":
    asyncio.run(test_moex_connection())