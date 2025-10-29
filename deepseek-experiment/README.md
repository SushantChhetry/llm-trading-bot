# DeepSeek Trading Bot Experiment

A modular Python trading bot powered by DeepSeek LLM for automated cryptocurrency trading decisions. Designed for solo developers to experiment with paper trading before moving to live trading.

## 🎯 Experiment Goals

- Test LLM-driven trading strategies in a safe, paper trading environment
- Understand how AI models make trading decisions
- Build a foundation that can easily upgrade to live trading
- Learn from simulated trades without financial risk

## 📁 Project Structure

```
deepseek-experiment/
├── README.md              # This file
├── requirements.txt      # Python dependencies
├── config/               # Configuration module
│   └── config.py         # Centralized settings
├── src/                  # Bot source code
│   ├── __init__.py
│   ├── data_fetcher.py   # Exchange data fetching (ccxt)
│   ├── llm_client.py    # DeepSeek API integration
│   ├── trading_engine.py # Paper trading simulation
│   └── main.py          # Main entry point & scheduler
├── tests/                # Unit tests
│   ├── __init__.py
│   └── test_trading_engine.py
└── data/                 # Generated data directory
    ├── logs/            # Log files
    ├── trades.json      # Trade history
    └── portfolio.json   # Portfolio state
```

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Settings

Edit `config/config.py` or set environment variables:

```bash
# Exchange API (optional for testnet)
export EXCHANGE_API_KEY="your_key"
export EXCHANGE_API_SECRET="your_secret"

# DeepSeek API (required for live mode)
export DEEPSEEK_API_KEY="your_deepseek_key"

# Trading settings
export SYMBOL="BTC/USDT"
export INITIAL_BALANCE="10000.0"
export RUN_INTERVAL_SECONDS="300"  # 5 minutes
```

Or modify values directly in `config/config.py`.

### 3. Run the Bot

```bash
# From project root
python -m src.main
```

The bot will:
- Run on a 5-minute schedule (configurable)
- Fetch market data from Bybit/Binance testnet
- Get trading decisions from DeepSeek (or mock mode)
- Execute paper trades and track portfolio
- Log all activity to `data/logs/bot.log`

### 4. Stop the Bot

Press `Ctrl+C` to gracefully stop. The bot will print a final portfolio summary.

## 🤖 How LLM Decisions Work

The bot uses a structured approach to LLM decision-making that ensures reliable, safe trading decisions:

### Prompt Template

The LLM receives a comprehensive prompt including:
- **Market Data**: Current price, volume, 24h change
- **Portfolio State**: Balance, positions, returns, trade count
- **Trading Rules**: Risk management guidelines
- **Response Format**: Structured JSON requirements

Example prompt structure:
```
You are an expert cryptocurrency trading assistant. Analyze the following market data and portfolio state to make a trading decision.

MARKET DATA:
- Symbol: BTC/USDT
- Current Price: $50,000.00
- 24h Volume: 1,000,000
- 24h Change: 2.50%

PORTFOLIO STATE:
- Available Balance: $5,000.00
- Total Portfolio Value: $10,000.00
- Open Positions: 1
- Total Return: 5.20%
- Total Trades: 10

REQUIRED RESPONSE FORMAT (JSON only):
{
    "action": "buy|sell|hold",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of your decision",
    "position_size": 0.0-1.0,
    "risk_assessment": "low|medium|high"
}
```

### Response Validation

All LLM responses are validated for:
- ✅ **Required fields**: action, confidence, reasoning
- ✅ **Valid actions**: buy, sell, hold only
- ✅ **Confidence range**: 0.0 to 1.0
- ✅ **JSON format**: Proper parsing and error handling
- ✅ **Fallback handling**: Hold decision on validation failure

### Decision Execution

The bot executes trades based on:
- **Confidence threshold**: Only trades if confidence > 0.6
- **Position sizing**: Uses LLM's position_size recommendation
- **Risk assessment**: Logs risk level for monitoring
- **Reasoning**: Full LLM reasoning saved with each trade

### Mock Mode vs Live Mode

**Mock Mode** (default):
- Simulates realistic trading decisions based on market conditions
- Uses market momentum to determine buy/sell/hold actions
- Perfect for testing and development

**Live Mode** (with API key):
- Real LLM API calls to DeepSeek or other providers
- TODO markers show where to implement actual API calls
- Easy to swap between different LLM providers

### Upgrading to Real LLM APIs

To use DeepSeek or other LLM providers:

1. **Get API credentials** from your chosen provider
2. **Set environment variable**: `export DEEPSEEK_API_KEY="your_key"`
3. **Update API call** in `src/llm_client.py`:
   ```python
   # TODO: Replace with actual DeepSeek API call
   response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
   ```

4. **For OpenAI**: Change API URL and headers in `_make_api_request()`
5. **For Anthropic**: Update payload format for Claude API

## 🔧 Configuration

### Trading Mode

The bot defaults to **paper trading** mode. All trades are simulated and recorded in `data/trades.json`.

### Exchange Setup

**Bybit Testnet** (default):
- No API keys needed for testnet
- Automatically uses testnet when `USE_TESTNET=true`

**Binance Testnet**:
- Set `EXCHANGE="binance"` in config
- Testnet is automatically enabled

**Switching to Live Trading**:
1. Set `USE_TESTNET=false`
2. Add real API keys via environment variables
3. **Warning**: Only do this after thorough testing!

### LLM Setup

**Mock Mode** (default if no API key):
- Uses simulated responses for testing
- Perfect for development without API costs

**DeepSeek Live Mode**:
1. Get API key from [DeepSeek](https://platform.deepseek.com/)
2. Set `DEEPSEEK_API_KEY` environment variable
3. Mock mode will automatically disable

**Swapping LLM Providers**:
To use a different LLM (OpenAI, Anthropic, etc.), modify `src/llm_client.py`:
- Change API endpoint in `_make_api_request()`
- Update request format if needed
- The interface remains the same (`get_trading_decision()`)

## 📊 Monitoring

### Logs
- Real-time logs in console
- Persistent logs in `data/logs/bot.log`

### Trade History
All trades are saved to `data/trades.json`:
```json
{
  "id": 1,
  "timestamp": "2024-01-01T12:00:00",
  "symbol": "BTC/USDT",
  "side": "buy",
  "price": 50000.0,
  "quantity": 0.002,
  "amount_usdt": 100.0,
  "confidence": 0.85,
  "mode": "paper"
}
```

### Portfolio State
Current portfolio snapshot in `data/portfolio.json`:
```json
{
  "balance": 9800.0,
  "positions": {...},
  "timestamp": "2024-01-01T12:00:00"
}
```

## 🔄 Upgrading to Live Trading

The bot is designed for easy upgrade. To switch from paper to live trading:

### Option 1: Modify `src/trading_engine.py`

Replace paper trading methods with real exchange API calls:

```python
def execute_buy(self, symbol: str, price: float, amount_usdt: float, confidence: float):
    if config.TRADING_MODE == "live":
        # Use ccxt to place real order
        order = self.exchange.create_market_buy_order(symbol, amount_usdt)
        # Record trade...
    else:
        # Paper trading logic...
```

### Option 2: Add Exchange Integration

Add a real exchange client in `src/data_fetcher.py`:

```python
def execute_trade(self, symbol: str, side: str, amount: float):
    """Execute real trade via exchange API."""
    if side == "buy":
        return self.exchange.create_market_buy_order(symbol, amount)
    else:
        return self.exchange.create_market_sell_order(symbol, amount)
```

**Important Safety Steps Before Live Trading:**
1. ✅ Test thoroughly in paper mode
2. ✅ Start with small amounts (`MAX_POSITION_SIZE`)
3. ✅ Enable stop-loss and take-profit limits
4. ✅ Monitor closely for first few days
5. ✅ Keep API keys secure (never commit to git)

## 🧪 Testing

### Run All Tests

```bash
python -m pytest tests/
# or
python -m unittest discover tests
```

### Test Specific Components

```bash
# Test LLM client functionality
python -m unittest tests.test_llm_client

# Test trading engine with LLM integration
python -m unittest tests.test_trading_engine_enhanced

# Test basic trading engine
python -m unittest tests.test_trading_engine
```

### Test Coverage

The test suite covers:
- ✅ **Prompt formatting** with market data and portfolio state
- ✅ **JSON response validation** with various edge cases
- ✅ **Mock LLM responses** with realistic decision logic
- ✅ **Trade execution** with LLM context
- ✅ **Error handling** for malformed responses
- ✅ **Portfolio tracking** with enhanced trade records

### Manual Testing

Test the bot end-to-end:

```bash
# Run in mock mode (no API key needed)
python -m src.main

# Check logs for LLM decision details
tail -f data/logs/bot.log

# Review trade history with LLM context
cat data/trades.json | jq '.[] | {action, confidence, llm_reasoning, llm_risk_assessment}'
```

## 💡 Tips for Solo Workflow

### Development Workflow
1. **Start with mock mode** - Develop without API costs
2. **Use testnet** - Real market data, fake money
3. **Review logs** - Understand bot behavior patterns
4. **Small iterations** - Test changes incrementally
5. **Version control** - Track strategy changes in git

### Experiment Ideas
- Adjust `MAX_POSITION_SIZE` to test different position sizing
- Modify LLM prompts in `llm_client.py` to change decision logic
- Add technical indicators to market data for better context
- Implement different confidence thresholds for trading
- Test different timeframes (change `RUN_INTERVAL_SECONDS`)

### Debugging
- Check `data/logs/bot.log` for detailed execution traces
- Review `data/trades.json` to analyze trade history
- Use Python debugger: add `breakpoint()` in code
- Enable `LOG_LEVEL=DEBUG` in config for verbose output

## 📝 Module Documentation

### `data_fetcher.py`
Fetches live market data from exchanges using ccxt. Supports:
- Ticker data (price, volume)
- OHLCV candlesticks
- Order book data

### `llm_client.py`
Handles LLM API communication. Features:
- DeepSeek API integration
- Mock mode for testing
- Error handling with fallback to "hold"

### `trading_engine.py`
Paper trading simulation engine. Tracks:
- Portfolio balance
- Open positions
- Trade history
- Profit/loss calculations

### `main.py`
Main orchestrator that:
- Schedules trading cycles
- Coordinates all components
- Handles errors gracefully
- Logs all activity

## 🔒 Security Best Practices

1. **Never commit API keys** - Use environment variables
2. **Use `.gitignore`** - Exclude `data/` and `.env` files
3. **Testnet first** - Always validate in safe environment
4. **API key permissions** - Use read-only keys for data fetching
5. **Regular backups** - Keep trade history backed up

## 🤝 Contributing

This is a solo developer experiment, but feel free to:
- Fork and customize for your needs
- Report issues or suggest improvements
- Share your results and learnings

## ⚠️ Disclaimer

This bot is for **educational and experimental purposes only**. Cryptocurrency trading involves substantial risk. The author is not responsible for any financial losses. Always:
- Start with paper trading
- Test thoroughly before live trading
- Never invest more than you can afford to lose
- Understand the risks involved

## 📄 License

See LICENSE file for details.

