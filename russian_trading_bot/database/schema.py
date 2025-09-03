"""
Схема базы данных для российского торгового бота
Database schema for Russian trading bot
"""

from sqlalchemy import (
    Column, String, Integer, BigInteger, DateTime, Numeric, 
    Text, JSON, Boolean, ForeignKey, Index, CheckConstraint
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import pytz

Base = declarative_base()

# Московская временная зона для российского рынка
MSK = pytz.timezone('Europe/Moscow')


class RussianStock(Base):
    """Модель российских акций на MOEX"""
    __tablename__ = 'russian_stocks'
    
    symbol = Column(String(10), primary_key=True, comment='Тикер MOEX (например, SBER, GAZP)')
    name = Column(String(200), nullable=False, comment='Название российской компании')
    sector = Column(String(100), nullable=False, comment='Сектор российского рынка')
    currency = Column(String(3), default='RUB', comment='Валюта торгов')
    lot_size = Column(Integer, default=1, comment='Размер лота')
    is_active = Column(Boolean, default=True, comment='Активна ли акция для торгов')
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(MSK))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(MSK), onupdate=lambda: datetime.now(MSK))
    
    # Связи
    market_data = relationship("MarketData", back_populates="stock")
    trades = relationship("Trade", back_populates="stock")
    
    __table_args__ = (
        CheckConstraint('lot_size > 0', name='positive_lot_size'),
        Index('idx_sector', 'sector'),
        Index('idx_active', 'is_active'),
    )


class MarketData(Base):
    """Рыночные данные MOEX"""
    __tablename__ = 'market_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), ForeignKey('russian_stocks.symbol'), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, comment='Время в MSK')
    price = Column(Numeric(15, 4), nullable=False, comment='Цена в рублях')
    volume = Column(Integer, nullable=False, comment='Объем торгов')
    bid = Column(Numeric(15, 4), comment='Цена покупки')
    ask = Column(Numeric(15, 4), comment='Цена продажи')
    open_price = Column(Numeric(15, 4), comment='Цена открытия')
    high_price = Column(Numeric(15, 4), comment='Максимальная цена')
    low_price = Column(Numeric(15, 4), comment='Минимальная цена')
    close_price = Column(Numeric(15, 4), comment='Цена закрытия')
    
    # Связи
    stock = relationship("RussianStock", back_populates="market_data")
    
    __table_args__ = (
        CheckConstraint('price > 0', name='positive_price'),
        CheckConstraint('volume >= 0', name='non_negative_volume'),
        CheckConstraint('bid > 0 OR bid IS NULL', name='positive_bid'),
        CheckConstraint('ask > 0 OR ask IS NULL', name='positive_ask'),
        Index('idx_symbol_timestamp', 'symbol', 'timestamp'),
        Index('idx_timestamp', 'timestamp'),
        # Уникальность по символу и времени для предотвращения дублей
        Index('idx_unique_symbol_time', 'symbol', 'timestamp', unique=True),
    )


class NewsArticle(Base):
    """Российские финансовые новости"""
    __tablename__ = 'news_articles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(Text, nullable=False, comment='Заголовок новости')
    content = Column(Text, nullable=False, comment='Содержание новости')
    source = Column(String(100), nullable=False, comment='Источник (РБК, Ведомости и т.д.)')
    url = Column(String(500), comment='URL новости')
    timestamp = Column(DateTime(timezone=True), nullable=False, comment='Время публикации в MSK')
    language = Column(String(2), default='ru', comment='Язык новости')
    sentiment_score = Column(Numeric(3, 2), comment='Оценка настроения (-1 до 1)')
    mentioned_stocks = Column(JSON, comment='Упомянутые акции')
    processed = Column(Boolean, default=False, comment='Обработана ли новость')
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(MSK))
    
    __table_args__ = (
        CheckConstraint('sentiment_score >= -1 AND sentiment_score <= 1', name='valid_sentiment'),
        Index('idx_source_timestamp', 'source', 'timestamp'),
        Index('idx_timestamp_processed', 'timestamp', 'processed'),
        Index('idx_sentiment', 'sentiment_score'),
        # Уникальность по URL для предотвращения дублей
        Index('idx_unique_url', 'url', unique=True),
    )


class Trade(Base):
    """Сделки на российском рынке"""
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), ForeignKey('russian_stocks.symbol'), nullable=False)
    action = Column(String(10), nullable=False, comment='BUY, SELL, HOLD')
    quantity = Column(Integer, nullable=False, comment='Количество акций')
    price = Column(Numeric(15, 4), nullable=False, comment='Цена исполнения в рублях')
    timestamp = Column(DateTime(timezone=True), nullable=False, comment='Время сделки в MSK')
    reasoning = Column(Text, comment='Обоснование решения на русском языке')
    status = Column(String(20), default='PENDING', comment='PENDING, EXECUTED, CANCELLED, FAILED')
    order_id = Column(String(100), comment='ID ордера у брокера')
    commission = Column(Numeric(10, 4), comment='Комиссия брокера')
    total_amount = Column(Numeric(15, 4), comment='Общая сумма сделки')
    
    # Связи
    stock = relationship("RussianStock", back_populates="trades")
    
    __table_args__ = (
        CheckConstraint("action IN ('BUY', 'SELL', 'HOLD')", name='valid_action'),
        CheckConstraint('quantity > 0', name='positive_quantity'),
        CheckConstraint('price > 0', name='positive_price'),
        CheckConstraint("status IN ('PENDING', 'EXECUTED', 'CANCELLED', 'FAILED')", name='valid_status'),
        Index('idx_trades_symbol_timestamp', 'symbol', 'timestamp'),
        Index('idx_status', 'status'),
        Index('idx_action', 'action'),
    )


class Portfolio(Base):
    """Портфель российских акций"""
    __tablename__ = 'portfolio'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(10), ForeignKey('russian_stocks.symbol'), nullable=False)
    quantity = Column(Integer, nullable=False, comment='Количество акций в портфеле')
    average_price = Column(Numeric(15, 4), nullable=False, comment='Средняя цена покупки')
    current_price = Column(Numeric(15, 4), comment='Текущая рыночная цена')
    unrealized_pnl = Column(Numeric(15, 4), comment='Нереализованная прибыль/убыток')
    realized_pnl = Column(Numeric(15, 4), default=0, comment='Реализованная прибыль/убыток')
    last_updated = Column(DateTime(timezone=True), default=lambda: datetime.now(MSK))
    
    # Связи
    stock = relationship("RussianStock")
    
    __table_args__ = (
        CheckConstraint('quantity >= 0', name='non_negative_quantity'),
        CheckConstraint('average_price > 0', name='positive_avg_price'),
        Index('idx_symbol_unique', 'symbol', unique=True),
    )


class DataRetentionPolicy(Base):
    """Политики хранения данных для соответствия российскому законодательству"""
    __tablename__ = 'data_retention_policies'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(100), nullable=False, comment='Название таблицы')
    retention_days = Column(Integer, nullable=False, comment='Дни хранения')
    description = Column(Text, comment='Описание политики')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(MSK))
    
    __table_args__ = (
        CheckConstraint('retention_days > 0', name='positive_retention'),
        Index('idx_table_active', 'table_name', 'is_active'),
    )