"""
Russian market configuration parameters
"""

from dataclasses import dataclass
from datetime import time
from typing import Dict, List
import pytz


@dataclass
class TradingHours:
    """MOEX trading hours configuration"""
    market_open: time = time(10, 0)  # 10:00 MSK
    market_close: time = time(18, 45)  # 18:45 MSK
    timezone: str = "Europe/Moscow"
    
    @property
    def moscow_tz(self):
        """Get Moscow timezone"""
        return pytz.timezone(self.timezone)


@dataclass
class MarketParameters:
    """Russian market parameters"""
    currency: str = "RUB"
    settlement_period: int = 2  # T+2 settlement
    min_lot_size: int = 1
    max_position_size: float = 0.1  # 10% of portfolio
    commission_rate: float = 0.0005  # 0.05%
    
    # MOEX market segments
    main_board_symbols: List[str] = None
    standard_market_symbols: List[str] = None
    
    def __post_init__(self):
        if self.main_board_symbols is None:
            self.main_board_symbols = [
                "SBER", "GAZP", "LKOH", "GMKN", "NVTK", "ROSN", "TATN", 
                "SNGS", "MGNT", "YNDX", "MTSS", "ALRS", "CHMF", "NLMK"
            ]
        
        if self.standard_market_symbols is None:
            self.standard_market_symbols = [
                "AFLT", "AGRO", "BANE", "CBOM", "FEES", "FIXP", "HYDR",
                "IRAO", "MAIL", "MOEX", "OZON", "PLZL", "POLY", "RUAL"
            ]


@dataclass
class RiskParameters:
    """Risk management parameters for Russian market"""
    max_daily_loss: float = 0.02  # 2% max daily loss
    max_position_loss: float = 0.05  # 5% max loss per position
    max_portfolio_volatility: float = 0.15  # 15% max portfolio volatility
    
    # Russian market specific risks
    geopolitical_risk_multiplier: float = 1.5
    sanctions_risk_adjustment: float = 0.8
    ruble_volatility_threshold: float = 0.03  # 3% daily RUB volatility
    
    # Sector concentration limits
    max_sector_exposure: Dict[str, float] = None
    
    def __post_init__(self):
        if self.max_sector_exposure is None:
            self.max_sector_exposure = {
                "oil_gas": 0.3,      # 30% max in oil & gas
                "banking": 0.25,     # 25% max in banking
                "metals": 0.2,       # 20% max in metals
                "telecom": 0.15,     # 15% max in telecom
                "retail": 0.15,      # 15% max in retail
                "tech": 0.2,         # 20% max in tech
                "utilities": 0.1     # 10% max in utilities
            }


@dataclass
class APIConfiguration:
    """API configuration for Russian market data sources"""
    moex_base_url: str = "https://iss.moex.com"
    moex_timeout: int = 30
    moex_rate_limit: int = 100  # requests per minute
    
    # News sources
    news_sources: Dict[str, str] = None
    news_update_interval: int = 300  # 5 minutes
    
    # Broker APIs
    tinkoff_api_url: str = "https://invest-public-api.tinkoff.ru/rest"
    finam_api_url: str = "https://trade-api.finam.ru"
    
    def __post_init__(self):
        if self.news_sources is None:
            self.news_sources = {
                "rbc": "https://www.rbc.ru/rss/rbcnews.rss",
                "vedomosti": "https://www.vedomosti.ru/rss/news",
                "kommersant": "https://www.kommersant.ru/RSS/news.xml",
                "interfax": "https://www.interfax.ru/rss.asp",
                "tass": "https://tass.ru/rss/v2.xml"
            }


class RussianMarketConfig:
    """Main configuration class for Russian market trading"""
    
    def __init__(self):
        self.trading_hours = TradingHours()
        self.market_params = MarketParameters()
        self.risk_params = RiskParameters()
        self.api_config = APIConfiguration()
    
    def is_market_open(self) -> bool:
        """Check if MOEX market is currently open"""
        from datetime import datetime
        
        now = datetime.now(self.trading_hours.moscow_tz)
        current_time = now.time()
        
        # Check if it's a weekday (Monday = 0, Sunday = 6)
        if now.weekday() >= 5:  # Saturday or Sunday
            return False
        
        return (self.trading_hours.market_open <= current_time <= 
                self.trading_hours.market_close)
    
    def get_sector_for_symbol(self, symbol: str) -> str:
        """Get sector classification for a Russian stock symbol"""
        sector_mapping = {
            # Banking
            "SBER": "banking", "VTB": "banking", "CBOM": "banking",
            
            # Oil & Gas
            "GAZP": "oil_gas", "LKOH": "oil_gas", "ROSN": "oil_gas", 
            "NVTK": "oil_gas", "SNGS": "oil_gas", "TATN": "oil_gas",
            
            # Metals & Mining
            "GMKN": "metals", "NLMK": "metals", "ALRS": "metals", 
            "CHMF": "metals", "RUAL": "metals", "PLZL": "metals",
            
            # Technology
            "YNDX": "tech", "MAIL": "tech", "OZON": "tech", "FIXP": "tech",
            
            # Telecom
            "MTSS": "telecom", "RTKM": "telecom",
            
            # Retail
            "MGNT": "retail", "LNTA": "retail", "FIVE": "retail",
            
            # Utilities
            "HYDR": "utilities", "IRAO": "utilities", "FEES": "utilities"
        }
        
        return sector_mapping.get(symbol, "other")


# Global configuration instance
russian_market_config = RussianMarketConfig()