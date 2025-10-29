"""
Market data fetcher module.

Fetches live market data from cryptocurrency exchanges using ccxt library.
Supports Bybit and Binance, with testnet option for safe experimentation.
"""

import logging
from typing import Dict, Optional
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
        
        # Configure testnet
        if exchange_name == "bybit" and use_testnet:
            exchange_params["options"] = {"defaultType": "test"}
        elif exchange_name == "binance" and use_testnet:
            exchange_params["options"] = {"defaultType": "testnet"}
        
        self.exchange = exchange_class(exchange_params)
        
        logger.info(f"Initialized {exchange_name} {'testnet' if use_testnet else 'live'}")
    
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
            logger.debug(f"Fetched ticker for {self.symbol}: {ticker['last']}")
            return ticker
        except Exception as e:
            logger.error(f"Error fetching ticker: {e}")
            raise
    
    def get_price(self) -> float:
        """
        Get the current market price for the symbol.
        
        Returns:
            Current last price as float
        """
        ticker = self.get_ticker()
        return float(ticker["last"])
    
    def get_ohlcv(self, timeframe: str = "1m", limit: int = 100) -> list:
        """
        Fetch OHLCV (Open, High, Low, Close, Volume) candlestick data.
        
        Args:
            timeframe: Candlestick timeframe (e.g., "1m", "5m", "1h")
            limit: Number of candles to fetch
            
        Returns:
            List of OHLCV candles
        """
        try:
            ohlcv = self.exchange.fetch_ohlcv(self.symbol, timeframe, limit=limit)
            logger.debug(f"Fetched {len(ohlcv)} candles for {self.symbol}")
            return ohlcv
        except Exception as e:
            logger.error(f"Error fetching OHLCV: {e}")
            raise
    
    def get_orderbook(self, limit: int = 20) -> Dict:
        """
        Fetch current order book data.
        
        Args:
            limit: Number of orders on each side to fetch
            
        Returns:
            Dictionary with 'bids' and 'asks' arrays
        """
        try:
            orderbook = self.exchange.fetch_order_book(self.symbol, limit)
            return orderbook
        except Exception as e:
            logger.error(f"Error fetching orderbook: {e}")
            raise

