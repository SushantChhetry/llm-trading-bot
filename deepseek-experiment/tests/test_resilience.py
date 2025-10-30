"""
Tests for resilience module.
"""

import unittest
import asyncio
import time
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.resilience import (
    CircuitBreaker, CircuitState, CircuitBreakerConfig,
    RetryHandler, RetryConfig, FallbackHandler,
    HealthChecker, circuit_breaker, retry, fallback
)


class TestCircuitBreaker(unittest.TestCase):
    """Test cases for CircuitBreaker."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = CircuitBreakerConfig(
            failure_threshold=2,
            recovery_timeout=1,
            expected_exception=Exception
        )
        self.breaker = CircuitBreaker(self.config)
    
    def test_initial_state(self):
        """Test initial circuit breaker state."""
        self.assertEqual(self.breaker.state, CircuitState.CLOSED)
        self.assertEqual(self.breaker.failure_count, 0)
    
    def test_successful_call(self):
        """Test successful function call."""
        def success_func():
            return "success"
        
        result = self.breaker.call(success_func)
        self.assertEqual(result, "success")
        self.assertEqual(self.breaker.state, CircuitState.CLOSED)
        self.assertEqual(self.breaker.failure_count, 0)
    
    def test_failure_opens_circuit(self):
        """Test that failures open the circuit."""
        def fail_func():
            raise Exception("Test failure")
        
        # First failure
        with self.assertRaises(Exception):
            self.breaker.call(fail_func)
        self.assertEqual(self.breaker.state, CircuitState.CLOSED)
        self.assertEqual(self.breaker.failure_count, 1)
        
        # Second failure should open circuit
        with self.assertRaises(Exception):
            self.breaker.call(fail_func)
        self.assertEqual(self.breaker.state, CircuitState.OPEN)
        self.assertEqual(self.breaker.failure_count, 2)
    
    def test_open_circuit_blocks_calls(self):
        """Test that open circuit blocks calls."""
        # Open the circuit
        self.breaker.state = CircuitState.OPEN
        self.breaker.failure_count = 2
        
        def any_func():
            return "should not be called"
        
        with self.assertRaises(Exception) as context:
            self.breaker.call(any_func)
        self.assertIn("Circuit breaker is OPEN", str(context.exception))
    
    def test_circuit_reset(self):
        """Test manual circuit reset."""
        self.breaker.state = CircuitState.OPEN
        self.breaker.failure_count = 5
        
        self.breaker.reset()
        
        self.assertEqual(self.breaker.state, CircuitState.CLOSED)
        self.assertEqual(self.breaker.failure_count, 0)
        self.assertEqual(self.breaker.success_count, 0)


class TestRetryHandler(unittest.TestCase):
    """Test cases for RetryHandler."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = RetryConfig(
            max_attempts=3,
            base_delay=0.01,  # Short delay for testing
            max_delay=0.1,
            exponential_base=2.0,
            jitter=False  # Disable jitter for predictable testing
        )
        self.retry_handler = RetryHandler(self.config)
    
    def test_successful_call_no_retry(self):
        """Test successful call without retries."""
        def success_func():
            return "success"
        
        result = self.retry_handler.call(success_func)
        self.assertEqual(result, "success")
    
    def test_retry_on_failure(self):
        """Test retry on failure."""
        call_count = 0
        
        def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = self.retry_handler.call(fail_then_succeed)
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 3)
    
    def test_max_attempts_exceeded(self):
        """Test behavior when max attempts exceeded."""
        call_count = 0
        
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise Exception("Permanent failure")
        
        with self.assertRaises(Exception) as context:
            self.retry_handler.call(always_fail)
        
        self.assertIn("Permanent failure", str(context.exception))
        self.assertEqual(call_count, 3)  # Max attempts
    
    def test_delay_calculation(self):
        """Test delay calculation with exponential backoff."""
        # Test exponential backoff
        delay1 = self.retry_handler._calculate_delay(0)
        delay2 = self.retry_handler._calculate_delay(1)
        delay3 = self.retry_handler._calculate_delay(2)
        
        self.assertGreater(delay2, delay1)
        self.assertGreater(delay3, delay2)
        self.assertLessEqual(delay3, self.config.max_delay)


class TestFallbackHandler(unittest.TestCase):
    """Test cases for FallbackHandler."""
    
    def test_primary_success(self):
        """Test fallback when primary function succeeds."""
        def primary_func():
            return "primary success"
        
        def fallback_func():
            return "fallback"
        
        handler = FallbackHandler(fallback_func)
        result = handler.call_with_fallback(primary_func)
        
        self.assertEqual(result, "primary success")
    
    def test_fallback_on_primary_failure(self):
        """Test fallback when primary function fails."""
        def primary_func():
            raise Exception("Primary failed")
        
        def fallback_func():
            return "fallback success"
        
        handler = FallbackHandler(fallback_func)
        result = handler.call_with_fallback(primary_func)
        
        self.assertEqual(result, "fallback success")
    
    def test_fallback_failure_raises_original_exception(self):
        """Test that fallback failure raises original exception."""
        def primary_func():
            raise ValueError("Primary failed")
        
        def fallback_func():
            raise RuntimeError("Fallback failed")
        
        handler = FallbackHandler(fallback_func)
        
        with self.assertRaises(ValueError) as context:
            handler.call_with_fallback(primary_func)
        
        self.assertIn("Primary failed", str(context.exception))


class TestHealthChecker(unittest.TestCase):
    """Test cases for HealthChecker."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.health_checker = HealthChecker()
    
    async def test_register_and_run_check(self):
        """Test registering and running health checks."""
        async def test_check():
            return {"status": "healthy", "message": "OK"}
        
        self.health_checker.register_check("test", test_check)
        
        result = await self.health_checker.run_check("test")
        
        self.assertEqual(result.name, "test")
        self.assertEqual(result.status, "healthy")
        self.assertEqual(result.message, "OK")
    
    async def test_check_with_exception(self):
        """Test health check that raises exception."""
        async def failing_check():
            raise Exception("Check failed")
        
        self.health_checker.register_check("failing", failing_check)
        
        result = await self.health_checker.run_check("failing")
        
        self.assertEqual(result.name, "failing")
        self.assertEqual(result.status, "unhealthy")
        self.assertIn("Check failed", result.message)
    
    async def test_check_returns_boolean(self):
        """Test health check that returns boolean."""
        async def boolean_check():
            return True
        
        self.health_checker.register_check("boolean", boolean_check)
        
        result = await self.health_checker.run_check("boolean")
        
        self.assertEqual(result.status, "healthy")
        self.assertEqual(result.message, "OK")
    
    async def test_check_returns_false(self):
        """Test health check that returns False."""
        async def false_check():
            return False
        
        self.health_checker.register_check("false", false_check)
        
        result = await self.health_checker.run_check("false")
        
        self.assertEqual(result.status, "unhealthy")
        self.assertEqual(result.message, "Check failed")
    
    def test_get_overall_health(self):
        """Test getting overall health status."""
        # No checks registered
        self.assertEqual(self.health_checker.get_overall_health(), "unknown")
        
        # Add some mock results
        from src.resilience import HealthCheck
        from datetime import datetime
        
        self.health_checker.results = {
            "check1": HealthCheck("check1", "healthy", "OK", datetime.utcnow()),
            "check2": HealthCheck("check2", "healthy", "OK", datetime.utcnow())
        }
        
        self.assertEqual(self.health_checker.get_overall_health(), "healthy")
        
        # Add unhealthy check
        self.health_checker.results["check3"] = HealthCheck("check3", "unhealthy", "Failed", datetime.utcnow())
        self.assertEqual(self.health_checker.get_overall_health(), "unhealthy")
        
        # Add degraded check
        self.health_checker.results["check3"] = HealthCheck("check3", "degraded", "Slow", datetime.utcnow())
        self.assertEqual(self.health_checker.get_overall_health(), "degraded")


class TestDecorators(unittest.TestCase):
    """Test cases for decorators."""
    
    def test_circuit_breaker_decorator(self):
        """Test circuit_breaker decorator."""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=1)
        
        @circuit_breaker(config)
        def test_func():
            return "success"
        
        result = test_func()
        self.assertEqual(result, "success")
    
    def test_retry_decorator(self):
        """Test retry decorator."""
        config = RetryConfig(max_attempts=2, base_delay=0.01)
        
        call_count = 0
        
        @retry(config)
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Temporary failure")
            return "success"
        
        result = test_func()
        self.assertEqual(result, "success")
        self.assertEqual(call_count, 2)
    
    def test_fallback_decorator(self):
        """Test fallback decorator."""
        def fallback_func():
            return "fallback"
        
        @fallback(fallback_func)
        def test_func():
            raise Exception("Primary failed")
        
        result = test_func()
        self.assertEqual(result, "fallback")


if __name__ == "__main__":
    unittest.main()
