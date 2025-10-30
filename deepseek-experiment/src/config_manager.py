"""
Secure configuration management for the trading bot.

Handles environment variables, secrets, and configuration validation.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
from dotenv import load_dotenv
import yaml

from .security import SecurityManager

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    host: str = "localhost"
    port: int = 5432
    database: str = "trading_bot"
    username: str = "trading_user"
    password: str = ""
    url: str = ""
    
    def __post_init__(self):
        if not self.url and all([self.host, self.database, self.username]):
            self.url = f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class LLMConfig:
    """LLM provider configuration."""
    provider: str = "mock"
    api_key: str = ""
    api_url: str = ""
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 500
    timeout: int = 30
    
    def __post_init__(self):
        # Set provider-specific defaults
        if self.provider == "deepseek":
            self.api_url = self.api_url or "https://api.deepseek.com/v1/chat/completions"
            self.model = self.model or "deepseek-chat"
        elif self.provider == "openai":
            self.api_url = self.api_url or "https://api.openai.com/v1/chat/completions"
            self.model = self.model or "gpt-3.5-turbo"
        elif self.provider == "anthropic":
            self.api_url = self.api_url or "https://api.anthropic.com/v1/messages"
            self.model = self.model or "claude-3-sonnet-20240229"


@dataclass
class ExchangeConfig:
    """Exchange configuration settings."""
    name: str = "bybit"
    api_key: str = ""
    api_secret: str = ""
    testnet_api_key: str = ""
    testnet_api_secret: str = ""
    use_testnet: bool = True
    symbol: str = "BTC/USDT"
    
    def get_active_credentials(self) -> tuple[str, str]:
        """Get active API credentials based on testnet setting."""
        if self.use_testnet and self.testnet_api_key:
            return self.testnet_api_key, self.testnet_api_secret
        return self.api_key, self.api_secret


@dataclass
class TradingConfig:
    """Trading configuration settings."""
    mode: str = "paper"  # "paper" or "live"
    initial_balance: float = 10000.0
    max_position_size: float = 0.1  # Max % of balance per trade
    max_leverage: float = 10.0
    default_leverage: float = 1.0
    trading_fee_percent: float = 0.05
    max_risk_per_trade: float = 2.0
    stop_loss_percent: float = 2.0
    take_profit_percent: float = 3.0
    max_active_positions: int = 6
    min_confidence_threshold: float = 0.6
    fee_impact_warning_threshold: float = 20.0
    run_interval_seconds: int = 150  # 2.5 minutes


@dataclass
class SecurityConfig:
    """Security configuration settings."""
    enable_rate_limiting: bool = True
    max_requests_per_minute: int = 60
    enable_input_validation: bool = True
    enable_api_key_validation: bool = True
    log_sensitive_data: bool = False
    allowed_origins: list[str] = field(default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"])


@dataclass
class LoggingConfig:
    """Logging configuration settings."""
    level: str = "INFO"
    file_path: Optional[Path] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


class ConfigManager:
    """Manages all configuration for the trading bot."""
    
    def __init__(self, config_file: Optional[Path] = None, env_file: Optional[Path] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Path to YAML configuration file
            env_file: Path to .env file
        """
        self.security_manager = SecurityManager()
        self.config_file = config_file
        self.env_file = env_file or Path(".env")
        
        # Load environment variables
        self._load_environment()
        
        # Initialize configuration sections
        self.database = DatabaseConfig()
        self.llm = LLMConfig()
        self.exchange = ExchangeConfig()
        self.trading = TradingConfig()
        self.security = SecurityConfig()
        self.logging = LoggingConfig()
        
        # Load configuration from file if provided
        if config_file and config_file.exists():
            self._load_config_file()
        
        # Override with environment variables
        self._load_from_environment()
        
        # Validate configuration
        self._validate_config()
        
        logger.info("Configuration manager initialized successfully")
    
    def _load_environment(self):
        """Load environment variables from .env file."""
        if self.env_file.exists():
            load_dotenv(self.env_file)
            logger.info(f"Loaded environment variables from {self.env_file}")
    
    def _load_config_file(self):
        """Load configuration from YAML file."""
        try:
            with open(self.config_file, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Update configuration sections
            if 'database' in config_data:
                self._update_dataclass(self.database, config_data['database'])
            if 'llm' in config_data:
                self._update_dataclass(self.llm, config_data['llm'])
            if 'exchange' in config_data:
                self._update_dataclass(self.exchange, config_data['exchange'])
            if 'trading' in config_data:
                self._update_dataclass(self.trading, config_data['trading'])
            if 'security' in config_data:
                self._update_dataclass(self.security, config_data['security'])
            if 'logging' in config_data:
                self._update_dataclass(self.logging, config_data['logging'])
            
            logger.info(f"Loaded configuration from {self.config_file}")
        except Exception as e:
            logger.error(f"Error loading config file {self.config_file}: {e}")
    
    def _update_dataclass(self, obj: Any, data: Dict[str, Any]):
        """Update dataclass fields from dictionary."""
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
    
    def _load_from_environment(self):
        """Load configuration from environment variables."""
        # Database configuration
        self.database.host = os.getenv("DB_HOST", self.database.host)
        self.database.port = int(os.getenv("DB_PORT", str(self.database.port)))
        self.database.database = os.getenv("DB_NAME", self.database.database)
        self.database.username = os.getenv("DB_USER", self.database.username)
        self.database.password = os.getenv("DB_PASSWORD", self.database.password)
        self.database.url = os.getenv("DATABASE_URL", self.database.url)
        
        # LLM configuration
        self.llm.provider = os.getenv("LLM_PROVIDER", self.llm.provider)
        self.llm.api_key = os.getenv("LLM_API_KEY", self.llm.api_key)
        self.llm.api_url = os.getenv("LLM_API_URL", self.llm.api_url)
        self.llm.model = os.getenv("LLM_MODEL", self.llm.model)
        self.llm.temperature = float(os.getenv("LLM_TEMPERATURE", str(self.llm.temperature)))
        self.llm.max_tokens = int(os.getenv("LLM_MAX_TOKENS", str(self.llm.max_tokens)))
        self.llm.timeout = int(os.getenv("LLM_TIMEOUT", str(self.llm.timeout)))
        
        # Exchange configuration
        self.exchange.name = os.getenv("EXCHANGE", self.exchange.name)
        self.exchange.api_key = os.getenv("EXCHANGE_API_KEY", self.exchange.api_key)
        self.exchange.api_secret = os.getenv("EXCHANGE_API_SECRET", self.exchange.api_secret)
        self.exchange.testnet_api_key = os.getenv("TESTNET_API_KEY", self.exchange.testnet_api_key)
        self.exchange.testnet_api_secret = os.getenv("TESTNET_API_SECRET", self.exchange.testnet_api_secret)
        self.exchange.use_testnet = os.getenv("USE_TESTNET", "true").lower() == "true"
        self.exchange.symbol = os.getenv("SYMBOL", self.exchange.symbol)
        
        # Trading configuration
        self.trading.mode = os.getenv("TRADING_MODE", self.trading.mode)
        self.trading.initial_balance = float(os.getenv("INITIAL_BALANCE", str(self.trading.initial_balance)))
        self.trading.max_position_size = float(os.getenv("MAX_POSITION_SIZE", str(self.trading.max_position_size)))
        self.trading.max_leverage = float(os.getenv("MAX_LEVERAGE", str(self.trading.max_leverage)))
        self.trading.default_leverage = float(os.getenv("DEFAULT_LEVERAGE", str(self.trading.default_leverage)))
        self.trading.trading_fee_percent = float(os.getenv("TRADING_FEE_PERCENT", str(self.trading.trading_fee_percent)))
        self.trading.max_risk_per_trade = float(os.getenv("MAX_RISK_PER_TRADE", str(self.trading.max_risk_per_trade)))
        self.trading.stop_loss_percent = float(os.getenv("STOP_LOSS_PERCENT", str(self.trading.stop_loss_percent)))
        self.trading.take_profit_percent = float(os.getenv("TAKE_PROFIT_PERCENT", str(self.trading.take_profit_percent)))
        self.trading.max_active_positions = int(os.getenv("MAX_ACTIVE_POSITIONS", str(self.trading.max_active_positions)))
        self.trading.min_confidence_threshold = float(os.getenv("MIN_CONFIDENCE_THRESHOLD", str(self.trading.min_confidence_threshold)))
        self.trading.fee_impact_warning_threshold = float(os.getenv("FEE_IMPACT_WARNING_THRESHOLD", str(self.trading.fee_impact_warning_threshold)))
        self.trading.run_interval_seconds = int(os.getenv("RUN_INTERVAL_SECONDS", str(self.trading.run_interval_seconds)))
        
        # Security configuration
        self.security.enable_rate_limiting = os.getenv("ENABLE_RATE_LIMITING", "true").lower() == "true"
        self.security.max_requests_per_minute = int(os.getenv("MAX_REQUESTS_PER_MINUTE", str(self.security.max_requests_per_minute)))
        self.security.enable_input_validation = os.getenv("ENABLE_INPUT_VALIDATION", "true").lower() == "true"
        self.security.enable_api_key_validation = os.getenv("ENABLE_API_KEY_VALIDATION", "true").lower() == "true"
        self.security.log_sensitive_data = os.getenv("LOG_SENSITIVE_DATA", "false").lower() == "true"
        
        # Logging configuration
        self.logging.level = os.getenv("LOG_LEVEL", self.logging.level)
        if os.getenv("LOG_FILE"):
            self.logging.file_path = Path(os.getenv("LOG_FILE"))
        self.logging.max_file_size = int(os.getenv("LOG_MAX_FILE_SIZE", str(self.logging.max_file_size)))
        self.logging.backup_count = int(os.getenv("LOG_BACKUP_COUNT", str(self.logging.backup_count)))
    
    def _validate_config(self):
        """Validate configuration settings."""
        errors = []
        
        # Validate LLM configuration
        if self.llm.provider != "mock" and not self.llm.api_key:
            errors.append("LLM API key is required for non-mock providers")
        
        if self.llm.provider != "mock" and not self.security_manager.validate_api_key(self.llm.api_key, self.llm.provider):
            errors.append(f"Invalid API key format for {self.llm.provider}")
        
        # Validate trading configuration
        if self.trading.mode not in ["paper", "live"]:
            errors.append("Trading mode must be 'paper' or 'live'")
        
        if not 0 < self.trading.max_position_size <= 1:
            errors.append("Max position size must be between 0 and 1")
        
        if not 1 <= self.trading.max_leverage <= 100:
            errors.append("Max leverage must be between 1 and 100")
        
        if not 0 <= self.trading.min_confidence_threshold <= 1:
            errors.append("Min confidence threshold must be between 0 and 1")
        
        # Validate exchange configuration
        if self.trading.mode == "live" and not self.exchange.api_key:
            errors.append("Exchange API key is required for live trading")
        
        if self.exchange.name not in ["bybit", "binance", "coinbase", "kraken"]:
            errors.append(f"Unsupported exchange: {self.exchange.name}")
        
        # Validate database configuration
        if not self.database.url and not all([self.database.host, self.database.database, self.database.username]):
            errors.append("Database configuration is incomplete")
        
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors)
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def get_safe_config(self) -> Dict[str, Any]:
        """
        Get configuration dictionary with sensitive data masked.
        
        Returns:
            Configuration dictionary with masked sensitive values
        """
        config = {
            "database": {
                "host": self.database.host,
                "port": self.database.port,
                "database": self.database.database,
                "username": self.database.username,
                "password": "***" if self.database.password else "",
                "url": "***" if self.database.url else ""
            },
            "llm": {
                "provider": self.llm.provider,
                "api_key": "***" if self.llm.api_key else "",
                "api_url": self.llm.api_url,
                "model": self.llm.model,
                "temperature": self.llm.temperature,
                "max_tokens": self.llm.max_tokens,
                "timeout": self.llm.timeout
            },
            "exchange": {
                "name": self.exchange.name,
                "api_key": "***" if self.exchange.api_key else "",
                "api_secret": "***" if self.exchange.api_secret else "",
                "testnet_api_key": "***" if self.exchange.testnet_api_key else "",
                "testnet_api_secret": "***" if self.exchange.testnet_api_secret else "",
                "use_testnet": self.exchange.use_testnet,
                "symbol": self.exchange.symbol
            },
            "trading": {
                "mode": self.trading.mode,
                "initial_balance": self.trading.initial_balance,
                "max_position_size": self.trading.max_position_size,
                "max_leverage": self.trading.max_leverage,
                "default_leverage": self.trading.default_leverage,
                "trading_fee_percent": self.trading.trading_fee_percent,
                "max_risk_per_trade": self.trading.max_risk_per_trade,
                "stop_loss_percent": self.trading.stop_loss_percent,
                "take_profit_percent": self.trading.take_profit_percent,
                "max_active_positions": self.trading.max_active_positions,
                "min_confidence_threshold": self.trading.min_confidence_threshold,
                "fee_impact_warning_threshold": self.trading.fee_impact_warning_threshold,
                "run_interval_seconds": self.trading.run_interval_seconds
            },
            "security": {
                "enable_rate_limiting": self.security.enable_rate_limiting,
                "max_requests_per_minute": self.security.max_requests_per_minute,
                "enable_input_validation": self.security.enable_input_validation,
                "enable_api_key_validation": self.security.enable_api_key_validation,
                "log_sensitive_data": self.security.log_sensitive_data,
                "allowed_origins": self.security.allowed_origins
            },
            "logging": {
                "level": self.logging.level,
                "file_path": str(self.logging.file_path) if self.logging.file_path else None,
                "max_file_size": self.logging.max_file_size,
                "backup_count": self.logging.backup_count,
                "format": self.logging.format
            }
        }
        
        return config
    
    def save_config(self, file_path: Path):
        """Save current configuration to file."""
        config = self.get_safe_config()
        
        with open(file_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        
        logger.info(f"Configuration saved to {file_path}")


# Global configuration manager instance
config_manager = ConfigManager()
