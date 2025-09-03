# Russian Stock Trading Bot

AI-powered trading system specifically designed for the Russian stock market (MOEX).

## Project Structure

```
russian_trading_bot/
├── __init__.py                 # Package initialization
├── README.md                   # This file
├── api/                        # API interfaces and implementations
│   ├── __init__.py
│   ├── moex_interface.py       # MOEX data interface
│   └── broker_interface.py     # Russian broker interface
├── models/                     # Data models
│   ├── __init__.py
│   ├── market_data.py          # Market data models
│   ├── trading.py              # Trading models
│   └── news.py                 # News data models
├── services/                   # Business logic services
│   └── __init__.py
└── config/                     # Configuration
    ├── __init__.py
    ├── market_config.py        # Russian market parameters
    └── settings.py             # Application settings
```

## Key Features

### Market Data Integration
- MOEX (Moscow Exchange) real-time data
- Russian stock information and technical indicators
- Market status and trading hours (10:00-18:45 MSK)

### Broker Integration
- Support for major Russian brokers (Tinkoff, Finam, Sberbank, VTB)
- Order management and execution
- Portfolio tracking in RUB currency

### Russian Market Specifics
- RUB currency handling
- T+2 settlement period
- Russian trading hours and holidays
- Sector-specific risk parameters
- Geopolitical risk adjustments

### Configuration
- Trading hours: 10:00-18:45 Moscow time
- Currency: RUB (Russian Ruble)
- Settlement: T+2
- Risk management parameters adapted for Russian market volatility

## Usage

```python
from russian_trading_bot.config.settings import settings
from russian_trading_bot.models.market_data import RussianStock, MarketData

# Check if market is open
if settings.market_config.is_market_open():
    print("MOEX market is currently open")

# Create a Russian stock
stock = RussianStock(
    symbol="SBER",
    name="ПАО Сбербанк",
    sector="banking"
)
```

## Environment Variables

Set the following environment variables for configuration:

```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=russian_trading_bot
DB_USER=postgres
DB_PASSWORD=your_password

# API Keys
MOEX_API_KEY=your_moex_key
TINKOFF_TOKEN=your_tinkoff_token
FINAM_API_KEY=your_finam_key

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/trading_bot.log

# Security
SECRET_KEY=your_secret_key
ENVIRONMENT=development
DEBUG=false
```

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables (see above)

3. Initialize the database (when database services are implemented)

## Next Steps

This is the foundational structure. The following services will be implemented in subsequent tasks:

1. Data collection services for MOEX and Russian news
2. Market analysis and technical indicators
3. AI decision engine
4. Risk management system
5. Trade execution services
6. Portfolio management
7. Web dashboard with Russian localization