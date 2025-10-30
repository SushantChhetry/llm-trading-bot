"""
Test utilities for secure testing.

Provides mock data generators and test helpers that don't expose sensitive information.
"""

import secrets
import string
from typing import Dict, Any


class MockDataGenerator:
    """Generates mock data for testing without exposing sensitive information."""
    
    @staticmethod
    def generate_mock_api_key(provider: str) -> str:
        """
        Generate a mock API key with correct format for testing.
        
        Args:
            provider: The API provider (deepseek, openai, anthropic)
            
        Returns:
            Mock API key string
        """
        if provider == "deepseek":
            # DeepSeek format: sk-{32 chars}
            return f"sk-{secrets.token_hex(16)}"
        elif provider == "openai":
            # OpenAI format: sk-{48 chars}
            return f"sk-{secrets.token_hex(24)}"
        elif provider == "anthropic":
            # Anthropic format: sk-ant-{50 chars}
            return f"sk-ant-{secrets.token_hex(25)}"
        else:
            # Generic format
            return f"sk-{secrets.token_hex(16)}"
    
    @staticmethod
    def generate_mock_trading_decision() -> Dict[str, Any]:
        """Generate a mock trading decision for testing."""
        return {
            "action": "buy",
            "direction": "long",
            "confidence": 0.8,
            "justification": "Mock test decision",
            "leverage": 2.0,
            "position_size_usdt": 1000.0,
            "risk_assessment": "medium",
            "exit_plan": {
                "profit_target": 52000.0,
                "stop_loss": 49000.0,
                "invalidation_conditions": ["test_condition"]
            }
        }
    
    @staticmethod
    def generate_mock_trade_data() -> Dict[str, Any]:
        """Generate mock trade data for testing."""
        return {
            "symbol": "BTC/USDT",
            "side": "buy",
            "direction": "long",
            "price": 50000.0,
            "quantity": 0.02,
            "amount_usdt": 1000.0,
            "leverage": 2.0,
            "confidence": 0.8,
            "mode": "paper",
            "timestamp": "2024-01-01T12:00:00Z"
        }
    
    @staticmethod
    def generate_mock_portfolio_data() -> Dict[str, Any]:
        """Generate mock portfolio data for testing."""
        return {
            "balance": 9000.0,
            "total_value": 10000.0,
            "positions_value": 1000.0,
            "active_positions": 1,
            "total_trades": 5,
            "total_return_pct": 0.0
        }
    
    @staticmethod
    def generate_mock_market_data() -> Dict[str, Any]:
        """Generate mock market data for testing."""
        return {
            "symbol": "BTC/USDT",
            "price": 50000.0,
            "volume": 1000000.0,
            "change_24h": 2.5
        }
    
    @staticmethod
    def generate_safe_string(length: int = 10) -> str:
        """Generate a safe string for testing (no special characters)."""
        return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))
    
    @staticmethod
    def generate_dangerous_input() -> str:
        """Generate input with potentially dangerous characters for security testing."""
        return "<script>alert('xss')</script>\"'><img src=x onerror=alert('xss')>"
    
    @staticmethod
    def generate_long_input(length: int = 2000) -> str:
        """Generate long input for length limit testing."""
        return 'x' * length


class TestConstants:
    """Constants for testing that don't expose sensitive information."""
    
    # Mock API keys (generated, not real)
    MOCK_DEEPSEEK_KEY = "sk-" + "a" * 32
    MOCK_OPENAI_KEY = "sk-" + "a" * 48
    MOCK_ANTHROPIC_KEY = "sk-ant-" + "a" * 50
    
    # Test data
    TEST_SYMBOL = "BTC/USDT"
    TEST_PRICE = 50000.0
    TEST_AMOUNT = 1000.0
    TEST_CONFIDENCE = 0.8
    TEST_LEVERAGE = 2.0
    
    # Security test data
    XSS_PAYLOAD = "<script>alert('xss')</script>"
    SQL_INJECTION_PAYLOAD = "'; DROP TABLE trades; --"
    COMMAND_INJECTION_PAYLOAD = "; rm -rf /"
    
    # Rate limiting test data
    TEST_IDENTIFIER = "test_user_123"
    TEST_IP_ADDRESS = "192.168.1.100"
    
    # Performance test data
    LARGE_JSON_SIZE = 10000  # 10KB
    LARGE_STRING_SIZE = 1000  # 1KB
    MAX_RETRY_ATTEMPTS = 3
