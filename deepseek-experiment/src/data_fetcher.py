"""
Market data fetcher module.

Fetches live market data from cryptocurrency exchanges using ccxt library.
Supports Bybit and Binance, with testnet option for safe experimentation.

Includes technical indicator calculations for Alpha Arena-style trading signals.
"""

import logging
import time
from typing import Dict, List

import ccxt
import pandas as pd
from ccxt.base.errors import ExchangeError, NetworkError, RateLimitExceeded

try:
    import pandas_ta as ta

    PANDAS_TA_AVAILABLE = True
except ImportError:
    PANDAS_TA_AVAILABLE = False
    logging.warning(
        "pandas-ta not available. Technical indicators will return mock data. Install with: pip install pandas-ta"
    )

from config import config

from .resilience import RetryConfig, RetryHandler, exchange_circuit_breaker

logger = logging.getLogger(__name__)


class DataFetcher:
    """
    Fetches market data from cryptocurrency exchanges.

    Supports paper trading via testnet and can be easily upgraded to live trading
    by changing the USE_TESTNET flag in config.

    Attributes:
        exchange: The ccxt exchange instance
        symbol: Trading pair symbol (e.g., "BTC/USDT")
    """

    def __init__(self, exchange_name: str = None, use_testnet: bool = None):
        """
        Initialize the data fetcher with exchange configuration.

        Args:
            exchange_name: Name of exchange ("bybit", "binance", "coinbase", or "kraken"). Defaults to config.
            use_testnet: Whether to use testnet. Defaults to config.
        """
        exchange_name = exchange_name or config.EXCHANGE
        use_testnet = use_testnet if use_testnet is not None else config.USE_TESTNET

        self.symbol = config.SYMBOL
        self.exchange_name = exchange_name

        # Initialize exchange
        exchange_class = getattr(ccxt, exchange_name)
        exchange_params = {
            "apiKey": config.EXCHANGE_API_KEY or None,
            "secret": config.EXCHANGE_API_SECRET or None,
            "enableRateLimit": True,
            "timeout": 30000,  # 30 second timeout
            "options": {
                "adjustForTimeDifference": True,
            },
        }

        # Configure testnet and exchange-specific options
        if exchange_name == "bybit" and use_testnet:
            exchange_params["options"]["defaultType"] = "test"
        elif exchange_name == "binance" and use_testnet:
            exchange_params["options"]["defaultType"] = "testnet"
        elif exchange_name == "coinbase":
            # Coinbase Pro/Advanced Trade (US-friendly)
            exchange_params["options"]["defaultType"] = "spot"
        elif exchange_name == "kraken":
            # Kraken (US-friendly)
            exchange_params["options"]["defaultType"] = "spot"

        self.exchange = exchange_class(exchange_params)

        # Initialize retry handler for API calls
        self.retry_handler = RetryHandler(
            RetryConfig(max_attempts=3, base_delay=2.0, max_delay=30.0, exponential_base=2.0, jitter=True)
        )

        # Enhanced logging with clear indicators
        mode_indicator = "🧪 TESTNET" if use_testnet else "🌐 LIVE"
        api_status = (
            "with API keys" if (exchange_params.get("apiKey") and exchange_params.get("secret")) else "without API keys"
        )

        logger.info(f"Exchange initialized: {exchange_name.upper()} {mode_indicator} {api_status}")

        if use_testnet:
            logger.info("📝 Testnet mode: Using simulated trading environment")
        else:
            logger.warning("⚠️  Live mode: Real market data and potential real trading")

    def _handle_exchange_error(self, error: Exception, operation: str) -> None:
        """
        Handle exchange API errors with appropriate logging and recovery suggestions.

        Args:
            error: The exception that occurred
            operation: Description of the operation that failed
        """
        error_msg = str(error)

        # Check for geo-blocking (403 from CloudFront)
        if "403" in error_msg or "Forbidden" in error_msg or "CloudFront" in error_msg:
            logger.error(
                f"🚫 Geo-blocking detected: {self.exchange_name} API is blocked in your region. "
                f"Consider using a different exchange (binance, coinbase, kraken) or proxy/VPN."
            )
        elif isinstance(error, RateLimitExceeded):
            logger.warning(f"⏱️ Rate limit exceeded for {operation}. Waiting before retry...")
        elif isinstance(error, NetworkError):
            logger.error(f"🌐 Network error during {operation}: {error_msg}")
        elif isinstance(error, ExchangeError):
            logger.error(f"📊 Exchange error during {operation}: {error_msg}")
        else:
            logger.error(f"❌ Unexpected error during {operation}: {error_msg}")

    def get_ticker(self) -> Dict:
        """
        Fetch current ticker data for the configured symbol.

        Returns:
            Dictionary containing ticker information (bid, ask, last, etc.)

        Raises:
            Exception: If fetching ticker fails after retries
        """

        def _fetch():
            try:
                return self.exchange.fetch_ticker(self.symbol)
            except (NetworkError, ExchangeError, RateLimitExceeded) as e:
                self._handle_exchange_error(e, f"fetch_ticker({self.symbol})")
                raise

        try:
            # Use circuit breaker and retry handler
            ticker = exchange_circuit_breaker.call(lambda: self.retry_handler.call(_fetch))
            mode_indicator = "🧪" if config.USE_TESTNET else "🌐"
            logger.debug(f"{mode_indicator} Fetched ticker for {self.symbol}: ${ticker['last']:,.2f}")
            return ticker
        except Exception as e:
            # Last resort: return mock data for geo-blocked scenarios
            if "403" in str(e) or "Forbidden" in str(e) or "CloudFront" in str(e):
                logger.warning(
                    f"⚠️ Using fallback mock price for {self.symbol} due to geo-blocking. "
                    "Set up proxy or use a different exchange for real data."
                )
                # Return mock ticker with reasonable defaults
                return {
                    "symbol": self.symbol,
                    "last": 50000.0,  # Default BTC price
                    "bid": 49950.0,
                    "ask": 50050.0,
                    "high": 51000.0,
                    "low": 49000.0,
                    "volume": 1000.0,
                    "timestamp": int(time.time() * 1000),
                    "info": {"fallback": True},
                }
            logger.error(f"❌ Error fetching ticker: {e}")
            raise

    def get_price(self) -> float:
        """
        Get the current market price for the symbol.

        Returns:
            Current last price as float

        Raises:
            ValueError: If price data is invalid
            Exception: If fetching ticker fails
        """
        ticker = self.get_ticker()
        try:
            price = float(ticker["last"])
            if price <= 0:
                raise ValueError(f"Invalid price: {price}")
            return price
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Error extracting price from ticker: {e}")
            raise ValueError(f"Invalid price data: {ticker.get('last', 'N/A')}")

    def get_ohlcv(self, timeframe: str = "1m", limit: int = 100) -> List[List]:
        """
        Fetch OHLCV (Open, High, Low, Close, Volume) candlestick data.

        Args:
            timeframe: Candlestick timeframe (e.g., "1m", "5m", "1h")
            limit: Number of candles to fetch (max 1000)

        Returns:
            List of OHLCV candles [timestamp, open, high, low, close, volume]

        Raises:
            ValueError: If parameters are invalid
            Exception: If fetching fails
        """
        # Validate inputs
        if not isinstance(timeframe, str) or not timeframe:
            raise ValueError("Timeframe must be a non-empty string")

        if not isinstance(limit, int) or limit <= 0 or limit > 1000:
            raise ValueError("Limit must be an integer between 1 and 1000")

        def _fetch():
            try:
                return self.exchange.fetch_ohlcv(self.symbol, timeframe, limit=limit)
            except (NetworkError, ExchangeError, RateLimitExceeded) as e:
                self._handle_exchange_error(e, f"fetch_ohlcv({self.symbol})")
                raise

        try:
            ohlcv = exchange_circuit_breaker.call(lambda: self.retry_handler.call(_fetch))

            # Validate response
            if not ohlcv or not isinstance(ohlcv, list):
                raise ValueError("Invalid OHLCV data received")

            logger.debug(f"Fetched {len(ohlcv)} candles for {self.symbol}")
            return ohlcv
        except Exception as e:
            if "403" in str(e) or "Forbidden" in str(e):
                logger.warning("⚠️ Geo-blocked from fetching OHLCV. Consider using alternative exchange.")
            logger.error(f"Error fetching OHLCV: {e}")
            raise

    def get_orderbook(self, limit: int = 20) -> Dict:
        """
        Fetch current order book data.

        Args:
            limit: Number of orders on each side to fetch (max 100)

        Returns:
            Dictionary with 'bids' and 'asks' arrays

        Raises:
            ValueError: If parameters are invalid
            Exception: If fetching fails
        """
        # Validate inputs
        if not isinstance(limit, int) or limit <= 0 or limit > 100:
            raise ValueError("Limit must be an integer between 1 and 100")

        def _fetch():
            try:
                return self.exchange.fetch_order_book(self.symbol, limit)
            except (NetworkError, ExchangeError, RateLimitExceeded) as e:
                self._handle_exchange_error(e, f"fetch_order_book({self.symbol})")
                raise

        try:
            orderbook = exchange_circuit_breaker.call(lambda: self.retry_handler.call(_fetch))

            # Validate response structure
            if not isinstance(orderbook, dict):
                raise ValueError("Invalid orderbook data received")

            if "bids" not in orderbook or "asks" not in orderbook:
                raise ValueError("Orderbook missing required 'bids' or 'asks' fields")

            return orderbook
        except Exception as e:
            if "403" in str(e) or "Forbidden" in str(e):
                logger.warning("⚠️ Geo-blocked from fetching orderbook. Consider using alternative exchange.")
            logger.error(f"Error fetching orderbook: {e}")
            raise

    def get_technical_indicators(self, timeframe: str = "5m", limit: int = 100) -> Dict[str, float]:
        """
        Calculate technical indicators for Alpha Arena-style trading signals.

        Calculates indicators matching Alpha Arena methodology:
        - EMA 20, EMA 50 (Exponential Moving Averages)
        - MACD (Moving Average Convergence Divergence)
        - RSI 7, RSI 14 (Relative Strength Index)
        - ATR (Average True Range)

        Args:
            timeframe: Candlestick timeframe (default "5m" - compatible with Kraken and most exchanges)
            limit: Number of candles to fetch for calculation (min 100)

        Returns:
            Dictionary containing all calculated indicators

        Note:
            Returns mock/fallback values if pandas-ta is not available or fetching fails.
        """
        try:
            if not PANDAS_TA_AVAILABLE:
                logger.warning("pandas-ta not available, returning mock indicators")
                return self._get_mock_indicators()

            # Fetch OHLCV data
            try:
                ohlcv = self.get_ohlcv(timeframe=timeframe, limit=limit)
            except Exception as e:
                logger.warning(f"Failed to fetch OHLCV for indicators: {e}. Using mock data.")
                return self._get_mock_indicators()

            # Convert to DataFrame
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)

            # Calculate indicators using pandas-ta
            try:
                # EMA (Exponential Moving Average)
                df["ema_20"] = ta.ema(df["close"], length=20)
                df["ema_50"] = ta.ema(df["close"], length=50)

                # MACD (Moving Average Convergence Divergence)
                macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
                df["macd"] = macd["MACD_12_26_9"]
                df["macd_signal"] = macd["MACDs_12_26_9"]
                df["macd_histogram"] = macd["MACDh_12_26_9"]

                # RSI (Relative Strength Index)
                df["rsi_7"] = ta.rsi(df["close"], length=7)
                df["rsi_14"] = ta.rsi(df["close"], length=14)

                # ATR (Average True Range)
                df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)

                # Get the latest (most recent) values
                latest = df.iloc[-1]

                indicators = {
                    "ema_20": float(latest["ema_20"]) if not pd.isna(latest["ema_20"]) else float(latest["close"]),
                    "ema_50": float(latest["ema_50"]) if not pd.isna(latest["ema_50"]) else float(latest["close"]),
                    "macd": float(latest["macd"]) if not pd.isna(latest["macd"]) else 0.0,
                    "macd_signal": float(latest["macd_signal"]) if not pd.isna(latest["macd_signal"]) else 0.0,
                    "macd_histogram": float(latest["macd_histogram"]) if not pd.isna(latest["macd_histogram"]) else 0.0,
                    "rsi_7": float(latest["rsi_7"]) if not pd.isna(latest["rsi_7"]) else 50.0,
                    "rsi_14": float(latest["rsi_14"]) if not pd.isna(latest["rsi_14"]) else 50.0,
                    "atr": float(latest["atr"]) if not pd.isna(latest["atr"]) else 100.0,
                    "current_price": float(latest["close"]),
                }

                logger.debug(
                    f"📊 Technical Indicators for {self.symbol}: "
                    f"EMA20=${indicators['ema_20']:.2f}, RSI14={indicators['rsi_14']:.1f}, "
                    f"MACD={indicators['macd']:.4f}"
                )

                return indicators

            except Exception as e:
                logger.error(f"Error calculating indicators: {e}")
                return self._get_mock_indicators()

        except Exception as e:
            logger.error(f"Unexpected error in get_technical_indicators: {e}")
            return self._get_mock_indicators()

    def _get_mock_indicators(self) -> Dict[str, float]:
        """
        Generate mock technical indicators as fallback.

        Returns reasonable default values that won't crash the LLM prompt.
        """
        try:
            current_price = self.get_price()
        except Exception:
            current_price = 50000.0  # Default BTC price

        return {
            "ema_20": current_price * 0.99,  # Slightly below current price
            "ema_50": current_price * 0.98,  # Further below
            "macd": 50.0,  # Neutral positive
            "macd_signal": 45.0,
            "macd_histogram": 5.0,  # Small bullish divergence
            "rsi_7": 55.0,  # Slightly bullish
            "rsi_14": 52.0,
            "atr": current_price * 0.02,  # 2% of price
            "current_price": current_price,
        }
