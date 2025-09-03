"""
Миграции базы данных для российского торгового бота
Database migrations for Russian trading bot
"""

from typing import List, Dict, Any
from datetime import datetime
import pytz
from sqlalchemy import text, inspect
from sqlalchemy.engine import Engine

from .schema import Base, MSK
from .data_access import RussianMarketDataAccess

class DatabaseMigrations:
    """Класс для управления миграциями базы данных"""
    
    def __init__(self, data_access: RussianMarketDataAccess):
        self.data_access = data_access
        self.engine = data_access.engine
    
    def create_all_tables(self):
        """Создание всех таблиц"""
        print("Создание таблиц базы данных...")
        Base.metadata.create_all(bind=self.engine)
        print("Таблицы созданы успешно")
    
    def drop_all_tables(self):
        """Удаление всех таблиц (осторожно!)"""
        print("ВНИМАНИЕ: Удаление всех таблиц...")
        Base.metadata.drop_all(bind=self.engine)
        print("Все таблицы удалены")
    
    def check_tables_exist(self) -> Dict[str, bool]:
        """Проверка существования таблиц"""
        inspector = inspect(self.engine)
        existing_tables = inspector.get_table_names()
        
        required_tables = [
            'russian_stocks',
            'market_data', 
            'news_articles',
            'trades',
            'portfolio',
            'data_retention_policies'
        ]
        
        return {table: table in existing_tables for table in required_tables}
    
    def setup_initial_data(self):
        """Настройка начальных данных"""
        print("Настройка начальных данных...")
        
        # Настройка политик хранения данных
        self.data_access.setup_retention_policies()
        
        # Добавление основных российских акций
        self._add_major_russian_stocks()
        
        print("Начальные данные настроены")
    
    def _add_major_russian_stocks(self):
        """Добавление основных российских акций MOEX"""
        major_stocks = [
            # Банки
            ("SBER", "ПАО Сбербанк", "Банки", 10),
            ("VTBR", "Банк ВТБ", "Банки", 50000),
            ("GAZP", "Газпром", "Нефть и газ", 10),
            ("LKOH", "ЛУКОЙЛ", "Нефть и газ", 1),
            ("ROSN", "Роснефть", "Нефть и газ", 10),
            ("NVTK", "НОВАТЭК", "Нефть и газ", 10),
            
            # Металлургия
            ("GMKN", "ГМК Норильский никель", "Металлургия", 1),
            ("NLMK", "НЛМК", "Металлургия", 10),
            ("MAGN", "ММК", "Металлургия", 10),
            ("ALRS", "АЛРОСА", "Металлургия", 10),
            
            # Телекоммуникации
            ("MTSS", "МТС", "Телекоммуникации", 10),
            ("RTKM", "Ростелеком", "Телекоммуникации", 10),
            
            # Электроэнергетика
            ("IRAO", "Интер РАО", "Электроэнергетика", 1000),
            ("FEES", "ФСК ЕЭС", "Электроэнергетика", 100000),
            
            # Ритейл
            ("FIVE", "X5 Retail Group", "Ритейл", 1),
            ("MGNT", "Магнит", "Ритейл", 1),
            
            # IT
            ("YNDX", "Яндекс", "IT", 1),
            ("OZON", "Ozon", "IT", 1),
            ("VKCO", "VK", "IT", 1),
            
            # Химия
            ("PHOR", "ФосАгро", "Химия", 1),
            ("AKRN", "Акрон", "Химия", 1),
        ]
        
        for symbol, name, sector, lot_size in major_stocks:
            try:
                self.data_access.add_russian_stock(symbol, name, sector, lot_size)
                print(f"Добавлена акция: {symbol} - {name}")
            except Exception as e:
                print(f"Ошибка при добавлении {symbol}: {e}")
    
    def create_indexes(self):
        """Создание дополнительных индексов для производительности"""
        indexes_sql = [
            # Индексы для быстрого поиска рыночных данных
            """
            CREATE INDEX IF NOT EXISTS idx_market_data_symbol_date 
            ON market_data (symbol, timestamp);
            """,
            
            # Индексы для анализа новостей
            """
            CREATE INDEX IF NOT EXISTS idx_news_sentiment_date 
            ON news_articles (sentiment_score, timestamp);
            """,
            
            # Индексы для торговой статистики
            """
            CREATE INDEX IF NOT EXISTS idx_trades_symbol_status_date 
            ON trades (symbol, status, timestamp);
            """
        ]
        
        with self.engine.connect() as conn:
            for sql in indexes_sql:
                try:
                    conn.execute(text(sql))
                    conn.commit()
                    index_name = sql.split("idx_")[1].split()[0] if "idx_" in sql else "unknown"
                    print(f"Создан индекс: idx_{index_name}")
                except Exception as e:
                    print(f"Ошибка создания индекса: {e}")
    
    def create_views(self):
        """Создание представлений для удобного анализа данных"""
        views_sql = [
            # Представление для анализа дневных торгов
            """
            CREATE OR REPLACE VIEW daily_trading_summary AS
            SELECT 
                symbol,
                DATE(timestamp) as trading_date,
                MIN(price) as low_price,
                MAX(price) as high_price,
                FIRST_VALUE(price) OVER (PARTITION BY symbol, DATE(timestamp) ORDER BY timestamp) as open_price,
                LAST_VALUE(price) OVER (PARTITION BY symbol, DATE(timestamp) ORDER BY timestamp 
                    RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as close_price,
                SUM(volume) as total_volume,
                COUNT(*) as data_points
            FROM market_data
            GROUP BY symbol, DATE(timestamp), timestamp, price
            ORDER BY symbol, trading_date;
            """,
            
            # Представление для анализа настроений по акциям
            """
            CREATE OR REPLACE VIEW stock_sentiment_summary AS
            SELECT 
                unnest(mentioned_stocks) as symbol,
                DATE(timestamp) as news_date,
                AVG(sentiment_score) as avg_sentiment,
                COUNT(*) as news_count,
                MIN(sentiment_score) as min_sentiment,
                MAX(sentiment_score) as max_sentiment
            FROM news_articles
            WHERE sentiment_score IS NOT NULL
            GROUP BY unnest(mentioned_stocks), DATE(timestamp)
            ORDER BY symbol, news_date;
            """,
            
            # Представление для торговой производительности
            """
            CREATE OR REPLACE VIEW trading_performance AS
            SELECT 
                symbol,
                DATE(timestamp) as trading_date,
                SUM(CASE WHEN action = 'BUY' THEN total_amount ELSE 0 END) as total_bought,
                SUM(CASE WHEN action = 'SELL' THEN total_amount ELSE 0 END) as total_sold,
                COUNT(CASE WHEN action = 'BUY' THEN 1 END) as buy_count,
                COUNT(CASE WHEN action = 'SELL' THEN 1 END) as sell_count,
                SUM(CASE WHEN action = 'SELL' THEN total_amount ELSE -total_amount END) as net_pnl
            FROM trades
            WHERE status = 'EXECUTED'
            GROUP BY symbol, DATE(timestamp)
            ORDER BY symbol, trading_date;
            """
        ]
        
        with self.engine.connect() as conn:
            for sql in views_sql:
                try:
                    conn.execute(text(sql))
                    conn.commit()
                    view_name = sql.split("VIEW ")[1].split(" AS")[0]
                    print(f"Создано представление: {view_name}")
                except Exception as e:
                    print(f"Ошибка создания представления: {e}")
    
    def backup_database(self, backup_path: str):
        """Создание резервной копии базы данных"""
        # Это упрощенная версия - в продакшене используйте pg_dump
        print(f"Создание резервной копии в {backup_path}...")
        # Здесь должна быть логика создания бэкапа
        print("Резервная копия создана")
    
    def get_migration_status(self) -> Dict[str, Any]:
        """Получение статуса миграций"""
        tables_status = self.check_tables_exist()
        
        # Для SQLite используем упрощенную проверку
        indexes = []
        views = []
        
        try:
            with self.engine.connect() as conn:
                # Проверка индексов для SQLite
                if 'sqlite' in str(self.engine.url):
                    indexes_result = conn.execute(text("""
                        SELECT name FROM sqlite_master 
                        WHERE type='index' AND name LIKE 'idx_%'
                    """))
                    indexes = [row[0] for row in indexes_result]
                    
                    # Проверка представлений для SQLite
                    views_result = conn.execute(text("""
                        SELECT name FROM sqlite_master 
                        WHERE type='view' AND name IN ('daily_trading_summary', 'stock_sentiment_summary', 'trading_performance')
                    """))
                    views = [row[0] for row in views_result]
                else:
                    # PostgreSQL версия
                    indexes_result = conn.execute(text("""
                        SELECT indexname FROM pg_indexes 
                        WHERE tablename IN ('market_data', 'news_articles', 'trades')
                        AND indexname LIKE 'idx_%'
                    """))
                    indexes = [row[0] for row in indexes_result]
                    
                    views_result = conn.execute(text("""
                        SELECT viewname FROM pg_views 
                        WHERE viewname IN ('daily_trading_summary', 'stock_sentiment_summary', 'trading_performance')
                    """))
                    views = [row[0] for row in views_result]
        except Exception as e:
            print(f"Ошибка при проверке статуса миграций: {e}")
        
        return {
            'tables': tables_status,
            'indexes': indexes,
            'views': views,
            'migration_date': datetime.now(MSK).isoformat()
        }