"""
Конфигурация базы данных для российского торгового бота
Database configuration for Russian trading bot
"""

import os
from typing import Optional
from dataclasses import dataclass

@dataclass
class DatabaseConfig:
    """Конфигурация подключения к базе данных"""
    host: str = "localhost"
    port: int = 5432
    database: str = "russian_trading_bot"
    username: str = "postgres"
    password: str = ""
    
    # Настройки для российского рынка
    timezone: str = "Europe/Moscow"
    
    # Настройки пула соединений
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    
    # SSL настройки
    ssl_mode: str = "prefer"
    
    def get_database_url(self) -> str:
        """Получение URL для подключения к базе данных"""
        if self.password:
            return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        else:
            return f"postgresql://{self.username}@{self.host}:{self.port}/{self.database}"
    
    def get_async_database_url(self) -> str:
        """Получение URL для асинхронного подключения"""
        if self.password:
            return f"postgresql+asyncpg://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        else:
            return f"postgresql+asyncpg://{self.username}@{self.host}:{self.port}/{self.database}"

def get_database_config() -> DatabaseConfig:
    """Получение конфигурации базы данных из переменных окружения"""
    return DatabaseConfig(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "russian_trading_bot"),
        username=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
        pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "3600"))
    )

# Настройки для тестовой базы данных
TEST_DATABASE_CONFIG = DatabaseConfig(
    host="localhost",
    port=5432,
    database="russian_trading_bot_test",
    username="postgres",
    password="",
    pool_size=5,
    max_overflow=10
)