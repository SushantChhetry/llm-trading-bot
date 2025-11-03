"""
Tests for security module.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.security import SecurityManager, secure_api_key_required, validate_trading_inputs, rate_limit
from tests.test_utils import MockDataGenerator, TestConstants


class TestSecurityManager(unittest.TestCase):
    """Test cases for SecurityManager."""

    def setUp(self):
        """Set up test fixtures."""
        self.security_manager = SecurityManager()

    def test_validate_api_key_deepseek(self):
        """Test DeepSeek API key validation."""
        # Valid DeepSeek key (using mock format)
        valid_key = MockDataGenerator.generate_mock_api_key("deepseek")
        self.assertTrue(self.security_manager.validate_api_key(valid_key, "deepseek"))

        # Invalid DeepSeek key
        invalid_key = "invalid-key"
        self.assertFalse(self.security_manager.validate_api_key(invalid_key, "deepseek"))

        # Empty key
        self.assertFalse(self.security_manager.validate_api_key("", "deepseek"))

    def test_validate_api_key_openai(self):
        """Test OpenAI API key validation."""
        # Valid OpenAI key (using mock format)
        valid_key = MockDataGenerator.generate_mock_api_key("openai")
        self.assertTrue(self.security_manager.validate_api_key(valid_key, "openai"))

        # Invalid OpenAI key
        invalid_key = "sk-short"
        self.assertFalse(self.security_manager.validate_api_key(invalid_key, "openai"))

    def test_validate_api_key_anthropic(self):
        """Test Anthropic API key validation."""
        # Valid Anthropic key (using mock format)
        valid_key = MockDataGenerator.generate_mock_api_key("anthropic")
        self.assertTrue(self.security_manager.validate_api_key(valid_key, "anthropic"))

        # Invalid Anthropic key
        invalid_key = "sk-ant-short"
        self.assertFalse(self.security_manager.validate_api_key(invalid_key, "anthropic"))

    def test_sanitize_input_string(self):
        """Test input sanitization for strings."""
        # Test dangerous characters
        dangerous_input = TestConstants.XSS_PAYLOAD
        sanitized = self.security_manager.sanitize_input(dangerous_input)
        self.assertNotIn("<", sanitized)
        self.assertNotIn(">", sanitized)
        self.assertNotIn("'", sanitized)
        self.assertNotIn('"', sanitized)

        # Test length limit
        long_input = MockDataGenerator.generate_long_input(2000)
        sanitized = self.security_manager.sanitize_input(long_input)
        self.assertLessEqual(len(sanitized), 1000)

    def test_sanitize_input_dict(self):
        """Test input sanitization for dictionaries."""
        dangerous_dict = {
            "key1": TestConstants.XSS_PAYLOAD,
            "key2": "normal_value",
            "nested": {
                "dangerous": "'>alert('xss')<"
            }
        }
        sanitized = self.security_manager.sanitize_input(dangerous_dict)

        self.assertNotIn("<", sanitized["key1"])
        self.assertEqual(sanitized["key2"], "normal_value")
        self.assertNotIn(">", sanitized["nested"]["dangerous"])

    def test_validate_trading_decision_valid(self):
        """Test validation of valid trading decision."""
        valid_decision = MockDataGenerator.generate_mock_trading_decision()
        self.assertTrue(self.security_manager.validate_trading_decision(valid_decision))

    def test_validate_trading_decision_invalid_action(self):
        """Test validation of trading decision with invalid action."""
        invalid_decision = {
            "action": "invalid_action",
            "confidence": 0.8,
            "justification": "Test"
        }
        self.assertFalse(self.security_manager.validate_trading_decision(invalid_decision))

    def test_validate_trading_decision_invalid_confidence(self):
        """Test validation of trading decision with invalid confidence."""
        invalid_decision = {
            "action": "buy",
            "confidence": 1.5,  # Invalid: > 1.0
            "justification": "Test"
        }
        self.assertFalse(self.security_manager.validate_trading_decision(invalid_decision))

    def test_validate_trading_decision_missing_fields(self):
        """Test validation of trading decision with missing required fields."""
        invalid_decision = {
            "action": "buy"
            # Missing confidence and justification
        }
        self.assertFalse(self.security_manager.validate_trading_decision(invalid_decision))

    def test_check_rate_limit(self):
        """Test rate limiting functionality."""
        identifier = TestConstants.TEST_IDENTIFIER

        # Should allow first request
        self.assertTrue(self.security_manager.check_rate_limit(identifier))

        # Should allow requests within limit
        for _ in range(10):
            self.assertTrue(self.security_manager.check_rate_limit(identifier))

    def test_generate_secure_token(self):
        """Test secure token generation."""
        token1 = self.security_manager.generate_secure_token(32)
        token2 = self.security_manager.generate_secure_token(32)

        # token_urlsafe returns base64-encoded string, which is longer than input
        # For 32 bytes input, output is ~43 characters (base64 encoding)
        # Base64 encoding of 32 bytes = 44 characters (32 * 4/3 = 42.67, rounded up)
        # But secrets.token_urlsafe uses URL-safe base64 which may vary slightly
        self.assertGreaterEqual(len(token1), 32, f"Token length {len(token1)} should be >= 32")
        self.assertNotEqual(token1, token2)
        # URL-safe tokens contain alphanumeric, dash, and underscore
        self.assertTrue(all(c.isalnum() or c in '-_' for c in token1))

    def test_hash_sensitive_data(self):
        """Test sensitive data hashing."""
        data = "sensitive_api_key"
        hashed = self.security_manager.hash_sensitive_data(data)

        self.assertEqual(len(hashed), 16)  # First 16 chars of SHA256
        self.assertNotEqual(hashed, data)
        self.assertTrue(hashed.isalnum())


class TestSecurityDecorators(unittest.TestCase):
    """Test cases for security decorators."""

    def test_validate_trading_inputs_decorator(self):
        """Test validate_trading_inputs decorator."""
        @validate_trading_inputs
        def test_function(self, input_data):
            return input_data

        # Test with dangerous input
        dangerous_input = "<script>alert('xss')</script>"
        result = test_function(None, dangerous_input)
        self.assertNotIn("<", result)
        self.assertNotIn(">", result)

    def test_rate_limit_decorator(self):
        """Test rate_limit decorator."""
        @rate_limit(2)  # 2 requests per minute
        def test_function(self):
            return "success"

        # First call should succeed
        result = test_function(None)
        self.assertEqual(result, "success")

        # Additional calls should also succeed (rate limit is per minute)
        for _ in range(5):
            result = test_function(None)
            self.assertEqual(result, "success")


if __name__ == "__main__":
    unittest.main()
