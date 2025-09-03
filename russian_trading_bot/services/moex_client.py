"""
MOEX API client for real-time Russian stock market data
Клиент для работы с API Московской биржи
"""

import asyncio
import aiohttp
import logging
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import json
import time
from dataclasses import asdict

from russian_trading_bot.models.market_data import (
    MarketData, RussianStock, MOEXMarketData, MOEXOrderBook, 
    MOEXTrade, MarketStatus, MOEXTradingSession, TechnicalIndicators,
    validate_moex_ticker, MOSCOW_TZ
)
from russian_trading_bot.api.moex_interface import MOEXDataInterface


logger = logging.getLogger(__name__)


class MOEXAPIError(Exception):
    """Исключение для ошибок MOEX API"""
    pass


class MOEXRateLimitError(MOEXAPIError):
    """Исключение для превышения лимита запросов"""
    pass


class MOEXConnectionError(MOEXAPIError):
    """Исключение для ошибок соединения с MOEX"""
    pass


class RateLimiter:
    """Ограничитель скорости запросов к MOEX API"""
    
    def __init__(self, max_requests: int = 60, time_window: int = 60):
        """
        Args:
            max_requests: Максимальное количество запросов
            time_window: Временное окно в секундах
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
        self._lock = asyncio.Lock()
    
    async def acquire(self):
        """Получить разрешение на выполнение запроса"""
        async with self._lock:
            now = time.time()
            # Удаляем старые запросы
            self.requests = [req_time for req_time in self.requests 
                           if now - req_time < self.time_window]
            
            if len(self.requests) >= self.max_requests:
                sleep_time = self.time_window - (now - self.requests[0])
                if sleep_time > 0:
                    logger.warning(f"Превышен лимит запросов к MOEX API. Ожидание {sleep_time:.2f} сек")
                    await asyncio.sleep(sleep_time)
                    return await self.acquire()
            
            self.requests.append(now)


class MOEXClient(MOEXDataInterface):
    """Клиент для работы с MOEX API"""
    
    BASE_URL = "https://iss.moex.com"
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 max_requests_per_minute: int = 60,
                 timeout: int = 30,
                 max_retries: int = 3):
        """
        Инициализация MOEX клиента
        
        Args:
            api_key: API ключ (если требуется)
            max_requests_per_minute: Максимум запросов в минуту
            timeout: Таймаут запроса в секундах
            max_retries: Максимальное количество повторных попыток
        """
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limiter = RateLimiter(max_requests_per_minute, 60)
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Кэш для данных
        self._cache = {}
        self._cache_ttl = {}
        self._default_cache_duration = 5  # секунд
    
    async def __aenter__(self):
        """Асинхронный контекстный менеджер - вход"""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Асинхронный контекстный менеджер - выход"""
        await self.close()
    
    async def _ensure_session(self):
        """Создать HTTP сессию если её нет"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            headers = {
                'User-Agent': 'Russian-Trading-Bot/1.0',
                'Accept': 'application/json'
            }
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers=headers
            )
    
    async def close(self):
        """Закрыть HTTP сессию"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def _get_cache_key(self, endpoint: str, params: Dict[str, Any]) -> str:
        """Создать ключ кэша"""
        params_str = json.dumps(params, sort_keys=True)
        return f"{endpoint}:{params_str}"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Проверить валидность кэша"""
        if cache_key not in self._cache_ttl:
            return False
        return time.time() < self._cache_ttl[cache_key]
    
    def _set_cache(self, cache_key: str, data: Any, ttl: Optional[int] = None):
        """Установить данные в кэш"""
        if ttl is None:
            ttl = self._default_cache_duration
        
        self._cache[cache_key] = data
        self._cache_ttl[cache_key] = time.time() + ttl
    
    def _get_cache(self, cache_key: str) -> Optional[Any]:
        """Получить данные из кэша"""
        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]
        return None
    
    async def _make_request(self, 
                          endpoint: str, 
                          params: Optional[Dict[str, Any]] = None,
                          use_cache: bool = True,
                          cache_ttl: Optional[int] = None) -> Dict[str, Any]:
        """
        Выполнить HTTP запрос к MOEX API
        
        Args:
            endpoint: Конечная точка API
            params: Параметры запроса
            use_cache: Использовать кэширование
            cache_ttl: Время жизни кэша в секундах
            
        Returns:
            Ответ API в виде словаря
            
        Raises:
            MOEXAPIError: При ошибке API
            MOEXRateLimitError: При превышении лимита запросов
            MOEXConnectionError: При ошибке соединения
        """
        if params is None:
            params = {}
        
        # Проверяем кэш
        cache_key = self._get_cache_key(endpoint, params)
        if use_cache:
            cached_data = self._get_cache(cache_key)
            if cached_data is not None:
                return cached_data
        
        # Ограничение скорости запросов
        await self.rate_limiter.acquire()
        
        await self._ensure_session()
        
        url = f"{self.BASE_URL}{endpoint}"
        
        # Добавляем формат JSON
        params['iss.json'] = 'extended'
        params['iss.meta'] = 'off'
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"MOEX API запрос: {url} с параметрами {params}")
                
                async with self.session.get(url, params=params) as response:
                    if response.status == 429:
                        # Слишком много запросов
                        retry_after = int(response.headers.get('Retry-After', 60))
                        logger.warning(f"MOEX API rate limit. Ожидание {retry_after} сек")
                        await asyncio.sleep(retry_after)
                        continue
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        # Сохраняем в кэш
                        if use_cache:
                            self._set_cache(cache_key, data, cache_ttl)
                        
                        return data
                    
                    elif response.status >= 500:
                        # Серверная ошибка - повторяем
                        if attempt < self.max_retries:
                            wait_time = 2 ** attempt
                            logger.warning(f"Серверная ошибка MOEX API {response.status}. "
                                         f"Повтор через {wait_time} сек")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            raise MOEXConnectionError(f"Серверная ошибка MOEX API: {response.status}")
                    
                    else:
                        # Клиентская ошибка
                        error_text = await response.text()
                        raise MOEXAPIError(f"Ошибка MOEX API {response.status}: {error_text}")
            
            except aiohttp.ClientError as e:
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt
                    logger.warning(f"Ошибка соединения с MOEX API: {e}. "
                                 f"Повтор через {wait_time} сек")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    raise MOEXConnectionError(f"Не удалось подключиться к MOEX API: {e}")
        
        raise MOEXConnectionError("Превышено максимальное количество попыток подключения")    

    async def get_stock_data(self, symbol: str) -> Optional[MarketData]:
        """
        Получить текущие рыночные данные для российской акции
        
        Args:
            symbol: Тикер MOEX (например, 'SBER', 'GAZP')
            
        Returns:
            Объект MarketData или None если не найдено
        """
        if not validate_moex_ticker(symbol):
            raise ValueError(f"Неверный формат тикера MOEX: {symbol}")
        
        symbol = symbol.upper()
        
        try:
            # Получаем данные с рынка акций
            endpoint = f"/iss/engines/stock/markets/shares/boards/TQBR/securities/{symbol}.json"
            
            data = await self._make_request(endpoint)
            
            if not data or 'securities' not in data:
                logger.warning(f"Нет данных для тикера {symbol}")
                return None
            
            securities_data = data['securities']['data']
            if not securities_data:
                return None
            
            # Парсим данные
            columns = data['securities']['columns']
            row = securities_data[0]
            
            # Создаем словарь из колонок и значений
            security_dict = dict(zip(columns, row))
            
            # Извлекаем необходимые поля
            price = security_dict.get('LAST')
            if price is None:
                price = security_dict.get('PREVPRICE', 0)
            
            volume = security_dict.get('VOLTODAY', 0)
            bid = security_dict.get('BID')
            ask = security_dict.get('OFFER')
            open_price = security_dict.get('OPEN')
            high_price = security_dict.get('HIGH')
            low_price = security_dict.get('LOW')
            prev_close = security_dict.get('PREVPRICE')
            
            # Вычисляем изменение
            change = None
            change_percent = None
            if price and prev_close:
                change = Decimal(str(price)) - Decimal(str(prev_close))
                change_percent = (change / Decimal(str(prev_close))) * 100
            
            return MarketData(
                symbol=symbol,
                timestamp=datetime.now(MOSCOW_TZ),
                price=Decimal(str(price)) if price else Decimal('0'),
                volume=int(volume) if volume else 0,
                bid=Decimal(str(bid)) if bid else None,
                ask=Decimal(str(ask)) if ask else None,
                currency="RUB",
                open_price=Decimal(str(open_price)) if open_price else None,
                high_price=Decimal(str(high_price)) if high_price else None,
                low_price=Decimal(str(low_price)) if low_price else None,
                previous_close=Decimal(str(prev_close)) if prev_close else None,
                change=change,
                change_percent=change_percent
            )
            
        except Exception as e:
            logger.error(f"Ошибка получения данных для {symbol}: {e}")
            raise MOEXAPIError(f"Не удалось получить данные для {symbol}: {e}")
    
    async def get_multiple_stocks_data(self, symbols: List[str]) -> Dict[str, MarketData]:
        """
        Получить рыночные данные для нескольких российских акций
        
        Args:
            symbols: Список тикеров MOEX
            
        Returns:
            Словарь с тикерами в качестве ключей и объектами MarketData в качестве значений
        """
        if not symbols:
            return {}
        
        # Валидируем все тикеры
        valid_symbols = []
        for symbol in symbols:
            if validate_moex_ticker(symbol):
                valid_symbols.append(symbol.upper())
            else:
                logger.warning(f"Пропускаем неверный тикер: {symbol}")
        
        if not valid_symbols:
            return {}
        
        try:
            # Получаем данные для всех акций одним запросом
            symbols_str = ','.join(valid_symbols)
            endpoint = "/iss/engines/stock/markets/shares/boards/TQBR/securities.json"
            params = {'securities': symbols_str}
            
            data = await self._make_request(endpoint, params)
            
            result = {}
            
            if data and 'securities' in data:
                columns = data['securities']['columns']
                
                for row in data['securities']['data']:
                    security_dict = dict(zip(columns, row))
                    symbol = security_dict.get('SECID')
                    
                    if symbol not in valid_symbols:
                        continue
                    
                    # Извлекаем данные аналогично get_stock_data
                    price = security_dict.get('LAST')
                    if price is None:
                        price = security_dict.get('PREVPRICE', 0)
                    
                    volume = security_dict.get('VOLTODAY', 0)
                    bid = security_dict.get('BID')
                    ask = security_dict.get('OFFER')
                    open_price = security_dict.get('OPEN')
                    high_price = security_dict.get('HIGH')
                    low_price = security_dict.get('LOW')
                    prev_close = security_dict.get('PREVPRICE')
                    
                    change = None
                    change_percent = None
                    if price and prev_close:
                        change = Decimal(str(price)) - Decimal(str(prev_close))
                        change_percent = (change / Decimal(str(prev_close))) * 100
                    
                    result[symbol] = MarketData(
                        symbol=symbol,
                        timestamp=datetime.now(MOSCOW_TZ),
                        price=Decimal(str(price)) if price else Decimal('0'),
                        volume=int(volume) if volume else 0,
                        bid=Decimal(str(bid)) if bid else None,
                        ask=Decimal(str(ask)) if ask else None,
                        currency="RUB",
                        open_price=Decimal(str(open_price)) if open_price else None,
                        high_price=Decimal(str(high_price)) if high_price else None,
                        low_price=Decimal(str(low_price)) if low_price else None,
                        previous_close=Decimal(str(prev_close)) if prev_close else None,
                        change=change,
                        change_percent=change_percent
                    )
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка получения данных для множественных тикеров: {e}")
            raise MOEXAPIError(f"Не удалось получить данные для тикеров: {e}")
    
    async def get_historical_data(self, 
                                symbol: str, 
                                start_date: datetime, 
                                end_date: datetime) -> List[MarketData]:
        """
        Получить исторические рыночные данные для российской акции
        
        Args:
            symbol: Тикер MOEX
            start_date: Начальная дата
            end_date: Конечная дата
            
        Returns:
            Список объектов MarketData
        """
        if not validate_moex_ticker(symbol):
            raise ValueError(f"Неверный формат тикера MOEX: {symbol}")
        
        symbol = symbol.upper()
        
        # Форматируем даты
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        try:
            endpoint = f"/iss/history/engines/stock/markets/shares/boards/TQBR/securities/{symbol}.json"
            params = {
                'from': start_str,
                'till': end_str,
                'start': 0
            }
            
            all_data = []
            
            # MOEX API возвращает данные порциями, нужно получить все
            while True:
                data = await self._make_request(endpoint, params, use_cache=False)
                
                if not data or 'history' not in data:
                    break
                
                history_data = data['history']['data']
                if not history_data:
                    break
                
                columns = data['history']['columns']
                
                for row in history_data:
                    row_dict = dict(zip(columns, row))
                    
                    trade_date = row_dict.get('TRADEDATE')
                    if not trade_date:
                        continue
                    
                    # Парсим дату
                    trade_datetime = datetime.strptime(trade_date, '%Y-%m-%d')
                    trade_datetime = MOSCOW_TZ.localize(trade_datetime.replace(hour=18, minute=45))
                    
                    close_price = row_dict.get('CLOSE')
                    if close_price is None:
                        continue
                    
                    volume = row_dict.get('VOLUME', 0)
                    open_price = row_dict.get('OPEN')
                    high_price = row_dict.get('HIGH')
                    low_price = row_dict.get('LOW')
                    
                    all_data.append(MarketData(
                        symbol=symbol,
                        timestamp=trade_datetime,
                        price=Decimal(str(close_price)),
                        volume=int(volume) if volume else 0,
                        currency="RUB",
                        open_price=Decimal(str(open_price)) if open_price else None,
                        high_price=Decimal(str(high_price)) if high_price else None,
                        low_price=Decimal(str(low_price)) if low_price else None
                    ))
                
                # Проверяем, есть ли еще данные
                if len(history_data) < 100:  # MOEX обычно возвращает по 100 записей
                    break
                
                params['start'] += len(history_data)
            
            return sorted(all_data, key=lambda x: x.timestamp)
            
        except Exception as e:
            logger.error(f"Ошибка получения исторических данных для {symbol}: {e}")
            raise MOEXAPIError(f"Не удалось получить исторические данные для {symbol}: {e}")
    
    async def get_stock_info(self, symbol: str) -> Optional[RussianStock]:
        """
        Получить детальную информацию о российской акции
        
        Args:
            symbol: Тикер MOEX
            
        Returns:
            Объект RussianStock или None если не найдено
        """
        if not validate_moex_ticker(symbol):
            raise ValueError(f"Неверный формат тикера MOEX: {symbol}")
        
        symbol = symbol.upper()
        
        try:
            # Получаем информацию о ценной бумаге
            endpoint = f"/iss/securities/{symbol}.json"
            
            data = await self._make_request(endpoint)
            
            if not data or 'description' not in data:
                return None
            
            description_data = data['description']['data']
            if not description_data:
                return None
            
            # Парсим описание
            columns = data['description']['columns']
            info_dict = {}
            
            for row in description_data:
                row_dict = dict(zip(columns, row))
                name = row_dict.get('name')
                value = row_dict.get('value')
                if name and value:
                    info_dict[name] = value
            
            # Извлекаем необходимые поля
            name = info_dict.get('NAME', info_dict.get('SHORTNAME', symbol))
            sector = info_dict.get('SECTNAME', 'UNKNOWN')
            lot_size = int(info_dict.get('LOTSIZE', 1))
            isin = info_dict.get('ISIN')
            face_value = info_dict.get('FACEVALUE')
            
            # Определяем сектор на основе названия
            sector_mapping = {
                'Нефть и газ': 'OIL_GAS',
                'Банки': 'BANKING',
                'Металлургия': 'METALS_MINING',
                'Электроэнергетика': 'UTILITIES',
                'Телекоммуникации': 'TELECOM',
                'Машиностроение': 'INDUSTRIALS',
                'Химия и нефтехимия': 'MATERIALS',
                'Пищевая промышленность': 'CONSUMER_STAPLES',
                'Розничная торговля': 'CONSUMER_DISCRETIONARY',
                'Транспорт': 'INDUSTRIALS',
                'Недвижимость': 'REAL_ESTATE',
                'IT': 'INFORMATION_TECHNOLOGY'
            }
            
            mapped_sector = 'UNKNOWN'
            for rus_sector, eng_sector in sector_mapping.items():
                if rus_sector.lower() in sector.lower():
                    mapped_sector = eng_sector
                    break
            
            return RussianStock(
                symbol=symbol,
                name=name,
                sector=mapped_sector,
                currency="RUB",
                lot_size=lot_size,
                isin=isin,
                market="MOEX",
                trading_status="NORMAL",
                face_value=Decimal(str(face_value)) if face_value else None
            )
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о {symbol}: {e}")
            raise MOEXAPIError(f"Не удалось получить информацию о {symbol}: {e}")    

    async def search_stocks(self, query: str) -> List[RussianStock]:
        """
        Поиск российских акций по названию или символу
        
        Args:
            query: Поисковый запрос (название компании или тикер)
            
        Returns:
            Список подходящих объектов RussianStock
        """
        if not query or len(query.strip()) < 2:
            return []
        
        query = query.strip().upper()
        
        try:
            # Получаем список всех акций на основном рынке
            endpoint = "/iss/engines/stock/markets/shares/boards/TQBR/securities.json"
            
            data = await self._make_request(endpoint, cache_ttl=300)  # Кэшируем на 5 минут
            
            results = []
            
            if data and 'securities' in data:
                columns = data['securities']['columns']
                
                for row in data['securities']['data']:
                    security_dict = dict(zip(columns, row))
                    
                    symbol = security_dict.get('SECID', '')
                    name = security_dict.get('SHORTNAME', '')
                    
                    # Проверяем соответствие запросу
                    if (query in symbol.upper() or 
                        query in name.upper() or
                        symbol.upper().startswith(query)):
                        
                        # Получаем дополнительную информацию
                        try:
                            stock_info = await self.get_stock_info(symbol)
                            if stock_info:
                                results.append(stock_info)
                        except Exception as e:
                            logger.warning(f"Не удалось получить информацию о {symbol}: {e}")
                            # Создаем базовый объект
                            results.append(RussianStock(
                                symbol=symbol,
                                name=name,
                                sector='UNKNOWN',
                                currency="RUB",
                                lot_size=1,
                                market="MOEX"
                            ))
            
            # Сортируем по релевантности
            def relevance_score(stock: RussianStock) -> int:
                score = 0
                if stock.symbol == query:
                    score += 100
                elif stock.symbol.startswith(query):
                    score += 50
                elif query in stock.symbol:
                    score += 25
                
                if query in stock.name.upper():
                    score += 10
                
                return score
            
            results.sort(key=relevance_score, reverse=True)
            return results[:20]  # Возвращаем топ-20 результатов
            
        except Exception as e:
            logger.error(f"Ошибка поиска акций по запросу '{query}': {e}")
            raise MOEXAPIError(f"Не удалось выполнить поиск: {e}")
    
    async def get_market_status(self) -> Dict[str, Any]:
        """
        Получить текущий статус рынка MOEX
        
        Returns:
            Словарь с информацией о статусе рынка
        """
        try:
            # Получаем информацию о торговых сессиях
            endpoint = "/iss/engines/stock/markets/shares/boards/TQBR/sessions.json"
            
            data = await self._make_request(endpoint, use_cache=False)
            
            now = datetime.now(MOSCOW_TZ)
            
            # Определяем статус рынка на основе времени
            market_open_time = now.replace(hour=10, minute=0, second=0, microsecond=0)
            market_close_time = now.replace(hour=18, minute=45, second=0, microsecond=0)
            
            is_weekend = now.weekday() >= 5  # Суббота или воскресенье
            is_trading_hours = market_open_time <= now <= market_close_time and not is_weekend
            
            market_phase = "CLOSED"
            if not is_weekend:
                if now < market_open_time:
                    market_phase = "PREMARKET"
                elif market_open_time <= now <= market_close_time:
                    market_phase = "OPEN"
                elif now > market_close_time:
                    market_phase = "POSTMARKET"
            
            return {
                "is_open": is_trading_hours,
                "market_phase": market_phase,
                "session_start": market_open_time if not is_weekend else None,
                "session_end": market_close_time if not is_weekend else None,
                "timezone": "Europe/Moscow",
                "trading_day": now.date() if not is_weekend else None,
                "is_weekend": is_weekend,
                "current_time": now,
                "next_trading_day": self._get_next_trading_day(now)
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статуса рынка: {e}")
            raise MOEXAPIError(f"Не удалось получить статус рынка: {e}")
    
    def _get_next_trading_day(self, current_date: datetime) -> datetime:
        """Получить следующий торговый день"""
        next_day = current_date + timedelta(days=1)
        
        # Пропускаем выходные
        while next_day.weekday() >= 5:
            next_day += timedelta(days=1)
        
        return next_day.replace(hour=10, minute=0, second=0, microsecond=0)
    
    async def get_order_book(self, symbol: str, depth: int = 10) -> Optional[MOEXOrderBook]:
        """
        Получить стакан заявок для акции
        
        Args:
            symbol: Тикер MOEX
            depth: Глубина стакана (количество уровней)
            
        Returns:
            Объект MOEXOrderBook или None
        """
        if not validate_moex_ticker(symbol):
            raise ValueError(f"Неверный формат тикера MOEX: {symbol}")
        
        symbol = symbol.upper()
        
        try:
            endpoint = f"/iss/engines/stock/markets/shares/boards/TQBR/securities/{symbol}/orderbook.json"
            params = {'depth': min(depth, 20)}  # MOEX ограничивает глубину
            
            data = await self._make_request(endpoint, params, use_cache=False)
            
            if not data or 'orderbook' not in data:
                return None
            
            orderbook_data = data['orderbook']['data']
            if not orderbook_data:
                return None
            
            columns = data['orderbook']['columns']
            
            bids = []
            asks = []
            
            for row in orderbook_data:
                row_dict = dict(zip(columns, row))
                
                price = row_dict.get('PRICE')
                buy_quantity = row_dict.get('BUYQUANTITY', 0)
                sell_quantity = row_dict.get('SELLQUANTITY', 0)
                
                if price:
                    price_decimal = Decimal(str(price))
                    
                    if buy_quantity > 0:
                        bids.append((price_decimal, int(buy_quantity)))
                    
                    if sell_quantity > 0:
                        asks.append((price_decimal, int(sell_quantity)))
            
            # Сортируем: биды по убыванию цены, аски по возрастанию
            bids.sort(key=lambda x: x[0], reverse=True)
            asks.sort(key=lambda x: x[0])
            
            return MOEXOrderBook(
                symbol=symbol,
                timestamp=datetime.now(MOSCOW_TZ),
                bids=bids[:depth],
                asks=asks[:depth]
            )
            
        except Exception as e:
            logger.error(f"Ошибка получения стакана для {symbol}: {e}")
            raise MOEXAPIError(f"Не удалось получить стакан для {symbol}: {e}")
    
    async def get_trades(self, symbol: str, limit: int = 100) -> List[MOEXTrade]:
        """
        Получить последние сделки по акции
        
        Args:
            symbol: Тикер MOEX
            limit: Максимальное количество сделок
            
        Returns:
            Список объектов MOEXTrade
        """
        if not validate_moex_ticker(symbol):
            raise ValueError(f"Неверный формат тикера MOEX: {symbol}")
        
        symbol = symbol.upper()
        
        try:
            endpoint = f"/iss/engines/stock/markets/shares/boards/TQBR/securities/{symbol}/trades.json"
            params = {'limit': min(limit, 500)}  # MOEX ограничение
            
            data = await self._make_request(endpoint, params, use_cache=False)
            
            if not data or 'trades' not in data:
                return []
            
            trades_data = data['trades']['data']
            if not trades_data:
                return []
            
            columns = data['trades']['columns']
            trades = []
            
            for row in trades_data:
                row_dict = dict(zip(columns, row))
                
                trade_time = row_dict.get('TRADETIME')
                price = row_dict.get('PRICE')
                quantity = row_dict.get('QUANTITY')
                trade_no = row_dict.get('TRADENO')
                
                if all([trade_time, price, quantity, trade_no]):
                    # Парсим время сделки
                    try:
                        trade_datetime = datetime.strptime(trade_time, '%H:%M:%S')
                        # Добавляем текущую дату
                        now = datetime.now(MOSCOW_TZ)
                        trade_datetime = now.replace(
                            hour=trade_datetime.hour,
                            minute=trade_datetime.minute,
                            second=trade_datetime.second,
                            microsecond=0
                        )
                    except ValueError:
                        trade_datetime = datetime.now(MOSCOW_TZ)
                    
                    trades.append(MOEXTrade(
                        symbol=symbol,
                        timestamp=trade_datetime,
                        price=Decimal(str(price)),
                        volume=int(quantity),
                        trade_id=str(trade_no),
                        buyer_initiated=True  # MOEX не предоставляет эту информацию
                    ))
            
            return sorted(trades, key=lambda x: x.timestamp, reverse=True)
            
        except Exception as e:
            logger.error(f"Ошибка получения сделок для {symbol}: {e}")
            raise MOEXAPIError(f"Не удалось получить сделки для {symbol}: {e}")
    
    async def get_market_indices(self) -> Dict[str, MarketData]:
        """
        Получить данные по основным российским индексам
        
        Returns:
            Словарь с данными индексов
        """
        try:
            endpoint = "/iss/engines/stock/markets/index/boards/RTSI/securities.json"
            
            data = await self._make_request(endpoint)
            
            indices = {}
            
            if data and 'securities' in data:
                columns = data['securities']['columns']
                
                for row in data['securities']['data']:
                    row_dict = dict(zip(columns, row))
                    
                    symbol = row_dict.get('SECID')
                    if symbol in ['IMOEX', 'RTSI', 'RUCBTR']:  # Основные индексы
                        last_price = row_dict.get('LAST')
                        prev_close = row_dict.get('PREVPRICE')
                        
                        if last_price:
                            change = None
                            change_percent = None
                            
                            if prev_close:
                                change = Decimal(str(last_price)) - Decimal(str(prev_close))
                                change_percent = (change / Decimal(str(prev_close))) * 100
                            
                            indices[symbol] = MarketData(
                                symbol=symbol,
                                timestamp=datetime.now(MOSCOW_TZ),
                                price=Decimal(str(last_price)),
                                volume=0,  # Индексы не имеют объема
                                currency="RUB" if symbol != 'RTSI' else "USD",
                                previous_close=Decimal(str(prev_close)) if prev_close else None,
                                change=change,
                                change_percent=change_percent
                            )
            
            return indices
            
        except Exception as e:
            logger.error(f"Ошибка получения данных индексов: {e}")
            raise MOEXAPIError(f"Не удалось получить данные индексов: {e}")


# Вспомогательные функции для работы с MOEX API

async def create_moex_client(api_key: Optional[str] = None) -> MOEXClient:
    """
    Создать и инициализировать MOEX клиент
    
    Args:
        api_key: API ключ (опционально)
        
    Returns:
        Инициализированный MOEXClient
    """
    client = MOEXClient(api_key=api_key)
    await client._ensure_session()
    return client


def format_moex_error(error: Exception) -> str:
    """
    Форматировать ошибку MOEX API для пользователя
    
    Args:
        error: Исключение
        
    Returns:
        Отформатированное сообщение об ошибке
    """
    if isinstance(error, MOEXRateLimitError):
        return "Превышен лимит запросов к MOEX API. Попробуйте позже."
    elif isinstance(error, MOEXConnectionError):
        return "Ошибка соединения с MOEX API. Проверьте интернет-подключение."
    elif isinstance(error, MOEXAPIError):
        return f"Ошибка MOEX API: {str(error)}"
    else:
        return f"Неизвестная ошибка: {str(error)}"