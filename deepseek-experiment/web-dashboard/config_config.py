"""Configuration settings for the trading bot."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path("/app")
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = DATA_DIR / "logs"

DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# Minimal config class - most values come from environment variables
class Config:
    DATA_DIR = DATA_DIR
    LOG_DIR = LOG_DIR
    INITIAL_BALANCE = float(os.getenv("INITIAL_BALANCE", "10000.0"))
    EXCHANGE = os.getenv("EXCHANGE", "kraken")
    TRADING_MODE = os.getenv("TRADING_MODE", "paper")
    SYMBOL = os.getenv("SYMBOL", "BTC/USDT")
    MAX_POSITION_SIZE = float(os.getenv("MAX_POSITION_SIZE", "0.1"))
    STOP_LOSS_PERCENT = float(os.getenv("STOP_LOSS_PERCENT", "2.0"))
    TAKE_PROFIT_PERCENT = float(os.getenv("TAKE_PROFIT_PERCENT", "3.0"))
    MAX_LEVERAGE = float(os.getenv("MAX_LEVERAGE", "10.0"))
    DEFAULT_LEVERAGE = float(os.getenv("DEFAULT_LEVERAGE", "1.0"))
    TRADING_FEE_PERCENT = float(os.getenv("TRADING_FEE_PERCENT", "0.05"))
    MAX_RISK_PER_TRADE = float(os.getenv("MAX_RISK_PER_TRADE", "2.0"))
    MAX_ACTIVE_POSITIONS = int(os.getenv("MAX_ACTIVE_POSITIONS", "6"))
    MIN_CONFIDENCE_THRESHOLD = float(os.getenv("MIN_CONFIDENCE_THRESHOLD", "0.6"))
    FEE_IMPACT_WARNING_THRESHOLD = float(os.getenv("FEE_IMPACT_WARNING_THRESHOLD", "20.0"))
    RUN_INTERVAL_SECONDS = int(os.getenv("RUN_INTERVAL_SECONDS", "150"))
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "mock")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = LOG_DIR / "bot.log"

config = Config()
