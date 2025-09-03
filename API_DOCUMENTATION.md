# 📡 API Documentation - Russian Trading Bot

## 📋 Обзор API

Russian Trading Bot предоставляет RESTful API для управления торговыми операциями, мониторинга портфеля и получения аналитических данных. API построен на FastAPI и поддерживает автоматическую документацию через OpenAPI/Swagger.

**Base URL**: `http://localhost:8000/api/v1`

**Документация**: `http://localhost:8000/docs` (Swagger UI)

## 🔐 Аутентификация

### JWT Token Authentication

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Использование токена:**
```http
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

## 📊 Portfolio API

### Получение текущего портфеля

```http
GET /api/v1/portfolio
Authorization: Bearer {token}
```

**Response:**
```json
{
  "total_value": 1500000.00,
  "currency": "RUB",
  "cash_balance": 150000.00,
  "positions": [
    {
      "symbol": "SBER",
      "name": "Сбербанк",
      "quantity": 1000,
      "average_price": 250.50,
      "current_price": 255.00,
      "market_value": 255000.00,
      "unrealized_pnl": 4500.00,
      "unrealized_pnl_percent": 1.8,
      "sector": "Банки"
    }
  ],
  "performance": {
    "total_return": 75000.00,
    "total_return_percent": 5.26,
    "daily_pnl": 2500.00,
    "daily_pnl_percent": 0.17
  }
}
```

### Получение истории портфеля

```http
GET /api/v1/portfolio/history?period=30d
Authorization: Bearer {token}
```

**Query Parameters:**
- `period`: `1d`, `7d`, `30d`, `90d`, `1y` (default: `30d`)
- `interval`: `1m`, `5m`, `1h`, `1d` (default: `1d`)

## 🔄 Trading API

### Размещение ордера

```http
POST /api/v1/trading/orders
Authorization: Bearer {token}
Content-Type: application/json

{
  "symbol": "SBER",
  "action": "BUY",
  "order_type": "MARKET",
  "quantity": 100,
  "price": null,
  "stop_loss": 240.00,
  "take_profit": 270.00
}
```

**Response:**
```json
{
  "order_id": "ord_123456789",
  "status": "PENDING",
  "symbol": "SBER",
  "action": "BUY",
  "quantity": 100,
  "order_type": "MARKET",
  "created_at": "2024-01-15T10:30:00Z",
  "estimated_commission": 127.50
}
```

### Получение активных ордеров

```http
GET /api/v1/trading/orders/active
Authorization: Bearer {token}
```

### Отмена ордера

```http
DELETE /api/v1/trading/orders/{order_id}
Authorization: Bearer {token}
```

### Получение истории сделок

```http
GET /api/v1/trading/trades?limit=50&offset=0
Authorization: Bearer {token}
```

## 📈 Market Data API

### Получение рыночных данных

```http
GET /api/v1/market/securities/{symbol}
```

**Response:**
```json
{
  "symbol": "SBER",
  "name": "Сбербанк",
  "price": 255.00,
  "change": 2.50,
  "change_percent": 0.99,
  "volume": 15000000,
  "market_cap": 5500000000000,
  "sector": "Банки",
  "currency": "RUB",
  "trading_status": "NORMAL_TRADING",
  "last_updated": "2024-01-15T15:45:00Z"
}
```

### Получение списка ценных бумаг

```http
GET /api/v1/market/securities?sector=Банки&limit=20
```

**Query Parameters:**
- `sector`: фильтр по сектору
- `limit`: количество результатов (default: 50)
- `offset`: смещение для пагинации
- `sort_by`: `price`, `volume`, `market_cap`, `change_percent`
- `sort_order`: `asc`, `desc`

### Получение исторических данных

```http
GET /api/v1/market/securities/{symbol}/history?period=30d&interval=1d
```

## 📰 News API

### Получение новостей

```http
GET /api/v1/news?limit=20&source=rbc
```

**Response:**
```json
{
  "news": [
    {
      "id": "news_123",
      "title": "Сбербанк увеличил прибыль на 15%",
      "summary": "Банк показал рекордные результаты за квартал...",
      "source": "rbc",
      "published_at": "2024-01-15T12:00:00Z",
      "url": "https://www.rbc.ru/finances/...",
      "sentiment": {
        "score": 0.75,
        "label": "POSITIVE",
        "confidence": 0.89
      },
      "mentioned_securities": ["SBER"],
      "categories": ["earnings", "banking"]
    }
  ],
  "total": 150,
  "page": 1,
  "per_page": 20
}
```

### Анализ настроений новостей

```http
GET /api/v1/news/sentiment?symbol=SBER&period=7d
```

**Response:**
```json
{
  "symbol": "SBER",
  "period": "7d",
  "overall_sentiment": {
    "score": 0.65,
    "label": "POSITIVE",
    "confidence": 0.82
  },
  "daily_sentiment": [
    {
      "date": "2024-01-15",
      "sentiment_score": 0.75,
      "news_count": 12,
      "positive_count": 8,
      "negative_count": 2,
      "neutral_count": 2
    }
  ]
}
```

## 🤖 AI Signals API

### Получение торговых сигналов

```http
GET /api/v1/signals/current
Authorization: Bearer {token}
```

**Response:**
```json
{
  "signals": [
    {
      "symbol": "SBER",
      "action": "BUY",
      "confidence": 0.85,
      "target_price": 270.00,
      "stop_loss": 240.00,
      "reasoning": [
        "Положительные новости о прибыли",
        "Технический прорыв уровня сопротивления",
        "Увеличение объемов торгов"
      ],
      "risk_score": 0.3,
      "expected_return": 0.06,
      "time_horizon": "2-4 weeks",
      "generated_at": "2024-01-15T16:00:00Z"
    }
  ],
  "market_conditions": {
    "overall_sentiment": "BULLISH",
    "volatility": "MEDIUM",
    "trend": "UPWARD"
  }
}
```

### Получение исторических сигналов

```http
GET /api/v1/signals/history?period=30d&symbol=SBER
Authorization: Bearer {token}
```

## ⚖️ Risk Management API

### Получение оценки рисков портфеля

```http
GET /api/v1/risk/portfolio-assessment
Authorization: Bearer {token}
```

**Response:**
```json
{
  "overall_risk_score": 0.35,
  "risk_level": "MEDIUM",
  "metrics": {
    "var_95": -45000.00,
    "max_drawdown": 0.12,
    "sharpe_ratio": 1.45,
    "beta": 0.85,
    "correlation_with_market": 0.78
  },
  "risk_factors": [
    {
      "factor": "Концентрация в банковском секторе",
      "impact": "HIGH",
      "description": "40% портфеля в банковских акциях",
      "recommendation": "Диверсифицировать в другие секторы"
    }
  ],
  "recommendations": [
    "Снизить долю банковского сектора до 25%",
    "Добавить защитные активы (облигации)",
    "Установить стоп-лоссы на крупные позиции"
  ]
}
```

### Проверка ордера на соответствие рискам

```http
POST /api/v1/risk/validate-order
Authorization: Bearer {token}
Content-Type: application/json

{
  "symbol": "GAZP",
  "action": "BUY",
  "quantity": 500,
  "price": 180.00
}
```

**Response:**
```json
{
  "approved": true,
  "risk_score": 0.25,
  "warnings": [],
  "position_size_percent": 0.06,
  "sector_exposure_after": {
    "Нефтегаз": 0.35,
    "Банки": 0.40,
    "Телеком": 0.15,
    "Другие": 0.10
  }
}
```

## 📊 Analytics API

### Получение аналитики производительности

```http
GET /api/v1/analytics/performance?period=90d
Authorization: Bearer {token}
```

**Response:**
```json
{
  "period": "90d",
  "total_return": 0.087,
  "annualized_return": 0.35,
  "volatility": 0.18,
  "sharpe_ratio": 1.45,
  "max_drawdown": 0.08,
  "win_rate": 0.68,
  "profit_factor": 1.85,
  "trades_count": 45,
  "avg_trade_return": 0.019,
  "best_trade": 0.12,
  "worst_trade": -0.05,
  "monthly_returns": [
    {"month": "2023-11", "return": 0.025},
    {"month": "2023-12", "return": 0.031},
    {"month": "2024-01", "return": 0.028}
  ]
}
```

### Сравнение с бенчмарком

```http
GET /api/v1/analytics/benchmark-comparison?benchmark=IMOEX&period=1y
Authorization: Bearer {token}
```

## 🔔 Notifications API

### Получение уведомлений

```http
GET /api/v1/notifications?limit=20&unread_only=true
Authorization: Bearer {token}
```

### Настройка уведомлений

```http
PUT /api/v1/notifications/settings
Authorization: Bearer {token}
Content-Type: application/json

{
  "telegram_enabled": true,
  "email_enabled": false,
  "trade_notifications": true,
  "risk_alerts": true,
  "news_alerts": false,
  "daily_reports": true
}
```

## 🏥 System Health API

### Проверка состояния системы

```http
GET /api/v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T16:30:00Z",
  "version": "1.0.0",
  "components": {
    "database": "healthy",
    "redis": "healthy",
    "moex_api": "healthy",
    "tinkoff_api": "healthy",
    "ai_engine": "healthy"
  },
  "metrics": {
    "uptime_seconds": 86400,
    "memory_usage_mb": 512,
    "cpu_usage_percent": 15.5,
    "active_connections": 25
  }
}
```

## 📋 Error Handling

### Стандартные коды ошибок

- `400` - Bad Request (неверные параметры)
- `401` - Unauthorized (требуется аутентификация)
- `403` - Forbidden (недостаточно прав)
- `404` - Not Found (ресурс не найден)
- `422` - Validation Error (ошибка валидации)
- `429` - Too Many Requests (превышен лимит запросов)
- `500` - Internal Server Error (внутренняя ошибка)

### Формат ошибок

```json
{
  "error": {
    "code": "INSUFFICIENT_FUNDS",
    "message": "Недостаточно средств для выполнения операции",
    "details": {
      "required_amount": 25500.00,
      "available_amount": 15000.00,
      "currency": "RUB"
    },
    "timestamp": "2024-01-15T16:30:00Z",
    "request_id": "req_123456789"
  }
}
```

## 🔄 Rate Limiting

### Лимиты запросов

- **Общие запросы**: 1000 запросов/час
- **Торговые операции**: 100 запросов/час
- **Рыночные данные**: 500 запросов/час
- **Аутентификация**: 10 попыток/минуту

### Заголовки лимитов

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 995
X-RateLimit-Reset: 1642262400
```

## 📡 WebSocket API

### Подключение к WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/v1/stream');

// Аутентификация
ws.send(JSON.stringify({
  type: 'auth',
  token: 'your_jwt_token'
}));

// Подписка на обновления портфеля
ws.send(JSON.stringify({
  type: 'subscribe',
  channel: 'portfolio'
}));
```

### Каналы подписки

- `portfolio` - обновления портфеля
- `trades` - исполненные сделки
- `orders` - изменения ордеров
- `market_data` - рыночные данные
- `news` - новые новости
- `signals` - торговые сигналы

## 🧪 Тестирование API

### Postman Collection

Импортируйте коллекцию Postman для тестирования API:
```bash
curl -o russian-trading-bot.postman_collection.json \
  https://raw.githubusercontent.com/yourusername/russian-trading-bot/main/docs/postman_collection.json
```

### Примеры cURL

```bash
# Получение токена
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "demo", "password": "demo123"}'

# Получение портфеля
curl -X GET "http://localhost:8000/api/v1/portfolio" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Размещение ордера
curl -X POST "http://localhost:8000/api/v1/trading/orders" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "SBER",
    "action": "BUY",
    "order_type": "MARKET",
    "quantity": 10
  }'
```

## 📚 SDK и библиотеки

### Python SDK

```python
from russian_trading_bot_sdk import TradingBotClient

client = TradingBotClient(
    base_url="http://localhost:8000",
    username="your_username",
    password="your_password"
)

# Получение портфеля
portfolio = await client.get_portfolio()

# Размещение ордера
order = await client.place_order(
    symbol="SBER",
    action="BUY",
    quantity=100,
    order_type="MARKET"
)
```

### JavaScript SDK

```javascript
import { TradingBotClient } from 'russian-trading-bot-js';

const client = new TradingBotClient({
  baseURL: 'http://localhost:8000',
  username: 'your_username',
  password: 'your_password'
});

// Получение портфеля
const portfolio = await client.getPortfolio();

// Размещение ордера
const order = await client.placeOrder({
  symbol: 'SBER',
  action: 'BUY',
  quantity: 100,
  orderType: 'MARKET'
});
```

---

**📡 Полная документация API доступна в Swagger UI: http://localhost:8000/docs**