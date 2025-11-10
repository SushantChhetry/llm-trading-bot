"""
Data Quality Checks - First-Class Risk Management

Data quality as a first-class risk:
- NTP sync and clock drift detection
- Symbol normalization
- Robust missing-bar handling
- Price triangulation (independent feeds vs venue)
- Clock & IDs: detect clock drift, normalize symbols
- Cold starts: explicit rules when features are NA
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple

import ntplib

logger = logging.getLogger(__name__)


class DataQualityStatus(Enum):
    """Data quality status."""

    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    DEGRADED = "degraded"


@dataclass
class ClockDriftCheck:
    """Clock drift check result."""

    local_time: datetime
    ntp_time: Optional[datetime]
    drift_seconds: float
    status: DataQualityStatus
    last_check: datetime


@dataclass
class PriceTriangulation:
    """Price triangulation result."""

    venue_price: float
    index_price: Optional[float]
    divergence_bps: float
    status: DataQualityStatus
    timestamp: datetime


@dataclass
class DataQualityReport:
    """Data quality report."""

    clock_drift: ClockDriftCheck
    price_triangulation: Optional[PriceTriangulation]
    missing_bars_count: int
    stale_data_seconds: float
    overall_status: DataQualityStatus
    timestamp: datetime


class DataQualityManager:
    """
    Manages data quality checks as first-class risk.
    """

    def __init__(
        self,
        max_clock_drift_seconds: float = 5.0,
        max_price_divergence_bps: float = 50.0,
        max_stale_data_seconds: float = 30.0,
        ntp_servers: List[str] = None,
    ):
        self.max_clock_drift_seconds = max_clock_drift_seconds
        self.max_price_divergence_bps = max_price_divergence_bps
        self.max_stale_data_seconds = max_stale_data_seconds

        self.ntp_servers = ntp_servers or ["pool.ntp.org", "time.google.com", "time.cloudflare.com"]

        self.clock_drift_check: Optional[ClockDriftCheck] = None
        self.last_data_update: Optional[datetime] = None
        self.missing_bars_count = 0
        self.price_history: Dict[str, List[Tuple[datetime, float]]] = {}

        logger.info("Data Quality Manager initialized")

    def check_clock_drift(self) -> ClockDriftCheck:
        """Check system clock drift against NTP servers."""
        local_time = datetime.utcnow()
        ntp_time = None
        drift_seconds = 0.0
        status = DataQualityStatus.HEALTHY

        try:
            ntp_client = ntplib.NTPClient()

            for ntp_server in self.ntp_servers:
                try:
                    response = ntp_client.request(ntp_server, timeout=2)
                    ntp_time = datetime.utcfromtimestamp(response.tx_time)
                    drift_seconds = abs((local_time - ntp_time).total_seconds())
                    break
                except Exception as e:
                    logger.debug(f"NTP check failed for {ntp_server}: {e}")
                    continue

            if ntp_time is None:
                status = DataQualityStatus.WARNING
                logger.warning("Could not sync with NTP servers")
            elif drift_seconds > self.max_clock_drift_seconds:
                status = DataQualityStatus.CRITICAL
                logger.error(f"Clock drift too large: {drift_seconds:.2f}s > {self.max_clock_drift_seconds:.2f}s")
            elif drift_seconds > self.max_clock_drift_seconds / 2:
                status = DataQualityStatus.WARNING

        except Exception as e:
            logger.warning(f"Error checking clock drift: {e}")
            status = DataQualityStatus.WARNING

        self.clock_drift_check = ClockDriftCheck(
            local_time=local_time, ntp_time=ntp_time, drift_seconds=drift_seconds, status=status, last_check=local_time
        )

        return self.clock_drift_check

    def normalize_symbol(self, symbol: str, venue: str) -> str:
        """
        Normalize symbol format across venues.

        Examples:
        - "BTC/USDT" -> "BTC/USDT" (standard)
        - "BTCUSDT" -> "BTC/USDT"
        - "XBT/USD" (Kraken) -> "BTC/USDT"
        """
        # Remove common separators and normalize
        normalized = symbol.replace("-", "/").replace("_", "/").upper()

        # Venue-specific mappings
        venue_mappings = {
            "kraken": {
                "XBT/USD": "BTC/USDT",
                "XBT/USDT": "BTC/USDT",
            },
            "binance": {
                "BTCUSDT": "BTC/USDT",
            },
        }

        if venue.lower() in venue_mappings:
            if normalized in venue_mappings[venue.lower()]:
                normalized = venue_mappings[venue.lower()][normalized]

        return normalized

    def check_price_triangulation(
        self, venue_price: float, index_price: Optional[float] = None, symbol: str = None
    ) -> PriceTriangulation:
        """
        Check price divergence between venue and index feed.

        Sets circuit breaker if divergence is too large.
        """
        timestamp = datetime.utcnow()
        divergence_bps = 0.0
        status = DataQualityStatus.HEALTHY

        if index_price is None:
            # Try to get historical average
            if symbol and symbol in self.price_history:
                recent_prices = [p for _, p in self.price_history[symbol][-10:]]
                if recent_prices:
                    index_price = sum(recent_prices) / len(recent_prices)
                else:
                    status = DataQualityStatus.WARNING
            else:
                status = DataQualityStatus.WARNING

        if index_price and index_price > 0:
            divergence_bps = abs(venue_price - index_price) / index_price * 10000

            if divergence_bps > self.max_price_divergence_bps:
                status = DataQualityStatus.CRITICAL
                logger.error(
                    f"Price divergence too large: {divergence_bps:.2f} bps "
                    f"(venue={venue_price:.2f}, index={index_price:.2f})"
                )
            elif divergence_bps > self.max_price_divergence_bps / 2:
                status = DataQualityStatus.WARNING

        # Store price history
        if symbol:
            if symbol not in self.price_history:
                self.price_history[symbol] = []
            self.price_history[symbol].append((timestamp, venue_price))

            # Keep only last 100 prices
            if len(self.price_history[symbol]) > 100:
                self.price_history[symbol] = self.price_history[symbol][-100:]

        triangulation = PriceTriangulation(
            venue_price=venue_price,
            index_price=index_price,
            divergence_bps=divergence_bps,
            status=status,
            timestamp=timestamp,
        )

        return triangulation

    def check_stale_data(self) -> Tuple[bool, float]:
        """
        Check if data is stale.

        Returns:
            (is_stale, seconds_since_update)
        """
        if self.last_data_update is None:
            return True, float("inf")

        seconds_since_update = (datetime.utcnow() - self.last_data_update).total_seconds()
        is_stale = seconds_since_update > self.max_stale_data_seconds

        return is_stale, seconds_since_update

    def update_data_timestamp(self):
        """Update last data update timestamp."""
        self.last_data_update = datetime.utcnow()

    def handle_missing_bar(self, expected_timestamp: datetime, timeframe_minutes: int = 5) -> Dict:
        """
        Handle missing bar data with explicit rules.

        Never let the model "wing it" on partial data.
        """
        self.missing_bars_count += 1

        # Calculate time since expected bar
        time_since_expected = (datetime.utcnow() - expected_timestamp).total_seconds()

        # Decision rules
        if time_since_expected > timeframe_minutes * 60 * 2:  # More than 2 bars missing
            status = DataQualityStatus.CRITICAL
            action = "skip_trading"  # Don't trade with stale data
        elif time_since_expected > timeframe_minutes * 60:  # 1-2 bars missing
            status = DataQualityStatus.WARNING
            action = "reduce_position_size"  # Trade with caution
        else:
            status = DataQualityStatus.HEALTHY
            action = "interpolate"  # Use interpolation

        return {
            "status": status.value,
            "action": action,
            "missing_bars": self.missing_bars_count,
            "time_since_expected": time_since_expected,
        }

    def validate_features(self, features: Dict) -> Tuple[bool, List[str]]:
        """
        Validate that required features are present and not NA.

        Returns:
            (is_valid, missing_features)
        """
        required_features = ["price", "volume", "timestamp"]

        missing = []

        for feature in required_features:
            if feature not in features:
                missing.append(feature)
            elif features[feature] is None:
                missing.append(f"{feature} (None)")
            elif isinstance(features[feature], float) and (features[feature] != features[feature]):  # NaN check
                missing.append(f"{feature} (NaN)")

        is_valid = len(missing) == 0

        if not is_valid:
            logger.warning(f"Missing or invalid features: {missing}")

        return is_valid, missing

    def get_quality_report(self) -> DataQualityReport:
        """Get comprehensive data quality report."""
        # Check clock drift
        if self.clock_drift_check is None:
            clock_drift = self.check_clock_drift()
        else:
            # Re-check if last check was > 1 hour ago
            if (datetime.utcnow() - self.clock_drift_check.last_check).total_seconds() > 3600:
                clock_drift = self.check_clock_drift()
            else:
                clock_drift = self.clock_drift_check

        # Check stale data
        is_stale, stale_seconds = self.check_stale_data()

        # Determine overall status
        statuses = [clock_drift.status]
        if is_stale:
            statuses.append(DataQualityStatus.CRITICAL)
        if self.missing_bars_count > 10:
            statuses.append(DataQualityStatus.WARNING)

        if DataQualityStatus.CRITICAL in statuses:
            overall_status = DataQualityStatus.CRITICAL
        elif DataQualityStatus.WARNING in statuses:
            overall_status = DataQualityStatus.WARNING
        else:
            overall_status = DataQualityStatus.HEALTHY

        return DataQualityReport(
            clock_drift=clock_drift,
            price_triangulation=None,  # Would be set by check_price_triangulation
            missing_bars_count=self.missing_bars_count,
            stale_data_seconds=stale_seconds if is_stale else 0.0,
            overall_status=overall_status,
            timestamp=datetime.utcnow(),
        )
