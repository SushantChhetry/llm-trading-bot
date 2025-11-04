"""
Security utilities for the trading bot.

Provides secure API key management, input validation, and security controls.
"""

import hashlib
import logging
import os
import re
import secrets
from functools import wraps
from typing import Any, Dict

logger = logging.getLogger(__name__)


class SecurityManager:
    """Manages security aspects of the trading bot."""

    def __init__(self):
        self.rate_limits = {}
        self.max_requests_per_minute = 60
        self.blocked_ips = set()

    def validate_api_key(self, api_key: str, provider: str) -> bool:
        """
        Validate API key format and security.

        Args:
            api_key: The API key to validate
            provider: The provider (deepseek, openai, anthropic)

        Returns:
            True if valid, False otherwise
        """
        if not api_key or len(api_key.strip()) == 0:
            return False

        # Basic format validation based on provider
        if provider == "deepseek":
            # DeepSeek keys typically start with 'sk-' and are 32+ chars
            return bool(re.match(r"^sk-[a-zA-Z0-9]{32,}$", api_key))
        elif provider == "openai":
            # OpenAI keys start with 'sk-' and are 48+ chars
            return bool(re.match(r"^sk-[a-zA-Z0-9]{48,}$", api_key))
        elif provider == "anthropic":
            # Anthropic keys start with 'sk-ant-' and are 50+ chars
            return bool(re.match(r"^sk-ant-[a-zA-Z0-9]{50,}$", api_key))

        # Generic validation for unknown providers
        return len(api_key) >= 20 and api_key.isalnum()

    def sanitize_input(self, input_data: Any) -> Any:
        """
        Sanitize input data to prevent injection attacks.

        Args:
            input_data: Data to sanitize

        Returns:
            Sanitized data
        """
        if isinstance(input_data, str):
            # Remove potentially dangerous characters
            sanitized = re.sub(r'[<>"\']', "", input_data)
            # Limit length to prevent DoS
            return sanitized[:1000]
        elif isinstance(input_data, dict):
            return {k: self.sanitize_input(v) for k, v in input_data.items()}
        elif isinstance(input_data, list):
            return [self.sanitize_input(item) for item in input_data]
        else:
            return input_data

    def validate_trading_decision(self, decision: Dict[str, Any]) -> bool:
        """
        Validate LLM trading decision for security and correctness.

        Args:
            decision: Trading decision dictionary

        Returns:
            True if valid, False otherwise
        """
        required_fields = ["action", "confidence", "justification"]

        # Check required fields
        for field in required_fields:
            if field not in decision:
                logger.warning(f"Missing required field: {field}")
                return False

        # Validate action
        valid_actions = ["buy", "sell", "hold"]
        if decision.get("action", "").lower() not in valid_actions:
            logger.warning(f"Invalid action: {decision.get('action')}")
            return False

        # Validate confidence (0.0 to 1.0)
        try:
            confidence = float(decision.get("confidence", 0))
            if not 0.0 <= confidence <= 1.0:
                logger.warning(f"Invalid confidence: {confidence}")
                return False
        except (ValueError, TypeError):
            logger.warning(f"Invalid confidence type: {decision.get('confidence')}")
            return False

        # Validate leverage (1.0 to 10.0)
        try:
            leverage = float(decision.get("leverage", 1.0))
            if not 1.0 <= leverage <= 10.0:
                logger.warning(f"Invalid leverage: {leverage}")
                return False
        except (ValueError, TypeError):
            logger.warning(f"Invalid leverage type: {decision.get('leverage')}")
            return False

        # Validate position size (positive number)
        try:
            position_size = float(decision.get("position_size_usdt", 0))
            if position_size < 0:
                logger.warning(f"Negative position size: {position_size}")
                return False
        except (ValueError, TypeError):
            logger.warning(f"Invalid position size type: {decision.get('position_size_usdt')}")
            return False

        # Sanitize justification
        if "justification" in decision:
            decision["justification"] = self.sanitize_input(decision["justification"])

        return True

    def check_rate_limit(self, identifier: str) -> bool:
        """
        Check if request is within rate limits.

        Args:
            identifier: Unique identifier (IP, user, etc.)

        Returns:
            True if within limits, False if rate limited
        """
        import time

        current_time = time.time()

        if identifier not in self.rate_limits:
            self.rate_limits[identifier] = []

        # Remove old entries (older than 1 minute)
        self.rate_limits[identifier] = [
            req_time for req_time in self.rate_limits[identifier] if current_time - req_time < 60
        ]

        # Check if under limit
        if len(self.rate_limits[identifier]) >= self.max_requests_per_minute:
            logger.warning(f"Rate limit exceeded for {identifier}")
            return False

        # Add current request
        self.rate_limits[identifier].append(current_time)
        return True

    def generate_secure_token(self, length: int = 32) -> str:
        """Generate a cryptographically secure random token."""
        return secrets.token_urlsafe(length)

    def hash_sensitive_data(self, data: str) -> str:
        """Hash sensitive data for logging/storage."""
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    @staticmethod
    def mask_api_key(key: str) -> str:
        """
        Mask API key for logging (show only first 8 and last 4 chars).
        
        Args:
            key: API key to mask
            
        Returns:
            Masked key string (e.g., "sk-12345...xyz")
        """
        if not key or len(key) < 8:
            return "***"
        if len(key) <= 12:
            return f"{key[:4]}...{key[-4:]}"
        return f"{key[:8]}...{key[-4:]}"


def secure_api_key_required(provider: str):
    """
    Decorator to ensure API key is present and valid.

    Args:
        provider: The LLM provider name
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            security_manager = SecurityManager()

            # Get API key from config or environment
            api_key = getattr(self, "api_key", None) or os.getenv(f"{provider.upper()}_API_KEY", "")

            if not security_manager.validate_api_key(api_key, provider):
                logger.error(f"Invalid or missing API key for {provider}")
                raise ValueError(f"Invalid or missing API key for {provider}")

            return func(self, *args, **kwargs)

        return wrapper

    return decorator


def validate_trading_inputs(func):
    """
    Decorator to validate trading function inputs.
    """

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        security_manager = SecurityManager()

        # Sanitize all string arguments
        sanitized_args = []
        for arg in args:
            if isinstance(arg, (str, dict, list)):
                sanitized_args.append(security_manager.sanitize_input(arg))
            else:
                sanitized_args.append(arg)

        # Sanitize keyword arguments
        sanitized_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, (str, dict, list)):
                sanitized_kwargs[key] = security_manager.sanitize_input(value)
            else:
                sanitized_kwargs[key] = value

        return func(self, *sanitized_args, **sanitized_kwargs)

    return wrapper


def rate_limit(requests_per_minute: int = 60):
    """
    Decorator to implement rate limiting.

    Args:
        requests_per_minute: Maximum requests per minute
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            security_manager = SecurityManager()
            security_manager.max_requests_per_minute = requests_per_minute

            # Use function name as identifier (could be enhanced with IP/user)
            identifier = f"{func.__name__}_{id(self)}"

            if not security_manager.check_rate_limit(identifier):
                raise Exception("Rate limit exceeded")

            return func(self, *args, **kwargs)

        return wrapper

    return decorator


# Global security manager instance
security_manager = SecurityManager()
