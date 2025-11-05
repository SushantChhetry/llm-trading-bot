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
            
            # Get current prices (would need data fetcher in real implementation)
            # For now, we'll check against portfolio file which should have current_price
            current_price = portfolio.get("current_price")
            if not current_price:
                logger.warning("No current price in portfolio, skipping position check")
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
                hit_take_take_profit = take_profit and current_price <= take_profit
            
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
    
    def _close_position(self, symbol: str, side: str, quantity: float, price: float, reason: str):
        """
        Close position by calling trading engine.
        
        In a real implementation, this would:
        1. Call the trading engine's execute_sell/execute_close method
        2. Or directly place a market order via exchange API
        3. Update risk service
        4. Log the closure
        """
        logger.info(
            f"CLOSING POSITION: {symbol} {side} quantity={quantity:.6f} "
            f"price={price:.2f} reason={reason}"
        )
        
        # In production, this would:
        # 1. Call risk service to validate closure
        # 2. Call trading engine to execute close
        # 3. Update portfolio state
        
        # For now, just log
        # TODO: Implement actual position closure via trading engine API
        
        # Notify risk service
        try:
            response = requests.post(
                f"{self.risk_service_url}/risk/update_portfolio",
                json={
                    "nav": 0,  # Would get from portfolio
                    "positions": {},  # Would update after closure
                    "daily_loss_pct": 0  # Would recalculate
                },
                timeout=5
            )
            if response.status_code == 200:
                logger.debug("Risk service updated after position closure")
        except Exception as e:
            logger.warning(f"Failed to update risk service: {e}")


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
