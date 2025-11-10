"""Configuration module for the trading bot.

This module provides a config object that loads from Supabase with fallback to config.py defaults.
The config object maintains backward compatibility with the old config.ATTRIBUTE interface.
"""

# Try to use config_loader for Supabase-backed configuration
# Fall back to direct config.py import if config_loader is not available
try:
    from src.config_loader import get_config_proxy

    config = get_config_proxy()
except (ImportError, ValueError) as e:
    # Fallback to direct config.py import if config_loader fails
    # This can happen during initial setup or if Supabase is not configured
    import logging

    logger = logging.getLogger(__name__)
    logger.warning(f"Could not load config_loader, falling back to config.py: {e}")

    from types import SimpleNamespace
    import sys
    from pathlib import Path

    # Import config.py module directly
    _config_py_path = Path(__file__).parent / "config.py"

    if _config_py_path.exists():
        import importlib.util

        spec = importlib.util.spec_from_file_location("config.config", _config_py_path)
        _config_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_config_module)
    else:
        raise ImportError(f"config.py not found at {_config_py_path}")

    # Create a config object that wraps all module-level variables
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
        # Position management (add missing attributes)
        ENABLE_POSITION_MONITORING=getattr(_config_module, "ENABLE_POSITION_MONITORING", True),
        PORTFOLIO_PROFIT_TARGET_PCT=getattr(_config_module, "PORTFOLIO_PROFIT_TARGET_PCT", 10.0),
        ENABLE_TRAILING_STOP_LOSS=getattr(_config_module, "ENABLE_TRAILING_STOP_LOSS", True),
        TRAILING_STOP_DISTANCE_PCT=getattr(_config_module, "TRAILING_STOP_DISTANCE_PCT", 1.0),
        TRAILING_STOP_ACTIVATION_PCT=getattr(_config_module, "TRAILING_STOP_ACTIVATION_PCT", 0.5),
        ENABLE_PARTIAL_PROFIT_TAKING=getattr(_config_module, "ENABLE_PARTIAL_PROFIT_TAKING", True),
        PARTIAL_PROFIT_PERCENT=getattr(_config_module, "PARTIAL_PROFIT_PERCENT", 50.0),
        PARTIAL_PROFIT_TARGET_PCT=getattr(_config_module, "PARTIAL_PROFIT_TARGET_PCT", 1.5),
        # LLM advanced settings
        LLM_TEMPERATURE=getattr(_config_module, "LLM_TEMPERATURE", 0.7),
        LLM_MAX_TOKENS=getattr(_config_module, "LLM_MAX_TOKENS", 500),
        LLM_TIMEOUT=getattr(_config_module, "LLM_TIMEOUT", 30),
    )
