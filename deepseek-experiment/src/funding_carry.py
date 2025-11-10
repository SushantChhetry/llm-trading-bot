"""
Funding and Carry Subsystem

Manages funding rates, borrow costs, and carry P&L attribution:
- Funding scheduling: decides when to hold/avoid perps across funding windows
- Borrow APR modeling: models borrow costs into expected edge
- Carry P&L attribution: separates alpha vs carry vs fees
- Capital efficiency: caps strategies where carry turns expected value negative
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class FundingRate:
    """Funding rate snapshot."""

    timestamp: datetime
    symbol: str
    funding_rate: float  # 8-hour funding rate (e.g., 0.0001 = 0.01%)
    funding_rate_annualized: float  # Annualized rate
    next_funding_time: datetime  # Next funding payment time


@dataclass
class BorrowCost:
    """Borrow cost information."""

    symbol: str
    borrow_rate_apr: float  # Annual percentage rate
    borrow_amount: float
    daily_cost: float
    expected_cost_per_trade: float


@dataclass
class CarryPnL:
    """Carry P&L attribution."""

    alpha_pnl: float  # PnL from price movement
    carry_pnl: float  # PnL from funding rates
    borrow_cost: float  # Cost of borrowing
    fee_pnl: float  # PnL impact from trading fees
    net_pnl: float  # Total net P&L


class FundingCarryManager:
    """
    Manages funding rates, borrow costs, and carry P&L attribution.
    """

    def __init__(self):
        self.funding_rates: Dict[str, List[FundingRate]] = {}
        self.borrow_costs: Dict[str, BorrowCost] = {}
        self.carry_history: List[Dict] = []

        # Funding windows (typically every 8 hours: 00:00, 08:00, 16:00 UTC)
        self.funding_times = [0, 8, 16]  # UTC hours

        logger.info("Funding/Carry Manager initialized")

    def update_funding_rate(self, symbol: str, funding_rate: float, timestamp: datetime = None):
        """Update funding rate for a symbol."""
        if timestamp is None:
            timestamp = datetime.utcnow()

        # Calculate next funding time
        current_hour = timestamp.hour
        next_funding_hour = None

        for funding_hour in sorted(self.funding_times):
            if funding_hour > current_hour:
                next_funding_hour = funding_hour
                break

        if next_funding_hour is None:
            # Next funding is tomorrow at first window
            next_funding_time = timestamp.replace(hour=self.funding_times[0], minute=0, second=0) + timedelta(days=1)
        else:
            next_funding_time = timestamp.replace(hour=next_funding_hour, minute=0, second=0)

        # Annualize funding rate (8-hour periods = 1095 periods per year)
        funding_rate_annualized = funding_rate * 1095

        rate = FundingRate(
            timestamp=timestamp,
            symbol=symbol,
            funding_rate=funding_rate,
            funding_rate_annualized=funding_rate_annualized,
            next_funding_time=next_funding_time,
        )

        if symbol not in self.funding_rates:
            self.funding_rates[symbol] = []

        self.funding_rates[symbol].append(rate)

        # Keep only last 100 rates
        if len(self.funding_rates[symbol]) > 100:
            self.funding_rates[symbol] = self.funding_rates[symbol][-100:]

        logger.debug(
            f"Funding rate updated: {symbol} = {funding_rate*100:.4f}% (annualized: {funding_rate_annualized*100:.2f}%)"
        )

    def get_current_funding_rate(self, symbol: str) -> Optional[FundingRate]:
        """Get current funding rate for symbol."""
        if symbol not in self.funding_rates or not self.funding_rates[symbol]:
            return None

        return self.funding_rates[symbol][-1]

    def should_hold_perpetual(
        self,
        symbol: str,
        position_side: str,  # "long" or "short"
        funding_rate: Optional[float] = None,
        expected_hold_hours: float = 8.0,
    ) -> Tuple[bool, float]:
        """
        Decide whether to hold a perpetual position through funding windows.

        Returns:
            (should_hold, expected_carry_cost)
        """
        if funding_rate is None:
            rate = self.get_current_funding_rate(symbol)
            if rate is None:
                return True, 0.0  # Default to hold if no funding data
            funding_rate = rate.funding_rate

        # Calculate expected carry cost
        funding_periods = expected_hold_hours / 8.0
        carry_cost = funding_rate * funding_periods

        # Long positions pay funding when rate is positive
        # Short positions receive funding when rate is positive
        if position_side == "long":
            expected_carry = -carry_cost  # Negative if funding is positive
        else:  # short
            expected_carry = carry_cost  # Positive if funding is positive

        # Hold if carry cost is acceptable (threshold: 0.05% per 8 hours)
        should_hold = abs(carry_cost) < 0.0005

        return should_hold, expected_carry

    def calculate_borrow_cost(
        self, symbol: str, borrow_amount: float, borrow_rate_apr: float, days: float = 1.0
    ) -> float:
        """Calculate borrow cost for a given period."""
        daily_rate = borrow_rate_apr / 365.0
        cost = borrow_amount * daily_rate * days
        return cost

    def update_borrow_cost(self, symbol: str, borrow_amount: float, borrow_rate_apr: float):
        """Update borrow cost tracking."""
        daily_cost = self.calculate_borrow_cost(symbol, borrow_amount, borrow_rate_apr, 1.0)

        self.borrow_costs[symbol] = BorrowCost(
            symbol=symbol,
            borrow_rate_apr=borrow_rate_apr,
            borrow_amount=borrow_amount,
            daily_cost=daily_cost,
            expected_cost_per_trade=daily_cost * 0.125,  # Assume 3-hour average trade duration
        )

    def calculate_carry_pnl(
        self,
        symbol: str,
        position_side: str,
        position_size: float,
        entry_price: float,
        current_price: float,
        entry_time: datetime,
        current_time: datetime,
        trading_fees: float = 0.0,
    ) -> CarryPnL:
        """
        Calculate carry P&L attribution.

        Separates P&L into:
        - Alpha: Price movement P&L
        - Carry: Funding rate P&L
        - Borrow: Borrow cost
        - Fees: Trading fee impact
        """
        # Calculate alpha P&L (price movement)
        if position_side == "long":
            alpha_pnl = (current_price - entry_price) * position_size
        else:  # short
            alpha_pnl = (entry_price - current_price) * position_size

        # Calculate carry P&L (funding payments)
        time_held = (current_time - entry_time).total_seconds() / 3600  # hours
        funding_periods = time_held / 8.0

        rate = self.get_current_funding_rate(symbol)
        if rate:
            funding_rate = rate.funding_rate
            notional_value = position_size * entry_price

            if position_side == "long":
                # Long pays funding
                carry_pnl = -notional_value * funding_rate * funding_periods
            else:
                # Short receives funding
                carry_pnl = notional_value * funding_rate * funding_periods
        else:
            carry_pnl = 0.0

        # Calculate borrow cost
        borrow_cost = 0.0
        if symbol in self.borrow_costs:
            borrow_cost = self.calculate_borrow_cost(
                symbol,
                self.borrow_costs[symbol].borrow_amount,
                self.borrow_costs[symbol].borrow_rate_apr,
                time_held / 24.0,  # days
            )

        # Fee impact
        fee_pnl = -trading_fees

        # Net P&L
        net_pnl = alpha_pnl + carry_pnl - borrow_cost + fee_pnl

        carry_pnl_obj = CarryPnL(
            alpha_pnl=alpha_pnl, carry_pnl=carry_pnl, borrow_cost=borrow_cost, fee_pnl=fee_pnl, net_pnl=net_pnl
        )

        # Store in history
        self.carry_history.append(
            {
                "timestamp": current_time.isoformat(),
                "symbol": symbol,
                "position_side": position_side,
                **{
                    "alpha_pnl": alpha_pnl,
                    "carry_pnl": carry_pnl,
                    "borrow_cost": borrow_cost,
                    "fee_pnl": fee_pnl,
                    "net_pnl": net_pnl,
                },
            }
        )

        # Keep only last 1000 entries
        if len(self.carry_history) > 1000:
            self.carry_history = self.carry_history[-1000:]

        return carry_pnl_obj

    def should_avoid_perp(
        self,
        symbol: str,
        expected_edge_bps: float,
        funding_rate: Optional[float] = None,
        borrow_rate_apr: Optional[float] = None,
    ) -> Tuple[bool, str]:
        """
        Determine if perpetual should be avoided due to carry costs.

        Returns:
            (should_avoid, reason)
        """
        if funding_rate is None:
            rate = self.get_current_funding_rate(symbol)
            if rate:
                funding_rate = rate.funding_rate
            else:
                return False, "No funding rate data"

        # Convert funding rate to bps (annualized)
        funding_bps = funding_rate * 1095 * 10000  # Annualized in bps

        # Expected carry cost per trade (assuming 8-hour hold)
        carry_cost_bps = funding_bps / 1095  # One 8-hour period

        # Borrow cost if applicable
        borrow_cost_bps = 0.0
        if borrow_rate_apr:
            # Daily borrow cost in bps
            borrow_cost_bps = (borrow_rate_apr / 365.0) * 10000

        # Total carry cost
        total_carry_bps = carry_cost_bps + borrow_cost_bps

        # Avoid if carry cost > expected edge
        if total_carry_bps > expected_edge_bps:
            reason = f"Carry cost ({total_carry_bps:.2f} bps) exceeds expected edge ({expected_edge_bps:.2f} bps)"
            return True, reason

        return False, ""

    def get_carry_summary(self, symbol: Optional[str] = None) -> Dict:
        """Get carry P&L summary."""
        if symbol:
            history = [h for h in self.carry_history if h.get("symbol") == symbol]
        else:
            history = self.carry_history

        if not history:
            return {
                "total_alpha_pnl": 0.0,
                "total_carry_pnl": 0.0,
                "total_borrow_cost": 0.0,
                "total_fee_pnl": 0.0,
                "net_pnl": 0.0,
            }

        return {
            "total_alpha_pnl": sum(h.get("alpha_pnl", 0) for h in history),
            "total_carry_pnl": sum(h.get("carry_pnl", 0) for h in history),
            "total_borrow_cost": sum(h.get("borrow_cost", 0) for h in history),
            "total_fee_pnl": sum(h.get("fee_pnl", 0) for h in history),
            "net_pnl": sum(h.get("net_pnl", 0) for h in history),
            "trade_count": len(history),
        }
