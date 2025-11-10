"""
Execution Engine - Venue Adapters and Order Selection

Provides execution quality controls:
- Venue adapters: Unify exchange idiosyncrasies (lot sizes, precision, rate limits)
- Order selection: post-only vs IOC depending on edge
- Dynamic limit offsets tied to spread/vol
- Cancel-replace budgets to avoid rate-limit bans
- Slippage budgets: each order carries max tolerable slip (bps)
"""

import logging
import threading
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import time

from config import config

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Order types."""

    MARKET = "market"
    LIMIT = "limit"
    POST_ONLY = "post_only"  # Maker order
    IOC = "ioc"  # Immediate or Cancel
    FOK = "fok"  # Fill or Kill


@dataclass
class OrderConfig:
    """Order configuration."""

    order_type: OrderType
    max_slippage_bps: float = 50.0  # Max 50 bps slippage
    limit_offset_bps: float = 0.0  # Offset from mid price for limit orders
    post_only: bool = False
    time_in_force: str = "GTC"  # Good Till Cancel
    cancel_replace_budget: int = 3  # Max cancel-replace attempts


@dataclass
class VenueConfig:
    """Venue-specific configuration."""

    venue_name: str
    min_lot_size: float
    lot_size_precision: int
    price_precision: int
    quantity_precision: int
    max_orders_per_second: int = 10
    max_orders_per_minute: int = 100
    supports_post_only: bool = True
    supports_ioc: bool = True
    supports_fok: bool = False


class ExecutionEngine:
    """
    Execution engine with venue adapters and order selection.
    """

    def __init__(self):
        # Venue configurations
        self.venue_configs = {
            "kraken": VenueConfig(
                venue_name="kraken",
                min_lot_size=0.0001,
                lot_size_precision=8,
                price_precision=1,
                quantity_precision=8,
                max_orders_per_second=10,
                max_orders_per_minute=100,
                supports_post_only=True,
                supports_ioc=True,
                supports_fok=False,
            ),
            "binance": VenueConfig(
                venue_name="binance",
                min_lot_size=0.001,
                lot_size_precision=8,
                price_precision=2,
                quantity_precision=8,
                max_orders_per_second=10,
                max_orders_per_minute=1200,
                supports_post_only=True,
                supports_ioc=True,
                supports_fok=True,
            ),
            "bybit": VenueConfig(
                venue_name="bybit",
                min_lot_size=0.001,
                lot_size_precision=8,
                price_precision=2,
                quantity_precision=8,
                max_orders_per_second=10,
                max_orders_per_minute=100,
                supports_post_only=True,
                supports_ioc=True,
                supports_fok=True,
            ),
        }

        # Rate limiting tracking (thread-safe)
        self.order_counts: Dict[str, Dict[str, int]] = {}  # venue -> {second: count, minute: count}
        self.order_counts_lock = threading.Lock()  # Lock for thread-safe order counting

        logger.info(f"Execution Engine initialized with {len(self.venue_configs)} venues")

    def get_venue_config(self, venue_name: str) -> VenueConfig:
        """Get venue configuration."""
        return self.venue_configs.get(venue_name.lower(), self.venue_configs["kraken"])

    def select_order_type(
        self,
        venue: str,
        spread_bps: float,
        volatility_bps: float,
        edge_bps: float,
        urgency: str = "normal",  # "low", "normal", "high"
    ) -> OrderType:
        """
        Select optimal order type based on market conditions.

        Args:
            venue: Exchange name
            spread_bps: Current spread in basis points
            volatility_bps: Current volatility in basis points
            edge_bps: Expected edge in basis points
            urgency: Trade urgency level

        Returns:
            Optimal order type
        """
        venue_config = self.get_venue_config(venue)

        # High urgency: Use market order
        if urgency == "high":
            return OrderType.MARKET

        # If edge > spread + volatility, use post-only to capture maker fee rebate
        if edge_bps > (spread_bps + volatility_bps) and venue_config.supports_post_only:
            return OrderType.POST_ONLY

        # If edge > spread/2, use limit order with offset
        if edge_bps > spread_bps / 2:
            return OrderType.LIMIT

        # If tight spread and low vol, use IOC for better fill probability
        if spread_bps < 10 and volatility_bps < 20 and venue_config.supports_ioc:
            return OrderType.IOC

        # Default: limit order
        return OrderType.LIMIT

    def calculate_limit_offset(
        self, order_type: OrderType, spread_bps: float, volatility_bps: float, side: str  # "buy" or "sell"
    ) -> float:
        """
        Calculate limit order offset from mid price.

        Returns:
            Offset in basis points (positive for buy, negative for sell)
        """
        if order_type == OrderType.POST_ONLY:
            # Post-only: place at mid price to maximize fill probability
            return 0.0

        if order_type == OrderType.LIMIT:
            # Limit: offset based on spread and volatility
            # Buy: slightly below mid to improve fill probability
            # Sell: slightly above mid
            offset = spread_bps * 0.3 + volatility_bps * 0.2

            if side == "buy":
                return -offset  # Negative offset for buy (below mid)
            else:
                return offset  # Positive offset for sell (above mid)

        return 0.0

    def check_rate_limit(self, venue: str) -> Tuple[bool, float]:
        """
        Check if order can be placed without hitting rate limit.

        Returns:
            (can_place, delay_seconds)
        """
        venue_config = self.get_venue_config(venue)
        current_time = time.time()

        with self.order_counts_lock:
            if venue not in self.order_counts:
                self.order_counts[venue] = {
                    "second": 0,
                    "second_timestamp": current_time,
                    "minute": 0,
                    "minute_timestamp": current_time,
                }

            counts = self.order_counts[venue]

            # Reset counters if time window passed
            if current_time - counts["second_timestamp"] >= 1.0:
                counts["second"] = 0
                counts["second_timestamp"] = current_time

            if current_time - counts["minute_timestamp"] >= 60.0:
                counts["minute"] = 0
                counts["minute_timestamp"] = current_time

            # Check limits
            can_place = True
            delay = 0.0

            if counts["second"] >= venue_config.max_orders_per_second:
                can_place = False
                delay = 1.0 - (current_time - counts["second_timestamp"])

            if counts["minute"] >= venue_config.max_orders_per_minute:
                can_place = False
                delay = max(delay, 60.0 - (current_time - counts["minute_timestamp"]))

        return can_place, delay

    def record_order(self, venue: str):
        """Record an order placement for rate limiting."""
        with self.order_counts_lock:
            if venue not in self.order_counts:
                self.order_counts[venue] = {
                    "second": 0,
                    "second_timestamp": time.time(),
                    "minute": 0,
                    "minute_timestamp": time.time(),
                }

            counts = self.order_counts[venue]
            current_time = time.time()

            # Reset if needed
            if current_time - counts["second_timestamp"] >= 1.0:
                counts["second"] = 0
                counts["second_timestamp"] = current_time

            if current_time - counts["minute_timestamp"] >= 60.0:
                counts["minute"] = 0
                counts["minute_timestamp"] = current_time

            counts["second"] += 1
            counts["minute"] += 1

    def normalize_order_params(self, venue: str, quantity: float, price: float) -> Tuple[float, float]:
        """
        Normalize order parameters to venue requirements.

        Args:
            venue: Exchange name
            quantity: Order quantity
            price: Order price

        Returns:
            (normalized_quantity, normalized_price)
        """
        venue_config = self.get_venue_config(venue)

        # Round quantity to lot size precision
        quantity = round(quantity, venue_config.quantity_precision)

        # Ensure quantity >= min_lot_size
        if quantity < venue_config.min_lot_size:
            quantity = venue_config.min_lot_size

        # Round price to price precision
        price = round(price, venue_config.price_precision)

        return quantity, price

    def check_slippage_budget(
        self, intended_price: float, actual_price: float, max_slippage_bps: float
    ) -> Tuple[bool, float]:
        """
        Check if actual price is within slippage budget.

        Returns:
            (within_budget, actual_slippage_bps)
        """
        slippage_bps = abs(actual_price - intended_price) / intended_price * 10000

        within_budget = slippage_bps <= max_slippage_bps

        return within_budget, slippage_bps

    def create_order(
        self,
        venue: str,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        order_type: OrderType,
        max_slippage_bps: float = 50.0,
        spread_bps: float = 10.0,
        volatility_bps: float = 20.0,
    ) -> Dict:
        """
        Create order with venue-specific normalization and validation.

        Returns:
            Order dictionary ready for exchange API
        """
        venue_config = self.get_venue_config(venue)

        # Normalize parameters
        quantity, price = self.normalize_order_params(venue, quantity, price)

        # Calculate limit offset if needed
        limit_offset_bps = 0.0
        if order_type == OrderType.LIMIT:
            limit_offset_bps = self.calculate_limit_offset(order_type, spread_bps, volatility_bps, side)
            price = price * (1 + limit_offset_bps / 10000)
            price, _ = self.normalize_order_params(venue, quantity, price)

        # Check rate limits
        can_place, delay = self.check_rate_limit(venue)
        if not can_place:
            logger.warning(f"Rate limit hit for {venue}, delay={delay:.2f}s")

        # Build order
        order = {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "type": order_type.value,
            "max_slippage_bps": max_slippage_bps,
            "limit_offset_bps": limit_offset_bps,
            "venue": venue,
            "rate_limit_delay": delay,
        }

        # Venue-specific adjustments
        if venue.lower() == "kraken":
            order["ordertype"] = order_type.value
        elif venue.lower() == "binance":
            order["type"] = order_type.value.upper()
            if order_type == OrderType.POST_ONLY:
                order["timeInForce"] = "POST_ONLY"
            elif order_type == OrderType.IOC:
                order["timeInForce"] = "IOC"

        # Record order for rate limiting
        if can_place:
            self.record_order(venue)

        logger.debug(f"Order created: {order}")

        return order
