"""
Configuration settings for the DeepSeek trading bot experiment.

This module centralizes all configuration parameters. Modify values here
to switch between paper trading and live trading, or change exchanges/LLM providers.
"""

import os
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = DATA_DIR / "logs"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# Exchange configuration
EXCHANGE = os.getenv("EXCHANGE", "bybit")  # Options: "bybit", "binance"
USE_TESTNET = os.getenv("USE_TESTNET", "true").lower() == "true"

# API keys (set via environment variables for security)
EXCHANGE_API_KEY = os.getenv("EXCHANGE_API_KEY", "")
EXCHANGE_API_SECRET = os.getenv("EXCHANGE_API_SECRET", "")

# Trading configuration
SYMBOL = os.getenv("SYMBOL", "BTC/USDT")  # Trading pair
INITIAL_BALANCE = float(os.getenv("INITIAL_BALANCE", "10000.0"))  # Starting paper balance

# DeepSeek API configuration
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = os.getenv(
    "DEEPSEEK_API_URL",
    "https://api.deepseek.com/v1/chat/completions"
)
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

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

