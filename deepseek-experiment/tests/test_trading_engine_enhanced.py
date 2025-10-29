"""
Enhanced unit tests for the trading engine with LLM integration.

Tests trade execution with LLM decision context and enhanced logging.
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.trading_engine import TradingEngine


class TestTradingEngineEnhanced(unittest.TestCase):
    """Enhanced test cases for TradingEngine with LLM integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.engine = TradingEngine(initial_balance=1000.0)
        # Clear any existing trades for clean test state
        self.engine.trades = []
        self.engine.positions = {}
        self.engine.balance = 1000.0
    
    def test_execute_buy_with_llm_context(self):
        """Test buy execution with full LLM decision context."""
        llm_decision = {
            "action": "buy",
            "confidence": 0.8,
            "reasoning": "Strong bullish momentum detected",
            "position_size": 0.15,
            "risk_assessment": "medium"
        }
        
        trade = self.engine.execute_buy(
            "BTC/USDT", 
            50000.0, 
            100.0, 
            0.8, 
            llm_decision
        )
        
        self.assertIsNotNone(trade)
        self.assertEqual(trade["side"], "buy")
        self.assertEqual(trade["llm_reasoning"], "Strong bullish momentum detected")
        self.assertEqual(trade["llm_risk_assessment"], "medium")
        self.assertEqual(trade["llm_position_size"], 0.15)
    
    def test_execute_sell_with_llm_context(self):
        """Test sell execution with full LLM decision context."""
        # First buy
        llm_buy_decision = {
            "action": "buy",
            "confidence": 0.8,
            "reasoning": "Initial position",
            "position_size": 0.1,
            "risk_assessment": "low"
        }
        
        self.engine.execute_buy("BTC/USDT", 50000.0, 100.0, 0.8, llm_buy_decision)
        
        # Then sell
        llm_sell_decision = {
            "action": "sell",
            "confidence": 0.9,
            "reasoning": "Take profit signal",
            "position_size": 1.0,
            "risk_assessment": "low"
        }
        
        trade = self.engine.execute_sell(
            "BTC/USDT", 
            51000.0, 
            confidence=0.9, 
            llm_decision=llm_sell_decision
        )
        
        self.assertIsNotNone(trade)
        self.assertEqual(trade["side"], "sell")
        self.assertEqual(trade["llm_reasoning"], "Take profit signal")
        self.assertEqual(trade["llm_risk_assessment"], "low")
        self.assertEqual(trade["llm_position_size"], 1.0)
        self.assertGreater(trade.get("profit", 0), 0)
    
    def test_execute_buy_without_llm_context(self):
        """Test buy execution without LLM decision context."""
        trade = self.engine.execute_buy("BTC/USDT", 50000.0, 100.0, 0.8)
        
        self.assertIsNotNone(trade)
        self.assertEqual(trade["side"], "buy")
        self.assertEqual(trade["llm_reasoning"], "")
        self.assertEqual(trade["llm_risk_assessment"], "medium")
        self.assertEqual(trade["llm_position_size"], 0.1)
    
    def test_execute_sell_without_llm_context(self):
        """Test sell execution without LLM decision context."""
        # First buy
        self.engine.execute_buy("BTC/USDT", 50000.0, 100.0, 0.8)
        
        # Then sell
        trade = self.engine.execute_sell("BTC/USDT", 51000.0, confidence=0.9)
        
        self.assertIsNotNone(trade)
        self.assertEqual(trade["side"], "sell")
        self.assertEqual(trade["llm_reasoning"], "")
        self.assertEqual(trade["llm_risk_assessment"], "medium")
        self.assertEqual(trade["llm_position_size"], 0.1)
    
    def test_trade_history_with_llm_context(self):
        """Test that trade history includes LLM context."""
        llm_decision = {
            "action": "buy",
            "confidence": 0.85,
            "reasoning": "Technical analysis shows upward trend",
            "position_size": 0.2,
            "risk_assessment": "high"
        }
        
        trade = self.engine.execute_buy("BTC/USDT", 50000.0, 200.0, 0.85, llm_decision)
        
        # Check that the trade is saved with LLM context
        self.assertEqual(len(self.engine.trades), 1)
        saved_trade = self.engine.trades[0]
        
        self.assertEqual(saved_trade["llm_reasoning"], "Technical analysis shows upward trend")
        self.assertEqual(saved_trade["llm_risk_assessment"], "high")
        self.assertEqual(saved_trade["llm_position_size"], 0.2)
    
    def test_portfolio_summary_includes_llm_trades(self):
        """Test that portfolio summary reflects trades with LLM context."""
        llm_decision = {
            "action": "buy",
            "confidence": 0.8,
            "reasoning": "Market momentum positive",
            "position_size": 0.1,
            "risk_assessment": "medium"
        }
        
        self.engine.execute_buy("BTC/USDT", 50000.0, 100.0, 0.8, llm_decision)
        
        portfolio = self.engine.get_portfolio_summary(51000.0)
        
        self.assertEqual(portfolio["total_trades"], 1)
        self.assertEqual(portfolio["open_positions"], 1)
        self.assertGreater(portfolio["total_value"], 1000.0)  # Should have gained value


if __name__ == "__main__":
    unittest.main()
