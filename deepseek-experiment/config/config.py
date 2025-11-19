"""
Configuration settings for the DeepSeek trading bot experiment.

This module centralizes all configuration parameters. Modify values here
to switch between paper trading and live trading, or change exchanges/LLM providers.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = DATA_DIR / "logs"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# Exchange configuration
EXCHANGE = os.getenv("EXCHANGE", "kraken")  # Options: "bybit", "binance", "coinbase", "kraken"
USE_TESTNET = os.getenv("USE_TESTNET", "true").lower() == "true"

# Exchange API keys (set via environment variables for security)
EXCHANGE_API_KEY = os.getenv("EXCHANGE_API_KEY", "")
EXCHANGE_API_SECRET = os.getenv("EXCHANGE_API_SECRET", "")

# Testnet API keys (separate from live trading keys)
TESTNET_API_KEY = os.getenv("TESTNET_API_KEY", "")
TESTNET_API_SECRET = os.getenv("TESTNET_API_SECRET", "")

# Use testnet keys if available and in testnet mode
if USE_TESTNET and TESTNET_API_KEY:
    EXCHANGE_API_KEY = TESTNET_API_KEY
    EXCHANGE_API_SECRET = TESTNET_API_SECRET

# Trading configuration
SYMBOL = os.getenv("SYMBOL", "BTC/USDT")  # Trading pair
INITIAL_BALANCE = float(os.getenv("INITIAL_BALANCE", "10000.0"))  # Starting paper balance

# LLM Provider configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock")  # Options: "mock", "deepseek", "openai", "anthropic"
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_URL = os.getenv("LLM_API_URL", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")

# Provider-specific defaults
if LLM_PROVIDER == "deepseek":
    LLM_API_URL = LLM_API_URL or "https://api.deepseek.com/v1/chat/completions"
    LLM_MODEL = LLM_MODEL or "deepseek-chat"
elif LLM_PROVIDER == "openai":
    LLM_API_URL = LLM_API_URL or "https://api.openai.com/v1/chat/completions"
    LLM_MODEL = LLM_MODEL or "gpt-3.5-turbo"
elif LLM_PROVIDER == "anthropic":
    LLM_API_URL = LLM_API_URL or "https://api.anthropic.com/v1/messages"
    LLM_MODEL = LLM_MODEL or "claude-3-sonnet-20240229"

# Bot workflow configuration - Reduced frequency to prevent over-trading
RUN_INTERVAL_SECONDS = int(os.getenv("RUN_INTERVAL_SECONDS", "300"))  # 5 minutes (300 seconds) - reduced from 150s
TRADING_MODE = os.getenv("TRADING_MODE", "paper")  # "paper" or "live"

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = LOG_DIR / "bot.log"

# Trading limits (safety measures)
MAX_POSITION_SIZE = float(os.getenv("MAX_POSITION_SIZE", "0.1"))  # Max % of balance per trade
STOP_LOSS_PERCENT = float(os.getenv("STOP_LOSS_PERCENT", "1.5"))  # 1.5% stop loss (tighter for mean-reverting)
TAKE_PROFIT_PERCENT = float(os.getenv("TAKE_PROFIT_PERCENT", "1.5"))  # 1.5% take profit (tighter for mean-reverting)

# Leverage and risk management
MAX_LEVERAGE = float(os.getenv("MAX_LEVERAGE", "10.0"))  # Maximum allowed leverage
DEFAULT_LEVERAGE = float(os.getenv("DEFAULT_LEVERAGE", "1.0"))  # Default leverage if not specified
TRADING_FEE_PERCENT = float(os.getenv("TRADING_FEE_PERCENT", "0.05"))  # 0.05% taker fee
MAX_RISK_PER_TRADE = float(os.getenv("MAX_RISK_PER_TRADE", "2.0"))  # Max 2% risk per trade

# Alpha Arena behavioral simulation
MAX_ACTIVE_POSITIONS = int(os.getenv("MAX_ACTIVE_POSITIONS", "6"))  # Max simultaneous positions
MIN_CONFIDENCE_THRESHOLD = float(os.getenv("MIN_CONFIDENCE_THRESHOLD", "0.58"))  # Min confidence to trade (balanced: filters low-quality trades while allowing good ones)
EXIT_CONFIDENCE_THRESHOLD = float(os.getenv("EXIT_CONFIDENCE_THRESHOLD", "0.5"))  # Confidence threshold for automatic exits (lower = more aggressive exits)
FEE_IMPACT_WARNING_THRESHOLD = float(os.getenv("FEE_IMPACT_WARNING_THRESHOLD", "50.0"))  # Block trades if fees > 50% of PnL (increased from 20%)

# Position monitoring and exit management
ENABLE_POSITION_MONITORING = (
    os.getenv("ENABLE_POSITION_MONITORING", "true").lower() == "true"
)  # Enable automatic position monitoring
PORTFOLIO_PROFIT_TARGET_PCT = float(
    os.getenv("PORTFOLIO_PROFIT_TARGET_PCT", "10.0")
)  # Close all positions at +10% portfolio profit
ENABLE_TRAILING_STOP_LOSS = (
    os.getenv("ENABLE_TRAILING_STOP_LOSS", "true").lower() == "true"
)  # Enable trailing stop-loss
TRAILING_STOP_DISTANCE_PCT = float(
    os.getenv("TRAILING_STOP_DISTANCE_PCT", "1.0")
)  # Trailing stop distance (1% below peak)
TRAILING_STOP_ACTIVATION_PCT = float(
    os.getenv("TRAILING_STOP_ACTIVATION_PCT", "0.5")
)  # Activate trailing stop after 0.5% profit
ENABLE_PARTIAL_PROFIT_TAKING = (
    os.getenv("ENABLE_PARTIAL_PROFIT_TAKING", "true").lower() == "true"
)  # Enable partial profit-taking
PARTIAL_PROFIT_PERCENT = float(os.getenv("PARTIAL_PROFIT_PERCENT", "50.0"))  # Close 50% at first target
PARTIAL_PROFIT_TARGET_PCT = float(os.getenv("PARTIAL_PROFIT_TARGET_PCT", "1.5"))  # First profit target (1.5%)

# Risk service configuration
RISK_SERVICE_FAIL_CLOSED = (
    os.getenv("RISK_SERVICE_FAIL_CLOSED", "").lower() == "true"
    if os.getenv("RISK_SERVICE_FAIL_CLOSED")
    else (TRADING_MODE == "live")
)  # Default: True for live, False for paper
RISK_SERVICE_REQUIRED = (
    os.getenv("RISK_SERVICE_REQUIRED", "").lower() == "true"
    if os.getenv("RISK_SERVICE_REQUIRED")
    else (TRADING_MODE == "live")
)  # Default: True for live trading
POSITION_RECONCILIATION_INTERVAL = int(
    os.getenv("POSITION_RECONCILIATION_INTERVAL", "5")
)  # Run reconciliation every N cycles

# Kelly Criterion Position Sizing
ENABLE_KELLY_SIZING = os.getenv("ENABLE_KELLY_SIZING", "false").lower() == "true"
KELLY_SAFETY_FACTOR = float(os.getenv("KELLY_SAFETY_FACTOR", "0.5"))  # Half-Kelly default
KELLY_LOOKBACK_TRADES = int(os.getenv("KELLY_LOOKBACK_TRADES", "30"))
KELLY_MIN_TRADES_FOR_CALC = int(os.getenv("KELLY_MIN_TRADES_FOR_CALC", "10"))

# Performance Learning and Adaptation
ENABLE_PERFORMANCE_LEARNING = os.getenv("ENABLE_PERFORMANCE_LEARNING", "true").lower() == "true"
ADAPTIVE_CONFIDENCE_ENABLED = os.getenv("ADAPTIVE_CONFIDENCE_ENABLED", "true").lower() == "true"
PERFORMANCE_LOOKBACK_TRADES = int(os.getenv("PERFORMANCE_LOOKBACK_TRADES", "20"))
CONFIDENCE_MIN_SAMPLE_SIZE = int(os.getenv("CONFIDENCE_MIN_SAMPLE_SIZE", "5"))
CONFIDENCE_Z_SCORE_THRESHOLD = float(os.getenv("CONFIDENCE_Z_SCORE_THRESHOLD", "1.0"))
EWMA_DECAY_FACTOR = float(os.getenv("EWMA_DECAY_FACTOR", "0.3"))  # 30% weight to new data

# LLM Agentic Decision Making
ENABLE_AGENTIC_DECISIONS = os.getenv("ENABLE_AGENTIC_DECISIONS", "false").lower() == "true"
AGENT_MAX_RETRIES = int(os.getenv("AGENT_MAX_RETRIES", "2"))
AGENT_TIMEOUT_SECONDS = int(os.getenv("AGENT_TIMEOUT_SECONDS", "60"))

# Multi-Strategy Management
ENABLE_MULTI_STRATEGY = os.getenv("ENABLE_MULTI_STRATEGY", "false").lower() == "true"
STRATEGY_REBALANCE_INTERVAL_HOURS = int(os.getenv("STRATEGY_REBALANCE_INTERVAL_HOURS", "24"))
MIN_STRATEGY_ALLOCATION = float(os.getenv("MIN_STRATEGY_ALLOCATION", "0.05"))  # 5% minimum
MAX_STRATEGY_ALLOCATION = float(os.getenv("MAX_STRATEGY_ALLOCATION", "0.50"))  # 50% maximum

# LLM advanced settings (with defaults if not in env)
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "500"))
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "30"))


def get_default_configuration() -> dict:
    """
    Export current configuration values as a dictionary.
    This represents the default configuration that can be saved to Supabase.

    Returns:
        Dictionary containing all configuration values organized by category
    """
    return {
        "llm": {
            "provider": LLM_PROVIDER,
            "api_key": "",  # Never export API keys
            "api_url": LLM_API_URL or "",
            "model": LLM_MODEL or "",
            "temperature": LLM_TEMPERATURE,
            "max_tokens": LLM_MAX_TOKENS,
            "timeout": LLM_TIMEOUT,
        },
        "exchange": {
            "name": EXCHANGE,
            "symbol": SYMBOL,
            "use_testnet": USE_TESTNET,
            "api_key": "",  # Never export API keys
            "api_secret": "",  # Never export API keys
            "testnet_api_key": "",  # Never export API keys
            "testnet_api_secret": "",  # Never export API keys
        },
        "trading": {
            "mode": TRADING_MODE,
            "initial_balance": INITIAL_BALANCE,
            "max_position_size": MAX_POSITION_SIZE,
            "max_leverage": MAX_LEVERAGE,
            "default_leverage": DEFAULT_LEVERAGE,
            "trading_fee_percent": TRADING_FEE_PERCENT,
            "max_risk_per_trade": MAX_RISK_PER_TRADE,
            "stop_loss_percent": STOP_LOSS_PERCENT,
            "take_profit_percent": TAKE_PROFIT_PERCENT,
            "max_active_positions": MAX_ACTIVE_POSITIONS,
            "min_confidence_threshold": MIN_CONFIDENCE_THRESHOLD,
            "exit_confidence_threshold": EXIT_CONFIDENCE_THRESHOLD,
            "fee_impact_warning_threshold": FEE_IMPACT_WARNING_THRESHOLD,
            "run_interval_seconds": RUN_INTERVAL_SECONDS,
        },
        "position_management": {
            "enable_position_monitoring": ENABLE_POSITION_MONITORING,
            "portfolio_profit_target_pct": PORTFOLIO_PROFIT_TARGET_PCT,
            "enable_trailing_stop_loss": ENABLE_TRAILING_STOP_LOSS,
            "trailing_stop_distance_pct": TRAILING_STOP_DISTANCE_PCT,
            "trailing_stop_activation_pct": TRAILING_STOP_ACTIVATION_PCT,
            "enable_partial_profit_taking": ENABLE_PARTIAL_PROFIT_TAKING,
            "partial_profit_percent": PARTIAL_PROFIT_PERCENT,
            "partial_profit_target_pct": PARTIAL_PROFIT_TARGET_PCT,
        },
        "logging": {
            "level": LOG_LEVEL,
        },
    }
