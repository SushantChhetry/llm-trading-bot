"""
Configuration loader that loads from Supabase with fallback to config.py defaults.

Priority order:
1. Supabase active configuration
2. Environment variables
3. config.py defaults
"""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Import config defaults
from config.config import (
    # LLM
    LLM_PROVIDER,
    LLM_API_KEY,
    LLM_API_URL,
    LLM_MODEL,
    LLM_TEMPERATURE,
    LLM_MAX_TOKENS,
    LLM_TIMEOUT,
    # Exchange
    EXCHANGE,
    SYMBOL,
    USE_TESTNET,
    # Trading
    TRADING_MODE,
    INITIAL_BALANCE,
    MAX_POSITION_SIZE,
    MAX_LEVERAGE,
    DEFAULT_LEVERAGE,
    TRADING_FEE_PERCENT,
    MAX_RISK_PER_TRADE,
    STOP_LOSS_PERCENT,
    TAKE_PROFIT_PERCENT,
    MAX_ACTIVE_POSITIONS,
    MIN_CONFIDENCE_THRESHOLD,
    FEE_IMPACT_WARNING_THRESHOLD,
    RUN_INTERVAL_SECONDS,
    # Position Management
    ENABLE_POSITION_MONITORING,
    PORTFOLIO_PROFIT_TARGET_PCT,
    ENABLE_TRAILING_STOP_LOSS,
    TRAILING_STOP_DISTANCE_PCT,
    TRAILING_STOP_ACTIVATION_PCT,
    ENABLE_PARTIAL_PROFIT_TAKING,
    PARTIAL_PROFIT_PERCENT,
    PARTIAL_PROFIT_TARGET_PCT,
    # Logging
    LOG_LEVEL,
)

# Cache for loaded configuration
_config_cache: Optional[Dict[str, Any]] = None
_config_source: str = "unknown"


def _get_default_config() -> Dict[str, Any]:
    """Get default configuration from config.py."""
    return {
        "llm": {
            "provider": LLM_PROVIDER,
            "api_key": LLM_API_KEY,
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


def _apply_env_overrides(config: Dict[str, Any]) -> Dict[str, Any]:
    """Apply environment variable overrides to configuration."""
    # LLM overrides
    if os.getenv("LLM_PROVIDER"):
        config["llm"]["provider"] = os.getenv("LLM_PROVIDER")
    if os.getenv("LLM_API_KEY"):
        config["llm"]["api_key"] = os.getenv("LLM_API_KEY")
    if os.getenv("LLM_API_URL"):
        config["llm"]["api_url"] = os.getenv("LLM_API_URL")
    if os.getenv("LLM_MODEL"):
        config["llm"]["model"] = os.getenv("LLM_MODEL")
    if os.getenv("LLM_TEMPERATURE"):
        config["llm"]["temperature"] = float(os.getenv("LLM_TEMPERATURE"))
    if os.getenv("LLM_MAX_TOKENS"):
        config["llm"]["max_tokens"] = int(os.getenv("LLM_MAX_TOKENS"))
    if os.getenv("LLM_TIMEOUT"):
        config["llm"]["timeout"] = int(os.getenv("LLM_TIMEOUT"))

    # Exchange overrides
    if os.getenv("EXCHANGE"):
        config["exchange"]["name"] = os.getenv("EXCHANGE")
    if os.getenv("SYMBOL"):
        config["exchange"]["symbol"] = os.getenv("SYMBOL")
    if os.getenv("USE_TESTNET"):
        config["exchange"]["use_testnet"] = os.getenv("USE_TESTNET", "true").lower() == "true"

    # Trading overrides
    if os.getenv("TRADING_MODE"):
        config["trading"]["mode"] = os.getenv("TRADING_MODE")
    if os.getenv("INITIAL_BALANCE"):
        config["trading"]["initial_balance"] = float(os.getenv("INITIAL_BALANCE"))
    if os.getenv("MAX_POSITION_SIZE"):
        config["trading"]["max_position_size"] = float(os.getenv("MAX_POSITION_SIZE"))
    if os.getenv("MAX_LEVERAGE"):
        config["trading"]["max_leverage"] = float(os.getenv("MAX_LEVERAGE"))
    if os.getenv("DEFAULT_LEVERAGE"):
        config["trading"]["default_leverage"] = float(os.getenv("DEFAULT_LEVERAGE"))
    if os.getenv("TRADING_FEE_PERCENT"):
        config["trading"]["trading_fee_percent"] = float(os.getenv("TRADING_FEE_PERCENT"))
    if os.getenv("MAX_RISK_PER_TRADE"):
        config["trading"]["max_risk_per_trade"] = float(os.getenv("MAX_RISK_PER_TRADE"))
    if os.getenv("STOP_LOSS_PERCENT"):
        config["trading"]["stop_loss_percent"] = float(os.getenv("STOP_LOSS_PERCENT"))
    if os.getenv("TAKE_PROFIT_PERCENT"):
        config["trading"]["take_profit_percent"] = float(os.getenv("TAKE_PROFIT_PERCENT"))
    if os.getenv("MAX_ACTIVE_POSITIONS"):
        config["trading"]["max_active_positions"] = int(os.getenv("MAX_ACTIVE_POSITIONS"))
    if os.getenv("MIN_CONFIDENCE_THRESHOLD"):
        config["trading"]["min_confidence_threshold"] = float(os.getenv("MIN_CONFIDENCE_THRESHOLD"))
    if os.getenv("FEE_IMPACT_WARNING_THRESHOLD"):
        config["trading"]["fee_impact_warning_threshold"] = float(os.getenv("FEE_IMPACT_WARNING_THRESHOLD"))
    if os.getenv("RUN_INTERVAL_SECONDS"):
        config["trading"]["run_interval_seconds"] = int(os.getenv("RUN_INTERVAL_SECONDS"))

    # Position management overrides
    if os.getenv("ENABLE_POSITION_MONITORING"):
        config["position_management"]["enable_position_monitoring"] = (
            os.getenv("ENABLE_POSITION_MONITORING", "true").lower() == "true"
        )
    if os.getenv("PORTFOLIO_PROFIT_TARGET_PCT"):
        config["position_management"]["portfolio_profit_target_pct"] = float(os.getenv("PORTFOLIO_PROFIT_TARGET_PCT"))
    if os.getenv("ENABLE_TRAILING_STOP_LOSS"):
        config["position_management"]["enable_trailing_stop_loss"] = (
            os.getenv("ENABLE_TRAILING_STOP_LOSS", "true").lower() == "true"
        )
    if os.getenv("TRAILING_STOP_DISTANCE_PCT"):
        config["position_management"]["trailing_stop_distance_pct"] = float(os.getenv("TRAILING_STOP_DISTANCE_PCT"))
    if os.getenv("TRAILING_STOP_ACTIVATION_PCT"):
        config["position_management"]["trailing_stop_activation_pct"] = float(os.getenv("TRAILING_STOP_ACTIVATION_PCT"))
    if os.getenv("ENABLE_PARTIAL_PROFIT_TAKING"):
        config["position_management"]["enable_partial_profit_taking"] = (
            os.getenv("ENABLE_PARTIAL_PROFIT_TAKING", "true").lower() == "true"
        )
    if os.getenv("PARTIAL_PROFIT_PERCENT"):
        config["position_management"]["partial_profit_percent"] = float(os.getenv("PARTIAL_PROFIT_PERCENT"))
    if os.getenv("PARTIAL_PROFIT_TARGET_PCT"):
        config["position_management"]["partial_profit_target_pct"] = float(os.getenv("PARTIAL_PROFIT_TARGET_PCT"))

    # Logging overrides
    if os.getenv("LOG_LEVEL"):
        config["logging"]["level"] = os.getenv("LOG_LEVEL")

    return config


def load_configuration(force_reload: bool = False) -> Dict[str, Any]:
    """
    Load configuration with priority: Supabase > Environment > Defaults.

    Args:
        force_reload: If True, reload from source even if cached

    Returns:
        Configuration dictionary
    """
    global _config_cache, _config_source

    if _config_cache and not force_reload:
        logger.debug(f"Using cached configuration (source: {_config_source})")
        return _config_cache

    # Start with defaults
    config = _get_default_config()
    _config_source = "default"

    # Try to load from Supabase
    try:
        from .supabase_client import get_supabase_service

        supabase = get_supabase_service()
        active_config = supabase.get_active_configuration()

        if active_config and "config_json" in active_config:
            # Merge Supabase config over defaults
            supabase_config = active_config["config_json"]

            # Deep merge configuration sections
            for section, values in supabase_config.items():
                if section in config and isinstance(values, dict):
                    config[section].update(values)
                else:
                    config[section] = values

            _config_source = f"supabase (version {active_config.get('version', 'unknown')})"
            logger.info(f"Loaded configuration from Supabase (version {active_config.get('version')})")
        else:
            logger.info("No active configuration in Supabase, using defaults")
    except ImportError:
        logger.debug("Supabase client not available, skipping Supabase load")
    except Exception as e:
        logger.warning(f"Failed to load from Supabase: {e}, using defaults")

    # Apply environment variable overrides (highest priority)
    config = _apply_env_overrides(config)
    if _config_source == "default":
        _config_source = "environment+default"
    else:
        _config_source = f"environment+{_config_source}"

    # Cache the configuration
    _config_cache = config
    logger.info(f"Configuration loaded (source: {_config_source})")

    return config


def get_config() -> Dict[str, Any]:
    """Get current configuration (cached if available)."""
    return load_configuration(force_reload=False)


def reload_configuration() -> Dict[str, Any]:
    """Force reload configuration from source."""
    return load_configuration(force_reload=True)


def get_config_source() -> str:
    """Get the source of the current configuration."""
    return _config_source


# Convenience functions to access config values (for backward compatibility)
def get_llm_config() -> Dict[str, Any]:
    """Get LLM configuration section."""
    return get_config()["llm"]


def get_exchange_config() -> Dict[str, Any]:
    """Get exchange configuration section."""
    return get_config()["exchange"]


def get_trading_config() -> Dict[str, Any]:
    """Get trading configuration section."""
    return get_config()["trading"]


def get_position_management_config() -> Dict[str, Any]:
    """Get position management configuration section."""
    return get_config()["position_management"]


def get_logging_config() -> Dict[str, Any]:
    """Get logging configuration section."""
    return get_config()["logging"]


class ConfigProxy:
    """
    Compatibility proxy that provides the old config.ATTRIBUTE interface
    while using the new config_loader under the hood.
    """

    def __init__(self):
        self._config = None
        self._reload()

    def _reload(self):
        """Reload configuration."""
        self._config = load_configuration(force_reload=True)

    # Project paths (from config.py)
    @property
    def PROJECT_ROOT(self):
        from config.config import PROJECT_ROOT

        return PROJECT_ROOT

    @property
    def DATA_DIR(self):
        from config.config import DATA_DIR

        return DATA_DIR

    @property
    def LOG_DIR(self):
        from config.config import LOG_DIR

        return LOG_DIR

    # LLM configuration
    @property
    def LLM_PROVIDER(self):
        return self._config["llm"]["provider"]

    @property
    def LLM_API_KEY(self):
        return self._config["llm"]["api_key"]

    @property
    def LLM_API_URL(self):
        return self._config["llm"]["api_url"]

    @property
    def LLM_MODEL(self):
        return self._config["llm"]["model"]

    @property
    def LLM_TEMPERATURE(self):
        return self._config["llm"]["temperature"]

    @property
    def LLM_MAX_TOKENS(self):
        return self._config["llm"]["max_tokens"]

    @property
    def LLM_TIMEOUT(self):
        return self._config["llm"]["timeout"]

    # Exchange configuration
    @property
    def EXCHANGE(self):
        return self._config["exchange"]["name"]

    @property
    def SYMBOL(self):
        return self._config["exchange"]["symbol"]

    @property
    def USE_TESTNET(self):
        return self._config["exchange"]["use_testnet"]

    @USE_TESTNET.setter
    def USE_TESTNET(self, value):
        self._config["exchange"]["use_testnet"] = value

    # Trading configuration
    @property
    def TRADING_MODE(self):
        return self._config["trading"]["mode"]

    @TRADING_MODE.setter
    def TRADING_MODE(self, value):
        self._config["trading"]["mode"] = value

    @property
    def INITIAL_BALANCE(self):
        return self._config["trading"]["initial_balance"]

    @property
    def MAX_POSITION_SIZE(self):
        return self._config["trading"]["max_position_size"]

    @property
    def MAX_LEVERAGE(self):
        return self._config["trading"]["max_leverage"]

    @property
    def DEFAULT_LEVERAGE(self):
        return self._config["trading"]["default_leverage"]

    @property
    def TRADING_FEE_PERCENT(self):
        return self._config["trading"]["trading_fee_percent"]

    @property
    def MAX_RISK_PER_TRADE(self):
        return self._config["trading"]["max_risk_per_trade"]

    @property
    def STOP_LOSS_PERCENT(self):
        return self._config["trading"]["stop_loss_percent"]

    @property
    def TAKE_PROFIT_PERCENT(self):
        return self._config["trading"]["take_profit_percent"]

    @property
    def MAX_ACTIVE_POSITIONS(self):
        return self._config["trading"]["max_active_positions"]

    @property
    def MIN_CONFIDENCE_THRESHOLD(self):
        return self._config["trading"]["min_confidence_threshold"]

    @property
    def FEE_IMPACT_WARNING_THRESHOLD(self):
        return self._config["trading"]["fee_impact_warning_threshold"]

    @property
    def RUN_INTERVAL_SECONDS(self):
        return self._config["trading"]["run_interval_seconds"]

    # Position management
    @property
    def ENABLE_POSITION_MONITORING(self):
        return self._config["position_management"]["enable_position_monitoring"]

    @property
    def PORTFOLIO_PROFIT_TARGET_PCT(self):
        return self._config["position_management"]["portfolio_profit_target_pct"]

    @property
    def ENABLE_TRAILING_STOP_LOSS(self):
        return self._config["position_management"]["enable_trailing_stop_loss"]

    @property
    def TRAILING_STOP_DISTANCE_PCT(self):
        return self._config["position_management"]["trailing_stop_distance_pct"]

    @property
    def TRAILING_STOP_ACTIVATION_PCT(self):
        return self._config["position_management"]["trailing_stop_activation_pct"]

    @property
    def ENABLE_PARTIAL_PROFIT_TAKING(self):
        return self._config["position_management"]["enable_partial_profit_taking"]

    @property
    def PARTIAL_PROFIT_PERCENT(self):
        return self._config["position_management"]["partial_profit_percent"]

    @property
    def PARTIAL_PROFIT_TARGET_PCT(self):
        return self._config["position_management"]["partial_profit_target_pct"]

    # Logging
    @property
    def LOG_LEVEL(self):
        return self._config["logging"]["level"]

    @property
    def LOG_FILE(self):
        from config.config import LOG_FILE

        return LOG_FILE


# Create a global config instance for backward compatibility
_config_proxy = None


def get_config_proxy() -> ConfigProxy:
    """Get the global config proxy instance."""
    global _config_proxy
    if _config_proxy is None:
        _config_proxy = ConfigProxy()
    return _config_proxy
