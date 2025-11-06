"""Configuration module for the trading bot."""
from types import SimpleNamespace
import importlib.util
from pathlib import Path

# Load config.py as a module to avoid circular import issues
_config_file = Path(__file__).parent / "config.py"
spec = importlib.util.spec_from_file_location("_config_module", _config_file)
_config_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_config_module)

# Create a config object that wraps all module-level variables
# This allows imports like: from config import config
config = SimpleNamespace(
    # Project paths
    PROJECT_ROOT=_config_module.PROJECT_ROOT,
    DATA_DIR=_config_module.DATA_DIR,
    LOG_DIR=_config_module.LOG_DIR,
    
    # Exchange configuration
    EXCHANGE=_config_module.EXCHANGE,
    USE_TESTNET=_config_module.USE_TESTNET,
    EXCHANGE_API_KEY=_config_module.EXCHANGE_API_KEY,
    EXCHANGE_API_SECRET=_config_module.EXCHANGE_API_SECRET,
    TESTNET_API_KEY=_config_module.TESTNET_API_KEY,
    TESTNET_API_SECRET=_config_module.TESTNET_API_SECRET,
    
    # Trading configuration
    SYMBOL=_config_module.SYMBOL,
    INITIAL_BALANCE=_config_module.INITIAL_BALANCE,
    
    # LLM Provider configuration
    LLM_PROVIDER=_config_module.LLM_PROVIDER,
    LLM_API_KEY=_config_module.LLM_API_KEY,
    LLM_API_URL=_config_module.LLM_API_URL,
    LLM_MODEL=_config_module.LLM_MODEL,
    
    # Bot workflow configuration
    RUN_INTERVAL_SECONDS=_config_module.RUN_INTERVAL_SECONDS,
    TRADING_MODE=_config_module.TRADING_MODE,
    
    # Logging configuration
    LOG_LEVEL=_config_module.LOG_LEVEL,
    LOG_FILE=_config_module.LOG_FILE,
    
    # Trading limits
    MAX_POSITION_SIZE=_config_module.MAX_POSITION_SIZE,
    STOP_LOSS_PERCENT=_config_module.STOP_LOSS_PERCENT,
    TAKE_PROFIT_PERCENT=_config_module.TAKE_PROFIT_PERCENT,
    
    # Leverage and risk management
    MAX_LEVERAGE=_config_module.MAX_LEVERAGE,
    DEFAULT_LEVERAGE=_config_module.DEFAULT_LEVERAGE,
    TRADING_FEE_PERCENT=_config_module.TRADING_FEE_PERCENT,
    MAX_RISK_PER_TRADE=_config_module.MAX_RISK_PER_TRADE,
    
    # Alpha Arena behavioral simulation
    MAX_ACTIVE_POSITIONS=_config_module.MAX_ACTIVE_POSITIONS,
    MIN_CONFIDENCE_THRESHOLD=_config_module.MIN_CONFIDENCE_THRESHOLD,
    FEE_IMPACT_WARNING_THRESHOLD=_config_module.FEE_IMPACT_WARNING_THRESHOLD,
)
