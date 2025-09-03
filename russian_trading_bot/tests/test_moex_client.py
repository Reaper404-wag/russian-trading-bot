"""
Unit tests for MOEX API client
Тесты для клиента MOEX API
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from decimal import Decimal
import aiohttp

from russian_trading_bot.services.moex_client import (
    MOEXClient, MOEXAPIError, MOEXRateLimitError, MOEXConnectionError,
    RateLimiter, create_moex_client, format_moex_error
)
from russian_trading_bot.models.market_data import (
    MarketData, RussianStock, MOEXOrderBook, MOEXTrade, MOSCOW_TZ
)


class TestRateLimiter:
    """Тесты для ограничителя скорости запросов"""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_allows_requests_within_limit(self):
        """Тест: ограничитель пропускает запросы в пределах лимита"""
        limiter = RateLimiter(max_requests=5, time_window=60)
        
        # Должны пройти 5 запросов без задержки
        for _ in range(5):
            await limiter.acquire()
        
        assert len(limiter.requests) == 5
    
    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_excess_requests(self):
        """Тест: ограничитель блокирует избыточные запросы"""
        limiter = RateLimiter(max_requests=2, time_window=1)
        
        # Первые 2 запроса проходят
        await limiter.acquire()
        await limiter.acquire()
        
        # Третий запрос должен заблокироваться
        start_time = asyncio.get_event_loop().time()
        await limiter.acquire()
        end_time = asyncio.get_event_loop().time()
        
        # Должна быть задержка
        assert end_time - start_time >= 0.9  # Почти 1 секунда


class TestMOEXClient:
    """Тесты для MOEX клиента"""
    
    @pytest.fixture
    def client(self):
        """Фикстура для создания клиента"""
        return MOEXClient(api_key="test_key", max_requests_per_minute=100)
    
    @pytest.fixture
    def mock_session(self):
        """Мок HTTP сессии"""
        session = AsyncMock()
        response = AsyncMock()
        response.status = 200
        response.json = AsyncMock(return_value={
            'securities': {
                'columns': ['SECID', 'LAST', 'VOLTODAY', 'BID', 'OFFER', 'PREVPRICE'],
                'data': [['SBER', 250.5, 1000000, 250.0, 251.0, 248.0]]
            }
        })
        session.get.return_value.__aenter__.return_value = response
        return session
    
    @pytest.mark.asyncio
    async def test_client_initialization(self, client):
        """Тест: инициализация клиента"""
        assert client.api_key == "test_key"
        assert client.timeout == 30
        assert client.max_retries == 3
        assert isinstance(client.rate_limiter, RateLimiter)
    
    @pytest.mark.asyncio
    async def test_ensure_session_creates_session(self, client):
        """Тест: создание HTTP сессии"""
        await client._ensure_session()
        
        assert client.session is not None
        assert isinstance(client.session, aiohttp.ClientSession)
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_cache_functionality(self, client):
        """Тест: функциональность кэширования"""
        cache_key = "test_key"
        test_data = {"test": "data"}
        
        # Устанавливаем данные в кэш
        client._set_cache(cache_key, test_data, ttl=10)
        
        # Проверяем, что данные есть в кэше
        cached_data = client._get_cache(cache_key)
        assert cached_data == test_data
        
        # Проверяем валидность кэша
        assert client._is_cache_valid(cache_key)
    
    @pytest.mark.asyncio
    async def test_get_stock_data_success(self, client, mock_session):
        """Тест: успешное получение данных акции"""
        client.session = mock_session
        
        result = await client.get_stock_data("SBER")
        
        assert result is not None
        assert isinstance(result, MarketData)
        assert result.symbol == "SBER"
        assert result.price == Decimal('250.5')
        assert result.volume == 1000000
        assert result.bid == Decimal('250.0')
        assert result.ask == Decimal('251.0')
        assert result.currency == "RUB"
    
    @pytest.mark.asyncio
    async def test_get_stock_data_invalid_ticker(self, client):
        """Тест: неверный тикер"""
        with pytest.raises(ValueError, match="Неверный формат тикера MOEX"):
            await client.get_stock_data("INVALID_TICKER_123")
    
    @pytest.mark.asyncio
    async def test_get_stock_data_not_found(self, client):
        """Тест: акция не найдена"""
        mock_session = AsyncMock()
        response = AsyncMock()
        response.status = 200
        response.json = AsyncMock(return_value={'securities': {'data': []}})
        mock_session.get.return_value.__aenter__.return_value = response
        client.session = mock_session
        
        result = await client.get_stock_data("XXXX")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_multiple_stocks_data(self, client):
        """Тест: получение данных нескольких акций"""
        mock_session = AsyncMock()
        response = AsyncMock()
        response.status = 200
        response.json = AsyncMock(return_value={
            'securities': {
                'columns': ['SECID', 'LAST', 'VOLTODAY', 'BID', 'OFFER', 'PREVPRICE'],
                'data': [
                    ['SBER', 250.5, 1000000, 250.0, 251.0, 248.0],
                    ['GAZP', 180.2, 500000, 179.8, 180.5, 179.0]
                ]
            }
        })
        mock_session.get.return_value.__aenter__.return_value = response
        client.session = mock_session
        
        result = await client.get_multiple_stocks_data(["SBER", "GAZP"])
        
        assert len(result) == 2
        assert "SBER" in result
        assert "GAZP" in result
        assert result["SBER"].price == Decimal('250.5')
        assert result["GAZP"].price == Decimal('180.2')
    
    @pytest.mark.asyncio
    async def test_get_historical_data(self, client):
        """Тест: получение исторических данных"""
        mock_session = AsyncMock()
        response = AsyncMock()
        response.status = 200
        response.json = AsyncMock(return_value={
            'history': {
                'columns': ['TRADEDATE', 'CLOSE', 'VOLUME', 'OPEN', 'HIGH', 'LOW'],
                'data': [
                    ['2024-01-15', 250.5, 1000000, 248.0, 252.0, 247.0],
                    ['2024-01-16', 251.0, 1200000, 250.5, 253.0, 249.5]
                ]
            }
        })
        mock_session.get.return_value.__aenter__.return_value = response
        client.session = mock_session
        
        start_date = datetime(2024, 1, 15)
        end_date = datetime(2024, 1, 16)
        
        result = await client.get_historical_data("SBER", start_date, end_date)
        
        assert len(result) == 2
        assert all(isinstance(item, MarketData) for item in result)
        assert result[0].symbol == "SBER"
        assert result[0].price == Decimal('250.5')
    
    @pytest.mark.asyncio
    async def test_get_stock_info(self, client):
        """Тест: получение информации об акции"""
        mock_session = AsyncMock()
        response = AsyncMock()
        response.status = 200
        response.json = AsyncMock(return_value={
            'description': {
                'columns': ['name', 'value'],
                'data': [
                    ['NAME', 'Сбербанк России ПАО ао'],
                    ['SHORTNAME', 'Сбербанк'],
                    ['SECTNAME', 'Банки'],
                    ['LOTSIZE', '10'],
                    ['ISIN', 'RU0009029540']
                ]
            }
        })
        mock_session.get.return_value.__aenter__.return_value = response
        client.session = mock_session
        
        result = await client.get_stock_info("SBER")
        
        assert result is not None
        assert isinstance(result, RussianStock)
        assert result.symbol == "SBER"
        assert result.name == "Сбербанк России ПАО ао"
        assert result.sector == "BANKING"
        assert result.lot_size == 10
        assert result.isin == "RU0009029540"
    
    @pytest.mark.asyncio
    async def test_search_stocks(self, client):
        """Тест: поиск акций"""
        mock_session = AsyncMock()
        response = AsyncMock()
        response.status = 200
        response.json = AsyncMock(return_value={
            'securities': {
                'columns': ['SECID', 'SHORTNAME'],
                'data': [
                    ['SBER', 'Сбербанк'],
                    ['SBERP', 'Сбербанк-п']
                ]
            }
        })
        mock_session.get.return_value.__aenter__.return_value = response
        client.session = mock_session
        
        # Мокаем get_stock_info для каждого найденного тикера
        with patch.object(client, 'get_stock_info') as mock_get_info:
            mock_get_info.side_effect = [
                RussianStock("SBER", "Сбербанк", "BANKING"),
                RussianStock("SBERP", "Сбербанк-п", "BANKING")
            ]
            
            result = await client.search_stocks("SBER")
            
            assert len(result) == 2
            assert all(isinstance(stock, RussianStock) for stock in result)
            assert result[0].symbol == "SBER"
    
    @pytest.mark.asyncio
    async def test_get_market_status(self, client):
        """Тест: получение статуса рынка"""
        mock_session = AsyncMock()
        response = AsyncMock()
        response.status = 200
        response.json = AsyncMock(return_value={})
        mock_session.get.return_value.__aenter__.return_value = response
        client.session = mock_session
        
        result = await client.get_market_status()
        
        assert isinstance(result, dict)
        assert "is_open" in result
        assert "market_phase" in result
        assert "timezone" in result
        assert result["timezone"] == "Europe/Moscow"
    
    @pytest.mark.asyncio
    async def test_get_order_book(self, client):
        """Тест: получение стакана заявок"""
        mock_session = AsyncMock()
        response = AsyncMock()
        response.status = 200
        response.json = AsyncMock(return_value={
            'orderbook': {
                'columns': ['PRICE', 'BUYQUANTITY', 'SELLQUANTITY'],
                'data': [
                    [250.0, 1000, 0],
                    [250.5, 0, 500],
                    [251.0, 0, 800]
                ]
            }
        })
        mock_session.get.return_value.__aenter__.return_value = response
        client.session = mock_session
        
        result = await client.get_order_book("SBER")
        
        assert result is not None
        assert isinstance(result, MOEXOrderBook)
        assert result.symbol == "SBER"
        assert len(result.bids) == 1
        assert len(result.asks) == 2
        assert result.bids[0] == (Decimal('250.0'), 1000)
    
    @pytest.mark.asyncio
    async def test_get_trades(self, client):
        """Тест: получение сделок"""
        mock_session = AsyncMock()
        response = AsyncMock()
        response.status = 200
        response.json = AsyncMock(return_value={
            'trades': {
                'columns': ['TRADETIME', 'PRICE', 'QUANTITY', 'TRADENO'],
                'data': [
                    ['10:30:15', 250.5, 100, '12345'],
                    ['10:31:20', 250.6, 200, '12346']
                ]
            }
        })
        mock_session.get.return_value.__aenter__.return_value = response
        client.session = mock_session
        
        result = await client.get_trades("SBER")
        
        assert len(result) == 2
        assert all(isinstance(trade, MOEXTrade) for trade in result)
        assert result[0].symbol == "SBER"
        assert result[0].price == Decimal('250.6')  # Сортировка по времени (убывание)
        assert result[0].volume == 200
    
    @pytest.mark.asyncio
    async def test_api_error_handling(self, client):
        """Тест: обработка ошибок API"""
        mock_session = AsyncMock()
        response = AsyncMock()
        response.status = 500
        response.text = AsyncMock(return_value="Internal Server Error")
        mock_session.get.return_value.__aenter__.return_value = response
        client.session = mock_session
        
        with pytest.raises(MOEXConnectionError):
            await client.get_stock_data("SBER")
    
    @pytest.mark.asyncio
    async def test_rate_limit_error_handling(self, client):
        """Тест: обработка ошибки превышения лимита"""
        mock_session = AsyncMock()
        response = AsyncMock()
        response.status = 429
        response.headers = {'Retry-After': '1'}
        mock_session.get.return_value.__aenter__.return_value = response
        client.session = mock_session
        
        # Мокаем второй запрос как успешный
        success_response = AsyncMock()
        success_response.status = 200
        success_response.json = AsyncMock(return_value={
            'securities': {
                'columns': ['SECID', 'LAST', 'VOLTODAY'],
                'data': [['SBER', 250.5, 1000000]]
            }
        })
        
        mock_session.get.side_effect = [
            mock_session.get.return_value,  # Первый запрос - 429
            success_response.__aenter__()   # Второй запрос - успех
        ]
        
        result = await client.get_stock_data("SBER")
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_connection_error_handling(self, client):
        """Тест: обработка ошибок соединения"""
        mock_session = AsyncMock()
        mock_session.get.side_effect = aiohttp.ClientError("Connection failed")
        client.session = mock_session
        
        with pytest.raises(MOEXConnectionError):
            await client.get_stock_data("SBER")


class TestHelperFunctions:
    """Тесты для вспомогательных функций"""
    
    @pytest.mark.asyncio
    async def test_create_moex_client(self):
        """Тест: создание MOEX клиента"""
        client = await create_moex_client("test_key")
        
        assert isinstance(client, MOEXClient)
        assert client.api_key == "test_key"
        assert client.session is not None
        
        await client.close()
    
    def test_format_moex_error(self):
        """Тест: форматирование ошибок"""
        # Тест ошибки лимита запросов
        rate_limit_error = MOEXRateLimitError("Rate limit exceeded")
        formatted = format_moex_error(rate_limit_error)
        assert "лимит запросов" in formatted.lower()
        
        # Тест ошибки соединения
        connection_error = MOEXConnectionError("Connection failed")
        formatted = format_moex_error(connection_error)
        assert "соединения" in formatted.lower()
        
        # Тест общей ошибки API
        api_error = MOEXAPIError("API error")
        formatted = format_moex_error(api_error)
        assert "API error" in formatted
        
        # Тест неизвестной ошибки
        unknown_error = ValueError("Unknown error")
        formatted = format_moex_error(unknown_error)
        assert "неизвестная ошибка" in formatted.lower()


@pytest.mark.integration
class TestMOEXClientIntegration:
    """Интеграционные тесты (требуют подключения к интернету)"""
    
    @pytest.mark.asyncio
    async def test_real_api_call(self):
        """Тест: реальный вызов API (только если есть подключение)"""
        try:
            async with MOEXClient() as client:
                # Пробуем получить данные по Сбербанку
                result = await client.get_stock_data("SBER")
                
                if result:  # Если рынок открыт и данные доступны
                    assert isinstance(result, MarketData)
                    assert result.symbol == "SBER"
                    assert result.currency == "RUB"
                    assert result.price > 0
        except (MOEXConnectionError, MOEXAPIError):
            # Пропускаем тест если нет подключения или API недоступен
            pytest.skip("MOEX API недоступен")


if __name__ == "__main__":
    # Запуск тестов
    pytest.main([__file__, "-v"])