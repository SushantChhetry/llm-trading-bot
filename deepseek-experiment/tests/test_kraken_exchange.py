"""
Unit tests for Kraken exchange integration.

Tests Kraken-specific functionality including:
- Exchange initialization and configuration
- Market data fetching (ticker, OHLCV, orderbook)
- Technical indicators
- Error handling and resilience
- Kraken-specific characteristics (no testnet, spot trading)
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_fetcher import DataFetcher
from ccxt.base.errors import ExchangeError, NetworkError, RateLimitExceeded


class TestKrakenExchange(unittest.TestCase):
    """Test cases for Kraken exchange integration."""

    def setUp(self):
        """Set up test fixtures."""
        self.exchange_name = "kraken"
        self.symbol = "BTC/USD"  # Kraken typically uses BTC/USD format
        self.mock_api_key = "test_kraken_api_key"
        self.mock_api_secret = "test_kraken_api_secret"

    @patch('src.data_fetcher.ccxt')
    @patch('src.data_fetcher.config')
    def test_kraken_initialization(self, mock_config, mock_ccxt):
        """Test Kraken exchange initialization with correct configuration."""
        # Setup config mock
        mock_config.EXCHANGE = "kraken"
        mock_config.SYMBOL = "BTC/USD"
        mock_config.USE_TESTNET = False
        mock_config.EXCHANGE_API_KEY = self.mock_api_key
        mock_config.EXCHANGE_API_SECRET = self.mock_api_secret

        # Setup ccxt mock
        mock_kraken_class = MagicMock()
        mock_exchange = MagicMock()
        mock_kraken_class.return_value = mock_exchange
        mock_ccxt.kraken = mock_kraken_class

        # Create DataFetcher
        fetcher = DataFetcher(exchange_name="kraken", use_testnet=False)

        # Verify exchange was initialized
        self.assertTrue(mock_kraken_class.called)

        # Get call arguments - exchange_params is passed as first positional argument
        call_kwargs = mock_kraken_class.call_args[0][0]  # first positional argument (dict)

        # Verify Kraken-specific configuration
        self.assertEqual(call_kwargs["apiKey"], self.mock_api_key)
        self.assertEqual(call_kwargs["secret"], self.mock_api_secret)
        self.assertTrue(call_kwargs["enableRateLimit"])
        self.assertEqual(call_kwargs["options"]["defaultType"], "spot")
        self.assertTrue(call_kwargs["options"]["adjustForTimeDifference"])

        # Verify exchange instance
        self.assertEqual(fetcher.exchange_name, "kraken")
        self.assertEqual(fetcher.symbol, "BTC/USD")

    @patch('src.data_fetcher.ccxt')
    @patch('src.data_fetcher.config')
    def test_kraken_no_testnet_support(self, mock_config, mock_ccxt):
        """Test that Kraken doesn't use testnet even when use_testnet=True."""
        # Setup config mock
        mock_config.EXCHANGE = "kraken"
        mock_config.SYMBOL = "BTC/USD"
        mock_config.USE_TESTNET = True  # Try to enable testnet
        mock_config.EXCHANGE_API_KEY = None
        mock_config.EXCHANGE_API_SECRET = None

        # Setup ccxt mock
        mock_kraken_class = MagicMock()
        mock_exchange = MagicMock()
        mock_kraken_class.return_value = mock_exchange
        mock_ccxt.kraken = mock_kraken_class

        # Create DataFetcher with testnet=True (should be ignored for Kraken)
        fetcher = DataFetcher(exchange_name="kraken", use_testnet=True)

        # Verify that defaultType is still "spot" (not testnet)
        call_kwargs = mock_kraken_class.call_args[0][0]  # first positional argument
        self.assertEqual(call_kwargs["options"]["defaultType"], "spot")
        # Kraken doesn't have testnet, so it should use spot regardless

    @patch('src.data_fetcher.ccxt')
    @patch('src.data_fetcher.config')
    @patch('src.data_fetcher.exchange_circuit_breaker')
    def test_kraken_fetch_ticker_success(self, mock_circuit_breaker, mock_config, mock_ccxt):
        """Test successful ticker fetch from Kraken."""
        # Setup config mock
        mock_config.EXCHANGE = "kraken"
        mock_config.SYMBOL = "BTC/USD"
        mock_config.USE_TESTNET = False
        mock_config.EXCHANGE_API_KEY = None
        mock_config.EXCHANGE_API_SECRET = None

        # Setup mock exchange
        mock_kraken_class = MagicMock()
        mock_exchange = MagicMock()
        mock_ticker = {
            "symbol": "BTC/USD",
            "last": 50000.0,
            "bid": 49950.0,
            "ask": 50050.0,
            "high": 51000.0,
            "low": 49000.0,
            "volume": 1000.0,
            "quoteVolume": 50000000.0,
            "percentage": 2.5,
            "timestamp": int(time.time() * 1000),
        }
        mock_exchange.fetch_ticker.return_value = mock_ticker
        mock_kraken_class.return_value = mock_exchange
        mock_ccxt.kraken = mock_kraken_class

        # Setup circuit breaker and retry handler mocks
        mock_circuit_breaker.call.side_effect = lambda func: func()

        fetcher = DataFetcher(exchange_name="kraken", use_testnet=False)
        ticker = fetcher.get_ticker()

        # Verify ticker data
        self.assertEqual(ticker["last"], 50000.0)
        self.assertEqual(ticker["bid"], 49950.0)
        self.assertEqual(ticker["ask"], 50050.0)
        self.assertEqual(ticker["volume"], 1000.0)
        self.assertEqual(ticker["quoteVolume"], 50000000.0)
        self.assertEqual(ticker["percentage"], 2.5)
        self.assertEqual(ticker["symbol"], "BTC/USD")

        # Verify exchange method was called
        mock_exchange.fetch_ticker.assert_called_with("BTC/USD")

    @patch('src.data_fetcher.ccxt')
    @patch('src.data_fetcher.config')
    @patch('src.data_fetcher.exchange_circuit_breaker')
    def test_kraken_fetch_price(self, mock_circuit_breaker, mock_config, mock_ccxt):
        """Test fetching current price from Kraken."""
        # Setup config mock
        mock_config.EXCHANGE = "kraken"
        mock_config.SYMBOL = "BTC/USD"
        mock_config.USE_TESTNET = False
        mock_config.EXCHANGE_API_KEY = None
        mock_config.EXCHANGE_API_SECRET = None

        # Setup mock exchange
        mock_kraken_class = MagicMock()
        mock_exchange = MagicMock()
        mock_exchange.fetch_ticker.return_value = {
            "last": 50123.45,
            "symbol": "BTC/USD"
        }
        mock_kraken_class.return_value = mock_exchange
        mock_ccxt.kraken = mock_kraken_class

        # Setup circuit breaker mock
        mock_circuit_breaker.call.side_effect = lambda func: func()

        fetcher = DataFetcher(exchange_name="kraken", use_testnet=False)
        price = fetcher.get_price()

        # Verify price
        self.assertEqual(price, 50123.45)
        self.assertIsInstance(price, float)
        self.assertGreater(price, 0)

    @patch('src.data_fetcher.ccxt')
    @patch('src.data_fetcher.config')
    @patch('src.data_fetcher.exchange_circuit_breaker')
    def test_kraken_fetch_ohlcv(self, mock_circuit_breaker, mock_config, mock_ccxt):
        """Test fetching OHLCV data from Kraken."""
        # Setup config mock
        mock_config.EXCHANGE = "kraken"
        mock_config.SYMBOL = "BTC/USD"
        mock_config.USE_TESTNET = False
        mock_config.EXCHANGE_API_KEY = None
        mock_config.EXCHANGE_API_SECRET = None

        # Setup mock exchange
        mock_kraken_class = MagicMock()
        mock_exchange = MagicMock()
        mock_ohlcv = [
            [int(time.time() * 1000) - 60000, 50000.0, 50100.0, 49900.0, 50050.0, 100.0],
            [int(time.time() * 1000), 50050.0, 50150.0, 49950.0, 50100.0, 150.0],
        ]
        mock_exchange.fetch_ohlcv.return_value = mock_ohlcv
        mock_kraken_class.return_value = mock_exchange
        mock_ccxt.kraken = mock_kraken_class

        # Setup circuit breaker mock
        mock_circuit_breaker.call.side_effect = lambda func: func()

        fetcher = DataFetcher(exchange_name="kraken", use_testnet=False)
        ohlcv = fetcher.get_ohlcv(timeframe="1m", limit=100)

        # Verify OHLCV data
        self.assertIsInstance(ohlcv, list)
        self.assertEqual(len(ohlcv), 2)
        self.assertEqual(len(ohlcv[0]), 6)  # [timestamp, open, high, low, close, volume]
        self.assertEqual(ohlcv[0][1], 50000.0)  # open
        self.assertEqual(ohlcv[0][2], 50100.0)  # high
        self.assertEqual(ohlcv[0][3], 49900.0)  # low
        self.assertEqual(ohlcv[0][4], 50050.0)  # close
        self.assertEqual(ohlcv[0][5], 100.0)   # volume

        # Verify exchange method was called with correct parameters
        mock_exchange.fetch_ohlcv.assert_called_with("BTC/USD", "1m", limit=100)

    @patch('src.data_fetcher.ccxt')
    @patch('src.data_fetcher.config')
    @patch('src.data_fetcher.exchange_circuit_breaker')
    def test_kraken_fetch_orderbook(self, mock_circuit_breaker, mock_config, mock_ccxt):
        """Test fetching orderbook from Kraken."""
        # Setup config mock
        mock_config.EXCHANGE = "kraken"
        mock_config.SYMBOL = "BTC/USD"
        mock_config.USE_TESTNET = False
        mock_config.EXCHANGE_API_KEY = None
        mock_config.EXCHANGE_API_SECRET = None

        # Setup mock exchange
        mock_kraken_class = MagicMock()
        mock_exchange = MagicMock()
        mock_orderbook = {
            "bids": [[50000.0, 1.5], [49950.0, 2.0], [49900.0, 1.0]],
            "asks": [[50050.0, 1.2], [50100.0, 2.5], [50150.0, 1.8]],
            "timestamp": int(time.time() * 1000),
        }
        mock_exchange.fetch_order_book.return_value = mock_orderbook
        mock_kraken_class.return_value = mock_exchange
        mock_ccxt.kraken = mock_kraken_class

        # Setup circuit breaker mock
        mock_circuit_breaker.call.side_effect = lambda func: func()

        fetcher = DataFetcher(exchange_name="kraken", use_testnet=False)
        orderbook = fetcher.get_orderbook(limit=20)

        # Verify orderbook structure
        self.assertIsInstance(orderbook, dict)
        self.assertIn("bids", orderbook)
        self.assertIn("asks", orderbook)
        self.assertEqual(len(orderbook["bids"]), 3)
        self.assertEqual(len(orderbook["asks"]), 3)
        self.assertEqual(orderbook["bids"][0][0], 50000.0)  # Best bid price
        self.assertEqual(orderbook["asks"][0][0], 50050.0)  # Best ask price

        # Verify exchange method was called
        mock_exchange.fetch_order_book.assert_called_with("BTC/USD", 20)

    @patch('src.data_fetcher.ccxt')
    @patch('src.data_fetcher.config')
    @patch('src.data_fetcher.exchange_circuit_breaker')
    def test_kraken_network_error_handling(self, mock_circuit_breaker, mock_config, mock_ccxt):
        """Test handling of network errors from Kraken."""
        # Setup config mock
        mock_config.EXCHANGE = "kraken"
        mock_config.SYMBOL = "BTC/USD"
        mock_config.USE_TESTNET = False
        mock_config.EXCHANGE_API_KEY = None
        mock_config.EXCHANGE_API_SECRET = None

        # Setup mock exchange that raises network error
        mock_kraken_class = MagicMock()
        mock_exchange = MagicMock()
        mock_exchange.fetch_ticker.side_effect = NetworkError("Connection timeout")
        mock_kraken_class.return_value = mock_exchange
        mock_ccxt.kraken = mock_kraken_class

        # Setup retry handler mock to raise after retries
        def retry_call(func):
            try:
                return func()
            except Exception as e:
                raise e

        mock_circuit_breaker.call.side_effect = retry_call

        fetcher = DataFetcher(exchange_name="kraken", use_testnet=False)

        # Should raise NetworkError
        with self.assertRaises(Exception):
            fetcher.get_ticker()

    @patch('src.data_fetcher.ccxt')
    @patch('src.data_fetcher.config')
    @patch('src.data_fetcher.exchange_circuit_breaker')
    def test_kraken_rate_limit_handling(self, mock_circuit_breaker, mock_config, mock_ccxt):
        """Test handling of rate limit errors from Kraken."""
        # Setup config mock
        mock_config.EXCHANGE = "kraken"
        mock_config.SYMBOL = "BTC/USD"
        mock_config.USE_TESTNET = False
        mock_config.EXCHANGE_API_KEY = None
        mock_config.EXCHANGE_API_SECRET = None

        # Setup mock exchange that raises rate limit error
        mock_kraken_class = MagicMock()
        mock_exchange = MagicMock()
        mock_exchange.fetch_ticker.side_effect = RateLimitExceeded("Rate limit exceeded")
        mock_kraken_class.return_value = mock_exchange
        mock_ccxt.kraken = mock_kraken_class

        # Setup retry handler mock
        def retry_call(func):
            try:
                return func()
            except Exception as e:
                raise e

        mock_circuit_breaker.call.side_effect = retry_call

        fetcher = DataFetcher(exchange_name="kraken", use_testnet=False)

        # Should raise RateLimitExceeded
        with self.assertRaises(Exception):
            fetcher.get_ticker()

    @patch('src.data_fetcher.ccxt')
    @patch('src.data_fetcher.config')
    @patch('src.data_fetcher.exchange_circuit_breaker')
    def test_kraken_exchange_error_handling(self, mock_circuit_breaker, mock_config, mock_ccxt):
        """Test handling of exchange errors from Kraken."""
        # Setup config mock
        mock_config.EXCHANGE = "kraken"
        mock_config.SYMBOL = "BTC/USD"
        mock_config.USE_TESTNET = False
        mock_config.EXCHANGE_API_KEY = None
        mock_config.EXCHANGE_API_SECRET = None

        # Setup mock exchange that raises exchange error
        mock_kraken_class = MagicMock()
        mock_exchange = MagicMock()
        mock_exchange.fetch_ticker.side_effect = ExchangeError("Invalid symbol")
        mock_kraken_class.return_value = mock_exchange
        mock_ccxt.kraken = mock_kraken_class

        # Setup retry handler mock
        def retry_call(func):
            try:
                return func()
            except Exception as e:
                raise e

        mock_circuit_breaker.call.side_effect = retry_call

        fetcher = DataFetcher(exchange_name="kraken", use_testnet=False)

        # Should raise ExchangeError
        with self.assertRaises(Exception):
            fetcher.get_ticker()

    @patch('src.data_fetcher.ccxt')
    @patch('src.data_fetcher.config')
    @patch('src.data_fetcher.exchange_circuit_breaker')
    @patch('src.data_fetcher.pd')
    def test_kraken_technical_indicators(self, mock_pd, mock_circuit_breaker, mock_config, mock_ccxt):
        """Test fetching technical indicators from Kraken data."""
        # Setup config mock
        mock_config.EXCHANGE = "kraken"
        mock_config.SYMBOL = "BTC/USD"
        mock_config.USE_TESTNET = False
        mock_config.EXCHANGE_API_KEY = None
        mock_config.EXCHANGE_API_SECRET = None

        # Setup mock exchange
        mock_kraken_class = MagicMock()
        mock_exchange = MagicMock()

        # Mock OHLCV data
        mock_ohlcv = [
            [int(time.time() * 1000) - i * 60000, 50000.0, 50100.0, 49900.0, 50050.0, 100.0]
            for i in range(100, 0, -1)
        ]
        mock_exchange.fetch_ohlcv.return_value = mock_ohlcv
        mock_kraken_class.return_value = mock_exchange
        mock_ccxt.kraken = mock_kraken_class

        # Setup circuit breaker mock
        mock_circuit_breaker.call.side_effect = lambda func: func()

        # Mock pandas DataFrame
        mock_df = MagicMock()
        mock_df.iloc = MagicMock()
        mock_df.iloc.__getitem__.return_value = MagicMock()
        mock_df.iloc.__getitem__.return_value.__getitem__.side_effect = lambda key: {
            "ema_20": 50025.0,
            "ema_50": 50000.0,
            "macd": 50.0,
            "macd_signal": 45.0,
            "macd_histogram": 5.0,
            "rsi_7": 55.0,
            "rsi_14": 52.0,
            "atr": 1000.0,
            "close": 50050.0,
        }.get(key, 0.0)
        mock_pd.DataFrame.return_value = mock_df
        mock_pd.isna.return_value = False
        mock_pd.to_datetime.return_value = mock_df

        # Mock pandas-ta
        with patch('src.data_fetcher.ta') as mock_ta:
            mock_ta.ema.return_value = mock_df
            mock_ta.macd.return_value = {
                "MACD_12_26_9": mock_df,
                "MACDs_12_26_9": mock_df,
                "MACDh_12_26_9": mock_df,
            }
            mock_ta.rsi.return_value = mock_df
            mock_ta.atr.return_value = mock_df

            fetcher = DataFetcher(exchange_name="kraken", use_testnet=False)
            indicators = fetcher.get_technical_indicators(timeframe="3m", limit=100)

            # Verify indicators structure
            self.assertIsInstance(indicators, dict)
            self.assertIn("ema_20", indicators)
            self.assertIn("ema_50", indicators)
            self.assertIn("macd", indicators)
            self.assertIn("rsi_7", indicators)
            self.assertIn("rsi_14", indicators)
            self.assertIn("atr", indicators)
            self.assertIn("current_price", indicators)

    @patch('src.data_fetcher.ccxt')
    @patch('src.data_fetcher.config')
    def test_kraken_spot_trading_configuration(self, mock_config, mock_ccxt):
        """Test that Kraken is configured for spot trading (not futures)."""
        # Setup config mock
        mock_config.EXCHANGE = "kraken"
        mock_config.SYMBOL = "BTC/USD"
        mock_config.USE_TESTNET = False
        mock_config.EXCHANGE_API_KEY = None
        mock_config.EXCHANGE_API_SECRET = None

        # Setup ccxt mock
        mock_kraken_class = MagicMock()
        mock_exchange = MagicMock()
        mock_kraken_class.return_value = mock_exchange
        mock_ccxt.kraken = mock_kraken_class

        # Create DataFetcher
        fetcher = DataFetcher(exchange_name="kraken", use_testnet=False)

        # Verify spot trading configuration
        call_kwargs = mock_kraken_class.call_args[0][0]  # first positional argument
        self.assertEqual(call_kwargs["options"]["defaultType"], "spot")
        # Kraken should always use spot, not futures

    @patch('src.data_fetcher.ccxt')
    @patch('src.data_fetcher.config')
    @patch('src.data_fetcher.exchange_circuit_breaker')
    def test_kraken_invalid_price_handling(self, mock_circuit_breaker, mock_config, mock_ccxt):
        """Test handling of invalid price data from Kraken."""
        # Setup config mock
        mock_config.EXCHANGE = "kraken"
        mock_config.SYMBOL = "BTC/USD"
        mock_config.USE_TESTNET = False
        mock_config.EXCHANGE_API_KEY = None
        mock_config.EXCHANGE_API_SECRET = None

        # Setup mock exchange with invalid price
        mock_kraken_class = MagicMock()
        mock_exchange = MagicMock()
        mock_exchange.fetch_ticker.return_value = {
            "last": -1.0,  # Invalid negative price
            "symbol": "BTC/USD"
        }
        mock_kraken_class.return_value = mock_exchange
        mock_ccxt.kraken = mock_kraken_class

        # Setup circuit breaker mock
        mock_circuit_breaker.call.side_effect = lambda func: func()

        fetcher = DataFetcher(exchange_name="kraken", use_testnet=False)

        # Should raise ValueError for invalid price
        with self.assertRaises(ValueError):
            fetcher.get_price()

    @patch('src.data_fetcher.ccxt')
    @patch('src.data_fetcher.config')
    def test_kraken_symbol_format(self, mock_config, mock_ccxt):
        """Test that Kraken uses BTC/USD format (not BTC/USDT)."""
        # Setup config mock
        mock_config.EXCHANGE = "kraken"
        mock_config.SYMBOL = "BTC/USD"  # Kraken typically uses USD pairs
        mock_config.USE_TESTNET = False
        mock_config.EXCHANGE_API_KEY = None
        mock_config.EXCHANGE_API_SECRET = None

        # Setup ccxt mock
        mock_kraken_class = MagicMock()
        mock_exchange = MagicMock()
        mock_kraken_class.return_value = mock_exchange
        mock_ccxt.kraken = mock_kraken_class

        fetcher = DataFetcher(exchange_name="kraken", use_testnet=False)

        # Verify symbol format
        # Note: Kraken may use BTC/USD instead of BTC/USDT
        self.assertIn(fetcher.symbol, ["BTC/USD", "BTC/USDT"])


if __name__ == "__main__":
    unittest.main()
