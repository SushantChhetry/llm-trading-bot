# 📚 API Documentation

This document provides comprehensive API documentation for the LLM Trading Bot system.

## 🌐 Base URLs

- **Development**: `http://localhost:8001`
- **Production**: `https://your-domain.com/api`

## 🔐 Authentication

### Current Status

Currently, the API does not require authentication for development. In production, consider implementing:

- API Key authentication
- JWT tokens
- OAuth 2.0

### Adding Authentication (Recommended for Production)

#### Option 1: API Key Authentication

Add to your API server:

```python
from fastapi import Header, HTTPException
from functools import wraps

API_KEY = os.getenv("API_KEY", "")

def require_api_key(func):
    @wraps(func)
    async def wrapper(*args, api_key: str = Header(...), **kwargs):
        if not API_KEY or api_key != API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return await func(*args, **kwargs)
    return wrapper

# Use in endpoints
@router.get("/api/trades")
@require_api_key
async def get_trades():
    ...
```

**Client Example:**
```bash
curl -H "X-API-Key: your-api-key" https://your-api.com/api/trades
```

#### Option 2: JWT Tokens

```python
from jose import JWTError, jwt
from datetime import datetime, timedelta

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=1)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
```

**Client Example:**
```bash
# Get token
TOKEN=$(curl -X POST https://your-api.com/auth/login -d '{"username":"user","password":"pass"}' | jq -r .token)

# Use token
curl -H "Authorization: Bearer $TOKEN" https://your-api.com/api/trades
```

## 📊 Endpoints

### Health Check

#### GET /api/health
Check the health status of the trading bot system.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "services": {
    "database": "healthy",
    "llm_api": "healthy",
    "exchange_api": "healthy"
  },
  "uptime": 3600,
  "version": "1.0.0"
}
```

**Status Codes:**
- `200 OK`: System is healthy
- `503 Service Unavailable`: System is unhealthy

---

### Trading Data

#### GET /api/trades
Retrieve recent trading history.

**Query Parameters:**
- `limit` (optional): Number of trades to return (default: 100, max: 1000)
- `symbol` (optional): Filter by trading symbol
- `side` (optional): Filter by trade side (buy/sell/short)
- `since` (optional): ISO timestamp to filter trades since

**Response:**
```json
[
  {
    "id": 1,
    "trade_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2024-01-01T12:00:00Z",
    "symbol": "BTC/USDT",
    "side": "buy",
    "direction": "long",
    "price": 50000.0,
    "quantity": 0.02,
    "amount_usdt": 1000.0,
    "leverage": 2.0,
    "margin_used": 500.0,
    "margin_returned": 0.0,
    "trading_fee": 0.5,
    "profit": 0.0,
    "profit_pct": 0.0,
    "confidence": 0.85,
    "mode": "paper",
    "llm_justification": "Strong bullish momentum with volume confirmation",
    "llm_risk_assessment": "medium",
    "llm_position_size_usdt": 1000.0,
    "exit_plan": {
      "profit_target": 52000.0,
      "stop_loss": 49000.0,
      "invalidation_conditions": ["market_volatility_spike"]
    }
  }
]
```

**Status Codes:**
- `200 OK`: Trades retrieved successfully
- `400 Bad Request`: Invalid query parameters
- `500 Internal Server Error`: Server error

---

#### GET /api/trades/{trade_id}
Retrieve a specific trade by ID.

**Path Parameters:**
- `trade_id`: Unique trade identifier

**Response:**
```json
{
  "id": 1,
  "trade_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2024-01-01T12:00:00Z",
  "symbol": "BTC/USDT",
  "side": "buy",
  "direction": "long",
  "price": 50000.0,
  "quantity": 0.02,
  "amount_usdt": 1000.0,
  "leverage": 2.0,
  "margin_used": 500.0,
  "margin_returned": 0.0,
  "trading_fee": 0.5,
  "profit": 0.0,
  "profit_pct": 0.0,
  "confidence": 0.85,
  "mode": "paper",
  "llm_justification": "Strong bullish momentum with volume confirmation",
  "llm_risk_assessment": "medium",
  "llm_position_size_usdt": 1000.0,
  "exit_plan": {
    "profit_target": 52000.0,
    "stop_loss": 49000.0,
    "invalidation_conditions": ["market_volatility_spike"]
  }
}
```

**Status Codes:**
- `200 OK`: Trade found
- `404 Not Found`: Trade not found
- `500 Internal Server Error`: Server error

---

### Portfolio Data

#### GET /api/portfolio
Retrieve current portfolio status and metrics.

**Response:**
```json
{
  "balance": 8500.0,
  "total_value": 10250.0,
  "positions_value": 1750.0,
  "unrealized_pnl": 250.0,
  "realized_pnl": 500.0,
  "total_fees": 25.0,
  "active_positions": 2,
  "total_trades": 15,
  "initial_balance": 10000.0,
  "total_return": 250.0,
  "total_return_pct": 2.5,
  "sharpe_ratio": 1.25,
  "volatility": 0.15,
  "max_drawdown": 150.0,
  "win_rate": 0.65,
  "profit_factor": 1.8,
  "avg_trade_duration_hours": 4.2,
  "max_consecutive_wins": 5,
  "max_consecutive_losses": 3,
  "excess_return": 0.025,
  "risk_adjusted_return": 0.167,
  "bullish_tilt": 0.65,
  "avg_holding_period_hours": 4.2,
  "trade_frequency_per_day": 2.3,
  "avg_position_size_usdt": 150.0,
  "avg_confidence": 0.75,
  "exit_plan_tightness": 2.5,
  "active_positions_count": 2,
  "total_trading_fees": 25.0,
  "fee_impact_pct": 10.0
}
```

**Status Codes:**
- `200 OK`: Portfolio data retrieved successfully
- `500 Internal Server Error`: Server error

---

#### GET /api/portfolio/positions
Retrieve current active positions.

**Response:**
```json
{
  "BTC/USDT": {
    "id": 1,
    "position_id": "550e8400-e29b-41d4-a716-446655440001",
    "symbol": "BTC/USDT",
    "side": "long",
    "quantity": 0.02,
    "avg_price": 50000.0,
    "current_price": 51000.0,
    "value": 1000.0,
    "leverage": 2.0,
    "margin_used": 500.0,
    "notional_value": 1020.0,
    "unrealized_pnl": 20.0,
    "is_active": true,
    "opened_at": "2024-01-01T12:00:00Z",
    "closed_at": null
  },
  "ETH/USDT": {
    "id": 2,
    "position_id": "550e8400-e29b-41d4-a716-446655440002",
    "symbol": "ETH/USDT",
    "side": "short",
    "quantity": 0.5,
    "avg_price": 3000.0,
    "current_price": 2950.0,
    "value": 1500.0,
    "leverage": 1.5,
    "margin_used": 1000.0,
    "notional_value": 1475.0,
    "unrealized_pnl": 25.0,
    "is_active": true,
    "opened_at": "2024-01-01T11:30:00Z",
    "closed_at": null
  }
}
```

**Status Codes:**
- `200 OK`: Positions retrieved successfully
- `500 Internal Server Error`: Server error

---

### Market Data

#### GET /api/market/ticker
Retrieve current market ticker data.

**Query Parameters:**
- `symbol` (optional): Trading symbol (default: BTC/USDT)

**Response:**
```json
{
  "symbol": "BTC/USDT",
  "price": 51000.0,
  "bid": 50995.0,
  "ask": 51005.0,
  "volume": 1500000.0,
  "change_24h": 2.5,
  "high_24h": 51500.0,
  "low_24h": 49500.0,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**Status Codes:**
- `200 OK`: Ticker data retrieved successfully
- `400 Bad Request`: Invalid symbol
- `500 Internal Server Error`: Server error

---

#### GET /api/market/ohlcv
Retrieve OHLCV (candlestick) data.

**Query Parameters:**
- `symbol` (optional): Trading symbol (default: BTC/USDT)
- `timeframe` (optional): Timeframe (1m, 5m, 15m, 1h, 4h, 1d) (default: 1h)
- `limit` (optional): Number of candles (default: 100, max: 1000)

**Response:**
```json
[
  {
    "timestamp": "2024-01-01T12:00:00Z",
    "open": 50000.0,
    "high": 51000.0,
    "low": 49500.0,
    "close": 50500.0,
    "volume": 1500000.0
  }
]
```

**Status Codes:**
- `200 OK`: OHLCV data retrieved successfully
- `400 Bad Request`: Invalid parameters
- `500 Internal Server Error`: Server error

---

### Bot Status

#### GET /api/status
Retrieve bot status and configuration.

**Response:**
```json
{
  "status": "running",
  "mode": "paper",
  "exchange": "bybit",
  "symbol": "BTC/USDT",
  "llm_provider": "deepseek",
  "initial_balance": 10000.0,
  "current_balance": 8500.0,
  "total_value": 10250.0,
  "active_positions": 2,
  "total_trades": 15,
  "uptime": 3600,
  "last_trade": "2024-01-01T11:45:00Z",
  "next_cycle": "2024-01-01T12:02:30Z",
  "configuration": {
    "max_position_size": 0.1,
    "max_leverage": 10.0,
    "min_confidence_threshold": 0.6,
    "run_interval_seconds": 150
  }
}
```

**Status Codes:**
- `200 OK`: Status retrieved successfully
- `500 Internal Server Error`: Server error

---

#### POST /api/status/start
Start the trading bot.

**Response:**
```json
{
  "status": "started",
  "message": "Trading bot started successfully",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**Status Codes:**
- `200 OK`: Bot started successfully
- `409 Conflict`: Bot already running
- `500 Internal Server Error`: Server error

---

#### POST /api/status/stop
Stop the trading bot.

**Response:**
```json
{
  "status": "stopped",
  "message": "Trading bot stopped successfully",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**Status Codes:**
- `200 OK`: Bot stopped successfully
- `409 Conflict`: Bot not running
- `500 Internal Server Error`: Server error

---

### Metrics and Monitoring

#### GET /api/metrics
Retrieve system metrics.

**Response:**
```json
{
  "counters": {
    "trades.total": 15,
    "trades.buy": 8,
    "trades.sell": 7,
    "api.calls.deepseek": 45,
    "api.success.deepseek": 42,
    "api.errors.deepseek": 3
  },
  "gauges": {
    "portfolio.value": 10250.0,
    "portfolio.positions": 2,
    "system.cpu.usage": 25.5,
    "system.memory.usage": 60.2
  },
  "histogram_stats": {
    "trades.profit": {
      "count": 7,
      "min": -50.0,
      "max": 200.0,
      "mean": 75.0,
      "p95": 180.0,
      "p99": 195.0
    },
    "api.response_time.deepseek": {
      "count": 45,
      "min": 100.0,
      "max": 2000.0,
      "mean": 500.0,
      "p95": 1200.0,
      "p99": 1800.0
    }
  },
  "health_status": "healthy",
  "recent_alerts": []
}
```

**Status Codes:**
- `200 OK`: Metrics retrieved successfully
- `500 Internal Server Error`: Server error

---

#### GET /api/metrics/export
Export metrics data.

**Query Parameters:**
- `format` (optional): Export format (json, csv) (default: json)
- `since` (optional): ISO timestamp to filter metrics since
- `until` (optional): ISO timestamp to filter metrics until

**Response:**
- **JSON format**: Returns metrics data as JSON
- **CSV format**: Returns metrics data as CSV file

**Status Codes:**
- `200 OK`: Metrics exported successfully
- `400 Bad Request`: Invalid parameters
- `500 Internal Server Error`: Server error

---

### Configuration

#### GET /api/config
Retrieve current configuration.

**Response:**
```json
{
  "trading": {
    "mode": "paper",
    "initial_balance": 10000.0,
    "max_position_size": 0.1,
    "max_leverage": 10.0,
    "min_confidence_threshold": 0.6,
    "run_interval_seconds": 150
  },
  "llm": {
    "provider": "deepseek",
    "model": "deepseek-chat",
    "temperature": 0.7,
    "max_tokens": 500
  },
  "exchange": {
    "name": "bybit",
    "symbol": "BTC/USDT",
    "use_testnet": true
  },
  "security": {
    "enable_rate_limiting": true,
    "max_requests_per_minute": 60,
    "enable_input_validation": true
  }
}
```

**Status Codes:**
- `200 OK`: Configuration retrieved successfully
- `500 Internal Server Error`: Server error

---

#### PUT /api/config
Update configuration (restricted in production).

**Request Body:**
```json
{
  "trading": {
    "max_position_size": 0.15,
    "min_confidence_threshold": 0.7
  }
}
```

**Response:**
```json
{
  "status": "updated",
  "message": "Configuration updated successfully",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**Status Codes:**
- `200 OK`: Configuration updated successfully
- `400 Bad Request`: Invalid configuration
- `403 Forbidden`: Configuration updates not allowed
- `500 Internal Server Error`: Server error

---

## 🔄 WebSocket API

### Connection
Connect to WebSocket for real-time updates:

```
ws://localhost:8002/ws
```

**JavaScript Example:**
```javascript
const ws = new WebSocket('ws://localhost:8002/ws');

ws.onopen = () => {
  console.log('WebSocket connected');

  // Subscribe to updates
  ws.send(JSON.stringify({
    type: 'subscribe',
    channels: ['portfolio', 'trades', 'alerts']
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message);

  // Handle different message types
  switch(message.type) {
    case 'portfolio_update':
      updatePortfolio(message.data);
      break;
    case 'trade_executed':
      addTradeToTable(message.data);
      break;
    case 'alert':
      showAlert(message.data);
      break;
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('WebSocket disconnected');
  // Reconnect logic
};
```

### Message Types

#### Portfolio Updates
```json
{
  "type": "portfolio_update",
  "data": {
    "balance": 8500.0,
    "total_value": 10250.0,
    "active_positions": 2,
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

#### Trade Executed
```json
{
  "type": "trade_executed",
  "data": {
    "trade_id": "550e8400-e29b-41d4-a716-446655440000",
    "symbol": "BTC/USDT",
    "side": "buy",
    "price": 50000.0,
    "quantity": 0.02,
    "confidence": 0.85,
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

#### Alert Triggered
```json
{
  "type": "alert",
  "data": {
    "name": "high_cpu_usage",
    "severity": "warning",
    "message": "CPU usage exceeded 80%",
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

### WebSocket Server Implementation (Example)

```python
from fastapi import WebSocket
import json

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Send updates
            portfolio_data = await get_portfolio_update()
            await websocket.send_json({
                "type": "portfolio_update",
                "data": portfolio_data
            })

            await asyncio.sleep(5)  # Update every 5 seconds
    except WebSocketDisconnect:
        pass
```

---

## 📝 Error Responses

All error responses follow this format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": "Additional error details",
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

### Common Error Codes

- `INVALID_REQUEST`: Invalid request parameters
- `UNAUTHORIZED`: Authentication required
- `FORBIDDEN`: Access denied
- `NOT_FOUND`: Resource not found
- `RATE_LIMITED`: Rate limit exceeded
- `SERVICE_UNAVAILABLE`: Service temporarily unavailable
- `INTERNAL_ERROR`: Internal server error

---

## 🔒 Rate Limiting

The API implements rate limiting to prevent abuse:

- **Default**: 60 requests per minute per IP
- **Burst**: Up to 10 requests per second
- **Headers**: Rate limit information in response headers
  - `X-RateLimit-Limit`: Requests per minute
  - `X-RateLimit-Remaining`: Remaining requests
  - `X-RateLimit-Reset`: Reset timestamp

---

## 📊 Response Formats

### Pagination
For endpoints that return lists, pagination is supported:

```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 100,
    "total": 1500,
    "pages": 15,
    "has_next": true,
    "has_prev": false
  }
}
```

### Sorting
Query parameter `sort` for sorting results:

- `sort=timestamp` - Sort by timestamp (default)
- `sort=-timestamp` - Sort by timestamp descending
- `sort=price` - Sort by price
- `sort=-profit` - Sort by profit descending

---

## 🧪 Testing

### Test Environment
Use the test environment for development:

```bash
# Start test environment
docker-compose -f docker-compose.dev.yml up -d

# Test API endpoints
curl http://localhost:8001/api/health
```

### Example Requests

```bash
# Get portfolio status
curl -X GET "http://localhost:8001/api/portfolio" \
  -H "Accept: application/json"

# Get recent trades
curl -X GET "http://localhost:8001/api/trades?limit=10" \
  -H "Accept: application/json"

# Get market data
curl -X GET "http://localhost:8001/api/market/ticker?symbol=BTC/USDT" \
  -H "Accept: application/json"

# Get trades with filters
curl -X GET "http://localhost:8001/api/trades?limit=50&side=buy&since=2024-01-01T00:00:00Z" \
  -H "Accept: application/json"

# Get specific trade
curl -X GET "http://localhost:8001/api/trades/550e8400-e29b-41d4-a716-446655440000" \
  -H "Accept: application/json"

# Get active positions
curl -X GET "http://localhost:8001/api/portfolio/positions" \
  -H "Accept: application/json"

# Start bot
curl -X POST "http://localhost:8001/api/status/start" \
  -H "Accept: application/json"

# Stop bot
curl -X POST "http://localhost:8001/api/status/stop" \
  -H "Accept: application/json"
```

---

## 📚 SDK Examples

### Python
```python
import requests
from typing import Dict, List, Optional

BASE_URL = "http://localhost:8001/api"

# Get portfolio status
def get_portfolio() -> Dict:
    response = requests.get(f"{BASE_URL}/portfolio")
    response.raise_for_status()
    return response.json()

# Get recent trades
def get_trades(limit: int = 10, symbol: Optional[str] = None) -> List[Dict]:
    params = {"limit": limit}
    if symbol:
        params["symbol"] = symbol

    response = requests.get(f"{BASE_URL}/trades", params=params)
    response.raise_for_status()
    return response.json()

# Get specific trade
def get_trade(trade_id: str) -> Dict:
    response = requests.get(f"{BASE_URL}/trades/{trade_id}")
    response.raise_for_status()
    return response.json()

# Get market data
def get_ticker(symbol: str = "BTC/USDT") -> Dict:
    response = requests.get(f"{BASE_URL}/market/ticker", params={"symbol": symbol})
    response.raise_for_status()
    return response.json()

# Start bot
def start_bot() -> Dict:
    response = requests.post(f"{BASE_URL}/status/start")
    response.raise_for_status()
    return response.json()

# Stop bot
def stop_bot() -> Dict:
    response = requests.post(f"{BASE_URL}/status/stop")
    response.raise_for_status()
    return response.json()

# Example usage
if __name__ == "__main__":
    portfolio = get_portfolio()
    print(f"Portfolio value: ${portfolio['total_value']}")

    trades = get_trades(limit=5)
    print(f"Recent trades: {len(trades)}")

    ticker = get_ticker()
    print(f"Current BTC price: ${ticker['price']}")
```

### JavaScript
```javascript
const API_BASE_URL = 'http://localhost:8001/api';

// Get portfolio status
async function getPortfolio() {
  const response = await fetch(`${API_BASE_URL}/portfolio`);
  if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
  return await response.json();
}

// Get recent trades
async function getTrades(limit = 10, symbol = null) {
  const params = new URLSearchParams({ limit: limit.toString() });
  if (symbol) params.append('symbol', symbol);

  const response = await fetch(`${API_BASE_URL}/trades?${params}`);
  if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
  return await response.json();
}

// Get specific trade
async function getTrade(tradeId) {
  const response = await fetch(`${API_BASE_URL}/trades/${tradeId}`);
  if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
  return await response.json();
}

// Get market data
async function getTicker(symbol = 'BTC/USDT') {
  const response = await fetch(`${API_BASE_URL}/market/ticker?symbol=${symbol}`);
  if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
  return await response.json();
}

// Start bot
async function startBot() {
  const response = await fetch(`${API_BASE_URL}/status/start`, {
    method: 'POST'
  });
  if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
  return await response.json();
}

// Stop bot
async function stopBot() {
  const response = await fetch(`${API_BASE_URL}/status/stop`, {
    method: 'POST'
  });
  if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
  return await response.json();
}

// Example usage with error handling
async function fetchPortfolioData() {
  try {
    const portfolio = await getPortfolio();
    console.log('Portfolio value:', portfolio.total_value);

    const trades = await getTrades(5);
    console.log('Recent trades:', trades.length);

    const ticker = await getTicker();
    console.log('BTC price:', ticker.price);
  } catch (error) {
    console.error('Error fetching data:', error);
  }
}

// React hook example
import { useState, useEffect } from 'react';

function useTradingData() {
  const [portfolio, setPortfolio] = useState(null);
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [portfolioData, tradesData] = await Promise.all([
          getPortfolio(),
          getTrades(10)
        ]);
        setPortfolio(portfolioData);
        setTrades(tradesData);
      } catch (error) {
        console.error('Error:', error);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
    const interval = setInterval(fetchData, 5000); // Refresh every 5s
    return () => clearInterval(interval);
  }, []);

  return { portfolio, trades, loading };
}
```

### cURL
```bash
# Health check
curl -X GET "http://localhost:8001/api/health"

# Get portfolio
curl -X GET "http://localhost:8001/api/portfolio"

# Get trades
curl -X GET "http://localhost:8001/api/trades?limit=10"
```

---

## 🔄 Changelog

### Version 1.0.0
- Initial API release
- Basic trading data endpoints
- Portfolio management
- Market data integration
- WebSocket support for real-time updates
- Comprehensive monitoring and metrics
