"""
Risk Daemon - Background Process for Stop-Loss Monitoring

Monitors open positions for stop-loss/take-profit triggers and revokes orders
when limits are breached. Runs independently of main trading loop.

For exchanges without server-side OCO support, this daemon emulates OCO
functionality by monitoring prices and closing positions when stop-loss is hit.
"""

import json
import logging
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RiskDaemon:
    """Background daemon for monitoring stop-losses and take-profits."""
    
    def __init__(
        self,
        risk_service_url: str = "http://localhost:8003",
        check_interval: float = 5.0,  # Check every 5 seconds
        data_dir: Path = None
    ):
        self.risk_service_url = risk_service_url
        self.check_interval = check_interval
        self.data_dir = data_dir or config.DATA_DIR
        
        # Load positions from file
        self.portfolio_file = self.data_dir / "portfolio.json"
        self.trades_file = self.data_dir / "trades.json"
        
        # Track last check time
        self.last_check_time = time.time()
        
        # Lazy initialization of trading components (will be initialized on first use)
        self._trading_engine = None
        self._data_fetcher = None
        
        logger.info(f"Risk Daemon initialized: {risk_service_url}, check_interval={check_interval}s")
    
    def run(self):
        """Main daemon loop."""
        logger.info("Risk Daemon started")
        
        try:
            while True:
                self._check_positions()
                time.sleep(self.check_interval)
        except KeyboardInterrupt:
            logger.info("Risk Daemon stopped by user")
        except Exception as e:
            logger.error(f"Risk Daemon error: {e}", exc_info=True)
            raise
    
    def _check_positions(self):
        """Check all open positions for stop-loss/take-profit triggers."""
        try:
            # Load portfolio state
            if not self.portfolio_file.exists():
                return
            
            with open(self.portfolio_file, 'r') as f:
                portfolio = json.load(f)
            
            positions = portfolio.get("positions", {})
            if not positions:
                return
            
            # Get current price from portfolio file or data fetcher
            current_price = portfolio.get("current_price")
            if not current_price:
                # Try to get price from data fetcher as fallback
                # Use first position's symbol to fetch price
                first_symbol = next(iter(positions.keys())) if positions else None
                if first_symbol:
                    current_price = self._get_current_price(first_symbol)
                if not current_price:
                    logger.warning("No current price available, skipping position check")
                    return
            
            # Check each position
            for symbol, position in positions.items():
                self._check_position(symbol, position, current_price)
                
        except Exception as e:
            logger.error(f"Error checking positions: {e}", exc_info=True)
    
    def _check_position(self, symbol: str, position: Dict, current_price: float):
        """Check a single position for stop-loss/take-profit triggers."""
        try:
            entry_price = position.get("avg_price", 0)
            if entry_price <= 0:
                return
            
            side = position.get("side", "long")
            quantity = position.get("quantity", 0)
            
            # Get stop-loss and take-profit from position or exit_plan
            stop_loss = position.get("stop_loss")
            take_profit = position.get("take_profit")
            
            # If not in position, try to get from last trade's exit_plan
            if not stop_loss or not take_profit:
                exit_plan = position.get("exit_plan", {})
                if exit_plan:
                    stop_loss = exit_plan.get("stop_loss")
                    take_profit = exit_plan.get("profit_target")
            
            # Calculate P&L
            if side == "long":
                pnl_pct = ((current_price - entry_price) / entry_price) * 100
                hit_stop = stop_loss and current_price <= stop_loss
                hit_take_profit = take_profit and current_price >= take_profit
            else:  # short
                pnl_pct = ((entry_price - current_price) / entry_price) * 100
                hit_stop = stop_loss and current_price >= stop_loss
                hit_take_profit = take_profit and current_price <= take_profit
            
            # Check if stop-loss hit
            if hit_stop:
                logger.critical(
                    f"STOP-LOSS TRIGGERED: {symbol} {side} "
                    f"entry={entry_price:.2f} current={current_price:.2f} "
                    f"stop_loss={stop_loss:.2f} pnl={pnl_pct:.2f}%"
                )
                self._close_position(symbol, side, quantity, current_price, "stop_loss")
                return
            
            # Check if take-profit hit
            if hit_take_profit:
                logger.info(
                    f"TAKE-PROFIT TRIGGERED: {symbol} {side} "
                    f"entry={entry_price:.2f} current={current_price:.2f} "
                    f"take_profit={take_profit:.2f} pnl={pnl_pct:.2f}%"
                )
                self._close_position(symbol, side, quantity, current_price, "take_profit")
                return
            
            # Log if approaching stop-loss (within 10% of stop)
            if stop_loss:
                if side == "long":
                    distance_to_stop = ((current_price - stop_loss) / entry_price) * 100
                else:
                    distance_to_stop = ((stop_loss - current_price) / entry_price) * 100
                
                if 0 < distance_to_stop < 10:
                    logger.warning(
                        f"APPROACHING STOP-LOSS: {symbol} {side} "
                        f"distance={distance_to_stop:.2f}% current={current_price:.2f} stop={stop_loss:.2f}"
                    )
        
        except Exception as e:
            logger.error(f"Error checking position {symbol}: {e}", exc_info=True)
    
    def _get_trading_engine(self):
        """Lazy initialization of trading engine."""
        if self._trading_engine is None:
            try:
                from src.trading_engine import TradingEngine
                self._trading_engine = TradingEngine()
                logger.info("Trading engine initialized for position closure")
            except Exception as e:
                logger.error(f"Failed to initialize trading engine: {e}", exc_info=True)
                raise
        return self._trading_engine
    
    def _get_data_fetcher(self):
        """Lazy initialization of data fetcher."""
        if self._data_fetcher is None:
            try:
                from src.data_fetcher import DataFetcher
                self._data_fetcher = DataFetcher()
                logger.info("Data fetcher initialized for price updates")
            except Exception as e:
                logger.warning(f"Failed to initialize data fetcher: {e}")
                # Not critical - we can use price from portfolio file
        return self._data_fetcher
    
    def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price from data fetcher or portfolio file."""
        # Try data fetcher first
        data_fetcher = self._get_data_fetcher()
        if data_fetcher:
            try:
                ticker = data_fetcher.get_ticker(symbol)
                if ticker and 'last' in ticker:
                    return float(ticker['last'])
            except Exception as e:
                logger.warning(f"Failed to get price from data fetcher: {e}")
        
        # Fallback to portfolio file
        try:
            if self.portfolio_file.exists():
                with open(self.portfolio_file, 'r') as f:
                    portfolio = json.load(f)
                    return portfolio.get("current_price")
        except Exception as e:
            logger.warning(f"Failed to get price from portfolio file: {e}")
        
        return None
    
    def _close_position(self, symbol: str, side: str, quantity: float, price: float, reason: str):
        """
        Close position by calling trading engine.
        
        This method:
        1. Validates the position exists
        2. Calls trading engine's execute_sell to close the position
        3. Updates risk service with new portfolio state
        4. Logs the closure
        """
        logger.info(
            f"CLOSING POSITION: {symbol} {side} quantity={quantity:.6f} "
            f"price={price:.2f} reason={reason}"
        )
        
        try:
            # Get trading engine
            trading_engine = self._get_trading_engine()
            
            # Verify position exists before attempting to close
            if symbol not in trading_engine.positions:
                logger.warning(
                    f"Position {symbol} not found in trading engine. "
                    f"Available positions: {list(trading_engine.positions.keys())}"
                )
                return
            
            position = trading_engine.positions[symbol]
            actual_quantity = position.get("quantity", 0)
            
            if actual_quantity <= 0:
                logger.warning(f"Position {symbol} has zero or negative quantity: {actual_quantity}")
                return
            
            # Use actual position quantity if provided quantity is larger
            sell_quantity = min(quantity, actual_quantity) if quantity else actual_quantity
            
            # Create LLM decision context for the closure
            llm_decision = {
                "action": "sell",
                "reason": f"Risk daemon triggered: {reason}",
                "justification": f"Automatic position closure due to {reason} trigger",
                "confidence": 1.0,  # High confidence for risk-based closures
            }
            
            # Execute the sell order
            trade = trading_engine.execute_sell(
                symbol=symbol,
                price=price,
                quantity=sell_quantity,
                confidence=1.0,
                llm_decision=llm_decision,
                leverage=position.get("leverage", 1.0)
            )
            
            if trade:
                logger.info(
                    f"POSITION CLOSED SUCCESSFULLY: {symbol} trade_id={trade.get('id')} "
                    f"quantity={sell_quantity:.6f} price={price:.2f} "
                    f"profit={trade.get('profit', 0):.2f} profit_pct={trade.get('profit_pct', 0):.2f}%"
                )
                
                # Get updated portfolio state
                # Calculate NAV properly by getting price for each symbol
                # (get_portfolio_value assumes single symbol, so we calculate manually for multi-symbol support)
                position_values = {}
                total_position_value = 0.0
                
                # Prepare updated positions dict for risk service
                # Fetch current price for each symbol individually
                updated_positions = {}
                for pos_symbol, pos_data in trading_engine.positions.items():
                    # Get current price for this specific symbol
                    pos_current_price = self._get_current_price(pos_symbol)
                    if not pos_current_price:
                        # Fallback: use avg_price if we can't get current price
                        pos_current_price = pos_data.get("avg_price", 0)
                        logger.warning(f"Could not get current price for {pos_symbol}, using avg_price")
                    
                    # Calculate notional value using symbol-specific price
                    notional_value = pos_data.get("quantity", 0) * pos_current_price
                    
                    # Calculate position value for NAV calculation
                    side = pos_data.get("side", "long")
                    if side == "long":
                        position_value = pos_data.get("quantity", 0) * pos_current_price
                    else:  # short
                        entry_value = pos_data.get("quantity", 0) * pos_data.get("avg_price", 0)
                        current_value = pos_data.get("quantity", 0) * pos_current_price
                        short_pnl = entry_value - current_value
                        position_value = entry_value + short_pnl
                    
                    position_values[pos_symbol] = position_value
                    total_position_value += position_value
                    
                    updated_positions[pos_symbol] = {
                        "symbol": pos_symbol,
                        "side": side,
                        "quantity": pos_data.get("quantity", 0),
                        "avg_price": pos_data.get("avg_price", 0),
                        "margin_used": pos_data.get("margin_used", 0),
                        "leverage": pos_data.get("leverage", 1.0),
                        "value": pos_data.get("value", 0),
                        "notional_value": notional_value,
                    }
                
                # Calculate NAV: balance + total position values
                nav = trading_engine.balance + total_position_value
                
                # Calculate daily loss percentage (if we have daily start NAV)
                daily_loss_pct = None
                try:
                    if self.portfolio_file.exists():
                        with open(self.portfolio_file, 'r') as f:
                            portfolio = json.load(f)
                            daily_start_nav = portfolio.get("daily_start_nav")
                            if daily_start_nav and daily_start_nav > 0:
                                daily_loss_pct = max(0, (daily_start_nav - nav) / daily_start_nav)
                except Exception as e:
                    logger.warning(f"Failed to calculate daily loss: {e}")
                
                # Update risk service with new portfolio state
                try:
                    response = requests.post(
                        f"{self.risk_service_url}/risk/update_portfolio",
                        json={
                            "nav": nav,
                            "positions": updated_positions,
                            "daily_loss_pct": daily_loss_pct
                        },
                        timeout=5
                    )
                    if response.status_code == 200:
                        logger.debug(f"Risk service updated after position closure: nav={nav:.2f}")
                    else:
                        logger.warning(f"Risk service update returned status {response.status_code}")
                except Exception as e:
                    logger.warning(f"Failed to update risk service: {e}")
            else:
                logger.error(f"Failed to close position {symbol}: execute_sell returned None")
                
        except Exception as e:
            logger.error(f"Error closing position {symbol}: {e}", exc_info=True)
            # Don't raise - allow daemon to continue monitoring other positions


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Risk Daemon for Stop-Loss Monitoring")
    parser.add_argument(
        "--risk-service-url",
        default="http://localhost:8003",
        help="Risk service URL"
    )
    parser.add_argument(
        "--check-interval",
        type=float,
        default=5.0,
        help="Position check interval in seconds"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        help="Data directory path"
    )
    
    args = parser.parse_args()
    
    data_dir = Path(args.data_dir) if args.data_dir else None
    
    daemon = RiskDaemon(
        risk_service_url=args.risk_service_url,
        check_interval=args.check_interval,
        data_dir=data_dir
    )
    
    daemon.run()


if __name__ == '__main__':
    main()
