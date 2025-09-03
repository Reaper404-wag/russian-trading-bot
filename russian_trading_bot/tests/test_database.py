"""
Тесты для слоя хранения данных российского торгового бота
Tests for Russian trading bot data storage layer
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from decimal import Decimal
import pytz

from russian_trading_bot.database.data_access import RussianMarketDataAccess
from russian_trading_bot.database.migrations import DatabaseMigrations
from russian_trading_bot.database.schema import MSK

# Используем SQLite для тестов
TEST_DATABASE_URL = "sqlite:///test_russian_trading.db"

@pytest.fixture
def data_access():
    """Фикстура для создания тестового доступа к данным"""
    # Используем in-memory SQLite для тестов
    test_db_url = "sqlite:///:memory:"
    
    da = RussianMarketDataAccess(test_db_url)
    da.create_tables()
    
    # Настройка миграций
    migrations = DatabaseMigrations(da)
    migrations.setup_initial_data()
    
    yield da

class TestRussianStocks:
    """Тесты для работы с российскими акциями"""
    
    def test_add_russian_stock(self, data_access):
        """Тест добавления российской акции"""
        result = data_access.add_russian_stock("TEST", "Тестовая компания", "IT", 10)
        assert result == True
        
        # Проверяем, что акция добавлена
        stocks = data_access.get_active_russian_stocks()
        test_stock = next((s for s in stocks if s.symbol == "TEST"), None)
        assert test_stock is not None
        assert test_stock.name == "Тестовая компания"
        assert test_stock.sector == "IT"
        assert test_stock.lot_size == 10
    
    def test_duplicate_stock_prevention(self, data_access):
        """Тест предотвращения дублирования акций"""
        # Добавляем новую акцию первый раз
        result1 = data_access.add_russian_stock("TESTDUP", "Тест дубликат", "IT", 10)
        assert result1 == True
        
        # Пытаемся добавить ту же акцию снова
        result2 = data_access.add_russian_stock("TESTDUP", "Тест дубликат 2", "IT", 20)
        assert result2 == False
    
    def test_get_stocks_by_sector(self, data_access):
        """Тест получения акций по сектору"""
        # Добавляем акции разных секторов
        data_access.add_russian_stock("BANK1", "Банк 1", "Банки", 10)
        data_access.add_russian_stock("BANK2", "Банк 2", "Банки", 10)
        data_access.add_russian_stock("OIL1", "Нефтяная 1", "Нефть и газ", 1)
        
        # Получаем банки
        bank_stocks = data_access.get_russian_stocks_by_sector("Банки")
        assert len(bank_stocks) >= 2
        
        bank_symbols = [s.symbol for s in bank_stocks]
        assert "BANK1" in bank_symbols
        assert "BANK2" in bank_symbols

class TestMarketData:
    """Тесты для работы с рыночными данными MOEX"""
    
    def test_add_market_data(self, data_access):
        """Тест добавления рыночных данных"""
        # Сначала добавляем акцию
        data_access.add_russian_stock("GAZP", "Газпром", "Нефть и газ", 10)
        
        # Добавляем рыночные данные
        timestamp = datetime.now(MSK)
        result = data_access.add_market_data(
            symbol="GAZP",
            timestamp=timestamp,
            price=Decimal("150.50"),
            volume=1000000,
            bid=Decimal("150.40"),
            ask=Decimal("150.60")
        )
        assert result == True
        
        # Проверяем данные
        latest_data = data_access.get_latest_market_data("GAZP")
        assert latest_data is not None
        assert latest_data.symbol == "GAZP"
        assert latest_data.price == Decimal("150.50")
        assert latest_data.volume == 1000000
    
    def test_market_data_range(self, data_access):
        """Тест получения рыночных данных за период"""
        # Добавляем акцию
        data_access.add_russian_stock("SBER", "Сбербанк", "Банки", 10)
        
        # Добавляем данные за несколько дней
        base_time = datetime.now(MSK)
        for i in range(5):
            timestamp = base_time - timedelta(days=i)
            data_access.add_market_data(
                symbol="SBER",
                timestamp=timestamp,
                price=Decimal(f"{200 + i}.00"),
                volume=100000 * (i + 1)
            )
        
        # Получаем данные за последние 3 дня
        start_date = base_time - timedelta(days=2)
        end_date = base_time + timedelta(days=1)
        
        data_range = data_access.get_market_data_range("SBER", start_date, end_date)
        assert len(data_range) == 3
    
    def test_moex_trading_hours(self, data_access):
        """Тест фильтрации данных по часам торгов MOEX"""
        # Добавляем акцию
        data_access.add_russian_stock("LKOH", "ЛУКОЙЛ", "Нефть и газ", 1)
        
        # Добавляем данные в разное время
        base_date = datetime.now(MSK).date()
        
        # Данные до открытия рынка (9:00)
        early_time = MSK.localize(datetime.combine(base_date, datetime.min.time().replace(hour=9)))
        data_access.add_market_data("LKOH", early_time, Decimal("100.00"), 1000)
        
        # Данные во время торгов (12:00)
        trading_time = MSK.localize(datetime.combine(base_date, datetime.min.time().replace(hour=12)))
        data_access.add_market_data("LKOH", trading_time, Decimal("101.00"), 2000)
        
        # Данные после закрытия (20:00)
        late_time = MSK.localize(datetime.combine(base_date, datetime.min.time().replace(hour=20)))
        data_access.add_market_data("LKOH", late_time, Decimal("102.00"), 3000)
        
        # Получаем только данные торгового времени
        trading_data = data_access.get_moex_trading_hours_data("LKOH", base_date)
        assert len(trading_data) == 1
        assert trading_data[0].price == Decimal("101.00")

class TestNewsArticles:
    """Тесты для работы с российскими новостями"""
    
    def test_add_news_article(self, data_access):
        """Тест добавления новостной статьи"""
        timestamp = datetime.now(MSK)
        result = data_access.add_news_article(
            title="Сбербанк показал рекордную прибыль",
            content="Сбербанк объявил о рекордной прибыли за квартал...",
            source="РБК",
            timestamp=timestamp,
            url="https://rbc.ru/test",
            sentiment_score=Decimal("0.8"),
            mentioned_stocks=["SBER"]
        )
        assert result == True
    
    def test_get_news_by_source(self, data_access):
        """Тест получения новостей по источнику"""
        timestamp = datetime.now(MSK)
        
        # Добавляем новости от разных источников
        data_access.add_news_article(
            "Новость РБК", "Содержание", "РБК", timestamp, 
            url="https://rbc.ru/1"
        )
        data_access.add_news_article(
            "Новость Ведомостей", "Содержание", "Ведомости", timestamp,
            url="https://vedomosti.ru/1"
        )
        
        # Получаем новости РБК
        rbc_news = data_access.get_news_by_russian_source("РБК")
        assert len(rbc_news) >= 1
        assert rbc_news[0].source == "РБК"
    
    def test_news_mentioning_stock(self, data_access):
        """Тест получения новостей, упоминающих акцию"""
        timestamp = datetime.now(MSK)
        
        # Добавляем новости с упоминанием акций
        data_access.add_news_article(
            "Газпром увеличил дивиденды", "Содержание", "РБК", timestamp,
            url="https://rbc.ru/gazp", mentioned_stocks=["GAZP"]
        )
        data_access.add_news_article(
            "Сбербанк и Газпром", "Содержание", "Ведомости", timestamp,
            url="https://vedomosti.ru/both", mentioned_stocks=["SBER", "GAZP"]
        )
        
        # Получаем новости о Газпроме
        gazp_news = data_access.get_news_mentioning_stock("GAZP")
        assert len(gazp_news) >= 2
    
    def test_sentiment_analysis(self, data_access):
        """Тест анализа настроений для акции"""
        timestamp = datetime.now(MSK)
        
        # Добавляем новости с разными настроениями
        data_access.add_news_article(
            "Позитивная новость", "Содержание", "РБК", timestamp,
            url="https://rbc.ru/pos", sentiment_score=Decimal("0.8"),
            mentioned_stocks=["SBER"]
        )
        data_access.add_news_article(
            "Негативная новость", "Содержание", "РБК", timestamp - timedelta(hours=1),
            url="https://rbc.ru/neg", sentiment_score=Decimal("-0.6"),
            mentioned_stocks=["SBER"]
        )
        
        # Анализируем настроения
        sentiment = data_access.get_sentiment_analysis_for_stock("SBER")
        assert sentiment['symbol'] == "SBER"
        assert sentiment['news_count'] == 2
        assert abs(sentiment['average_sentiment'] - 0.1) < 0.001  # (0.8 + (-0.6)) / 2 с погрешностью

class TestTrades:
    """Тесты для работы со сделками"""
    
    def test_add_trade(self, data_access):
        """Тест добавления сделки"""
        # Добавляем акцию
        data_access.add_russian_stock("NVTK", "НОВАТЭК", "Нефть и газ", 10)
        
        # Добавляем сделку
        trade_id = data_access.add_trade(
            symbol="NVTK",
            action="BUY",
            quantity=100,
            price=Decimal("1500.00"),
            reasoning="Покупка на основе технического анализа",
            order_id="ORDER123"
        )
        assert trade_id > 0
        
        # Проверяем сделку
        trades = data_access.get_trades_by_symbol("NVTK")
        assert len(trades) >= 1
        assert trades[0].action == "BUY"
        assert trades[0].quantity == 100
        assert trades[0].total_amount == Decimal("150000.00")
    
    def test_trading_performance(self, data_access):
        """Тест анализа торговой производительности"""
        # Добавляем акцию
        data_access.add_russian_stock("MTSS", "МТС", "Телекоммуникации", 10)
        
        # Добавляем несколько сделок
        data_access.add_trade("MTSS", "BUY", 100, Decimal("300.00"), "Покупка")
        data_access.add_trade("MTSS", "SELL", 50, Decimal("320.00"), "Продажа части")
        
        # Обновляем статус сделок на выполненные
        with data_access.get_session() as session:
            from russian_trading_bot.database.schema import Trade
            session.query(Trade).filter(Trade.symbol == "MTSS").update({"status": "EXECUTED"})
            session.commit()
        
        # Анализируем производительность
        performance = data_access.get_trading_performance("MTSS")
        assert performance['symbol'] == "MTSS"
        assert performance['total_trades'] == 2
        assert performance['buy_trades'] == 1
        assert performance['sell_trades'] == 1

class TestPortfolio:
    """Тесты для работы с портфелем"""
    
    def test_update_portfolio_position(self, data_access):
        """Тест обновления позиции в портфеле"""
        # Добавляем акцию
        data_access.add_russian_stock("ALRS", "АЛРОСА", "Металлургия", 10)
        
        # Обновляем позицию
        result = data_access.update_portfolio_position(
            symbol="ALRS",
            quantity=500,
            average_price=Decimal("120.50")
        )
        assert result == True
        
        # Проверяем позицию
        positions = data_access.get_portfolio_positions()
        alrs_position = next((p for p in positions if p.symbol == "ALRS"), None)
        assert alrs_position is not None
        assert alrs_position.quantity == 500
        assert alrs_position.average_price == Decimal("120.50")

class TestDataRetention:
    """Тесты для политик хранения данных"""
    
    def test_setup_retention_policies(self, data_access):
        """Тест настройки политик хранения"""
        data_access.setup_retention_policies()
        
        # Проверяем, что политики созданы
        with data_access.get_session() as session:
            from russian_trading_bot.database.schema import DataRetentionPolicy
            policies = session.query(DataRetentionPolicy).all()
            assert len(policies) >= 4
            
            # Проверяем конкретные политики
            policy_names = [p.table_name for p in policies]
            assert 'market_data' in policy_names
            assert 'trades' in policy_names
            assert 'news_articles' in policy_names
    
    def test_database_statistics(self, data_access):
        """Тест получения статистики базы данных"""
        # Добавляем тестовые данные
        data_access.add_russian_stock("STAT", "Статистика", "IT", 1)
        
        # Получаем статистику
        stats = data_access.get_database_statistics()
        assert 'stocks_count' in stats
        assert 'active_stocks' in stats
        assert 'market_data_count' in stats
        assert stats['stocks_count'] > 0

class TestDatabaseMigrations:
    """Тесты для миграций базы данных"""
    
    def test_migration_status(self, data_access):
        """Тест получения статуса миграций"""
        migrations = DatabaseMigrations(data_access)
        status = migrations.get_migration_status()
        
        assert 'tables' in status
        assert 'migration_date' in status
        assert status['tables']['russian_stocks'] == True
        assert status['tables']['market_data'] == True

if __name__ == "__main__":
    # Запуск тестов
    pytest.main([__file__, "-v"])