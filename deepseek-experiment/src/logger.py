"""
Production logging configuration with structured output and rotation.
Industry-standard implementation following twelve-factor app methodology.

Enhanced with domain-specific logging, context management, and improved formatting.
"""

import json
import logging
import logging.handlers
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from colorama import Fore, Style, init as colorama_init

    colorama_init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False
    # Create dummy constants if colorama not available
    class Fore:
        RESET = ""
        RED = ""
        YELLOW = ""
        GREEN = ""
        BLUE = ""
        MAGENTA = ""
        CYAN = ""

    class Style:
        RESET_ALL = ""
        BRIGHT = ""


# Domain constants for log categorization
class LogDomain:
    """Log domain constants for categorizing logs."""

    TRADING = "TRADING"
    LLM = "LLM"
    RISK = "RISK"
    DATA = "DATA"
    PORTFOLIO = "PORTFOLIO"
    REGIME = "REGIME"
    STRATEGY = "STRATEGY"
    EXECUTION = "EXECUTION"
    MONITORING = "MONITORING"
    SYSTEM = "SYSTEM"
    SECURITY = "SECURITY"
    UNKNOWN = "UNKNOWN"


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging compatible with log aggregation tools."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
            "environment": "production",
        }

        # Add domain if present
        if hasattr(record, "domain"):
            log_data["domain"] = record.domain

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from context
        extra_fields = [
            "trade_id",
            "symbol",
            "action",
            "provider",
            "model",
            "duration_ms",
            "tokens",
            "position_size",
            "balance",
            "pnl",
            "error_code",
            "retry_count",
        ]
        for field in extra_fields:
            if hasattr(record, field):
                log_data[field] = getattr(record, field)

        # Add any additional extra fields
        if hasattr(record, "extra_context"):
            log_data.update(record.extra_context)

        return json.dumps(log_data)


class DomainFormatter(logging.Formatter):
    """Enhanced formatter that includes domain prefix and colors."""

    def __init__(self, use_colors: bool = True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_colors = use_colors and COLORAMA_AVAILABLE

    def _get_level_color(self, levelname: str) -> str:
        """Get color for log level."""
        if not self.use_colors:
            return ""
        color_map = {
            "DEBUG": Fore.CYAN,
            "INFO": Fore.GREEN,
            "WARNING": Fore.YELLOW,
            "ERROR": Fore.RED,
            "CRITICAL": Fore.RED + Style.BRIGHT,
        }
        return color_map.get(levelname, "")

    def _get_domain_color(self, domain: Optional[str]) -> str:
        """Get color for domain."""
        if not self.use_colors or not domain:
            return ""
        color_map = {
            LogDomain.TRADING: Fore.GREEN,
            LogDomain.LLM: Fore.BLUE,
            LogDomain.RISK: Fore.YELLOW,
            LogDomain.DATA: Fore.CYAN,
            LogDomain.PORTFOLIO: Fore.MAGENTA,
            LogDomain.REGIME: Fore.CYAN,
            LogDomain.STRATEGY: Fore.BLUE,
            LogDomain.EXECUTION: Fore.GREEN,
            LogDomain.MONITORING: Fore.MAGENTA,
            LogDomain.SYSTEM: Fore.RESET,
            LogDomain.SECURITY: Fore.RED,
        }
        return color_map.get(domain, "")

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with domain and colors."""
        # Get domain from record
        domain = getattr(record, "domain", None)
        domain_prefix = f"[{domain}] " if domain else ""

        # Format base message
        base_message = record.getMessage()

        # Build formatted message
        if domain:
            domain_color = self._get_domain_color(domain)
            reset = Style.RESET_ALL if self.use_colors else ""
            formatted_message = f"{domain_color}{domain_prefix}{reset}{base_message}"
        else:
            formatted_message = f"{domain_prefix}{base_message}"

        # Create a copy of the record with formatted message
        record_copy = logging.makeLogRecord(record.__dict__)
        record_copy.msg = formatted_message
        record_copy.args = ()

        # Use parent formatter for final formatting
        return super().format(record_copy)


class LogContext:
    """Context manager for adding structured context to log messages."""

    def __init__(self, logger: logging.Logger, **context):
        """
        Initialize log context.

        Args:
            logger: Logger instance to add context to
            **context: Key-value pairs to add as context
        """
        self.logger = logger
        self.context = context
        self.old_factory = None

    def __enter__(self):
        """Enter context manager."""
        # Store old factory
        self.old_factory = logging.getLogRecordFactory()

        def record_factory(*args, **kwargs):
            record = self.old_factory(*args, **kwargs)
            # Add context fields to record
            for key, value in self.context.items():
                setattr(record, key, value)
            return record

        logging.setLogRecordFactory(record_factory)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        if self.old_factory:
            logging.setLogRecordFactory(self.old_factory)


class DomainLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that adds domain prefix to all log messages."""

    def __init__(self, logger: logging.Logger, domain: str):
        """
        Initialize domain logger adapter.

        Args:
            logger: Base logger instance
            domain: Domain name (e.g., "TRADING", "LLM")
        """
        super().__init__(logger, {"domain": domain})
        self.domain = domain

    def process(self, msg, kwargs):
        """Process log message to add domain context."""
        # Add domain to extra if not present
        if "extra" not in kwargs:
            kwargs["extra"] = {}
        kwargs["extra"]["domain"] = self.domain
        return msg, kwargs


def configure_production_logging(
    log_level: str = "INFO", log_directory: str = "data/logs", app_name: str = "trading-bot", use_colors: bool = True
) -> logging.Logger:
    """
    Configure production-grade logging with multiple handlers.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_directory: Directory to store log files
        app_name: Application name for log identification
        use_colors: Whether to use colors in console output

    Returns:
        Configured root logger instance
    """
    log_path = Path(log_directory)
    log_path.mkdir(parents=True, exist_ok=True)

    # Enhanced formatter with domain support for file logs
    detailed_formatter = DomainFormatter(
        use_colors=False,
        fmt="%(asctime)s | %(levelname)-8s | %(name)-25s | %(funcName)-15s:%(lineno)-4d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Structured JSON formatter for parsing/aggregation
    structured_formatter = StructuredFormatter(datefmt="%Y-%m-%dT%H:%M:%S.%fZ")

    # Enhanced console formatter with domain and colors
    console_formatter = DomainFormatter(
        use_colors=use_colors,
        fmt="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )

    # Application log handler - all logs (rotating 10MB files, keep 30)
    app_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / f"{app_name}.log", maxBytes=10 * 1024 * 1024, backupCount=30, encoding="utf-8"  # 10MB
    )
    app_handler.setFormatter(detailed_formatter)
    app_handler.setLevel(logging.DEBUG)

    # Error log handler - errors only (rotating 10MB files, keep 10)
    error_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / f"{app_name}.error.log", maxBytes=10 * 1024 * 1024, backupCount=10, encoding="utf-8"
    )
    error_handler.setFormatter(detailed_formatter)
    error_handler.setLevel(logging.ERROR)

    # Structured JSON log handler - for log aggregation tools
    json_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / f"{app_name}.json.log", maxBytes=10 * 1024 * 1024, backupCount=10, encoding="utf-8"
    )
    json_handler.setFormatter(structured_formatter)
    json_handler.setLevel(logging.INFO)

    # Console handler - stdout for systemd/docker
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers to prevent duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Add all configured handlers
    root_logger.addHandler(app_handler)
    root_logger.addHandler(error_handler)
    root_logger.addHandler(json_handler)
    root_logger.addHandler(console_handler)

    # Log initialization
    root_logger.info("=" * 80)
    root_logger.info(f"Application logging initialized - {app_name}")
    root_logger.info(f"Log level: {log_level}")
    root_logger.info(f"Log directory: {log_path.absolute()}")
    root_logger.info("Environment: production")
    root_logger.info("=" * 80)

    return root_logger


def get_logger(name: str, domain: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance for a specific module with optional domain.

    Args:
        name: Logger name (typically __name__)
        domain: Optional domain name (e.g., LogDomain.TRADING, LogDomain.LLM)

    Returns:
        Logger instance (DomainLoggerAdapter if domain provided, otherwise standard Logger)
    """
    base_logger = logging.getLogger(name)
    if domain:
        return DomainLoggerAdapter(base_logger, domain)
    return base_logger


def get_domain_logger(name: str, domain: str) -> DomainLoggerAdapter:
    """
    Get a domain-specific logger instance.

    Args:
        name: Logger name (typically __name__)
        domain: Domain name (e.g., LogDomain.TRADING, LogDomain.LLM)

    Returns:
        DomainLoggerAdapter instance
    """
    base_logger = logging.getLogger(name)
    return DomainLoggerAdapter(base_logger, domain)


@contextmanager
def log_context(logger: logging.Logger, **context):
    """
    Context manager for adding temporary context to log messages.

    Usage:
        with log_context(logger, trade_id="12345", symbol="BTC/USD"):
            logger.info("Processing trade")
            # All logs within this block will include trade_id and symbol

    Args:
        logger: Logger instance
        **context: Key-value pairs to add as context
    """
    ctx = LogContext(logger, **context)
    ctx.__enter__()
    try:
        yield ctx
    finally:
        ctx.__exit__(None, None, None)
