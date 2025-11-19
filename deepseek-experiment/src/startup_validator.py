"""
Startup validation for trading bot.

Validates environment, configuration, and dependencies before starting the bot.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from .logger import LogDomain, get_logger

logger = get_logger(__name__, domain=LogDomain.SYSTEM)


class ValidationError(Exception):
    """Raised when validation fails."""

    pass


class StartupValidator:
    """Validates bot configuration and dependencies at startup."""

    REQUIRED_ENV_VARS = {
        "production": [
            "LLM_PROVIDER",
            "TRADING_MODE",
            "EXCHANGE",
            "SYMBOL",
        ],
        "development": [],
    }

    OPTIONAL_ENV_VARS = [
        "LLM_API_KEY",
        "LLM_MODEL",
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "EXCHANGE_API_KEY",
        "EXCHANGE_API_SECRET",
    ]

    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "development")
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate_all(self) -> Tuple[bool, Dict[str, List[str]]]:
        """
        Run all validation checks.

        Returns:
            Tuple of (is_valid, {errors: [], warnings: []})
        """
        self.errors.clear()
        self.warnings.clear()

        try:
            self.validate_environment_variables()
            self.validate_file_permissions()
            self.validate_directory_structure()
            self.validate_database_connectivity()
            self.validate_api_keys()
            self.validate_configuration_values()
            self.validate_risk_service()
        except ValidationError as e:
            self.errors.append(str(e))

        is_valid = len(self.errors) == 0

        return is_valid, {"errors": self.errors, "warnings": self.warnings}

    def validate_environment_variables(self):
        """Validate required environment variables."""
        required = self.REQUIRED_ENV_VARS.get(self.environment, [])

        for var in required:
            if not os.getenv(var):
                self.errors.append(f"Missing required environment variable: {var}")

        for var in self.OPTIONAL_ENV_VARS:
            if not os.getenv(var):
                self.warnings.append(f"Optional environment variable not set: {var}")

    def validate_file_permissions(self):
        """Validate file and directory permissions."""
        data_dir = Path("data")
        logs_dir = data_dir / "logs"

        if not data_dir.exists():
            try:
                data_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                self.errors.append(f"Cannot create data directory: {e}")

        if not logs_dir.exists():
            try:
                logs_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                self.errors.append(f"Cannot create logs directory: {e}")

        if data_dir.exists():
            if not os.access(data_dir, os.W_OK):
                self.errors.append(f"Data directory is not writable: {data_dir}")

    def validate_directory_structure(self):
        """Validate required directories exist."""
        required_dirs = [
            Path("src"),
            Path("config"),
        ]

        for dir_path in required_dirs:
            if not dir_path.exists():
                self.errors.append(f"Required directory missing: {dir_path}")

    def validate_database_connectivity(self):
        """Validate Supabase connection if configured."""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")

        if supabase_url and supabase_key:
            try:
                from .supabase_client import get_supabase_service

                supabase = get_supabase_service()

                # Test connection with a simple query
                supabase.get_trades(limit=1)
                logger.debug("Supabase connection validated successfully")
            except Exception as e:
                self.errors.append(f"Supabase connection failed: {e}")

    def validate_api_keys(self):
        """Validate API key formats if provided."""
        from .security import SecurityManager

        security_manager = SecurityManager()
        llm_provider = os.getenv("LLM_PROVIDER", "").lower()
        llm_api_key = os.getenv("LLM_API_KEY", "")

        if llm_provider and llm_provider != "mock":
            if not llm_api_key:
                self.errors.append(f"LLM_API_KEY required when LLM_PROVIDER={llm_provider}")
            elif not security_manager.validate_api_key(llm_api_key, llm_provider):
                self.errors.append(f"Invalid LLM_API_KEY format for provider: {llm_provider}")

    def validate_risk_service(self):
        """Validate risk service is available and healthy."""
        import os

        import requests

        risk_service_url = os.getenv("RISK_SERVICE_URL", "http://localhost:8003")

        try:
            # Check health endpoint
            response = requests.get(f"{risk_service_url}/health", timeout=5)
            if response.status_code == 200:
                logger.info(f"Risk service health check passed: {risk_service_url}")
                return True
            else:
                self.errors.append(f"Risk service health check failed: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            # Risk service is optional for paper trading, required for live trading
            from config import config

            if config.TRADING_MODE == "live" and config.RISK_SERVICE_REQUIRED:
                self.errors.append(
                    f"Risk service is required for live trading but unavailable: {risk_service_url}\n"
                    f"Error: {str(e)}\n"
                    f"Please start the risk service or set RISK_SERVICE_REQUIRED=false"
                )
                return False
            else:
                logger.warning(f"Risk service not available (optional for paper trading): {e}")
                return True  # Not an error for paper trading

    def validate_configuration_values(self):
        """Validate configuration values are within acceptable ranges."""
        try:
            max_leverage = float(os.getenv("MAX_LEVERAGE", "10.0"))
            if max_leverage > 10.0:
                self.warnings.append(f"MAX_LEVERAGE ({max_leverage}) exceeds recommended limit (10.0)")

            max_position_size = float(os.getenv("MAX_POSITION_SIZE", "0.1"))
            if max_position_size > 0.5:
                self.warnings.append(f"MAX_POSITION_SIZE ({max_position_size}) exceeds recommended limit (0.5)")

            trading_mode = os.getenv("TRADING_MODE", "paper").lower()

            # CRITICAL: Validate live trading mode with confirmation requirement
            if trading_mode == "live":
                # Require explicit confirmation to prevent accidental live trading
                confirmation = os.getenv("TRADING_MODE_LIVE_CONFIRMED", "").lower()
                if confirmation != "yes":
                    self.errors.append(
                        "🚨 LIVE TRADING MODE DETECTED BUT NOT CONFIRMED!\n"
                        "   To enable live trading, set: TRADING_MODE_LIVE_CONFIRMED=yes\n"
                        "   This prevents accidental real money trading.\n"
                        "   ⚠️  WARNING: Live trading uses real money - ensure you have tested thoroughly!"
                    )
                    return  # Exit early - don't proceed with other validations

                # Additional checks for live mode
                llm_provider = os.getenv("LLM_PROVIDER", "").lower()
                llm_api_key = os.getenv("LLM_API_KEY", "")

                if llm_provider == "mock" or not llm_api_key:
                    self.errors.append(
                        "Live trading requires real LLM API key. "
                        f"Current LLM_PROVIDER={llm_provider}, LLM_API_KEY={'SET' if llm_api_key else 'NOT SET'}"
                    )

                exchange_api_key = os.getenv("EXCHANGE_API_KEY")
                exchange_api_secret = os.getenv("EXCHANGE_API_SECRET")
                if not exchange_api_key or not exchange_api_secret:
                    self.errors.append("EXCHANGE_API_KEY and EXCHANGE_API_SECRET required for live trading")

                # Log warning about live trading
                logger.warning("=" * 60)
                logger.warning("🚨 LIVE TRADING MODE ENABLED - REAL MONEY AT RISK!")
                logger.warning("=" * 60)
                logger.warning("Ensure you have:")
                logger.warning("  1. Tested extensively in paper mode")
                logger.warning("  2. Verified all risk management settings")
                logger.warning("  3. Confirmed API keys are correct")
                logger.warning("  4. Set up monitoring and alerts")
                logger.warning("=" * 60)

            elif trading_mode not in ["paper", "live"]:
                self.errors.append(f"Invalid TRADING_MODE: {trading_mode}. Must be 'paper' or 'live'")

            # Validate position monitoring configuration
            trailing_stop_distance = float(os.getenv("TRAILING_STOP_DISTANCE_PCT", "1.0"))
            stop_loss_percent = float(os.getenv("STOP_LOSS_PERCENT", "2.0"))

            if trailing_stop_distance >= stop_loss_percent:
                self.warnings.append(
                    f"TRAILING_STOP_DISTANCE_PCT ({trailing_stop_distance}%) should be less than "
                    f"STOP_LOSS_PERCENT ({stop_loss_percent}%) to be effective"
                )

            partial_profit_target = float(os.getenv("PARTIAL_PROFIT_TARGET_PCT", "1.5"))
            take_profit_percent = float(os.getenv("TAKE_PROFIT_PERCENT", "3.0"))

            if partial_profit_target >= take_profit_percent:
                self.warnings.append(
                    f"PARTIAL_PROFIT_TARGET_PCT ({partial_profit_target}%) should be less than "
                    f"TAKE_PROFIT_PERCENT ({take_profit_percent}%) to be effective"
                )

            trailing_stop_activation = float(os.getenv("TRAILING_STOP_ACTIVATION_PCT", "0.5"))
            if trailing_stop_activation < 0 or trailing_stop_activation > 10:
                self.warnings.append(
                    f"TRAILING_STOP_ACTIVATION_PCT ({trailing_stop_activation}%) is outside recommended range (0-10%)"
                )

        except ValueError as e:
            self.errors.append(f"Invalid configuration value: {e}")


def validate_startup():
    """
    Run startup validation and exit if critical errors found.

    Returns:
        True if validation passed, False otherwise
    """
    validator = StartupValidator()
    is_valid, results = validator.validate_all()

    # Log errors and exit if critical
    if results["errors"]:
        logger.error("=" * 60)
        logger.error("❌ STARTUP VALIDATION FAILED")
        logger.error("=" * 60)
        for error in results["errors"]:
            logger.error(f"   • {error}")
        logger.error("=" * 60)
        logger.error("Please fix the errors above before starting the bot.")
        return False

    # Log warnings if any
    if results["warnings"]:
        logger.info("⚠️  Startup validation passed with warnings:")
        for warning in results["warnings"]:
            logger.warning(f"   • {warning}")
        logger.info("Bot will start but some features may be limited.")
    else:
        logger.info("✅ Startup validation passed - all checks OK")

    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    if not validate_startup():
        sys.exit(1)
