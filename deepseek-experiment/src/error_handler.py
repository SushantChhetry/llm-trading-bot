"""
Comprehensive error handling utilities for the trading bot.

Provides centralized error handling, logging, and recovery mechanisms.
"""

import logging
import traceback
from typing import Any, Callable, Optional, Dict, Type
from functools import wraps
from enum import Enum
import asyncio
import time

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for better classification."""
    NETWORK = "network"
    DATA_VALIDATION = "data_validation"
    API_ERROR = "api_error"
    TRADING_ERROR = "trading_error"
    DATABASE_ERROR = "database_error"
    CONFIGURATION_ERROR = "configuration_error"
    UNKNOWN = "unknown"


class TradingBotError(Exception):
    """Base exception for trading bot errors."""
    
    def __init__(
        self, 
        message: str, 
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.timestamp = time.time()


class NetworkError(TradingBotError):
    """Network-related errors."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.NETWORK, ErrorSeverity.HIGH, context)


class DataValidationError(TradingBotError):
    """Data validation errors."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.DATA_VALIDATION, ErrorSeverity.MEDIUM, context)


class APIError(TradingBotError):
    """API-related errors."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.API_ERROR, ErrorSeverity.HIGH, context)


class TradingError(TradingBotError):
    """Trading execution errors."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.TRADING_ERROR, ErrorSeverity.CRITICAL, context)


class DatabaseError(TradingBotError):
    """Database-related errors."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.DATABASE_ERROR, ErrorSeverity.HIGH, context)


class ConfigurationError(TradingBotError):
    """Configuration-related errors."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.CONFIGURATION_ERROR, ErrorSeverity.CRITICAL, context)


class ErrorHandler:
    """Centralized error handling and recovery."""
    
    def __init__(self):
        self.error_counts: Dict[str, int] = {}
        self.last_error_time: Dict[str, float] = {}
        self.max_errors_per_hour = 10
        self.circuit_breaker_threshold = 5
    
    def handle_error(
        self, 
        error: Exception, 
        context: Optional[Dict[str, Any]] = None,
        recovery_action: Optional[Callable] = None
    ) -> bool:
        """
        Handle an error with appropriate logging and recovery.
        
        Args:
            error: The exception that occurred
            context: Additional context information
            recovery_action: Optional recovery function to call
            
        Returns:
            True if error was handled successfully, False otherwise
        """
        context = context or {}
        error_key = f"{type(error).__name__}_{error.category.value if hasattr(error, 'category') else 'unknown'}"
        
        # Track error frequency
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        self.last_error_time[error_key] = time.time()
        
        # Check if we should trigger circuit breaker
        if self._should_trigger_circuit_breaker(error_key):
            logger.critical(f"Circuit breaker triggered for {error_key} - too many errors")
            return False
        
        # Log error with appropriate level
        self._log_error(error, context)
        
        # Attempt recovery if provided
        if recovery_action:
            try:
                recovery_action()
                logger.info(f"Recovery action completed for {error_key}")
                return True
            except Exception as recovery_error:
                logger.error(f"Recovery action failed: {recovery_error}")
                return False
        
        return True
    
    def _should_trigger_circuit_breaker(self, error_key: str) -> bool:
        """Check if circuit breaker should be triggered."""
        current_time = time.time()
        
        # Reset counts older than 1 hour
        if (error_key in self.last_error_time and 
            current_time - self.last_error_time[error_key] > 3600):
            self.error_counts[error_key] = 0
        
        return self.error_counts.get(error_key, 0) >= self.circuit_breaker_threshold
    
    def _log_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """Log error with appropriate level and details."""
        if isinstance(error, TradingBotError):
            severity = error.severity
            category = error.category
        else:
            severity = ErrorSeverity.MEDIUM
            category = ErrorCategory.UNKNOWN
        
        # Create detailed error message
        error_msg = f"[{category.value.upper()}] {str(error)}"
        if context:
            error_msg += f" | Context: {context}"
        
        # Log with appropriate level
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(error_msg, exc_info=True)
        elif severity == ErrorSeverity.HIGH:
            logger.error(error_msg, exc_info=True)
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(error_msg)
        else:
            logger.info(error_msg)
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        current_time = time.time()
        
        # Clean up old entries
        for error_key in list(self.error_counts.keys()):
            if (error_key in self.last_error_time and 
                current_time - self.last_error_time[error_key] > 3600):
                del self.error_counts[error_key]
                del self.last_error_time[error_key]
        
        return {
            "error_counts": self.error_counts.copy(),
            "total_errors": sum(self.error_counts.values()),
            "unique_error_types": len(self.error_counts)
        }


def safe_execute(
    func: Callable,
    error_category: ErrorCategory = ErrorCategory.UNKNOWN,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    recovery_action: Optional[Callable] = None,
    context: Optional[Dict[str, Any]] = None
):
    """
    Decorator to safely execute functions with error handling.
    
    Args:
        func: Function to execute
        error_category: Category for errors from this function
        severity: Severity level for errors
        recovery_action: Optional recovery function
        context: Additional context for error handling
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        error_handler = ErrorHandler()
        
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Wrap exception if it's not already a TradingBotError
            if not isinstance(e, TradingBotError):
                wrapped_error = TradingBotError(
                    str(e), 
                    error_category, 
                    severity, 
                    context
                )
            else:
                wrapped_error = e
            
            success = error_handler.handle_error(wrapped_error, context, recovery_action)
            
            if not success:
                raise wrapped_error
            
            # Return None or default value if error was handled
            return None
    
    return wrapper


def async_safe_execute(
    func: Callable,
    error_category: ErrorCategory = ErrorCategory.UNKNOWN,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    recovery_action: Optional[Callable] = None,
    context: Optional[Dict[str, Any]] = None
):
    """
    Decorator to safely execute async functions with error handling.
    
    Args:
        func: Async function to execute
        error_category: Category for errors from this function
        severity: Severity level for errors
        recovery_action: Optional recovery function
        context: Additional context for error handling
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        error_handler = ErrorHandler()
        
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Wrap exception if it's not already a TradingBotError
            if not isinstance(e, TradingBotError):
                wrapped_error = TradingBotError(
                    str(e), 
                    error_category, 
                    severity, 
                    context
                )
            else:
                wrapped_error = e
            
            success = error_handler.handle_error(wrapped_error, context, recovery_action)
            
            if not success:
                raise wrapped_error
            
            # Return None or default value if error was handled
            return None
    
    return wrapper


# Global error handler instance
error_handler = ErrorHandler()
