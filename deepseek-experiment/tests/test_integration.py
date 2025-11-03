"""
Integration tests for the trading bot system.
"""

import unittest
import asyncio
import json
import tempfile
import shutil
from unittest.mock import patch, MagicMock, AsyncMock
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.trading_engine import TradingEngine
from src.llm_client import LLMClient
from src.data_fetcher import DataFetcher
from src.database_manager import DatabaseManager
from src.monitoring import MonitoringService


class TestTradingBotIntegration(unittest.TestCase):
    """Integration tests for the trading bot system."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for test data
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

        # Mock configuration
        self.mock_config = {
            "INITIAL_BALANCE": 10000.0,
            "MAX_POSITION_SIZE": 0.1,
            "MAX_LEVERAGE": 10.0,
            "TRADING_FEE_PERCENT": 0.05,
            "MAX_ACTIVE_POSITIONS": 6,
            "MIN_CONFIDENCE_THRESHOLD": 0.6,
            "DATA_DIR": self.temp_path
        }

        # Patch config
        self.config_patcher = patch('src.trading_engine.config')
        self.mock_config_obj = self.config_patcher.start()
        for key, value in self.mock_config.items():
            setattr(self.mock_config_obj, key, value)

    def tearDown(self):
        """Clean up test fixtures."""
        self.config_patcher.stop()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_trading_engine_initialization(self):
        """Test trading engine initialization."""
        engine = TradingEngine(initial_balance=5000.0)

        self.assertEqual(engine.balance, 5000.0)
        self.assertEqual(len(engine.positions), 0)
        self.assertEqual(len(engine.trades), 0)

    def test_trading_engine_buy_sell_cycle(self):
        """Test complete buy-sell trading cycle."""
        engine = TradingEngine(initial_balance=10000.0)

        # Execute buy order
        trade = engine.execute_buy(
            symbol="BTC/USDT",
            price=50000.0,
            amount_usdt=1000.0,
            confidence=0.8,
            leverage=2.0
        )

        self.assertIsNotNone(trade)
        self.assertEqual(trade["side"], "buy")
        self.assertEqual(trade["symbol"], "BTC/USDT")
        self.assertEqual(trade["leverage"], 2.0)
        self.assertIn("BTC/USDT", engine.positions)

        # Check portfolio value
        portfolio_value = engine.get_portfolio_value(51000.0)
        self.assertGreater(portfolio_value, 10000.0)  # Should be profitable

        # Execute sell order
        sell_trade = engine.execute_sell(
            symbol="BTC/USDT",
            price=51000.0,
            confidence=0.8
        )

        self.assertIsNotNone(sell_trade)
        self.assertEqual(sell_trade["side"], "sell")
        self.assertGreater(sell_trade.get("profit", 0), 0)  # Should be profitable
        self.assertNotIn("BTC/USDT", engine.positions)  # Position should be closed

    def test_trading_engine_short_position(self):
        """Test short position trading."""
        engine = TradingEngine(initial_balance=10000.0)

        # Execute short order
        trade = engine.execute_short(
            symbol="BTC/USDT",
            price=50000.0,
            amount_usdt=1000.0,
            confidence=0.8,
            leverage=2.0
        )

        self.assertIsNotNone(trade)
        self.assertEqual(trade["side"], "short")
        self.assertEqual(trade["direction"], "short")
        self.assertIn("BTC/USDT", engine.positions)

        # Check portfolio value with price decrease (profitable for short)
        portfolio_value = engine.get_portfolio_value(49000.0)
        self.assertGreater(portfolio_value, 10000.0)

    def test_trading_engine_risk_limits(self):
        """Test risk limit enforcement."""
        engine = TradingEngine(initial_balance=1000.0)

        # Try to buy more than available balance
        trade = engine.execute_buy(
            symbol="BTC/USDT",
            price=50000.0,
            amount_usdt=2000.0,  # More than balance
            confidence=0.8
        )

        self.assertIsNone(trade)  # Should be rejected
        self.assertEqual(engine.balance, 1000.0)  # Balance unchanged

    def test_llm_client_mock_mode(self):
        """Test LLM client in mock mode."""
        client = LLMClient(provider="mock", mock_mode=True)

        market_data = {
            "symbol": "BTC/USDT",
            "price": 50000.0,
            "volume": 1000000,
            "change_24h": 2.5
        }

        portfolio_state = {
            "balance": 10000.0,
            "total_value": 10000.0,
            "open_positions": 0,
            "total_return_pct": 0.0
        }

        decision = client.get_trading_decision(market_data, portfolio_state)

        self.assertIn("action", decision)
        self.assertIn("confidence", decision)
        self.assertIn("justification", decision)
        self.assertIn(decision["action"], ["buy", "sell", "hold"])
        self.assertGreaterEqual(decision["confidence"], 0.0)
        self.assertLessEqual(decision["confidence"], 1.0)

    def test_data_fetcher_mock(self):
        """Test data fetcher with mocked exchange."""
        with patch('src.data_fetcher.ccxt') as mock_ccxt:
            # Mock exchange
            mock_exchange = MagicMock()
            mock_exchange.fetch_ticker.return_value = {
                "last": 50000.0,
                "quoteVolume": 1000000,
                "percentage": 2.5
            }
            mock_ccxt.bybit.return_value = mock_exchange

            fetcher = DataFetcher(exchange_name="bybit", use_testnet=True)
            ticker = fetcher.get_ticker()

            self.assertEqual(ticker["last"], 50000.0)
            self.assertEqual(ticker["quoteVolume"], 1000000)
            self.assertEqual(ticker["percentage"], 2.5)

    def test_portfolio_summary_calculation(self):
        """Test portfolio summary calculation."""
        engine = TradingEngine(initial_balance=10000.0)

        # Execute some trades
        engine.execute_buy("BTC/USDT", 50000.0, 1000.0, 0.8, leverage=2.0)
        engine.execute_buy("ETH/USDT", 3000.0, 500.0, 0.7, leverage=1.5)

        summary = engine.get_portfolio_summary(51000.0)  # BTC price increased

        self.assertIn("balance", summary)
        self.assertIn("total_value", summary)
        self.assertIn("total_return_pct", summary)
        self.assertIn("open_positions", summary)
        self.assertIn("total_trades", summary)

        self.assertEqual(summary["open_positions"], 2)
        self.assertEqual(summary["total_trades"], 2)
        self.assertGreater(summary["total_value"], 10000.0)  # Should be profitable

    def test_behavioral_metrics_calculation(self):
        """Test behavioral metrics calculation."""
        engine = TradingEngine(initial_balance=10000.0)

        # Execute multiple trades to generate behavioral data
        for i in range(5):
            engine.execute_buy(f"SYMBOL{i}/USDT", 1000.0, 100.0, 0.8)
            engine.execute_sell(f"SYMBOL{i}/USDT", 1100.0, confidence=0.8)

        summary = engine.get_portfolio_summary(1000.0)

        # Check behavioral metrics
        self.assertIn("bullish_tilt", summary)
        self.assertIn("avg_holding_period_hours", summary)
        self.assertIn("trade_frequency_per_day", summary)
        self.assertIn("avg_position_size_usdt", summary)
        self.assertIn("avg_confidence", summary)

        # Validate metric ranges
        self.assertGreaterEqual(summary["bullish_tilt"], 0.0)
        self.assertLessEqual(summary["bullish_tilt"], 1.0)
        self.assertGreaterEqual(summary["avg_confidence"], 0.0)
        self.assertLessEqual(summary["avg_confidence"], 1.0)

    def test_error_handling_in_trading_cycle(self):
        """Test error handling in trading operations."""
        engine = TradingEngine(initial_balance=10000.0)

        # Test with invalid inputs
        trade = engine.execute_buy(
            symbol="",  # Empty symbol
            price=-1000.0,  # Negative price
            amount_usdt=0.0,  # Zero amount
            confidence=1.5,  # Invalid confidence
            leverage=0.5  # Invalid leverage
        )

        # Should handle invalid inputs gracefully
        self.assertIsNone(trade)
        self.assertEqual(engine.balance, 10000.0)  # Balance unchanged

    def test_position_management(self):
        """Test position management and tracking."""
        engine = TradingEngine(initial_balance=10000.0)

        # Open multiple positions
        engine.execute_buy("BTC/USDT", 50000.0, 1000.0, 0.8)
        engine.execute_buy("ETH/USDT", 3000.0, 500.0, 0.7)
        engine.execute_short("ADA/USDT", 0.5, 1000.0, 0.6)

        # Check positions
        self.assertEqual(len(engine.positions), 3)
        self.assertIn("BTC/USDT", engine.positions)
        self.assertIn("ETH/USDT", engine.positions)
        self.assertIn("ADA/USDT", engine.positions)

        # Check position details
        btc_pos = engine.positions["BTC/USDT"]
        self.assertEqual(btc_pos["side"], "long")
        self.assertGreater(btc_pos["quantity"], 0)

        ada_pos = engine.positions["ADA/USDT"]
        self.assertEqual(ada_pos["side"], "short")
        self.assertGreater(ada_pos["quantity"], 0)

    def test_trade_persistence(self):
        """Test trade data persistence."""
        engine = TradingEngine(initial_balance=10000.0)

        # Execute some trades
        engine.execute_buy("BTC/USDT", 50000.0, 1000.0, 0.8)
        engine.execute_sell("BTC/USDT", 51000.0, confidence=0.8)

        # Check that trades are saved
        self.assertTrue(engine.trades_file.exists())

        # Load trades from file
        with open(engine.trades_file, 'r') as f:
            saved_trades = json.load(f)

        self.assertEqual(len(saved_trades), 2)
        self.assertEqual(saved_trades[0]["side"], "buy")
        self.assertEqual(saved_trades[1]["side"], "sell")


class TestDatabaseIntegration(unittest.TestCase):
    """Integration tests for database functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Patch asyncio.create_task to avoid event loop issues in tests
        # This prevents the coroutine warning by mocking the task creation
        self.mock_create_task_patcher = patch('src.database_manager.asyncio.create_task')
        self.mock_create_task = self.mock_create_task_patcher.start()

        # Mock task creation to return a mock task object
        def mock_task_func(coro):
            mock_task = MagicMock()
            mock_task.done.return_value = False
            mock_task.cancel = MagicMock()
            return mock_task

        self.mock_create_task.side_effect = mock_task_func

        # Use in-memory SQLite for testing
        self.database_url = "sqlite+aiosqlite:///:memory:"
        self.db_manager = DatabaseManager(self.database_url, fallback_to_json=True)
        # Mark as not connected to use JSON fallback in tests
        self.db_manager.is_connected = False

    def tearDown(self):
        """Clean up after tests."""
        # Stop the patcher
        if hasattr(self, 'mock_create_task_patcher'):
            self.mock_create_task_patcher.stop()

    def test_database_operations(self):
        """Test database operations."""
        import asyncio

        async def _run_test():
            # Test trade saving
            trade_data = {
                "symbol": "BTC/USDT",
                "side": "buy",
                "direction": "long",
                "price": 50000.0,
                "quantity": 0.02,
                "amount_usdt": 1000.0,
                "confidence": 0.8,
                "timestamp": datetime.utcnow().isoformat()
            }

            trade_id = await self.db_manager.save_trade(trade_data)
            self.assertIsNotNone(trade_id)

            # Test position saving
            position_data = {
                "symbol": "BTC/USDT",
                "side": "long",
                "quantity": 0.02,
                "avg_price": 50000.0,
                "value": 1000.0,
                "is_active": True,
                "opened_at": datetime.utcnow().isoformat()
            }

            position_id = await self.db_manager.save_position(position_data)
            self.assertIsNotNone(position_id)

            # Test portfolio snapshot
            portfolio_data = {
                "balance": 9000.0,
                "total_value": 10000.0,
                "active_positions": 1,
                "total_trades": 1,
                "timestamp": datetime.utcnow().isoformat()
            }

            snapshot_id = await self.db_manager.save_portfolio_snapshot(portfolio_data)
            self.assertIsNotNone(snapshot_id)

        try:
            asyncio.run(_run_test())
        except RuntimeError:
            # Skip if event loop is already running
            import sys
            self.skipTest("Async test skipped - event loop already running")

    def test_database_fallback(self):
        """Test database fallback to JSON files."""
        import asyncio

        async def _run_test():
            # Force database connection failure
            self.db_manager.is_connected = False

            trade_data = {
                "symbol": "BTC/USDT",
                "side": "buy",
                "price": 50000.0,
                "quantity": 0.02,
                "amount_usdt": 1000.0,
                "confidence": 0.8,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Should fallback to JSON
            trade_id = await self.db_manager.save_trade(trade_data)
            self.assertIsNotNone(trade_id)

        try:
            asyncio.run(_run_test())
        except RuntimeError:
            # Skip if event loop is already running
            self.skipTest("Async test skipped - event loop already running")

        # Check JSON file was created
        self.assertTrue(self.db_manager.trades_file.exists())


class TestMonitoringIntegration(unittest.TestCase):
    """Integration tests for monitoring functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.monitoring_service = MonitoringService()

    def test_metrics_collection(self):
        """Test metrics collection."""
        # Test counter metrics
        self.monitoring_service.metrics_collector.increment_counter("test.counter")
        self.monitoring_service.metrics_collector.increment_counter("test.counter", 5)

        value = self.monitoring_service.metrics_collector.get_counter_value("test.counter")
        self.assertEqual(value, 6.0)

        # Test gauge metrics
        self.monitoring_service.metrics_collector.set_gauge("test.gauge", 42.0)
        value = self.monitoring_service.metrics_collector.get_gauge_value("test.gauge")
        self.assertEqual(value, 42.0)

        # Test histogram metrics
        for i in range(10):
            self.monitoring_service.metrics_collector.record_histogram("test.histogram", i)

        stats = self.monitoring_service.metrics_collector.get_histogram_stats("test.histogram")
        self.assertEqual(stats["count"], 10)
        self.assertEqual(stats["min"], 0)
        self.assertEqual(stats["max"], 9)
        self.assertEqual(stats["mean"], 4.5)

    def test_health_checks(self):
        """Test health check functionality."""
        async def healthy_check():
            return {"status": "healthy", "message": "OK"}

        async def unhealthy_check():
            return {"status": "unhealthy", "message": "Failed"}

        # Register health checks
        self.monitoring_service.health_checker.register_check("healthy", healthy_check)
        self.monitoring_service.health_checker.register_check("unhealthy", unhealthy_check)

        # Run health checks
        asyncio.run(self.monitoring_service.health_checker.run_all_checks())

        # Check results
        results = self.monitoring_service.health_checker.results
        self.assertIn("healthy", results)
        self.assertIn("unhealthy", results)
        self.assertEqual(results["healthy"].status, "healthy")
        self.assertEqual(results["unhealthy"].status, "unhealthy")

    def test_alert_rules(self):
        """Test alert rule functionality."""
        # Add a test alert rule
        def test_condition(metrics):
            return metrics.get_gauge_value("test.gauge") > 50

        self.monitoring_service.alert_manager.add_alert_rule(
            "test_alert", test_condition, "warning"
        )

        # Set gauge value that should trigger alert
        self.monitoring_service.metrics_collector.set_gauge("test.gauge", 60.0)

        # Check alerts
        try:
            asyncio.run(self.monitoring_service.alert_manager.check_alerts(
                self.monitoring_service.metrics_collector
            ))
        except RuntimeError:
            # If event loop is already running, skip this test
            self.skipTest("Async test skipped - event loop already running")

        # Should have triggered an alert
        self.assertGreater(len(self.monitoring_service.alert_manager.alerts), 0)
        self.assertEqual(self.monitoring_service.alert_manager.alerts[-1]["name"], "test_alert")


if __name__ == "__main__":
    # Run async tests
    asyncio.run(unittest.main())
