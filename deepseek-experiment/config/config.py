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
EXCHANGE = os.getenv("EXCHANGE", "bybit")  # Options: "bybit", "binance", "coinbase", "kraken"
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

# Bot workflow configuration
RUN_INTERVAL_SECONDS = int(os.getenv("RUN_INTERVAL_SECONDS", "300"))  # 5 minutes
TRADING_MODE = os.getenv("TRADING_MODE", "paper")  # "paper" or "live"

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = LOG_DIR / "bot.log"

# Trading limits (safety measures)
MAX_POSITION_SIZE = float(os.getenv("MAX_POSITION_SIZE", "0.1"))  # Max % of balance per trade
STOP_LOSS_PERCENT = float(os.getenv("STOP_LOSS_PERCENT", "2.0"))  # 2% stop loss
TAKE_PROFIT_PERCENT = float(os.getenv("TAKE_PROFIT_PERCENT", "3.0"))  # 3% take profit

