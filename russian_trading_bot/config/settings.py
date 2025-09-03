"""
Main settings and configuration for Russian trading bot
"""

import os
from typing import Optional
from dataclasses import dataclass
from russian_trading_bot.config.market_config import RussianMarketConfig


@dataclass
class DatabaseConfig:
    """Database configuration"""
    host: str = "localhost"
    port: int = 5432
    database: str = "russian_trading_bot"
    username: str = "postgres"
    password: str = ""
    
    @property
    def connection_string(self) -> str:
        """Get database connection string"""
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = "logs/trading_bot.log"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


@dataclass
class SecurityConfig:
    """Security configuration"""
    secret_key: str = ""
    api_key_header: str = "X-API-Key"
    token_expiry_hours: int = 24
    max_login_attempts: int = 5
    
    def __post_init__(self):
        """Load secret key from environment"""
        if not self.secret_key:
            self.secret_key = os.getenv("SECRET_KEY", "default-secret-key-change-in-production")


class Settings:
    """Main application settings"""
    
    def __init__(self):
        self.market_config = RussianMarketConfig()
        self.database = DatabaseConfig()
        self.logging = LoggingConfig()
        self.security = SecurityConfig()
        
        # Load from environment variables
        self._load_from_env()
    
    def _load_from_env(self):
        """Load configuration from environment variables"""
        # Database
        self.database.host = os.getenv("DB_HOST", self.database.host)
        self.database.port = int(os.getenv("DB_PORT", str(self.database.port)))
        self.database.database = os.getenv("DB_NAME", self.database.database)
        self.database.username = os.getenv("DB_USER", self.database.username)
        self.database.password = os.getenv("DB_PASSWORD", self.database.password)
        
        # Logging
        self.logging.level = os.getenv("LOG_LEVEL", self.logging.level)
        self.logging.file_path = os.getenv("LOG_FILE", self.logging.file_path)
        
        # API Keys (to be set by user)
        self.moex_api_key = os.getenv("MOEX_API_KEY", "")
        self.tinkoff_token = os.getenv("TINKOFF_TOKEN", "")
        self.finam_api_key = os.getenv("FINAM_API_KEY", "")
        
        # News API keys
        self.news_api_keys = {
            "rbc": os.getenv("RBC_API_KEY", ""),
            "interfax": os.getenv("INTERFAX_API_KEY", ""),
        }
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return os.getenv("ENVIRONMENT", "development").lower() == "production"
    
    @property
    def debug(self) -> bool:
        """Check if debug mode is enabled"""
        return os.getenv("DEBUG", "false").lower() == "true"


# Global settings instance
settings = Settings()