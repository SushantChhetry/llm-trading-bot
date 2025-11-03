# Configuration Reference

Complete reference for all configuration options in the Alpha Arena Trading Bot.

## 📋 Configuration Methods

The bot supports configuration via:
1. **Environment Variables** (recommended) - `.env` file or system environment
2. **Command Line Arguments** - Override specific settings
3. **config.yaml** - YAML configuration file (if used)

**Precedence**: Command Line > Environment Variables > Defaults

---

## 🔧 Core Configuration

### Environment

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `ENVIRONMENT` | string | `development` | No | `production` or `development` (affects logging, security) |

---

## 🤖 LLM Configuration

### Required

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `LLM_PROVIDER` | string | `mock` | Yes* | Provider: `deepseek`, `openai`, `anthropic`, `mock` |
| `LLM_API_KEY` | string | `""` | Yes* | API key for LLM provider (*not needed for `mock`) |
| `LLM_MODEL` | string | auto | Yes* | Model name (*auto-set if empty based on provider) |

### Optional

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LLM_API_URL` | string | auto | Custom API URL (auto-detected if empty) |
| `LLM_TEMPERATURE` | float | `0.7` | Sampling temperature (0.0-2.0) |
| `LLM_MAX_TOKENS` | int | `2000` | Maximum tokens in response |
| `LLM_TIMEOUT` | int | `30` | Request timeout in seconds |

### Provider-Specific Defaults

**DeepSeek:**
- API URL: `https://api.deepseek.com/v1/chat/completions`
- Default Model: `deepseek-chat`

**OpenAI:**
- API URL: `https://api.openai.com/v1/chat/completions`
- Default Model: `gpt-3.5-turbo`

**Anthropic:**
- API URL: `https://api.anthropic.com/v1/messages`
- Default Model: `claude-3-sonnet-20240229`

---

## 💰 Trading Configuration

### Required

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `TRADING_MODE` | string | `paper` | Yes | `paper` or `live` |
| `EXCHANGE` | string | `bybit` | Yes | Exchange: `bybit`, `binance`, `coinbase`, `kraken` |
| `SYMBOL` | string | `BTC/USDT` | Yes | Trading pair (e.g., `BTC/USDT`, `ETH/USDT`) |
| `USE_TESTNET` | bool | `true` | Yes | Use testnet exchange data |

### Recommended

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `INITIAL_BALANCE` | float | `10000.0` | Starting balance in USDT |
| `RUN_INTERVAL_SECONDS` | int | `150` | Bot cycle interval (150 = 2.5 minutes, Alpha Arena style) |

### Exchange API Keys

| Variable | Type | Default | When Required |
|----------|------|---------|---------------|
| `EXCHANGE_API_KEY` | string | `""` | If `TRADING_MODE=live` |
| `EXCHANGE_API_SECRET` | string | `""` | If `TRADING_MODE=live` |
| `TESTNET_API_KEY` | string | `""` | If `USE_TESTNET=true` and connecting to real testnet |
| `TESTNET_API_SECRET` | string | `""` | If `USE_TESTNET=true` and connecting to real testnet |

**Note**: If `USE_TESTNET=true` and `TESTNET_API_KEY` is set, testnet keys will be used instead of live keys.

---

## ⚠️ Risk Management

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MAX_POSITION_SIZE` | float | `0.1` | Maximum % of balance per trade (0.1 = 10%) |
| `MAX_LEVERAGE` | float | `10.0` | Maximum allowed leverage (1.0-10.0) |
| `DEFAULT_LEVERAGE` | float | `1.0` | Default leverage if not specified by LLM |
| `STOP_LOSS_PERCENT` | float | `2.0` | Stop loss percentage (2.0 = 2%) |
| `TAKE_PROFIT_PERCENT` | float | `3.0` | Take profit percentage (3.0 = 3%) |
| `MAX_RISK_PER_TRADE` | float | `2.0` | Maximum risk per trade as % of portfolio |
| `TRADING_FEE_PERCENT` | float | `0.05` | Trading fee percentage (0.05 = 0.05%) |

---

## 📊 Position Management

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MAX_ACTIVE_POSITIONS` | int | `6` | Maximum simultaneous positions |
| `MIN_CONFIDENCE_THRESHOLD` | float | `0.6` | Minimum confidence to trade (0.0-1.0) |
| `FEE_IMPACT_WARNING_THRESHOLD` | float | `20.0` | Warn if fees > X% of PnL |

---

## 💾 Database Configuration

### Supabase (Recommended)

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `SUPABASE_URL` | string | `""` | Yes* | Supabase project URL (*required for API server) |
| `SUPABASE_KEY` | string | `""` | Yes* | Supabase anon key (*required for API server) |
| `SUPABASE_SERVICE_KEY` | string | `""` | No | Service role key (for admin operations) |

### Direct PostgreSQL (Alternative)

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `DATABASE_URL` | string | `""` | No | PostgreSQL connection string (for Alembic migrations) |

**Note**: See [Database Setup Guide](../guides/database/setup.md) for details on SUPABASE_URL vs DATABASE_URL.

---

## 📝 Logging Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LOG_LEVEL` | string | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_FILE` | string | `data/logs/bot.log` | Log file path |
| `LOG_MAX_FILE_SIZE` | int | `10485760` | Max log file size in bytes (10MB) |
| `LOG_BACKUP_COUNT` | int | `30` | Number of backup log files to keep |

---

## 🌐 API Server Configuration

| Variable | Type | Default | Required | Description |
|----------|------|---------|----------|-------------|
| `PORT` | int | `8001` | No | API server port |
| `CORS_ORIGINS` | string | `""` | Yes* | Comma-separated allowed origins (*required for production) |

**CORS_ORIGINS Examples:**
```bash
# Single origin
CORS_ORIGINS=https://your-app.vercel.app

# Multiple origins
CORS_ORIGINS=https://your-app.vercel.app,https://your-app.railway.app
```

---

## 🔒 Security Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ENABLE_RATE_LIMITING` | bool | `true` | Enable rate limiting |
| `MAX_REQUESTS_PER_MINUTE` | int | `60` | Rate limit threshold |
| `ENABLE_INPUT_VALIDATION` | bool | `true` | Enable input validation |
| `ENABLE_API_KEY_VALIDATION` | bool | `true` | Enable API key validation |
| `LOG_SENSITIVE_DATA` | bool | `false` | Log sensitive data (keep false in production) |

---

## 📝 Configuration Examples

### Minimal Setup (Testing)

```bash
# .env file
LLM_PROVIDER=mock
TRADING_MODE=paper
EXCHANGE=bybit
SYMBOL=BTC/USDT
USE_TESTNET=true
```

### Development Setup

```bash
# .env file
ENVIRONMENT=development
LLM_PROVIDER=deepseek
LLM_API_KEY=sk-your-deepseek-key
LLM_MODEL=deepseek-chat
TRADING_MODE=paper
USE_TESTNET=true
EXCHANGE=bybit
SYMBOL=BTC/USDT
INITIAL_BALANCE=10000.0
LOG_LEVEL=DEBUG
```

### Production Setup (Paper Trading)

```bash
# .env file
ENVIRONMENT=production
LLM_PROVIDER=deepseek
LLM_API_KEY=sk-your-deepseek-key
LLM_MODEL=deepseek-chat
TRADING_MODE=paper
USE_TESTNET=true
EXCHANGE=bybit
SYMBOL=BTC/USDT
INITIAL_BALANCE=10000.0
RUN_INTERVAL_SECONDS=150
MAX_POSITION_SIZE=0.1
MAX_LEVERAGE=10.0
STOP_LOSS_PERCENT=2.0
TAKE_PROFIT_PERCENT=3.0
MAX_ACTIVE_POSITIONS=6
MIN_CONFIDENCE_THRESHOLD=0.6
LOG_LEVEL=INFO

# Database (if using)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
DATABASE_URL=postgresql://...
```

### Production Setup (Live Trading)

```bash
# .env file
ENVIRONMENT=production
LLM_PROVIDER=deepseek
LLM_API_KEY=sk-your-deepseek-key
LLM_MODEL=deepseek-chat
TRADING_MODE=live
USE_TESTNET=false
EXCHANGE=bybit
SYMBOL=BTC/USDT
EXCHANGE_API_KEY=your-exchange-key
EXCHANGE_API_SECRET=your-exchange-secret
INITIAL_BALANCE=10000.0
RUN_INTERVAL_SECONDS=150
MAX_POSITION_SIZE=0.1
MAX_LEVERAGE=10.0
STOP_LOSS_PERCENT=2.0
TAKE_PROFIT_PERCENT=3.0
MAX_ACTIVE_POSITIONS=6
MIN_CONFIDENCE_THRESHOLD=0.6
LOG_LEVEL=INFO

# Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
DATABASE_URL=postgresql://...
```

### API Server Setup

```bash
# .env file
ENVIRONMENT=production
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
CORS_ORIGINS=https://your-app.vercel.app,https://your-app.railway.app
PORT=8001
```

---

## 🎯 Agent Behavior Simulation

Pre-configured settings to simulate different agent behaviors:

### Grok 4 Style (Conservative, Long Holds)

```bash
MAX_ACTIVE_POSITIONS=2
MIN_CONFIDENCE_THRESHOLD=0.8
MAX_POSITION_SIZE=0.15
```

### Gemini 2.5 Pro Style (Active, Frequent Trading)

```bash
MAX_ACTIVE_POSITIONS=6
MIN_CONFIDENCE_THRESHOLD=0.5
MAX_POSITION_SIZE=0.05
```

### Qwen 3 Style (Large Positions, High Confidence)

```bash
MAX_ACTIVE_POSITIONS=2
MIN_CONFIDENCE_THRESHOLD=0.7
MAX_POSITION_SIZE=0.25
```

### Claude Sonnet 4.5 Style (Conservative, Few Positions)

```bash
MAX_ACTIVE_POSITIONS=1
MIN_CONFIDENCE_THRESHOLD=0.8
MAX_POSITION_SIZE=0.1
```

---

## ✅ Validation

### Check Configuration

```bash
# Test configuration loading
python -c "from src.startup_validator import validate_startup; validate_startup()"

# Check specific variable
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('LLM_PROVIDER'))"
```

### Common Validation Errors

**Invalid LLM Provider:**
- Must be: `deepseek`, `openai`, `anthropic`, or `mock`
- Case-sensitive

**Invalid Trading Mode:**
- Must be: `paper` or `live`
- Case-sensitive

**Invalid Leverage:**
- Must be between 1.0 and 10.0
- Cannot exceed MAX_LEVERAGE

**Missing Required Variables:**
- Check [Quick Start Guide](../getting-started/quickstart.md) for minimum setup

---

## 🔄 Configuration Priority

When multiple configuration sources exist, priority is:

1. **Command Line Arguments** (highest priority)
2. **Environment Variables** (from `.env` or system)
3. **Defaults** (lowest priority)

Example:
```bash
# .env has: MAX_POSITION_SIZE=0.1
# Command line: --max-position-size 0.2
# Result: 0.2 (command line wins)
```

---

## 📋 Configuration Checklist

### Before Starting Bot

- [ ] `LLM_PROVIDER` set (or use `mock` for testing)
- [ ] `LLM_API_KEY` set (if not using `mock`)
- [ ] `TRADING_MODE` set to `paper` or `live`
- [ ] `EXCHANGE` and `SYMBOL` configured
- [ ] Risk parameters reviewed (`MAX_POSITION_SIZE`, `MAX_LEVERAGE`)
- [ ] Logging configured (`LOG_LEVEL`)

### Before Production Deployment

- [ ] `ENVIRONMENT=production` set
- [ ] All API keys secured (not in code)
- [ ] Database credentials configured
- [ ] CORS settings configured (if using API server)
- [ ] Rate limiting enabled
- [ ] Sensitive data logging disabled
- [ ] Backup configuration reviewed

---

## 🆘 Troubleshooting

### Configuration Not Loading

1. Check `.env` file exists in correct location
2. Verify variable names (case-sensitive, no spaces)
3. Check for syntax errors (no quotes around values)
4. Ensure `python-dotenv` is installed

### Invalid Values

1. Check valid enum values (provider, mode, etc.)
2. Verify numeric ranges (leverage, percentages)
3. Review [Troubleshooting Guide](../troubleshooting/common-issues.md)

---

## Related Documentation

- **[Quick Start Guide](../getting-started/quickstart.md)** - Minimal configuration
- **[Database Setup Guide](../guides/database/setup.md)** - Database configuration
- **[Troubleshooting Guide](../troubleshooting/common-issues.md)** - Config issues
- **[Environment Variables Reference](environment-variables.md)** - Complete Railway environment variables

---

**Last Updated**: See git history for changes to configuration options.
