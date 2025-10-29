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

### ⚠️ Important for US Users
**Bybit and Binance are restricted in the USA.** US users should:
- Use **mock mode** (default) for development
- Use **Coinbase** or **Kraken** for live trading
- See [US-Friendly Alternatives](#us-friendly-alternatives) below

### 1. Setup Environment

```bash
# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Settings

**Option A: Use .env file (Recommended)**
```bash
# Copy the template
cp .env.template .env

# Edit with your settings
nano .env
```

**Option B: Set environment variables**
```bash
# Basic testnet setup (no API keys needed)
export USE_TESTNET=true
export TRADING_MODE=paper
export LLM_PROVIDER=mock

# For real LLM API
export LLM_PROVIDER=deepseek
export LLM_API_KEY="your_api_key"

# For testnet API keys
export TESTNET_API_KEY="your_testnet_key"
export TESTNET_API_SECRET="your_testnet_secret"
```

### 3. Run the Bot

```bash
# Basic run (testnet + mock LLM)
python -m src.main

# With command line arguments
python -m src.main --provider deepseek --api-key YOUR_KEY
python -m src.main --no-testnet --live
python -m src.main --help  # See all options
```

### 4. Monitor Performance

```bash
# View real-time logs
tail -f data/logs/bot.log

# Analyze trading performance
python scripts/visualize_pnl.py

# Save performance charts
python scripts/visualize_pnl.py --save-charts
```

### 5. Stop the Bot

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

The bot now supports multiple LLM providers with automatic fallback to mock mode on API failures.

#### Supported Providers

| Provider | Status | API Key Required | Cost |
|----------|--------|------------------|------|
| **Mock** | ✅ Built-in | No | Free |
| **DeepSeek** | ✅ Ready | Yes | Low |
| **OpenAI** | ✅ Ready | Yes | Medium |
| **Anthropic** | ✅ Ready | Yes | Medium |

#### Setup Instructions

**1. DeepSeek API (Recommended)**
```bash
# Get API key from https://platform.deepseek.com/
export LLM_PROVIDER=deepseek
export LLM_API_KEY="sk-your-deepseek-key"

# Run bot
python -m src.main
```

**2. OpenAI API**
```bash
# Get API key from https://platform.openai.com/
export LLM_PROVIDER=openai
export LLM_API_KEY="sk-your-openai-key"

# Run bot
python -m src.main
```

**3. Anthropic Claude API**
```bash
# Get API key from https://console.anthropic.com/
export LLM_PROVIDER=anthropic
export LLM_API_KEY="sk-ant-your-anthropic-key"

# Run bot
python -m src.main
```

#### API Fallback Behavior

- ✅ **Automatic fallback**: If API call fails, bot automatically switches to mock mode for that cycle
- ✅ **Transparent logging**: All API failures are logged with clear error messages
- ✅ **No interruption**: Bot continues running even if API is temporarily unavailable
- ✅ **Easy debugging**: Check logs to see which mode is being used

## 🔧 Configuration

### Trading Mode

The bot defaults to **paper trading** mode. All trades are simulated and recorded in `data/trades.json`.

### Exchange Setup

#### Testnet Mode (Recommended for Development)

**Bybit Testnet** (default):
```bash
# No API keys needed for basic testnet
export USE_TESTNET=true
export EXCHANGE=bybit

# Optional: Add testnet API keys for more features
export TESTNET_API_KEY="your_bybit_testnet_key"
export TESTNET_API_SECRET="your_bybit_testnet_secret"
```

**Binance Testnet**:
```bash
export USE_TESTNET=true
export EXCHANGE=binance
export TESTNET_API_KEY="your_binance_testnet_key"
export TESTNET_API_SECRET="your_binance_testnet_secret"
```

#### Getting Testnet API Keys

⚠️ **Important Note for US Users**: Many exchanges (Bybit, Binance) are restricted in the USA. See [US-Friendly Alternatives](#us-friendly-alternatives) below.

**Bybit Testnet (Non-US Users):**
1. Go to [https://testnet.bybit.com/](https://testnet.bybit.com/)
2. Create account and verify email
3. Go to API Management → Create New Key
4. Set permissions: **Read** (for market data)
5. Copy API Key and Secret

**Binance Testnet (Non-US Users):**
1. Go to [https://testnet.binance.vision/](https://testnet.binance.vision/)
2. Create account and verify email
3. Go to API Management → Create API
4. Set permissions: **Enable Reading** (for market data)
5. Copy API Key and Secret

#### US-Friendly Alternatives

**Coinbase Pro/Advanced Trade (US Users):**
1. Go to [https://pro.coinbase.com/](https://pro.coinbase.com/)
2. Create account and complete KYC
3. Go to API Settings → Create API Key
4. Set permissions: **View** (for market data)
5. Copy API Key and Secret

**Kraken (US Users):**
1. Go to [https://www.kraken.com/](https://www.kraken.com/)
2. Create account and complete verification
3. Go to Security → API Management → Add Key
4. Set permissions: **Query Funds** (for market data)
5. Copy API Key and Secret

**For Development/Testing (US Users):**
- Use **mock mode** (default) - no API keys needed
- Use **paper trading** with live market data from free APIs
- Consider using **Alpaca Markets** for US stock/crypto trading

### US User Setup Examples

**Option 1: Mock Mode (No API Keys)**
```bash
# Perfect for development and testing
export LLM_PROVIDER=mock
export USE_TESTNET=true
export TRADING_MODE=paper
python -m src.main
```

**Option 2: Coinbase (US-Friendly)**
```bash
# Get API key from pro.coinbase.com
export EXCHANGE=coinbase
export EXCHANGE_API_KEY="your_coinbase_key"
export EXCHANGE_API_SECRET="your_coinbase_secret"
export USE_TESTNET=false
export TRADING_MODE=paper  # Start with paper trading!
python -m src.main
```

**Option 3: Kraken (US-Friendly)**
```bash
# Get API key from kraken.com
export EXCHANGE=kraken
export EXCHANGE_API_KEY="your_kraken_key"
export EXCHANGE_API_SECRET="your_kraken_secret"
export USE_TESTNET=false
export TRADING_MODE=paper  # Start with paper trading!
python -m src.main
```

#### Live Trading Setup (Advanced)

⚠️ **WARNING**: Only enable live trading after thorough testnet testing!

```bash
# Enable live trading
export TRADING_MODE=live
export USE_TESTNET=false

# Add live API keys
export EXCHANGE_API_KEY="your_live_api_key"
export EXCHANGE_API_SECRET="your_live_api_secret"

# Set appropriate permissions for live trading
# Bybit: Enable "Trade" permissions
# Binance: Enable "Spot & Margin Trading"
```

#### Command Line Overrides

```bash
# Force testnet mode
python -m src.main --no-testnet

# Force live trading
python -m src.main --live

# Use specific exchange
python -m src.main --exchange binance
```

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

### Performance Analysis

Use the built-in P&L visualization script:

```bash
# Show performance summary and charts
python scripts/visualize_pnl.py

# Save charts to files
python scripts/visualize_pnl.py --save-charts

# Show only summary statistics
python scripts/visualize_pnl.py --summary-only

# Analyze specific data directory
python scripts/visualize_pnl.py --data-dir /path/to/data
```

**Visualization Features:**
- 📊 **P&L Timeline**: Cumulative profit over time
- 📈 **Trade Analysis**: Individual trade profits/losses
- 🤖 **LLM Insights**: Confidence distribution, risk assessment patterns
- 📋 **Performance Summary**: Win rate, average profit, total trades

## 🧪 Experimentation & Parameter Tuning

The project includes advanced experimentation features for systematic testing of trading strategies and LLM behaviors.

### Experiment Runner

Run parameter sweeps and systematic experiments:

```bash
# Run single experiment with custom parameters
python -m src.experiment_runner --llm-provider deepseek --max-position-size 0.05

# Run parameter sweep from configuration file
python -m src.experiment_runner --config experiments/risk_sweep.yaml --duration 60

# Run provider comparison
python -m src.experiment_runner --provider-sweep deepseek,openai,anthropic --duration 30
```

### Experiment Configuration

Create YAML configuration files for complex parameter sweeps:

```yaml
# experiments/my_experiment.yaml
llm_provider: ["deepseek", "openai"]
max_position_size: [0.01, 0.05, 0.10]
stop_loss_percent: [2.0, 5.0, 10.0]
run_interval: [180, 300, 600]
use_testnet: true
trading_mode: "paper"
```

### Live Monitoring Dashboard

Monitor bot performance in real-time:

```bash
# Monitor indefinitely
python scripts/monitor_dashboard.py

# Monitor for 60 minutes with custom refresh
python scripts/monitor_dashboard.py --duration 60 --refresh-interval 10

# Custom alert thresholds
python scripts/monitor_dashboard.py --max-consecutive-losses 3 --max-drawdown-percent 5.0
```

### Results Comparison

Compare multiple experiments and generate analysis:

```bash
# Compare by LLM provider
python scripts/compare_results.py --parameter llm_provider --plot

# Compare by position size
python scripts/compare_results.py --parameter max_position_size --export results.csv

# Generate correlation analysis
python scripts/compare_results.py --parameter llm_provider --correlation --plot
```

### Experiment Features

#### Parameter Sweeps
- **Risk Levels**: Test different position sizes and stop-loss/take-profit levels
- **LLM Providers**: Compare DeepSeek, OpenAI, and Anthropic performance
- **Trading Intervals**: Test different run frequencies
- **Strategy Parameters**: Optimize trading strategy parameters

#### Advanced Metrics
- **Performance Metrics**: Win rate, Sharpe ratio, max drawdown, volatility
- **Risk Metrics**: Profit factor, consecutive wins/losses, trade duration
- **LLM Metrics**: Confidence patterns, risk assessment distribution
- **Hyperparameter Tracking**: Complete parameter logging for reproducibility

#### Monitoring & Alerts
- **Real-time Dashboard**: Live P&L, trade history, LLM decisions
- **Dangerous Pattern Detection**: Consecutive losses, extreme confidence
- **Performance Tracking**: Win rate, drawdown monitoring
- **Alert System**: Configurable thresholds with rate limiting

#### Results Analysis
- **Statistical Comparison**: Mean, std, min/max across parameter groups
- **Visual Analysis**: Bar charts, correlation heatmaps, performance plots
- **Export Options**: CSV, JSON, Excel formats
- **Correlation Analysis**: Parameter-metric relationships

### Experiment Workflow

1. **Design Experiment**: Create YAML config or use command-line parameters
2. **Run Experiments**: Use experiment runner for systematic testing
3. **Monitor Progress**: Use live dashboard for real-time monitoring
4. **Analyze Results**: Use comparison tools for statistical analysis
5. **Iterate**: Refine parameters based on results

### Best Practices

#### For Solo Developers

1. **Start Small**: Begin with single experiments before complex sweeps
2. **Use Testnet**: Always test strategies on testnet before live trading
3. **Document Everything**: Hyperparameters are automatically logged
4. **Monitor Actively**: Use dashboard during experiments for early detection
5. **Compare Systematically**: Use comparison tools to identify best parameters

#### Experiment Design

1. **Control Variables**: Change one parameter at a time for clear attribution
2. **Sufficient Duration**: Run experiments long enough for statistical significance
3. **Multiple Runs**: Repeat experiments to account for randomness
4. **Baseline Comparison**: Always include a baseline configuration
5. **Risk Management**: Set appropriate stop-losses and position sizes

#### Parameter Selection

1. **LLM Providers**: Test different providers for consistency
2. **Risk Levels**: Sweep position sizes from conservative to aggressive
3. **Time Intervals**: Test different run frequencies for market conditions
4. **Strategy Parameters**: Optimize stop-loss and take-profit levels
5. **Market Conditions**: Test across different market volatility periods

### Example Experiments

#### Risk Level Sweep
```bash
python -m src.experiment_runner --config experiments/risk_sweep.yaml --duration 60
```
Tests 4 position sizes × 3 stop-loss levels × 3 take-profit levels = 36 combinations

#### Provider Comparison
```bash
python -m src.experiment_runner --config experiments/provider_comparison.yaml --duration 30
```
Compares DeepSeek, OpenAI, and Anthropic with identical parameters

#### Strategy Optimization
```bash
python -m src.experiment_runner --config experiments/strategy_optimization.yaml --duration 45
```
Tests 3 position sizes × 3 stop-loss levels × 3 take-profit levels × 3 intervals = 81 combinations

## 🔬 Automated Hyperparameter Optimization

The project includes advanced automated hyperparameter optimization for systematic strategy tuning.

### Strategy Optimization

Run automated optimization to find optimal trading parameters:

```bash
# Grid search with conservative parameters
python scripts/optimize_strategy.py --method grid --preset conservative --duration 30

# Random search with custom parameters
python scripts/optimize_strategy.py --method random --trials 50 --duration 45

# LLM provider comparison
python scripts/optimize_strategy.py --method grid --preset llm_comparison --runs 5

# Custom parameter optimization
python scripts/optimize_strategy.py --method grid \
  --max-position-size 0.05,0.10,0.15 \
  --stop-loss 2.0,5.0,8.0 \
  --take-profit 8.0,12.0,15.0 \
  --confidence-threshold 0.6,0.7,0.8
```

### Optimization Features

#### Parameter Search Methods
- **Grid Search**: Systematic exploration of all parameter combinations
- **Random Search**: Efficient sampling of parameter space
- **Multi-run Averaging**: Statistical significance through multiple runs
- **Reproducible Results**: Seed-based reproducibility for consistent results

#### Supported Parameters
- **Position Sizing**: `max_position_size` (0.01 to 0.25)
- **Risk Management**: `stop_loss_percent`, `take_profit_percent`
- **Decision Thresholds**: `confidence_threshold` (0.5 to 0.9)
- **LLM Providers**: `llm_provider` (deepseek, openai, anthropic)
- **Trading Intervals**: `run_interval` (180 to 900 seconds)

#### Performance Metrics
- **Risk-Adjusted Returns**: Sharpe ratio, Sortino ratio
- **Risk Metrics**: Max drawdown, volatility, VaR
- **Trading Performance**: Win rate, profit factor, average trade duration
- **LLM Performance**: Confidence patterns, decision consistency

### Visualization and Analysis

Create comprehensive visualizations of optimization results:

```bash
# Comprehensive analysis report
python scripts/visualize_optimization.py --comprehensive

# Parameter interaction heatmap
python scripts/visualize_optimization.py --heatmap max_position_size stop_loss_percent

# Best configurations analysis
python scripts/visualize_optimization.py --best-configs --top-k 10

# Parameter importance analysis
python scripts/visualize_optimization.py --importance
```

#### Visualization Types
- **Parameter Heatmaps**: Interaction effects between parameters
- **Scatter Plots**: Parameter vs performance relationships
- **Distribution Plots**: Performance metric distributions
- **Best Configs Analysis**: Top performing configurations
- **Parameter Importance**: Correlation analysis across metrics

### Optimization Workflow

#### 1. Define Search Space
```bash
# Use predefined parameter spaces
python scripts/optimize_strategy.py --preset conservative

# Or define custom parameters
python scripts/optimize_strategy.py \
  --max-position-size 0.05,0.10,0.15 \
  --stop-loss 2.0,5.0 \
  --take-profit 8.0,12.0
```

#### 2. Run Optimization
```bash
# Grid search (systematic)
python scripts/optimize_strategy.py --method grid --duration 30 --runs 3

# Random search (efficient)
python scripts/optimize_strategy.py --method random --trials 100 --duration 45
```

#### 3. Analyze Results
```bash
# Create comprehensive report
python scripts/visualize_optimization.py --comprehensive --top-k 5

# Export results for further analysis
python scripts/optimize_strategy.py --export results.csv
```

#### 4. Validate Best Configurations
```bash
# Test best configuration with longer duration
python -m src.experiment_runner \
  --max-position-size 0.10 \
  --stop-loss 3.0 \
  --take-profit 12.0 \
  --duration 120
```

### Best Practices for Optimization

#### Parameter Space Design
1. **Start Conservative**: Begin with small position sizes and tight risk controls
2. **Incremental Expansion**: Gradually increase parameter ranges based on results
3. **Focus on Key Parameters**: Prioritize position size and risk management
4. **Consider Market Conditions**: Adjust parameters for different market regimes

#### Statistical Significance
1. **Multiple Runs**: Use at least 3-5 runs per configuration
2. **Sufficient Duration**: Run experiments for at least 30-60 minutes
3. **Random Seeds**: Use fixed seeds for reproducible results
4. **Cross-Validation**: Test best configurations on different time periods

#### Performance Evaluation
1. **Risk-Adjusted Metrics**: Focus on Sharpe ratio over raw returns
2. **Drawdown Analysis**: Consider maximum drawdown and recovery time
3. **Consistency**: Look for stable performance across multiple runs
4. **Market Regime**: Test across different market conditions

#### Resource Management
1. **Parallel Execution**: Run multiple experiments simultaneously
2. **Resource Monitoring**: Monitor CPU and memory usage
3. **Result Storage**: Regularly backup optimization results
4. **Incremental Analysis**: Analyze results as they become available

### Example Optimization Scenarios

#### Conservative Strategy Optimization
```bash
# Test conservative parameters
python scripts/optimize_strategy.py \
  --method grid \
  --max-position-size 0.01,0.02,0.03,0.05 \
  --stop-loss 1.0,2.0,3.0 \
  --take-profit 2.0,3.0,5.0 \
  --confidence-threshold 0.7,0.8,0.9 \
  --duration 60 --runs 5
```

#### Aggressive Strategy Optimization
```bash
# Test aggressive parameters
python scripts/optimize_strategy.py \
  --method random \
  --max-position-size 0.10,0.15,0.20,0.25 \
  --stop-loss 3.0,5.0,8.0 \
  --take-profit 8.0,12.0,15.0 \
  --confidence-threshold 0.5,0.6,0.7 \
  --trials 100 --duration 45
```

#### LLM Provider Comparison
```bash
# Compare different LLM providers
python scripts/optimize_strategy.py \
  --method grid \
  --preset llm_comparison \
  --duration 60 --runs 3
```

### Results Interpretation

#### Key Metrics to Monitor
- **Sharpe Ratio**: Risk-adjusted returns (target: >1.0)
- **Max Drawdown**: Maximum loss from peak (target: <10%)
- **Win Rate**: Percentage of profitable trades (target: >50%)
- **Profit Factor**: Gross profit / gross loss (target: >1.5)

#### Parameter Insights
- **Position Size**: Larger sizes = higher returns but higher risk
- **Stop Loss**: Tighter stops = lower drawdown but more false signals
- **Take Profit**: Higher targets = better risk/reward but lower win rate
- **Confidence Threshold**: Higher thresholds = fewer trades but better quality

#### Optimization Success Criteria
1. **Statistical Significance**: Consistent performance across multiple runs
2. **Risk Management**: Acceptable drawdown levels
3. **Profitability**: Positive risk-adjusted returns
4. **Stability**: Performance doesn't degrade over time

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

