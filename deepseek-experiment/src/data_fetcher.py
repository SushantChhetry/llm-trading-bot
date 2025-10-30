"""
Market data fetcher module.

Fetches live market data from cryptocurrency exchanges using ccxt library.
Supports Bybit and Binance, with testnet option for safe experimentation.
"""

import logging
from typing import Dict, Optional, List
import ccxt

from config import config

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
        
        # Initialize exchange
        exchange_class = getattr(ccxt, exchange_name)
        exchange_params = {
            "apiKey": config.EXCHANGE_API_KEY or None,
            "secret": config.EXCHANGE_API_SECRET or None,
            "enableRateLimit": True,
        }
        
        # Configure testnet and exchange-specific options
        if exchange_name == "bybit" and use_testnet:
            exchange_params["options"] = {"defaultType": "test"}
        elif exchange_name == "binance" and use_testnet:
            exchange_params["options"] = {"defaultType": "testnet"}
        elif exchange_name == "coinbase":
            # Coinbase Pro/Advanced Trade (US-friendly)
            exchange_params["options"] = {"defaultType": "spot"}
        elif exchange_name == "kraken":
            # Kraken (US-friendly)
            exchange_params["options"] = {"defaultType": "spot"}
        
        self.exchange = exchange_class(exchange_params)
        
        # Enhanced logging with clear indicators
        mode_indicator = "🧪 TESTNET" if use_testnet else "🌐 LIVE"
        api_status = "with API keys" if (exchange_params.get("apiKey") and exchange_params.get("secret")) else "without API keys"
        
        logger.info(f"Exchange initialized: {exchange_name.upper()} {mode_indicator} {api_status}")
        
        if use_testnet:
            logger.info("📝 Testnet mode: Using simulated trading environment")
        else:
            logger.warning("⚠️  Live mode: Real market data and potential real trading")
    
    def get_ticker(self) -> Dict:
        """
        Fetch current ticker data for the configured symbol.
        
        Returns:
            Dictionary containing ticker information (bid, ask, last, etc.)
            
        Raises:
            Exception: If fetching ticker fails
        """
        try:
            ticker = self.exchange.fetch_ticker(self.symbol)
            mode_indicator = "🧪" if config.USE_TESTNET else "🌐"
            logger.debug(f"{mode_indicator} Fetched ticker for {self.symbol}: ${ticker['last']:,.2f}")
            return ticker
        except Exception as e:
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
        
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, timeframe, limit=limit)
            
            # Validate response
            if not ohlcv or not isinstance(ohlcv, list):
                raise ValueError("Invalid OHLCV data received")
            
            logger.debug(f"Fetched {len(ohlcv)} candles for {self.symbol}")
            return ohlcv
        except Exception as e:
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
        
        try:
            orderbook = self.exchange.fetch_order_book(self.symbol, limit)
            
            # Validate response structure
            if not isinstance(orderbook, dict):
                raise ValueError("Invalid orderbook data received")
            
            if 'bids' not in orderbook or 'asks' not in orderbook:
                raise ValueError("Orderbook missing required 'bids' or 'asks' fields")
            
            return orderbook
        except Exception as e:
            logger.error(f"Error fetching orderbook: {e}")
            raise

