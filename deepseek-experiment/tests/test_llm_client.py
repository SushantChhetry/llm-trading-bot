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


if __name__ == "__main__":
    unittest.main()
