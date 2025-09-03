# Слой хранения данных российского торгового бота
# Russian Trading Bot Data Storage Layer

Этот модуль предоставляет полнофункциональный слой хранения данных для российского торгового бота, специально адаптированный для работы с MOEX (Московская биржа) и российскими финансовыми данными.

## Основные возможности

### 🇷🇺 Российская специфика
- Поддержка российских акций и тикеров MOEX
- Работа с московским временем (MSK)
- Валюта в рублях (RUB)
- Размеры лотов согласно правилам MOEX
- Торговые часы MOEX (10:00-18:45 MSK)

### 📊 Типы данных
- **Российские акции**: тикеры, названия компаний, секторы
- **Рыночные данные MOEX**: цены, объемы, bid/ask
- **Российские новости**: РБК, Ведомости, Коммерсантъ и др.
- **Сделки**: покупки/продажи с обоснованием на русском языке
- **Портфель**: позиции в российских акциях

### ⚖️ Соответствие законодательству
- Политики хранения данных согласно требованиям ЦБ РФ
- Аудиторские логи для налоговой отчетности
- Автоматическая очистка старых данных
- Поддержка российских стандартов отчетности

## Структура модуля

```
russian_trading_bot/database/
├── __init__.py              # Инициализация пакета
├── schema.py                # Схема базы данных
├── data_access.py           # Слой доступа к данным
├── config.py                # Конфигурация базы данных
├── migrations.py            # Миграции и настройка
├── example_usage.py         # Примеры использования
├── requirements.txt         # Зависимости
└── README.md               # Документация
```

## Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r russian_trading_bot/database/requirements.txt
```

### 2. Настройка базы данных

```python
from russian_trading_bot.database.data_access import RussianMarketDataAccess
from russian_trading_bot.database.migrations import DatabaseMigrations

# Создание подключения
data_access = RussianMarketDataAccess("postgresql://user:pass@localhost/db")

# Создание таблиц и настройка
migrations = DatabaseMigrations(data_access)
migrations.create_all_tables()
migrations.setup_initial_data()
```

### 3. Работа с российскими акциями

```python
# Добавление российской акции
data_access.add_russian_stock(
    symbol="SBER",
    name="ПАО Сбербанк",
    sector="Банки",
    lot_size=10
)

# Получение акций по сектору
bank_stocks = data_access.get_russian_stocks_by_sector("Банки")
```

### 4. Работа с рыночными данными MOEX

```python
from datetime import datetime
from decimal import Decimal
import pytz

msk = pytz.timezone('Europe/Moscow')

# Добавление рыночных данных
data_access.add_market_data(
    symbol="SBER",
    timestamp=datetime.now(msk),
    price=Decimal("250.50"),
    volume=1000000,
    bid=Decimal("250.40"),
    ask=Decimal("250.60")
)

# Получение последних данных
latest_data = data_access.get_latest_market_data("SBER")
```

### 5. Работа с российскими новостями

```python
# Добавление новости
data_access.add_news_article(
    title="Сбербанк увеличил прибыль",
    content="Сбербанк объявил о росте прибыли...",
    source="РБК",
    timestamp=datetime.now(msk),
    sentiment_score=Decimal("0.8"),
    mentioned_stocks=["SBER"]
)

# Анализ настроений
sentiment = data_access.get_sentiment_analysis_for_stock("SBER", days=30)
```

## Схема базы данных

### Основные таблицы

#### `russian_stocks` - Российские акции
- `symbol` (VARCHAR) - Тикер MOEX (например, SBER, GAZP)
- `name` (VARCHAR) - Название российской компании
- `sector` (VARCHAR) - Сектор российского рынка
- `lot_size` (INTEGER) - Размер лота
- `currency` (VARCHAR) - Валюта (по умолчанию RUB)

#### `market_data` - Рыночные данные MOEX
- `symbol` (VARCHAR) - Тикер акции
- `timestamp` (TIMESTAMP) - Время в MSK
- `price` (DECIMAL) - Цена в рублях
- `volume` (BIGINT) - Объем торгов
- `bid/ask` (DECIMAL) - Цены покупки/продажи

#### `news_articles` - Российские финансовые новости
- `title` (TEXT) - Заголовок новости
- `content` (TEXT) - Содержание
- `source` (VARCHAR) - Источник (РБК, Ведомости и т.д.)
- `sentiment_score` (DECIMAL) - Оценка настроения (-1 до 1)
- `mentioned_stocks` (JSON) - Упомянутые акции

#### `trades` - Сделки
- `symbol` (VARCHAR) - Тикер акции
- `action` (VARCHAR) - BUY, SELL, HOLD
- `quantity` (INTEGER) - Количество акций
- `price` (DECIMAL) - Цена исполнения в рублях
- `reasoning` (TEXT) - Обоснование на русском языке

#### `portfolio` - Портфель
- `symbol` (VARCHAR) - Тикер акции
- `quantity` (INTEGER) - Количество в портфеле
- `average_price` (DECIMAL) - Средняя цена покупки
- `unrealized_pnl` (DECIMAL) - Нереализованная прибыль/убыток

## API методов

### Российские акции
- `add_russian_stock()` - Добавление российской акции
- `get_russian_stocks_by_sector()` - Получение акций по сектору
- `get_active_russian_stocks()` - Все активные акции

### Рыночные данные MOEX
- `add_market_data()` - Добавление рыночных данных
- `get_latest_market_data()` - Последние данные по акции
- `get_market_data_range()` - Данные за период
- `get_moex_trading_hours_data()` - Данные в торговые часы

### Российские новости
- `add_news_article()` - Добавление новости
- `get_news_by_russian_source()` - Новости по источнику
- `get_news_mentioning_stock()` - Новости об акции
- `get_sentiment_analysis_for_stock()` - Анализ настроений

### Сделки
- `add_trade()` - Добавление сделки
- `get_trades_by_symbol()` - Сделки по акции
- `get_trading_performance()` - Анализ производительности

### Портфель
- `update_portfolio_position()` - Обновление позиции
- `get_portfolio_positions()` - Все позиции

### Соответствие законодательству
- `setup_retention_policies()` - Настройка политик хранения
- `cleanup_old_data()` - Очистка старых данных
- `get_database_statistics()` - Статистика базы данных

## Политики хранения данных

Согласно российскому законодательству:

| Тип данных | Срок хранения | Обоснование |
|------------|---------------|-------------|
| Рыночные данные | 7 лет | Требования ЦБ РФ |
| Сделки | 5 лет | Налоговая отчетность |
| Новости | 1 год | Аналитические цели |
| Портфель | 7 лет | Аудиторские требования |

## Индексы и производительность

Созданы специальные индексы для:
- Быстрого поиска рыночных данных по символу и времени
- Анализа настроений новостей
- Торговой статистики
- Поиска по упомянутым в новостях акциям

## Представления (Views)

- `daily_trading_summary` - Дневная торговая сводка
- `stock_sentiment_summary` - Сводка настроений по акциям
- `trading_performance` - Торговая производительность

## Тестирование

Запуск тестов:

```bash
cd russian_trading_bot
python -m pytest tests/test_database.py -v
```

Тесты покрывают:
- Работу с российскими акциями
- Рыночные данные MOEX
- Российские новости и анализ настроений
- Сделки и торговую производительность
- Управление портфелем
- Политики хранения данных
- Миграции базы данных

## Конфигурация

### Переменные окружения

```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=russian_trading_bot
DB_USER=postgres
DB_PASSWORD=your_password
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
```

### Пример конфигурации

```python
from russian_trading_bot.database.config import DatabaseConfig

config = DatabaseConfig(
    host="localhost",
    port=5432,
    database="russian_trading_bot",
    username="postgres",
    password="password",
    timezone="Europe/Moscow"
)
```

## Миграции

```python
from russian_trading_bot.database.migrations import DatabaseMigrations

migrations = DatabaseMigrations(data_access)

# Создание всех таблиц
migrations.create_all_tables()

# Настройка начальных данных
migrations.setup_initial_data()

# Создание индексов
migrations.create_indexes()

# Создание представлений
migrations.create_views()

# Проверка статуса
status = migrations.get_migration_status()
```

## Примеры использования

Полные примеры использования смотрите в файле `example_usage.py`.

## Требования

- Python 3.8+
- PostgreSQL 12+
- SQLAlchemy 2.0+
- pytz для работы с московским временем

## Лицензия

Этот модуль является частью российского торгового бота и предназначен для работы с российским фондовым рынком в соответствии с местным законодательством.