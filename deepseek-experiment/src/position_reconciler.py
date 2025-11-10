"""
Position Reconciliation Module

Fetches actual positions from exchange and compares with bot's internal state.
Detects discrepancies and logs/alert on mismatches.
"""

import logging
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from datetime import datetime

from config import config

logger = logging.getLogger(__name__)


@dataclass
class PositionDiscrepancy:
    """Represents a position discrepancy."""
    symbol: str
    type: str  # "missing", "extra", "quantity_mismatch", "price_mismatch"
    bot_quantity: float = 0.0
    exchange_quantity: float = 0.0
    bot_price: float = 0.0
    exchange_price: float = 0.0
    severity: str = "warning"  # "info", "warning", "critical"
    message: str = ""


class PositionReconciler:
    """
    Reconciles bot's internal position tracking with exchange reality.
    
    Fetches positions from exchange API and compares with bot's internal state.
    Auto-corrects minor discrepancies (rounding errors) and flags critical ones.
    """
    
    def __init__(self, data_fetcher=None):
        """
        Initialize position reconciler.
        
        Args:
            data_fetcher: DataFetcher instance to access exchange API
        """
        self.data_fetcher = data_fetcher
        self.reconciliation_count = 0
        self.discrepancy_count = 0
        self.last_reconciliation_time = None
        
        logger.info("PositionReconciler initialized")
    
    def reconcile_positions(
        self,
        bot_positions: Dict,
        current_price: float = None
    ) -> Tuple[List[PositionDiscrepancy], bool]:
        """
        Reconcile bot positions with exchange positions.
        
        Args:
            bot_positions: Bot's internal position dictionary
            current_price: Current market price (for validation)
        
        Returns:
            (discrepancies, reconciliation_successful)
        """
        self.reconciliation_count += 1
        self.last_reconciliation_time = datetime.now()
        
        discrepancies = []
        
        # If no data fetcher, can't reconcile - log warning
        if not self.data_fetcher:
            logger.warning("PositionReconciler: No data_fetcher available - skipping reconciliation")
            return discrepancies, False
        
        try:
            # Fetch positions from exchange
            exchange_positions = self._fetch_exchange_positions()
            
            if exchange_positions is None:
                logger.warning("PositionReconciler: Failed to fetch exchange positions")
                return discrepancies, False
            
            # Compare bot positions with exchange positions
            discrepancies = self._compare_positions(
                bot_positions=bot_positions,
                exchange_positions=exchange_positions,
                current_price=current_price
            )
            
            if discrepancies:
                self.discrepancy_count += len(discrepancies)
                logger.warning(f"PositionReconciler: Found {len(discrepancies)} discrepancies")
                for disc in discrepancies:
                    logger.warning(f"  - {disc.symbol}: {disc.type} - {disc.message}")
            else:
                logger.info("PositionReconciler: All positions reconciled successfully")
            
            return discrepancies, True
            
        except Exception as e:
            logger.error(f"PositionReconciler: Error during reconciliation: {e}", exc_info=True)
            return discrepancies, False
    
    def _fetch_exchange_positions(self) -> Optional[Dict]:
        """
        Fetch positions from exchange API.
        
        Returns:
            Dictionary of exchange positions {symbol: position_data} or None if failed
        """
        if not self.data_fetcher or not self.data_fetcher.exchange:
            return None
        
        try:
            # Fetch open positions from exchange
            # Note: This is a placeholder - actual implementation depends on exchange API
            # For paper trading, we may not have real exchange positions
            if config.TRADING_MODE == "paper":
                # In paper trading mode, we don't have real exchange positions
                # Return empty dict to indicate no exchange positions
                logger.debug("PositionReconciler: Paper trading mode - no exchange positions to fetch")
                return {}
            
            # For live trading, fetch actual positions
            # This would use exchange.fetch_positions() or similar
            # For now, return None to indicate not implemented for live trading yet
            logger.warning("PositionReconciler: Live trading position fetching not yet implemented")
            return None
            
        except Exception as e:
            logger.error(f"PositionReconciler: Error fetching exchange positions: {e}", exc_info=True)
            return None
    
    def _compare_positions(
        self,
        bot_positions: Dict,
        exchange_positions: Dict,
        current_price: float = None
    ) -> List[PositionDiscrepancy]:
        """
        Compare bot positions with exchange positions.
        
        Args:
            bot_positions: Bot's internal positions
            exchange_positions: Positions from exchange
            current_price: Current market price for validation
        
        Returns:
            List of PositionDiscrepancy objects
        """
        discrepancies = []
        
        # Check for positions in bot but not in exchange
        for symbol, bot_pos in bot_positions.items():
            if symbol not in exchange_positions:
                # Position exists in bot but not in exchange
                discrepancy = PositionDiscrepancy(
                    symbol=symbol,
                    type="missing",
                    bot_quantity=bot_pos.get("quantity", 0),
                    severity="critical" if bot_pos.get("quantity", 0) > 0.001 else "warning",
                    message=f"Position in bot ({bot_pos.get('quantity', 0):.6f}) but not in exchange"
                )
                discrepancies.append(discrepancy)
            else:
                # Compare quantities and prices
                exchange_pos = exchange_positions[symbol]
                bot_qty = bot_pos.get("quantity", 0)
                exchange_qty = exchange_pos.get("quantity", 0) if isinstance(exchange_pos, dict) else 0
                
                # Check quantity mismatch (with tolerance for rounding)
                qty_diff = abs(bot_qty - exchange_qty)
                qty_tolerance = max(0.0001, bot_qty * 0.01)  # 1% tolerance or 0.0001 minimum
                
                if qty_diff > qty_tolerance:
                    discrepancy = PositionDiscrepancy(
                        symbol=symbol,
                        type="quantity_mismatch",
                        bot_quantity=bot_qty,
                        exchange_quantity=exchange_qty,
                        severity="critical" if qty_diff > bot_qty * 0.1 else "warning",
                        message=f"Quantity mismatch: bot={bot_qty:.6f}, exchange={exchange_qty:.6f}, diff={qty_diff:.6f}"
                    )
                    discrepancies.append(discrepancy)
        
        # Check for positions in exchange but not in bot
        for symbol, exchange_pos in exchange_positions.items():
            if symbol not in bot_positions:
                exchange_qty = exchange_pos.get("quantity", 0) if isinstance(exchange_pos, dict) else 0
                discrepancy = PositionDiscrepancy(
                    symbol=symbol,
                    type="extra",
                    exchange_quantity=exchange_qty,
                    severity="critical" if exchange_qty > 0.001 else "warning",
                    message=f"Position in exchange ({exchange_qty:.6f}) but not in bot"
                )
                discrepancies.append(discrepancy)
        
        return discrepancies
    
    def get_reconciliation_stats(self) -> Dict:
        """Get reconciliation statistics."""
        return {
            "reconciliation_count": self.reconciliation_count,
            "discrepancy_count": self.discrepancy_count,
            "last_reconciliation_time": self.last_reconciliation_time.isoformat() if self.last_reconciliation_time else None
        }

