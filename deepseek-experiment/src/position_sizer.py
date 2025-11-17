"""
Position Sizer - Kelly Criterion Implementation

Calculates optimal position sizes based on historical win rate and profit/loss ratios
using the Kelly Criterion formula, with safety factors and portfolio-level correlation checks.
"""

import logging
import math
from typing import Dict, List, Optional, Any

from config import config

logger = logging.getLogger(__name__)


class PositionSizer:
    """
    Calculates optimal position sizes using Kelly Criterion.
    
    The Kelly Criterion maximizes long-term growth by calculating the optimal
    fraction of capital to bet based on win rate and win/loss ratio.
    """

    def __init__(self, safety_factor: float = None, lookback_trades: int = None, min_trades: int = None):
        """
        Initialize the position sizer.
        
        Args:
            safety_factor: Fraction of Kelly to use (0.5 = half-Kelly, more conservative)
            lookback_trades: Number of recent trades to analyze
            min_trades: Minimum trades needed for Kelly calculation
        """
        self.safety_factor = safety_factor or getattr(config, 'KELLY_SAFETY_FACTOR', 0.5)
        self.lookback_trades = lookback_trades or getattr(config, 'KELLY_LOOKBACK_TRADES', 30)
        self.min_trades = min_trades or getattr(config, 'KELLY_MIN_TRADES_FOR_CALC', 10)
        
        logger.info(
            f"PositionSizer initialized: safety_factor={self.safety_factor}, "
            f"lookback={self.lookback_trades}, min_trades={self.min_trades}"
        )

    def calculate_kelly_fraction(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        Calculate Kelly fraction from win rate and profit/loss ratios.
        
        Formula: f = (p * W - q) / W
        where:
            p = win rate (0-1)
            W = avg_win / abs(avg_loss) (win/loss ratio)
            q = 1 - p
        
        Args:
            win_rate: Win rate (0-1)
            avg_win: Average profit per winning trade
            avg_loss: Average loss per losing trade (should be negative)
        
        Returns:
            Kelly fraction (0-1), optimal fraction of balance to bet
        """
        # Edge case: no valid trades
        if win_rate <= 0 or win_rate >= 1:
            logger.debug(f"Invalid win_rate: {win_rate}, returning 0.0")
            return 0.0
        
        # Edge case: invalid P&L (losses should be negative)
        if avg_win <= 0 or avg_loss >= 0:
            logger.debug(f"Invalid P&L: avg_win={avg_win}, avg_loss={avg_loss}, returning 0.0")
            return 0.0
        
        # Edge case: division by zero (avg_loss is exactly 0)
        if abs(avg_loss) < 1e-10:
            logger.debug(f"avg_loss is zero or near-zero, returning 0.0")
            return 0.0
        
        # Calculate win/loss ratio
        W = avg_win / abs(avg_loss)
        q = 1 - win_rate
        
        # Kelly formula
        kelly_fraction = (win_rate * W - q) / W
        
        # Clamp to [0, 0.95] to prevent extreme values
        kelly_fraction = max(0.0, min(kelly_fraction, 0.95))
        
        logger.debug(
            f"Kelly calculation: win_rate={win_rate:.3f}, W={W:.3f}, "
            f"kelly_fraction={kelly_fraction:.3f}"
        )
        
        return kelly_fraction

    def calculate_optimal_position_size(
        self,
        portfolio: Dict[str, Any],
        recent_trades: List[Dict[str, Any]],
        max_position_size: float,
        existing_positions: Optional[Dict[str, Dict]] = None
    ) -> float:
        """
        Calculate optimal position size using Kelly Criterion.
        
        Args:
            portfolio: Portfolio state with balance, total_value, etc.
            recent_trades: List of recent trades (should be closed trades with profit/loss)
            max_position_size: Maximum position size as fraction of balance
            existing_positions: Dictionary of existing positions (symbol -> position dict)
        
        Returns:
            Optimal position size in USDT
        """
        balance = portfolio.get("balance", 0.0)
        
        if balance <= 0:
            logger.warning("Balance is zero or negative, returning 0")
            return 0.0
        
        # Analyze trade history
        trade_stats = self._analyze_trade_history(recent_trades)
        
        if not trade_stats:
            # No valid trades, use default position size
            default_size = balance * max_position_size
            logger.debug(f"No valid trades, using default position size: {default_size:.2f}")
            return default_size
        
        win_rate = trade_stats["win_rate"]
        avg_win = trade_stats["avg_win"]
        avg_loss = trade_stats["avg_loss"]
        sample_size = trade_stats["sample_size"]
        
        # Handle edge cases
        if sample_size < self.min_trades:
            # Insufficient data: blend with default (30% Kelly, 70% default)
            kelly_fraction = self.calculate_kelly_fraction(win_rate, avg_win, avg_loss)
            kelly_size = balance * kelly_fraction * self.safety_factor
            default_size = balance * max_position_size
            blended_size = kelly_size * 0.3 + default_size * 0.7
            logger.debug(
                f"Insufficient data ({sample_size} < {self.min_trades}), "
                f"blending: kelly={kelly_size:.2f}, default={default_size:.2f}, "
                f"blended={blended_size:.2f}"
            )
            return min(blended_size, default_size)
        
        # Calculate Kelly fraction
        kelly_fraction = self.calculate_kelly_fraction(win_rate, avg_win, avg_loss)
        
        # Apply safety factor (half-Kelly by default)
        adjusted_kelly = kelly_fraction * self.safety_factor
        
        # Calculate base position size
        base_position_size = balance * adjusted_kelly
        
        # CORRECTED: Portfolio-level correlation check with proper adjustment
        if existing_positions:
            num_existing = len(existing_positions)
            num_total = num_existing + 1  # Including this new position
            
            # Apply correlation penalty: divide Kelly by sqrt(number of positions)
            # This accounts for correlation between assets (e.g., BTC and ETH ~0.7-0.9 correlation)
            correlation_adjustment = 1.0 / math.sqrt(max(num_total, 1))
            
            # Adjust Kelly fraction for correlation
            adjusted_kelly = adjusted_kelly * correlation_adjustment
            
            logger.debug(
                f"Applied correlation adjustment: num_positions={num_total}, "
                f"adjustment={correlation_adjustment:.3f}, "
                f"adjusted_kelly={adjusted_kelly:.3f}"
            )
            
            # Recalculate base position size with correlation adjustment
            base_position_size = balance * adjusted_kelly
        
        # Apply caps
        max_size_by_config = balance * max_position_size
        max_risk_per_trade = balance * getattr(config, 'MAX_RISK_PER_TRADE', 0.02)
        
        optimal_size = min(base_position_size, max_size_by_config, max_risk_per_trade)
        
        logger.debug(
            f"Optimal position size: kelly={base_position_size:.2f}, "
            f"capped={optimal_size:.2f} (max_config={max_size_by_config:.2f}, "
            f"max_risk={max_risk_per_trade:.2f})"
        )
        
        return optimal_size

    def _analyze_trade_history(self, trades: List[Dict[str, Any]]) -> Optional[Dict[str, float]]:
        """
        Analyze trade history to extract win rate and profit/loss statistics.
        
        Args:
            trades: List of trade dictionaries
        
        Returns:
            Dictionary with win_rate, avg_win, avg_loss, sample_size, or None if insufficient data
        """
        if not trades:
            return None
        
        # Filter to closed trades (sells) with profit data
        closed_trades = [
            t for t in trades
            if t.get("side") == "sell" and "profit" in t
        ]
        
        if not closed_trades:
            return None
        
        # Take most recent N trades
        recent_closed = closed_trades[-self.lookback_trades:]
        
        if not recent_closed:
            return None
        
        # Calculate statistics
        profits = [t.get("profit", 0) for t in recent_closed]
        winning_trades = [p for p in profits if p > 0]
        losing_trades = [p for p in profits if p < 0]
        
        # Edge case: all wins (no loss data)
        # Use conservative estimate: assume losses are 10% of average win
        # This prevents over-leverage when we haven't seen losses yet
        CONSERVATIVE_LOSS_RATIO = 0.1  # Assume losses are 10% of wins
        if not losing_trades:
            logger.debug("All recent trades were wins, using conservative Kelly estimate")
            avg_win = sum(winning_trades) / len(winning_trades) if winning_trades else 0.0
            return {
                "win_rate": 1.0,
                "avg_win": avg_win,
                "avg_loss": -avg_win * CONSERVATIVE_LOSS_RATIO if avg_win > 0 else -100.0,
                "sample_size": len(recent_closed)
            }
        
        # Edge case: all losses
        if not winning_trades:
            logger.debug("All recent trades were losses, returning None (don't trade)")
            return None
        
        # Calculate win rate
        win_rate = len(winning_trades) / len(recent_closed)
        
        # Calculate averages
        avg_win = sum(winning_trades) / len(winning_trades)
        avg_loss = sum(losing_trades) / len(losing_trades)  # Already negative
        
        return {
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "sample_size": len(recent_closed)
        }

    def _calculate_total_kelly_allocation(
        self,
        existing_positions: Dict[str, Dict],
        recent_trades: List[Dict[str, Any]],
        balance: float
    ) -> float:
        """
        Calculate total Kelly allocation across all existing positions.
        
        CORRECTED: Accounts for correlation between positions.
        Uses correlation adjustment: divide Kelly by sqrt(number of positions).
        
        Args:
            existing_positions: Dictionary of existing positions
            recent_trades: Recent trade history
            balance: Current balance
        
        Returns:
            Total Kelly fraction allocated across all positions (0-1)
        """
        if not existing_positions:
            return 0.0
        
        # Analyze trades to get overall statistics
        trade_stats = self._analyze_trade_history(recent_trades)
        if not trade_stats:
            # If no trade history, assume conservative allocation
            return 0.0
        
        # Calculate Kelly fraction for overall strategy
        kelly_fraction = self.calculate_kelly_fraction(
            trade_stats["win_rate"],
            trade_stats["avg_win"],
            trade_stats["avg_loss"]
        )
        
        # CORRECTED: Apply correlation adjustment
        # Rule of thumb: Divide Kelly by sqrt(number of positions)
        # This accounts for correlation between assets (e.g., BTC and ETH)
        num_positions = len(existing_positions)
        correlation_adjustment = 1.0 / math.sqrt(max(num_positions, 1))
        
        # Calculate total allocation with correlation penalty
        total_position_value = sum(
            pos.get("notional_value", 0) for pos in existing_positions.values()
        )
        
        if total_position_value > 0 and balance > 0:
            total_position_fraction = total_position_value / balance
            # Apply correlation-adjusted Kelly
            total_allocation = (
                total_position_fraction * 
                kelly_fraction * 
                self.safety_factor * 
                correlation_adjustment
            )
        else:
            total_allocation = 0.0
        
        return min(total_allocation, 1.0)

