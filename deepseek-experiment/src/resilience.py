"""
Resilience and error handling utilities for the trading bot.

Provides circuit breakers, retry logic, and graceful degradation.
"""

import asyncio
import time
import logging
from typing import Callable, Any, Optional, Dict, List, Union
from functools import wraps
from enum import Enum
from dataclasses import dataclass
import random

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service is back


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5  # Number of failures before opening
    recovery_timeout: int = 60  # Seconds to wait before trying again
    expected_exception: type = Exception  # Exception type to catch
    success_threshold: int = 3  # Successes needed to close from half-open


@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_attempts: int = 3
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 60.0  # Maximum delay in seconds
    exponential_base: float = 2.0  # Exponential backoff base
    jitter: bool = True  # Add random jitter to prevent thundering herd


class CircuitBreaker:
    """Circuit breaker implementation for external service calls."""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.success_count = 0
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.config.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        return time.time() - self.last_failure_time >= self.config.recovery_timeout
    
    def _on_success(self):
        """Handle successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info("Circuit breaker closed after successful calls")
        else:
            self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def reset(self):
        """Manually reset circuit breaker."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        logger.info("Circuit breaker manually reset")


class RetryHandler:
    """Handles retry logic with exponential backoff."""
    
    def __init__(self, config: RetryConfig):
        self.config = config
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with retry logic.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If all retry attempts fail
        """
        last_exception = None
        
        for attempt in range(self.config.max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt == self.config.max_attempts - 1:
                    logger.error(f"All {self.config.max_attempts} retry attempts failed")
                    raise last_exception
                
                delay = self._calculate_delay(attempt)
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.2f}s")
                time.sleep(delay)
        
        raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""
        delay = min(
            self.config.base_delay * (self.config.exponential_base ** attempt),
            self.config.max_delay
        )
        
        if self.config.jitter:
            # Add random jitter (±25% of delay)
            jitter_range = delay * 0.25
            jitter = random.uniform(-jitter_range, jitter_range)
            delay += jitter
        
        return max(0, delay)


class FallbackHandler:
    """Handles fallback logic when primary operations fail."""
    
    def __init__(self, fallback_func: Callable, fallback_args: tuple = (), fallback_kwargs: dict = None):
        self.fallback_func = fallback_func
        self.fallback_args = fallback_args
        self.fallback_kwargs = fallback_kwargs or {}
    
    def call_with_fallback(self, primary_func: Callable, *args, **kwargs) -> Any:
        """
        Execute primary function with fallback.
        
        Args:
            primary_func: Primary function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Primary function result or fallback result
        """
        try:
            return primary_func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Primary function failed: {e}. Using fallback.")
            try:
                return self.fallback_func(*self.fallback_args, **self.fallback_kwargs)
            except Exception as fallback_error:
                logger.error(f"Fallback function also failed: {fallback_error}")
                raise e  # Re-raise original exception


class HealthChecker:
    """Health checking for external services."""
    
    def __init__(self):
        self.health_status: Dict[str, bool] = {}
        self.last_check: Dict[str, float] = {}
        self.check_interval = 30  # seconds
    
    def check_health(self, service_name: str, check_func: Callable) -> bool:
        """
        Check health of a service.
        
        Args:
            service_name: Name of the service
            check_func: Function that returns True if healthy
            
        Returns:
            True if service is healthy
        """
        current_time = time.time()
        
        # Use cached result if recent enough
        if (service_name in self.last_check and 
            current_time - self.last_check[service_name] < self.check_interval):
            return self.health_status.get(service_name, False)
        
        try:
            is_healthy = check_func()
            self.health_status[service_name] = is_healthy
            self.last_check[service_name] = current_time
            
            if is_healthy:
                logger.debug(f"Health check passed for {service_name}")
            else:
                logger.warning(f"Health check failed for {service_name}")
            
            return is_healthy
        except Exception as e:
            logger.error(f"Health check error for {service_name}: {e}")
            self.health_status[service_name] = False
            self.last_check[service_name] = current_time
            return False
    
    def is_healthy(self, service_name: str) -> bool:
        """Check if service is currently healthy."""
        return self.health_status.get(service_name, False)


# Decorators for easy use
def circuit_breaker(config: CircuitBreakerConfig):
    """Decorator to add circuit breaker to function."""
    breaker = CircuitBreaker(config)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator


def retry(config: RetryConfig):
    """Decorator to add retry logic to function."""
    retry_handler = RetryHandler(config)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return retry_handler.call(func, *args, **kwargs)
        return wrapper
    return decorator


def fallback(fallback_func: Callable, *fallback_args, **fallback_kwargs):
    """Decorator to add fallback logic to function."""
    fallback_handler = FallbackHandler(fallback_func, fallback_args, fallback_kwargs)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return fallback_handler.call_with_fallback(func, *args, **kwargs)
        return wrapper
    return decorator


def timeout(seconds: int):
    """Decorator to add timeout to function."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return asyncio.wait_for(
                    asyncio.coroutine(func)(*args, **kwargs),
                    timeout=seconds
                )
            except asyncio.TimeoutError:
                raise TimeoutError(f"Function {func.__name__} timed out after {seconds} seconds")
        return wrapper
    return decorator


# Global instances
health_checker = HealthChecker()

# Pre-configured circuit breakers for common services
llm_circuit_breaker = CircuitBreaker(CircuitBreakerConfig(
    failure_threshold=3,
    recovery_timeout=30,
    expected_exception=Exception
))

exchange_circuit_breaker = CircuitBreaker(CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=60,
    expected_exception=Exception
))

# Pre-configured retry handlers
api_retry_handler = RetryHandler(RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=10.0,
    exponential_base=2.0,
    jitter=True
))

database_retry_handler = RetryHandler(RetryConfig(
    max_attempts=5,
    base_delay=0.5,
    max_delay=30.0,
    exponential_base=1.5,
    jitter=True
))
