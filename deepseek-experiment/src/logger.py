"""
Production logging configuration with structured output and rotation.
Industry-standard implementation following twelve-factor app methodology.
"""

import json
import logging
import logging.handlers
import sys
from pathlib import Path


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

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, "trade_id"):
            log_data["trade_id"] = record.trade_id
        if hasattr(record, "symbol"):
            log_data["symbol"] = record.symbol
        if hasattr(record, "action"):
            log_data["action"] = record.action

        return json.dumps(log_data)


def configure_production_logging(
    log_level: str = "INFO", log_directory: str = "data/logs", app_name: str = "trading-bot"
) -> logging.Logger:
    """
    Configure production-grade logging with multiple handlers.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_directory: Directory to store log files
        app_name: Application name for log identification

    Returns:
        Configured root logger instance
    """
    log_path = Path(log_directory)
    log_path.mkdir(parents=True, exist_ok=True)

    # Human-readable formatter for file logs
    detailed_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)-15s:%(lineno)-4d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Structured JSON formatter for parsing/aggregation
    structured_formatter = StructuredFormatter(datefmt="%Y-%m-%dT%H:%M:%S.%fZ")

    # Console formatter (colorized for systemd/journald)
    console_formatter = logging.Formatter(fmt="%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%H:%M:%S")

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


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
