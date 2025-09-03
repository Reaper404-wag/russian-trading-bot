"""
Слой доступа к данным для российского торгового бота
Data access layer for Russian trading bot
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import pytz
from sqlalchemy import create_engine, and_, or_, desc, asc, func, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .schema import (
    Base, RussianStock, MarketData, NewsArticle, 
    Trade, Portfolio, DataRetentionPolicy, MSK
)

class RussianMarketDataAccess:
    """Класс для доступа к данным российского рынка"""
    
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
    def create_tables(self):
        """Создание всех таблиц в базе данных"""
        Base.metadata.create_all(bind=self.engine)
        
    def get_session(self) -> Session:
        """Получение сессии базы данных"""
        return self.SessionLocal()
    
    # === Методы для работы с российскими акциями ===
    
    def add_russian_stock(self, symbol: str, name: str, sector: str, 
                         lot_size: int = 1) -> bool:
        """Добавление российской акции в базу данных"""
        with self.get_session() as session:
            try:
                stock = RussianStock(
                    symbol=symbol.upper(),
                    name=name,
                    sector=sector,
                    lot_size=lot_size
                )
                session.add(stock)
                session.commit()
                return True
            except IntegrityError:
                session.rollback()
                return False
            except Exception as e:
                session.rollback()
                raise e
    
    def get_russian_stocks_by_sector(self, sector: str) -> List[RussianStock]:
        """Получение российских акций по сектору"""
        with self.get_session() as session:
            return session.query(RussianStock).filter(
                and_(
                    RussianStock.sector == sector,
                    RussianStock.is_active == True
                )
            ).all()
    
    def get_active_russian_stocks(self) -> List[RussianStock]:
        """Получение всех активных российских акций"""
        with self.get_session() as session:
            return session.query(RussianStock).filter(
                RussianStock.is_active == True
            ).order_by(RussianStock.symbol).all()
    
    # === Методы для работы с рыночными данными MOEX ===
    
    def add_market_data(self, symbol: str, timestamp: datetime, price: Decimal,
                       volume: int, bid: Optional[Decimal] = None, 
                       ask: Optional[Decimal] = None, **kwargs) -> bool:
        """Добавление рыночных данных MOEX"""
        with self.get_session() as session:
            try:
                # Конвертация времени в MSK если необходимо
                if timestamp.tzinfo is None:
                    timestamp = MSK.localize(timestamp)
                elif timestamp.tzinfo != MSK:
                    timestamp = timestamp.astimezone(MSK)
                
                market_data = MarketData(
                    symbol=symbol.upper(),
                    timestamp=timestamp,
                    price=price,
                    volume=volume,
                    bid=bid,
                    ask=ask,
                    **kwargs
                )
                session.add(market_data)
                session.commit()
                return True
            except IntegrityError:
                session.rollback()
                return False
            except Exception as e:
                session.rollback()
                raise e
    
    def get_latest_market_data(self, symbol: str) -> Optional[MarketData]:
        """Получение последних рыночных данных для акции"""
        with self.get_session() as session:
            return session.query(MarketData).filter(
                MarketData.symbol == symbol.upper()
            ).order_by(desc(MarketData.timestamp)).first()
    
    def get_market_data_range(self, symbol: str, start_date: datetime, 
                             end_date: datetime) -> List[MarketData]:
        """Получение рыночных данных за период"""
        with self.get_session() as session:
            return session.query(MarketData).filter(
                and_(
                    MarketData.symbol == symbol.upper(),
                    MarketData.timestamp >= start_date,
                    MarketData.timestamp <= end_date
                )
            ).order_by(MarketData.timestamp).all()
    
    def get_moex_trading_hours_data(self, symbol: str, date: datetime) -> List[MarketData]:
        """Получение данных только в часы торгов MOEX (10:00-18:45 MSK)"""
        with self.get_session() as session:
            # Начало и конец торгового дня
            if isinstance(date, datetime):
                date = date.date()
            trading_start = MSK.localize(datetime.combine(date, datetime.min.time().replace(hour=10)))
            trading_end = MSK.localize(datetime.combine(date, datetime.min.time().replace(hour=18, minute=45)))
            
            return session.query(MarketData).filter(
                and_(
                    MarketData.symbol == symbol.upper(),
                    MarketData.timestamp >= trading_start,
                    MarketData.timestamp <= trading_end
                )
            ).order_by(MarketData.timestamp).all()
    
    # === Методы для работы с российскими новостями ===
    
    def add_news_article(self, title: str, content: str, source: str, 
                        timestamp: datetime, url: Optional[str] = None,
                        sentiment_score: Optional[Decimal] = None,
                        mentioned_stocks: Optional[List[str]] = None) -> bool:
        """Добавление российской финансовой новости"""
        with self.get_session() as session:
            try:
                # Конвертация времени в MSK
                if timestamp.tzinfo is None:
                    timestamp = MSK.localize(timestamp)
                elif timestamp.tzinfo != MSK:
                    timestamp = timestamp.astimezone(MSK)
                
                article = NewsArticle(
                    title=title,
                    content=content,
                    source=source,
                    url=url,
                    timestamp=timestamp,
                    sentiment_score=sentiment_score,
                    mentioned_stocks=mentioned_stocks or []
                )
                session.add(article)
                session.commit()
                return True
            except IntegrityError:
                session.rollback()
                return False
            except Exception as e:
                session.rollback()
                raise e
    
    def get_news_by_russian_source(self, source: str, limit: int = 100) -> List[NewsArticle]:
        """Получение новостей от российских источников (РБК, Ведомости и т.д.)"""
        with self.get_session() as session:
            return session.query(NewsArticle).filter(
                NewsArticle.source == source
            ).order_by(desc(NewsArticle.timestamp)).limit(limit).all()
    
    def get_news_mentioning_stock(self, symbol: str, days: int = 7) -> List[NewsArticle]:
        """Получение новостей, упоминающих конкретную российскую акцию"""
        with self.get_session() as session:
            cutoff_date = datetime.now(MSK) - timedelta(days=days)
            
            # Для SQLite используем простой поиск по строке в JSON
            if 'sqlite' in str(self.engine.url):
                return session.query(NewsArticle).filter(
                    and_(
                        NewsArticle.mentioned_stocks.like(f'%"{symbol.upper()}"%'),
                        NewsArticle.timestamp >= cutoff_date
                    )
                ).order_by(desc(NewsArticle.timestamp)).all()
            else:
                # PostgreSQL версия
                return session.query(NewsArticle).filter(
                    and_(
                        NewsArticle.mentioned_stocks.contains([symbol.upper()]),
                        NewsArticle.timestamp >= cutoff_date
                    )
                ).order_by(desc(NewsArticle.timestamp)).all()
    
    def get_sentiment_analysis_for_stock(self, symbol: str, days: int = 30) -> Dict[str, Any]:
        """Анализ настроений новостей для российской акции"""
        with self.get_session() as session:
            cutoff_date = datetime.now(MSK) - timedelta(days=days)
            
            # Для SQLite используем простой поиск по строке в JSON
            if 'sqlite' in str(self.engine.url):
                result = session.query(
                    func.avg(NewsArticle.sentiment_score).label('avg_sentiment'),
                    func.count(NewsArticle.id).label('news_count'),
                    func.min(NewsArticle.sentiment_score).label('min_sentiment'),
                    func.max(NewsArticle.sentiment_score).label('max_sentiment')
                ).filter(
                    and_(
                        NewsArticle.mentioned_stocks.like(f'%"{symbol.upper()}"%'),
                        NewsArticle.timestamp >= cutoff_date,
                        NewsArticle.sentiment_score.isnot(None)
                    )
                ).first()
            else:
                # PostgreSQL версия
                result = session.query(
                    func.avg(NewsArticle.sentiment_score).label('avg_sentiment'),
                    func.count(NewsArticle.id).label('news_count'),
                    func.min(NewsArticle.sentiment_score).label('min_sentiment'),
                    func.max(NewsArticle.sentiment_score).label('max_sentiment')
                ).filter(
                    and_(
                        NewsArticle.mentioned_stocks.contains([symbol.upper()]),
                        NewsArticle.timestamp >= cutoff_date,
                        NewsArticle.sentiment_score.isnot(None)
                    )
                ).first()
            
            return {
                'symbol': symbol.upper(),
                'period_days': days,
                'average_sentiment': float(result.avg_sentiment) if result.avg_sentiment else 0.0,
                'news_count': result.news_count,
                'min_sentiment': float(result.min_sentiment) if result.min_sentiment else 0.0,
                'max_sentiment': float(result.max_sentiment) if result.max_sentiment else 0.0
            }
    
    # === Методы для работы со сделками ===
    
    def add_trade(self, symbol: str, action: str, quantity: int, price: Decimal,
                  reasoning: str, order_id: Optional[str] = None) -> int:
        """Добавление сделки на российском рынке"""
        with self.get_session() as session:
            try:
                trade = Trade(
                    symbol=symbol.upper(),
                    action=action.upper(),
                    quantity=quantity,
                    price=price,
                    timestamp=datetime.now(MSK),
                    reasoning=reasoning,
                    order_id=order_id,
                    total_amount=price * quantity
                )
                session.add(trade)
                session.commit()
                return trade.id
            except Exception as e:
                session.rollback()
                raise e
    
    def get_trades_by_symbol(self, symbol: str, limit: int = 100) -> List[Trade]:
        """Получение сделок по российской акции"""
        with self.get_session() as session:
            return session.query(Trade).filter(
                Trade.symbol == symbol.upper()
            ).order_by(desc(Trade.timestamp)).limit(limit).all()
    
    def get_trading_performance(self, symbol: str, days: int = 30) -> Dict[str, Any]:
        """Анализ торговой производительности по российской акции"""
        with self.get_session() as session:
            cutoff_date = datetime.now(MSK) - timedelta(days=days)
            
            trades = session.query(Trade).filter(
                and_(
                    Trade.symbol == symbol.upper(),
                    Trade.timestamp >= cutoff_date,
                    Trade.status == 'EXECUTED'
                )
            ).all()
            
            buy_trades = [t for t in trades if t.action == 'BUY']
            sell_trades = [t for t in trades if t.action == 'SELL']
            
            total_bought = sum(t.total_amount for t in buy_trades)
            total_sold = sum(t.total_amount for t in sell_trades)
            
            return {
                'symbol': symbol.upper(),
                'period_days': days,
                'total_trades': len(trades),
                'buy_trades': len(buy_trades),
                'sell_trades': len(sell_trades),
                'total_bought_rub': float(total_bought),
                'total_sold_rub': float(total_sold),
                'net_pnl_rub': float(total_sold - total_bought)
            }
    
    # === Методы для работы с портфелем ===
    
    def update_portfolio_position(self, symbol: str, quantity: int, 
                                 average_price: Decimal) -> bool:
        """Обновление позиции в портфеле российских акций"""
        with self.get_session() as session:
            try:
                position = session.query(Portfolio).filter(
                    Portfolio.symbol == symbol.upper()
                ).first()
                
                if position:
                    position.quantity = quantity
                    position.average_price = average_price
                    position.last_updated = datetime.now(MSK)
                else:
                    position = Portfolio(
                        symbol=symbol.upper(),
                        quantity=quantity,
                        average_price=average_price
                    )
                    session.add(position)
                
                session.commit()
                return True
            except Exception as e:
                session.rollback()
                raise e
    
    def get_portfolio_positions(self) -> List[Portfolio]:
        """Получение всех позиций в портфеле"""
        with self.get_session() as session:
            return session.query(Portfolio).filter(
                Portfolio.quantity > 0
            ).all()
    
    # === Методы для соблюдения российского законодательства ===
    
    def setup_retention_policies(self):
        """Настройка политик хранения данных согласно российскому законодательству"""
        policies = [
            ('market_data', 2555, 'Рыночные данные - 7 лет согласно требованиям ЦБ РФ'),
            ('trades', 1825, 'Сделки - 5 лет для налоговой отчетности'),
            ('news_articles', 365, 'Новости - 1 год для анализа'),
            ('portfolio', 2555, 'Портфель - 7 лет для аудита')
        ]
        
        with self.get_session() as session:
            try:
                for table_name, retention_days, description in policies:
                    existing = session.query(DataRetentionPolicy).filter(
                        DataRetentionPolicy.table_name == table_name
                    ).first()
                    
                    if not existing:
                        policy = DataRetentionPolicy(
                            table_name=table_name,
                            retention_days=retention_days,
                            description=description
                        )
                        session.add(policy)
                
                session.commit()
            except Exception as e:
                session.rollback()
                raise e
    
    def cleanup_old_data(self):
        """Очистка старых данных согласно политикам хранения"""
        with self.get_session() as session:
            try:
                policies = session.query(DataRetentionPolicy).filter(
                    DataRetentionPolicy.is_active == True
                ).all()
                
                for policy in policies:
                    cutoff_date = datetime.now(MSK) - timedelta(days=policy.retention_days)
                    
                    if policy.table_name == 'market_data':
                        deleted = session.query(MarketData).filter(
                            MarketData.timestamp < cutoff_date
                        ).delete()
                    elif policy.table_name == 'news_articles':
                        deleted = session.query(NewsArticle).filter(
                            NewsArticle.timestamp < cutoff_date
                        ).delete()
                    elif policy.table_name == 'trades':
                        deleted = session.query(Trade).filter(
                            Trade.timestamp < cutoff_date
                        ).delete()
                    
                    print(f"Удалено {deleted} записей из {policy.table_name}")
                
                session.commit()
            except Exception as e:
                session.rollback()
                raise e
    
    def get_database_statistics(self) -> Dict[str, Any]:
        """Получение статистики базы данных для мониторинга"""
        with self.get_session() as session:
            stats = {}
            
            # Статистика по акциям
            stats['stocks_count'] = session.query(RussianStock).count()
            stats['active_stocks'] = session.query(RussianStock).filter(
                RussianStock.is_active == True
            ).count()
            
            # Статистика по рыночным данным
            stats['market_data_count'] = session.query(MarketData).count()
            latest_data = session.query(func.max(MarketData.timestamp)).scalar()
            stats['latest_market_data'] = latest_data.isoformat() if latest_data else None
            
            # Статистика по новостям
            stats['news_count'] = session.query(NewsArticle).count()
            stats['processed_news'] = session.query(NewsArticle).filter(
                NewsArticle.processed == True
            ).count()
            
            # Статистика по сделкам
            stats['total_trades'] = session.query(Trade).count()
            stats['executed_trades'] = session.query(Trade).filter(
                Trade.status == 'EXECUTED'
            ).count()
            
            # Статистика по портфелю
            stats['portfolio_positions'] = session.query(Portfolio).filter(
                Portfolio.quantity > 0
            ).count()
            
            return stats