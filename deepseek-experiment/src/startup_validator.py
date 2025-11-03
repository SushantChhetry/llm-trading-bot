"""
Startup validation for trading bot.

Validates environment, configuration, and dependencies before starting the bot.
"""

import os
import sys
import logging
from typing import Dict, List, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


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
                trades = supabase.get_trades(limit=1)
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

    def validate_configuration_values(self):
        """Validate configuration values are within acceptable ranges."""
        try:
            max_leverage = float(os.getenv("MAX_LEVERAGE", "10.0"))
            if max_leverage > 10.0:
                self.warnings.append(f"MAX_LEVERAGE ({max_leverage}) exceeds recommended limit (10.0)")

            max_position_size = float(os.getenv("MAX_POSITION_SIZE", "0.1"))
            if max_position_size > 0.5:
                self.warnings.append(f"MAX_POSITION_SIZE ({max_position_size}) exceeds recommended limit (0.5)")

            trading_mode = os.getenv("TRADING_MODE", "paper")
            if trading_mode == "live":
                exchange_api_key = os.getenv("EXCHANGE_API_KEY")
                exchange_api_secret = os.getenv("EXCHANGE_API_SECRET")
                if not exchange_api_key or not exchange_api_secret:
                    self.errors.append("EXCHANGE_API_KEY and EXCHANGE_API_SECRET required for live trading")
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
