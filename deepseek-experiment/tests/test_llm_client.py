"""
Unit tests for the LLM client module.

Tests prompt formatting, response validation, and mock functionality.
"""

import unittest
from unittest.mock import patch, MagicMock
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.llm_client import LLMClient


class TestLLMClient(unittest.TestCase):
    """Test cases for LLMClient."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = LLMClient(mock_mode=True)

    def test_format_trading_prompt(self):
        """Test prompt formatting with market data and portfolio state."""
        market_data = {
            "symbol": "BTC/USDT",
            "price": 50000.0,
            "volume": 1000000,
            "change_24h": 2.5
        }

        portfolio_state = {
            "balance": 5000.0,
            "total_value": 10000.0,
            "open_positions": 1,
            "total_return_pct": 5.2,
            "total_trades": 10
        }

        prompt = self.client._format_trading_prompt(market_data, portfolio_state)

        # Check that all key information is included
        self.assertIn("BTC/USDT", prompt)
        self.assertIn("50000.00", prompt)
        self.assertIn("1,000,000", prompt)
        self.assertIn("2.50%", prompt)
        self.assertIn("5000.00", prompt)
        self.assertIn("10000.00", prompt)
        self.assertIn("JSON", prompt)
        self.assertIn("action", prompt)
        self.assertIn("confidence", prompt)
        self.assertIn("reasoning", prompt)

    def test_validate_llm_response_valid(self):
        """Test validation of valid LLM response."""
        valid_response = {
            "action": "buy",
            "confidence": 0.8,
            "reasoning": "Strong bullish signal",
            "position_size": 0.15,
            "risk_assessment": "medium"
        }

        result = self.client._validate_llm_response(json.dumps(valid_response))

        self.assertIsNotNone(result)
        self.assertEqual(result["action"], "buy")
        self.assertEqual(result["confidence"], 0.8)
        self.assertEqual(result["reasoning"], "Strong bullish signal")
        self.assertEqual(result["position_size"], 0.15)
        self.assertEqual(result["risk_assessment"], "medium")

    def test_validate_llm_response_missing_fields(self):
        """Test validation fails with missing required fields."""
        invalid_response = {
            "action": "buy",
            "confidence": 0.8
            # Missing "reasoning"
        }

        result = self.client._validate_llm_response(json.dumps(invalid_response))
        self.assertIsNone(result)

    def test_validate_llm_response_invalid_action(self):
        """Test validation fails with invalid action."""
        invalid_response = {
            "action": "invalid_action",
            "confidence": 0.8,
            "reasoning": "Test reasoning"
        }

        result = self.client._validate_llm_response(json.dumps(invalid_response))
        self.assertIsNone(result)

    def test_validate_llm_response_invalid_confidence(self):
        """Test validation fails with invalid confidence."""
        invalid_response = {
            "action": "buy",
            "confidence": 1.5,  # Invalid: > 1.0
            "reasoning": "Test reasoning"
        }

        result = self.client._validate_llm_response(json.dumps(invalid_response))
        self.assertIsNone(result)

    def test_validate_llm_response_json_extraction(self):
        """Test JSON extraction from text with extra content."""
        response_text = """
        Here is my trading decision:
        {
            "action": "sell",
            "confidence": 0.75,
            "reasoning": "Market showing bearish signals"
        }
        This concludes my analysis.
        """

        result = self.client._validate_llm_response(response_text)

        self.assertIsNotNone(result)
        self.assertEqual(result["action"], "sell")
        self.assertEqual(result["confidence"], 0.75)
        self.assertEqual(result["reasoning"], "Market showing bearish signals")

    def test_validate_llm_response_unquoted_keys_and_values(self):
        """Test validation of JSON with unquoted keys and string values."""
        # This matches the actual error case reported
        response_text = """{
    action: hold,
    direction: none,
    quantity: 0.0,
    leverage: 1.0,
    confidence: 0.3,
    justification: Insufficient quantitative data for high-conviction trade. Only current price and basic metrics available.
}"""

        result = self.client._validate_llm_response(response_text)

        self.assertIsNotNone(result, "Should parse JSON with unquoted keys and values")
        self.assertEqual(result["action"], "hold")
        self.assertEqual(result["direction"], "none")
        self.assertEqual(result["quantity"], 0.0)
        self.assertEqual(result["leverage"], 1.0)
        self.assertEqual(result["confidence"], 0.3)
        self.assertIn("justification", result)

    def test_get_mock_response(self):
        """Test mock response generation."""
        market_data = {
            "price": 50000,
            "change_24h": 3.0
        }

        portfolio_state = {
            "balance": 5000,
            "open_positions": 0
        }

        response = self.client._get_mock_response(market_data, portfolio_state)

        self.assertIn("choices", response)
        self.assertIn("message", response["choices"][0])

        content = json.loads(response["choices"][0]["message"]["content"])
        self.assertIn("action", content)
        self.assertIn("confidence", content)
        self.assertIn("reasoning", content)
        self.assertIn("position_size", content)
        self.assertIn("risk_assessment", content)

    def test_get_trading_decision_mock_mode(self):
        """Test trading decision in mock mode."""
        market_data = {
            "symbol": "BTC/USDT",
            "price": 50000.0,
            "volume": 1000000,
            "change_24h": 2.5
        }

        portfolio_state = {
            "balance": 5000.0,
            "total_value": 10000.0,
            "open_positions": 0,
            "total_return_pct": 0.0,
            "total_trades": 0
        }

        decision = self.client.get_trading_decision(market_data, portfolio_state)

        self.assertIsNotNone(decision)
        self.assertIn("action", decision)
        self.assertIn("confidence", decision)
        self.assertIn("reasoning", decision)
        self.assertIn("position_size", decision)
        self.assertIn("risk_assessment", decision)

        # Validate action is one of the expected values
        self.assertIn(decision["action"], ["buy", "sell", "hold"])

        # Validate confidence is between 0 and 1
        self.assertGreaterEqual(decision["confidence"], 0.0)
        self.assertLessEqual(decision["confidence"], 1.0)

    def test_get_trading_decision_error_handling(self):
        """Test error handling in trading decision."""
        # Test with None market data to trigger error in mock response
        with patch.object(self.client, '_get_mock_response', side_effect=Exception("Test error")):
            decision = self.client.get_trading_decision({"price": 50000})

            # Should return hold decision on error
            self.assertEqual(decision["action"], "hold")
            self.assertEqual(decision["confidence"], 0.0)
            self.assertIn("Error occurred", decision["reasoning"])

    @patch('src.llm_client.requests.post')
    def test_deepseek_api_call_success(self, mock_post):
        """Test successful DeepSeek API call and response parsing."""
        from tests.test_utils import MockDataGenerator

        # Setup mock API response with valid JSON content
        valid_json_content = json.dumps({
            "action": "buy",
            "direction": "long",
            "quantity": 0.02,
            "leverage": 2.0,
            "confidence": 0.85,
            "justification": "Strong bullish momentum detected with high volume",
            "exit_plan": {
                "profit_target": 52000.0,
                "stop_loss": 49000.0,
                "invalidation_conditions": ["market_reversal", "volume_drop"]
            },
            "position_size_usdt": 1000.0,
            "risk_assessment": "medium"
        })

        mock_response_data = {
            "choices": [
                {
                    "message": {
                        "content": valid_json_content
                    }
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        # Create client with DeepSeek provider (not in mock mode)
        client = LLMClient(
            provider="deepseek",
            api_key=MockDataGenerator.generate_mock_api_key("deepseek"),
            api_url="https://api.deepseek.com/v1/chat/completions",
            model="deepseek-chat",
            mock_mode=False
        )

        market_data = {
            "symbol": "BTC/USDT",
            "price": 50000.0,
            "volume": 1000000,
            "change_24h": 2.5
        }

        portfolio_state = {
            "balance": 5000.0,
            "total_value": 10000.0,
            "open_positions": 0,
            "total_return_pct": 0.0,
            "total_trades": 0
        }

        # Make the API call
        decision = client.get_trading_decision(market_data, portfolio_state)

        # Verify API was called
        self.assertTrue(mock_post.called)
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "https://api.deepseek.com/v1/chat/completions")

        # Verify request payload
        payload = call_args[1]["json"]
        self.assertEqual(payload["model"], "deepseek-chat")
        self.assertEqual(len(payload["messages"]), 2)
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertEqual(payload["messages"][1]["role"], "user")

        # Verify response parsing
        self.assertIsNotNone(decision)
        self.assertEqual(decision["action"], "buy")
        self.assertEqual(decision["direction"], "long")
        self.assertEqual(decision["confidence"], 0.85)
        self.assertIn("justification", decision)
        self.assertIn("exit_plan", decision)
        self.assertEqual(decision["exit_plan"]["profit_target"], 52000.0)

    @patch('src.llm_client.requests.post')
    def test_deepseek_api_call_authentication_error(self, mock_post):
        """Test DeepSeek API call with 401 authentication error."""
        from tests.test_utils import MockDataGenerator

        # Setup mock API response for 401 error
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status = MagicMock(side_effect=Exception("401 Unauthorized"))
        mock_post.return_value = mock_response

        client = LLMClient(
            provider="deepseek",
            api_key=MockDataGenerator.generate_mock_api_key("deepseek"),
            api_url="https://api.deepseek.com/v1/chat/completions",
            model="deepseek-chat",
            mock_mode=False
        )

        market_data = {"symbol": "BTC/USDT", "price": 50000.0}
        portfolio_state = {"balance": 5000.0, "total_value": 10000.0}

        # Should fall back to mock mode on error
        decision = client.get_trading_decision(market_data, portfolio_state)

        # Verify API was called
        self.assertTrue(mock_post.called)

        # Should return a decision (fallback to mock)
        self.assertIsNotNone(decision)
        self.assertIn("action", decision)

    @patch('src.llm_client.requests.post')
    def test_deepseek_api_call_payment_required_error(self, mock_post):
        """Test DeepSeek API call with 402 payment required error."""
        from tests.test_utils import MockDataGenerator

        # Setup mock API response for 402 error
        mock_response = MagicMock()
        mock_response.status_code = 402
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        client = LLMClient(
            provider="deepseek",
            api_key=MockDataGenerator.generate_mock_api_key("deepseek"),
            api_url="https://api.deepseek.com/v1/chat/completions",
            model="deepseek-chat",
            mock_mode=False
        )

        market_data = {"symbol": "BTC/USDT", "price": 50000.0}
        portfolio_state = {"balance": 5000.0, "total_value": 10000.0}

        # Should fall back to mock mode on payment error
        decision = client.get_trading_decision(market_data, portfolio_state)

        # Verify API was called
        self.assertTrue(mock_post.called)

        # Should return a decision (fallback to mock)
        self.assertIsNotNone(decision)
        self.assertIn("action", decision)

    @patch('src.llm_client.requests.post')
    def test_deepseek_api_call_invalid_json_response(self, mock_post):
        """Test DeepSeek API call with invalid JSON in response."""
        from tests.test_utils import MockDataGenerator

        # Setup mock API response with invalid JSON
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "{ action: buy, confidence: 0.8, justification: Test }"  # Unquoted keys/values
                    }
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        client = LLMClient(
            provider="deepseek",
            api_key=MockDataGenerator.generate_mock_api_key("deepseek"),
            api_url="https://api.deepseek.com/v1/chat/completions",
            model="deepseek-chat",
            mock_mode=False
        )

        market_data = {"symbol": "BTC/USDT", "price": 50000.0}
        portfolio_state = {"balance": 5000.0, "total_value": 10000.0}

        # Should handle unquoted JSON and parse it
        decision = client.get_trading_decision(market_data, portfolio_state)

        # Verify API was called
        self.assertTrue(mock_post.called)

        # Should parse the unquoted JSON successfully (thanks to our fix)
        self.assertIsNotNone(decision)
        self.assertEqual(decision["action"], "buy")
        self.assertEqual(decision["confidence"], 0.8)

    @patch('src.llm_client.requests.post')
    def test_deepseek_api_call_http_error(self, mock_post):
        """Test DeepSeek API call with HTTP error."""
        from tests.test_utils import MockDataGenerator

        # Setup mock API response for HTTP error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status = MagicMock(side_effect=Exception("500 Internal Server Error"))
        mock_post.return_value = mock_response

        client = LLMClient(
            provider="deepseek",
            api_key=MockDataGenerator.generate_mock_api_key("deepseek"),
            api_url="https://api.deepseek.com/v1/chat/completions",
            model="deepseek-chat",
            mock_mode=False
        )

        market_data = {"symbol": "BTC/USDT", "price": 50000.0}
        portfolio_state = {"balance": 5000.0, "total_value": 10000.0}

        # Should fall back to mock mode on HTTP error
        decision = client.get_trading_decision(market_data, portfolio_state)

        # Verify API was called
        self.assertTrue(mock_post.called)

        # Should return a decision (fallback to mock)
        self.assertIsNotNone(decision)
        self.assertIn("action", decision)

    @patch('src.llm_client.requests.post')
    def test_deepseek_api_call_network_error(self, mock_post):
        """Test DeepSeek API call with network/connection error."""
        from tests.test_utils import MockDataGenerator
        import requests

        # Setup mock to raise connection error
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection failed")

        client = LLMClient(
            provider="deepseek",
            api_key=MockDataGenerator.generate_mock_api_key("deepseek"),
            api_url="https://api.deepseek.com/v1/chat/completions",
            model="deepseek-chat",
            mock_mode=False
        )

        market_data = {"symbol": "BTC/USDT", "price": 50000.0}
        portfolio_state = {"balance": 5000.0, "total_value": 10000.0}

        # Should fall back to mock mode on network error
        decision = client.get_trading_decision(market_data, portfolio_state)

        # Verify API was called
        self.assertTrue(mock_post.called)

        # Should return a decision (fallback to mock)
        self.assertIsNotNone(decision)
        self.assertIn("action", decision)

    @patch('src.llm_client.requests.post')
    def test_deepseek_api_call_with_markdown_code_block(self, mock_post):
        """Test DeepSeek API call with JSON wrapped in markdown code block."""
        from tests.test_utils import MockDataGenerator

        # Setup mock API response with markdown code block
        mock_response_data = {
            "choices": [
                {
                    "message": {
                        "content": """Here is my trading decision:
```json
{
    "action": "sell",
    "direction": "short",
    "quantity": 0.01,
    "leverage": 3.0,
    "confidence": 0.75,
    "justification": "Bearish signal detected",
    "exit_plan": {
        "profit_target": 48000.0,
        "stop_loss": 52000.0,
        "invalidation_conditions": []
    },
    "position_size_usdt": 500.0,
    "risk_assessment": "high"
}
```
This is the end of my analysis."""
                    }
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        client = LLMClient(
            provider="deepseek",
            api_key=MockDataGenerator.generate_mock_api_key("deepseek"),
            api_url="https://api.deepseek.com/v1/chat/completions",
            model="deepseek-chat",
            mock_mode=False
        )

        market_data = {"symbol": "BTC/USDT", "price": 50000.0}
        portfolio_state = {"balance": 5000.0, "total_value": 10000.0}

        # Should extract JSON from markdown code block
        decision = client.get_trading_decision(market_data, portfolio_state)

        # Verify response parsing
        self.assertIsNotNone(decision)
        self.assertEqual(decision["action"], "sell")
        self.assertEqual(decision["direction"], "short")
        self.assertEqual(decision["confidence"], 0.75)
        self.assertEqual(decision["risk_assessment"], "high")


if __name__ == "__main__":
    unittest.main()
