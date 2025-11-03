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
        # Ensure trades file doesn't interfere with tests - delete it BEFORE creating engine
        trades_file = Path("data/trades.json")
        if trades_file.exists():
            trades_file.unlink()

        self.engine = TradingEngine(initial_balance=1000.0)
        # Clear any existing trades for clean test state (in case any were loaded from file)
        self.engine.trades = []
        self.engine.positions = {}
        self.engine.balance = 1000.0

    def test_execute_buy_with_llm_context(self):
        """Test buy execution with full LLM decision context."""
        llm_decision = {
            "action": "buy",
            "confidence": 0.8,
            "justification": "Strong bullish momentum detected",
            "position_size_usdt": 100.0,
            "risk_assessment": "medium"
        }

        # Verify llm_decision is properly structured before passing
        self.assertIn("justification", llm_decision)
        self.assertEqual(llm_decision["justification"], "Strong bullish momentum detected")

        trade = self.engine.execute_buy(
            "BTC/USDT",
            50000.0,
            100.0,
            0.8,
            llm_decision
        )

        self.assertIsNotNone(trade, "Trade should not be None")
        self.assertEqual(trade["side"], "buy")
        # Add debug message if assertion fails
        self.assertEqual(trade["llm_reasoning"], "Strong bullish momentum detected",
                        f"Expected 'Strong bullish momentum detected' but got '{trade.get('llm_reasoning')}'. "
                        f"llm_decision was: {llm_decision}, trade keys: {list(trade.keys())}")
        self.assertEqual(trade["llm_risk_assessment"], "medium")
        self.assertEqual(trade["llm_position_size_usdt"], 100.0)

    def test_execute_sell_with_llm_context(self):
        """Test sell execution with full LLM decision context."""
        # First buy
        llm_buy_decision = {
            "action": "buy",
            "confidence": 0.8,
            "justification": "Initial position",
            "position_size_usdt": 100.0,
            "risk_assessment": "low"
        }

        self.engine.execute_buy("BTC/USDT", 50000.0, 100.0, 0.8, llm_buy_decision)

        # Then sell
        llm_sell_decision = {
            "action": "sell",
            "confidence": 0.9,
            "justification": "Take profit signal",
            "position_size_usdt": 100.0,
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
        # Verify LLM context is properly extracted
        self.assertEqual(trade["llm_reasoning"], "Take profit signal",
                        f"Expected 'Take profit signal' but got '{trade.get('llm_reasoning')}'. "
                        f"Trade keys: {list(trade.keys())}, llm_decision: {llm_sell_decision}")
        self.assertEqual(trade["llm_risk_assessment"], "low")
        self.assertEqual(trade["llm_position_size_usdt"], 100.0)
        self.assertGreater(trade.get("profit", 0), 0)

    def test_execute_buy_without_llm_context(self):
        """Test buy execution without LLM decision context."""
        trade = self.engine.execute_buy("BTC/USDT", 50000.0, 100.0, 0.8)

        self.assertIsNotNone(trade)
        self.assertEqual(trade["side"], "buy")
        self.assertEqual(trade["llm_reasoning"], "")
        self.assertEqual(trade["llm_risk_assessment"], "medium")
        self.assertEqual(trade["llm_position_size_usdt"], 0.0)  # No LLM decision provided

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
        self.assertEqual(trade["llm_position_size_usdt"], 0.0)  # No LLM decision provided

    def test_trade_history_with_llm_context(self):
        """Test that trade history includes LLM context."""
        llm_decision = {
            "action": "buy",
            "confidence": 0.85,
            "justification": "Technical analysis shows upward trend",
            "position_size_usdt": 200.0,
            "risk_assessment": "high"
        }

        # Verify llm_decision structure before passing
        self.assertIn("justification", llm_decision)
        self.assertEqual(llm_decision["justification"], "Technical analysis shows upward trend")

        trade = self.engine.execute_buy("BTC/USDT", 50000.0, 200.0, 0.85, llm_decision)

        # Verify the returned trade has LLM context
        self.assertIsNotNone(trade, "Trade should not be None")
        self.assertEqual(trade["llm_reasoning"], "Technical analysis shows upward trend",
                        f"Expected 'Technical analysis shows upward trend' but got '{trade.get('llm_reasoning')}'. "
                        f"llm_decision was: {llm_decision}, trade keys: {list(trade.keys())}")
        self.assertEqual(trade["llm_risk_assessment"], "high")
        self.assertEqual(trade["llm_position_size_usdt"], 200.0)

        # Check that the trade is saved with LLM context (use the most recent trade)
        self.assertGreaterEqual(len(self.engine.trades), 1,
                               f"Expected at least 1 trade, but found {len(self.engine.trades)}")
        saved_trade = self.engine.trades[-1]  # Get the last trade (most recently added)

        # Verify the saved trade matches what we just created
        self.assertEqual(saved_trade["id"], trade["id"],
                       f"Saved trade ID {saved_trade.get('id')} should match returned trade ID {trade.get('id')}")
        self.assertEqual(saved_trade["llm_reasoning"], "Technical analysis shows upward trend",
                        f"Expected 'Technical analysis shows upward trend' but got '{saved_trade.get('llm_reasoning')}'. "
                        f"Saved trade keys: {list(saved_trade.keys())}, saved trade llm keys: "
                        f"{[k for k in saved_trade.keys() if 'llm' in k]}")
        self.assertEqual(saved_trade["llm_risk_assessment"], "high")
        self.assertEqual(saved_trade["llm_position_size_usdt"], 200.0)

    def test_portfolio_summary_includes_llm_trades(self):
        """Test that portfolio summary reflects trades with LLM context."""
        llm_decision = {
            "action": "buy",
            "confidence": 0.8,
            "justification": "Market momentum positive",
            "position_size_usdt": 100.0,
            "risk_assessment": "medium"
        }

        self.engine.execute_buy("BTC/USDT", 50000.0, 100.0, 0.8, llm_decision)

        portfolio = self.engine.get_portfolio_summary(51000.0)

        self.assertEqual(portfolio["total_trades"], 1)
        self.assertEqual(portfolio["open_positions"], 1)
        self.assertGreater(portfolio["total_value"], 1000.0)  # Should have gained value


if __name__ == "__main__":
    unittest.main()
