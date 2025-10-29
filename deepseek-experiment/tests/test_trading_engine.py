"""
Unit tests for the trading engine.

Example test file - expand with more tests as needed.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.trading_engine import TradingEngine


class TestTradingEngine(unittest.TestCase):
    """Test cases for TradingEngine."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.engine = TradingEngine(initial_balance=1000.0)
    
    def test_initial_balance(self):
        """Test that initial balance is set correctly."""
        self.assertEqual(self.engine.balance, 1000.0)
    
    def test_execute_buy(self):
        """Test buy order execution."""
        trade = self.engine.execute_buy("BTC/USDT", 50000.0, 100.0, 0.8)
        
        self.assertIsNotNone(trade)
        self.assertEqual(trade["side"], "buy")
        self.assertEqual(self.engine.balance, 900.0)
        self.assertIn("BTC/USDT", self.engine.positions)
    
    def test_execute_sell(self):
        """Test sell order execution."""
        # First buy
        self.engine.execute_buy("BTC/USDT", 50000.0, 100.0, 0.8)
        
        # Then sell
        trade = self.engine.execute_sell("BTC/USDT", 51000.0, confidence=0.8)
        
        self.assertIsNotNone(trade)
        self.assertEqual(trade["side"], "sell")
        self.assertGreater(trade.get("profit", 0), 0)
    
    def test_insufficient_balance(self):
        """Test that buy fails with insufficient balance."""
        trade = self.engine.execute_buy("BTC/USDT", 50000.0, 2000.0, 0.8)
        self.assertIsNone(trade)
    
    def test_get_portfolio_value(self):
        """Test portfolio value calculation."""
        self.engine.execute_buy("BTC/USDT", 50000.0, 100.0, 0.8)
        value = self.engine.get_portfolio_value(51000.0)
        
        self.assertGreater(value, 1000.0)  # Should be more due to price increase


if __name__ == "__main__":
    unittest.main()

