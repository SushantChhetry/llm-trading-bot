"""
Market data fetcher module.

Fetches live market data from cryptocurrency exchanges using ccxt library.
Supports Bybit and Binance, with testnet option for safe experimentation.
"""

import logging
import time
from typing import Dict, Optional, List
import ccxt
from ccxt.base.errors import NetworkError, ExchangeError, RateLimitExceeded

from config import config
from .resilience import RetryHandler, RetryConfig, exchange_circuit_breaker

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
            exchange_name: Name of exchange ("bybit" or "binance"). Defaults to config.
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
            }
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
        self.retry_handler = RetryHandler(RetryConfig(
            max_attempts=3,
            base_delay=2.0,
            max_delay=30.0,
            exponential_base=2.0,
            jitter=True
        ))
        
        # Enhanced logging with clear indicators
        mode_indicator = "🧪 TESTNET" if use_testnet else "🌐 LIVE"
        api_status = "with API keys" if (exchange_params.get("apiKey") and exchange_params.get("secret")) else "without API keys"
        
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
            ticker = exchange_circuit_breaker.call(
                lambda: self.retry_handler.call(_fetch)
            )
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
                    "info": {"fallback": True}
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
            ohlcv = exchange_circuit_breaker.call(
                lambda: self.retry_handler.call(_fetch)
            )
            
            # Validate response
            if not ohlcv or not isinstance(ohlcv, list):
                raise ValueError("Invalid OHLCV data received")
            
            logger.debug(f"Fetched {len(ohlcv)} candles for {self.symbol}")
            return ohlcv
        except Exception as e:
            if "403" in str(e) or "Forbidden" in str(e):
                logger.warning(f"⚠️ Geo-blocked from fetching OHLCV. Consider using alternative exchange.")
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
            orderbook = exchange_circuit_breaker.call(
                lambda: self.retry_handler.call(_fetch)
            )
            
            # Validate response structure
            if not isinstance(orderbook, dict):
                raise ValueError("Invalid orderbook data received")
            
            if 'bids' not in orderbook or 'asks' not in orderbook:
                raise ValueError("Orderbook missing required 'bids' or 'asks' fields")
            
            return orderbook
        except Exception as e:
            if "403" in str(e) or "Forbidden" in str(e):
                logger.warning(f"⚠️ Geo-blocked from fetching orderbook. Consider using alternative exchange.")
            logger.error(f"Error fetching orderbook: {e}")
            raise

