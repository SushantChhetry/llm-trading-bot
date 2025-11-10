"""
Risk Service Client - Python Client Library

Client library for interacting with the out-of-process risk service.
Provides caching, retry logic, and easy integration with trading engine.
"""

import logging
import time
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import config

logger = logging.getLogger(__name__)


@dataclass
class OrderValidationResult:
    """Result of order validation."""

    approved: bool
    status: str  # "approved", "rejected", "kill_switch"
    reason: str
    details: Dict


class RiskClient:
    """Client for risk service API."""

    def __init__(
        self,
        risk_service_url: str = "http://localhost:8003",
        timeout: float = 5.0,
        cache_ttl: float = 1.0,  # Cache limit checks for 1 second
        max_retries: int = 3,
    ):
        self.risk_service_url = risk_service_url.rstrip("/")
        self.timeout = timeout
        self.cache_ttl = cache_ttl

        # Setup session with retry logic
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Cache for limit checks
        self.cache: Dict[str, Tuple[float, OrderValidationResult]] = {}

        logger.info(f"Risk Client initialized: {risk_service_url}")

    def validate_order(
        self,
        strategy_id: str,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        leverage: float,
        current_nav: float,
        position_value: float,
    ) -> OrderValidationResult:
        """
        Validate order with risk service.

        Args:
            strategy_id: Strategy identifier
            symbol: Trading symbol
            side: "buy", "sell", "short"
            quantity: Order quantity
            price: Order price
            leverage: Leverage multiplier
            current_nav: Current portfolio NAV
            position_value: Position value in base currency

        Returns:
            OrderValidationResult
        """
        # Check cache
        cache_key = f"{strategy_id}:{symbol}:{side}:{quantity}:{price}:{leverage}:{current_nav}"
        if cache_key in self.cache:
            cached_time, cached_result = self.cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                logger.debug(f"Using cached validation result for {symbol}")
                return cached_result

        try:
            response = self.session.post(
                f"{self.risk_service_url}/risk/validate_order",
                json={
                    "strategy_id": strategy_id,
                    "symbol": symbol,
                    "side": side,
                    "quantity": quantity,
                    "price": price,
                    "leverage": leverage,
                    "current_nav": current_nav,
                    "position_value": position_value,
                },
                timeout=self.timeout,
            )

            if response.status_code == 200:
                data = response.json()
                result = OrderValidationResult(
                    approved=data.get("approved", False),
                    status=data.get("status", "rejected"),
                    reason=data.get("reason", "Unknown"),
                    details=data.get("details", {}),
                )

                # Cache result
                self.cache[cache_key] = (time.time(), result)

                # Clean old cache entries
                self._clean_cache()

                return result
            else:
                logger.error(f"Risk service returned {response.status_code}: {response.text}")
                # Fail-closed behavior: reject trades when risk service is down (if configured)
                if config.RISK_SERVICE_FAIL_CLOSED:
                    logger.critical(f"Risk service error ({response.status_code}) - REJECTING trade (fail-closed mode)")
                    return OrderValidationResult(
                        approved=False,
                        status="rejected",
                        reason=f"Risk service error: {response.status_code} (fail-closed mode)",
                        details={},
                    )
                else:
                    # Fail-open behavior: approve trades when risk service is down (paper trading only)
                    logger.warning(f"Risk service error ({response.status_code}) - APPROVING trade (fail-open mode)")
                    return OrderValidationResult(
                        approved=True,
                        status="approved",
                        reason=f"Risk service error but fail-open mode enabled",
                        details={},
                    )

        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling risk service: {e}")
            # Fail-closed behavior: reject trades when risk service is unreachable (if configured)
            if config.RISK_SERVICE_FAIL_CLOSED:
                logger.critical(f"Risk service unreachable - REJECTING trade (fail-closed mode)")
                return OrderValidationResult(
                    approved=False,
                    status="rejected",
                    reason=f"Risk service unreachable: {str(e)} (fail-closed mode)",
                    details={},
                )
            else:
                # Fail-open behavior: approve trades when risk service is unreachable (paper trading only)
                logger.warning(f"Risk service unreachable - APPROVING trade (fail-open mode)")
                return OrderValidationResult(
                    approved=True,
                    status="approved",
                    reason=f"Risk service unreachable but fail-open mode enabled",
                    details={},
                )

    def get_risk_state(self) -> Optional[Dict]:
        """Get current risk state from risk service."""
        try:
            response = self.session.get(f"{self.risk_service_url}/risk/limits", timeout=self.timeout)

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Risk service returned {response.status_code}: {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting risk state: {e}")
            return None

    def update_market_data(self, market_data: Dict) -> bool:
        """Update market data in risk service."""
        try:
            response = self.session.post(
                f"{self.risk_service_url}/risk/update_market_data", json=market_data, timeout=self.timeout
            )

            return response.status_code == 200

        except requests.exceptions.RequestException as e:
            logger.error(f"Error updating market data: {e}")
            return False

    def update_portfolio(self, nav: float, positions: Dict, daily_loss_pct: float = None) -> bool:
        """Update portfolio state in risk service."""
        try:
            payload = {"nav": nav, "positions": positions}
            if daily_loss_pct is not None:
                payload["daily_loss_pct"] = daily_loss_pct

            response = self.session.post(
                f"{self.risk_service_url}/risk/update_portfolio", json=payload, timeout=self.timeout
            )

            return response.status_code == 200

        except requests.exceptions.RequestException as e:
            logger.error(f"Error updating portfolio: {e}")
            return False

    def calculate_volatility_targeted_size(
        self,
        risk_budget: float,
        atr: float = 0,
        realized_vol: float = 0,
        horizon_days: float = 1.0,
        current_price: float = None,
    ) -> Optional[float]:
        """Calculate volatility-targeted position size."""
        try:
            response = self.session.post(
                f"{self.risk_service_url}/risk/volatility_targeted_size",
                json={
                    "risk_budget": risk_budget,
                    "atr": atr,
                    "realized_vol": realized_vol,
                    "horizon_days": horizon_days,
                    "current_price": current_price,
                },
                timeout=self.timeout,
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("size")
            else:
                logger.error(f"Risk service returned {response.status_code}: {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Error calculating volatility size: {e}")
            return None

    def _clean_cache(self):
        """Remove old cache entries."""
        current_time = time.time()
        keys_to_remove = [
            key for key, (cached_time, _) in self.cache.items() if current_time - cached_time > self.cache_ttl * 2
        ]
        for key in keys_to_remove:
            del self.cache[key]
