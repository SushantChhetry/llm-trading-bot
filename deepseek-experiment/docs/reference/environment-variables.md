# Railway Environment Variables Configuration Guide

This document lists all environment variables you need to configure in Railway for production deployment.

## 📋 Quick Setup Checklist

### ✅ Required for Trading Bot Service

These are **ESSENTIAL** - the bot won't work without them:

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `ENVIRONMENT` | Set to `production` | `production` |
| `LLM_PROVIDER` | LLM provider to use | `deepseek` |
| `LLM_API_KEY` | API key for LLM provider | `sk-your-deepseek-key` |
| `LLM_MODEL` | LLM model name | `deepseek-chat` |
| `TRADING_MODE` | Trading mode | `paper` (or `live` for real trading) |
| `USE_TESTNET` | Use testnet exchange | `true` (recommended) |
| | | **Note:** Kraken does not provide testnet - this flag has limited effect with Kraken |
| `EXCHANGE` | Exchange name | `kraken` (options: `kraken`, `bybit`, `binance`, `coinbase`) |
| `SYMBOL` | Trading pair | `BTC/USDT` |
| `LOG_LEVEL` | Logging level | `INFO` |

### ✅ Required for API Server Service

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `ENVIRONMENT` | Set to `production` | `production` |
| `SUPABASE_KEY` | Supabase anon key | `eyJhbGc...` |
| `SUPABASE_URL` | Supabase project URL | `https://your-project.supabase.co` |
| `CORS_ORIGINS` | Allowed frontend origins | `https://your-app.vercel.app,https://your-app.railway.app` |

### 📝 Recommended Configuration

These have sensible defaults but should be reviewed:

| Variable | Description | Default | Recommended |
|----------|-------------|---------|-------------|
| `RUN_INTERVAL_SECONDS` | Bot execution interval | `150` | `150` (2.5 min) |
| `INITIAL_BALANCE` | Starting balance | `10000.0` | `10000.0` |
| `MAX_POSITION_SIZE` | Max % per trade | `0.1` | `0.1` (10%) |
| `MAX_LEVERAGE` | Maximum leverage | `10.0` | `10.0` |
| `STOP_LOSS_PERCENT` | Stop loss % | `2.0` | `2.0` |
| `TAKE_PROFIT_PERCENT` | Take profit % | `3.0` | `3.0` |
| `MAX_ACTIVE_POSITIONS` | Max simultaneous positions | `6` | `6` |
| `MIN_CONFIDENCE_THRESHOLD` | Min confidence to trade | `0.6` | `0.6` |

### 🔐 Exchange API Keys (Only if using live/testnet trading)

| Variable | Description | When Needed |
|----------|-------------|-------------|
| `EXCHANGE_API_KEY` | Exchange API key | If `TRADING_MODE=live` or for fetching market data |
| `EXCHANGE_API_SECRET` | Exchange API secret | If `TRADING_MODE=live` or for fetching market data |
| `TESTNET_API_KEY` | Testnet API key | If `USE_TESTNET=true` (only for Bybit/Binance) |
| `TESTNET_API_SECRET` | Testnet API secret | If `USE_TESTNET=true` (only for Bybit/Binance) |

**Kraken-specific notes:**
- Kraken does **NOT** provide a testnet/sandbox environment
- Only `EXCHANGE_API_KEY` and `EXCHANGE_API_SECRET` are used (ignore `TESTNET_*` keys)
- For paper trading with Kraken, API keys are optional but may be needed for real market data

---

## 🔧 Complete Environment Variables List

### Core Configuration

```bash
# ============================================
# ENVIRONMENT
# ============================================
ENVIRONMENT=production                    # Required: production or development

# ============================================
# LLM CONFIGURATION
# ============================================
LLM_PROVIDER=deepseek                     # Required: deepseek, openai, anthropic, mock
LLM_API_KEY=sk-your-api-key-here          # Required: Your LLM provider API key
LLM_MODEL=deepseek-chat                    # Required: Model name
LLM_API_URL=                               # Optional: Custom API URL (auto-detected if empty)
LLM_TEMPERATURE=0.7                        # Optional: Default 0.7
LLM_MAX_TOKENS=2000                       # Optional: Default 2000
LLM_TIMEOUT=30                            # Optional: Default 30 seconds

# ============================================
# TRADING CONFIGURATION
# ============================================
TRADING_MODE=paper                         # Required: paper or live
USE_TESTNET=true                           # Required: true or false
# Note: With Kraken, USE_TESTNET has limited effect (Kraken has no testnet)
EXCHANGE=kraken                            # Required: kraken, bybit, binance, coinbase
SYMBOL=BTC/USDT                           # Required: Trading pair
# Note: Kraken may use BTC/USD format instead of BTC/USDT
INITIAL_BALANCE=10000.0                   # Recommended: Starting balance
RUN_INTERVAL_SECONDS=150                  # Recommended: Bot cycle interval (2.5 min)

# ============================================
# RISK MANAGEMENT
# ============================================
MAX_POSITION_SIZE=0.1                      # Recommended: Max % of balance per trade (10%)
MAX_LEVERAGE=10.0                         # Recommended: Maximum leverage
DEFAULT_LEVERAGE=1.0                      # Optional: Default leverage if not specified
STOP_LOSS_PERCENT=2.0                     # Recommended: Stop loss percentage
TAKE_PROFIT_PERCENT=3.0                   # Recommended: Take profit percentage
MAX_RISK_PER_TRADE=2.0                    # Optional: Max risk per trade (%)
TRADING_FEE_PERCENT=0.05                  # Optional: Trading fee percentage

# ============================================
# POSITION MANAGEMENT
# ============================================
MAX_ACTIVE_POSITIONS=6                    # Recommended: Max simultaneous positions
MIN_CONFIDENCE_THRESHOLD=0.6              # Recommended: Min confidence to trade (0-1)
FEE_IMPACT_WARNING_THRESHOLD=20.0         # Optional: Warn if fees > X% of PnL

# ============================================
# EXCHANGE API KEYS
# ============================================
# For paper trading: Optional - may be needed for fetching real market data
# For live trading: Required - must have valid exchange API credentials
# Note: Kraken does NOT provide separate testnet keys (no testnet available)
EXCHANGE_API_KEY=                         # Required if live trading or for market data
EXCHANGE_API_SECRET=                      # Required if live trading or for market data
TESTNET_API_KEY=                          # Only for Bybit/Binance testnet (not used with Kraken)
TESTNET_API_SECRET=                       # Only for Bybit/Binance testnet (not used with Kraken)

# ============================================
# SUPABASE CONFIGURATION (For API Server)
# ============================================
SUPABASE_URL=https://your-project.supabase.co  # Required for API server
SUPABASE_KEY=eyJhbGc...                        # Required: Supabase anon key
SUPABASE_SERVICE_KEY=                          # Optional: Service role key (for admin operations)

# ============================================
# DATABASE CONFIGURATION (Alternative)
# ============================================
DATABASE_URL=postgresql://...             # Optional: If not using Supabase
DB_HOST=localhost                          # Optional
DB_PORT=5432                               # Optional
DB_NAME=trading_bot                        # Optional
DB_USER=trading_user                       # Optional
DB_PASSWORD=secure_password                # Optional

# ============================================
# LOGGING CONFIGURATION
# ============================================
LOG_LEVEL=INFO                            # Recommended: DEBUG, INFO, WARNING, ERROR
LOG_FILE=data/logs/bot.log                # Optional: Log file path
LOG_MAX_FILE_SIZE=10485760                # Optional: Max log file size (10MB)
LOG_BACKUP_COUNT=30                       # Optional: Number of backup log files

# ============================================
# API SERVER CONFIGURATION
# ============================================
CORS_ORIGINS=https://your-app.vercel.app,https://your-app.railway.app  # Required: Comma-separated origins
PORT=8001                                 # Optional: API server port (default: 8001)

# ============================================
# SECURITY CONFIGURATION
# ============================================
ENABLE_RATE_LIMITING=true                 # Optional: Enable rate limiting
MAX_REQUESTS_PER_MINUTE=60                # Optional: Rate limit threshold
ENABLE_INPUT_VALIDATION=true              # Optional: Enable input validation
ENABLE_API_KEY_VALIDATION=true            # Optional: Enable API key validation
LOG_SENSITIVE_DATA=false                  # Recommended: Keep false in production
```

---

## 🚀 Railway Setup Instructions

### Step 1: Add Environment Variables

1. Go to your Railway project dashboard
2. Click on your service (Trading Bot or API Server)
3. Go to the **Variables** tab
4. Click **+ New Variable** for each environment variable
5. Add the variables from the list above

### Step 2: Service-Specific Variables

#### For Trading Bot Service:
- Focus on: `ENVIRONMENT`, `LLM_*`, `TRADING_*`, `EXCHANGE_*`, `LOG_LEVEL`

#### For API Server Service:
- Focus on: `ENVIRONMENT`, `SUPABASE_*`, `CORS_ORIGINS`

### Step 3: Secure Your Keys

- ✅ Never commit `.env` files to git
- ✅ Use Railway's environment variables (encrypted at rest)
- ✅ Rotate API keys regularly
- ✅ Use different keys for testnet vs production
- ✅ Enable Railway's audit log to track changes

---

## 📝 Example Configuration

### Minimal Production Setup (Paper Trading)

```bash
ENVIRONMENT=production
LLM_PROVIDER=deepseek
LLM_API_KEY=sk-your-deepseek-key
LLM_MODEL=deepseek-chat
TRADING_MODE=paper
USE_TESTNET=true
# Note: USE_TESTNET has limited effect with Kraken (no testnet available)
EXCHANGE=kraken  # US-friendly exchange, safe for paper trading
SYMBOL=BTC/USDT  # Note: May need BTC/USD for Kraken
LOG_LEVEL=INFO
# API keys optional for paper trading but may be needed for market data
```

### Full Production Setup (Live Trading)

```bash
ENVIRONMENT=production
LLM_PROVIDER=deepseek
LLM_API_KEY=sk-your-deepseek-key
LLM_MODEL=deepseek-chat
TRADING_MODE=live
USE_TESTNET=false
EXCHANGE=kraken
SYMBOL=BTC/USDT
EXCHANGE_API_KEY=your-kraken-api-key
EXCHANGE_API_SECRET=your-kraken-api-secret
# Note: TESTNET_API_KEY and TESTNET_API_SECRET are not used with Kraken
INITIAL_BALANCE=10000.0
MAX_POSITION_SIZE=0.1
MAX_LEVERAGE=10.0
STOP_LOSS_PERCENT=2.0
TAKE_PROFIT_PERCENT=3.0
RUN_INTERVAL_SECONDS=150
MAX_ACTIVE_POSITIONS=6
MIN_CONFIDENCE_THRESHOLD=0.6
LOG_LEVEL=INFO
```

### API Server Setup

```bash
ENVIRONMENT=production
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJhbGc...
CORS_ORIGINS=https://your-app.vercel.app
PORT=8001
```

---

## 🔍 Validation

After setting up variables, verify they're loaded correctly:

1. Check Railway logs: `railway logs`
2. Look for configuration messages at startup
3. Test API endpoints: `curl https://your-service.railway.app/health`

---

## ⚠️ Important Notes

1. **Never use `TRADING_MODE=live` with real money until thoroughly tested**
2. **Always start with `USE_TESTNET=true` for safety** (note: has limited effect with Kraken)
3. **Kraken-specific**: Kraken does not provide testnet - use `TRADING_MODE=paper` for safe paper trading
4. **Monitor your LLM API usage to avoid unexpected costs**
5. **Set appropriate `MAX_POSITION_SIZE` based on your risk tolerance**
6. **Use strong, unique API keys for production**
7. **Enable Railway's usage alerts to monitor costs**

---

## 🆘 Troubleshooting

### Bot won't start
- Check `ENVIRONMENT=production` is set
- Verify `LLM_API_KEY` is valid
- Check logs: `railway logs`

### API server CORS errors
- Verify `CORS_ORIGINS` includes your frontend URL
- Check origin is exact match (no trailing slashes)

### Database connection issues
- Verify `SUPABASE_KEY` and `SUPABASE_URL` are correct
- Check Supabase project is active
- Verify database schema is initialized

### High LLM costs
- Monitor `LLM_MAX_TOKENS` - lower if needed
- Check `RUN_INTERVAL_SECONDS` - longer intervals = fewer API calls
- Review logs for excessive API calls
