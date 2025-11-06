"""
Risk Management Service - Out-of-Process Service

Authoritative risk management service that enforces hard limits and kill switches.
This service runs independently and can revoke orders before execution.

Hard Limits (Per-Strategy):
- max_position_value: 10% of NAV (default)
- max_leverage: ≤3x (default, configurable per strategy)
- per_trade_var: 0.35% of NAV (default)
- max_daily_loss: 2% of NAV (default)
- max_drawdown_trading_pause: 10% drawdown triggers 48h cooldown

Kill Switch Triggers:
- Exchange outage detection (no data for >30s)
- Funding rate spikes >500 bps
- API latency >100ms (p99)
- Price feed divergence >50 bps between venues
- Equity drop >5% in single bar
"""

import json
import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

from flask import Flask, request, jsonify
from flask_cors import CORS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RiskStatus(Enum):
    """Risk check status."""
    APPROVED = "approved"
    REJECTED = "rejected"
    KILL_SWITCH = "kill_switch"


@dataclass
class RiskLimits:
    """Hard risk limits per strategy."""
    max_position_value_pct: float = 0.10  # 10% of NAV
    max_leverage: float = 3.0  # ≤3x
    per_trade_var_pct: float = 0.0035  # 0.35% of NAV
    max_daily_loss_pct: float = 0.02  # 2% of NAV
    max_drawdown_pct: float = 0.10  # 10% drawdown
    drawdown_cooldown_hours: int = 48  # 48h cooldown after drawdown
    correlation_limit: float = 0.7  # Max correlation between positions


@dataclass
class KillSwitchThresholds:
    """Kill switch trigger thresholds."""
    exchange_outage_seconds: float = 30.0  # No data for >30s
    funding_spike_bps: float = 500.0  # >500 bps
    api_latency_ms_p99: float = 100.0  # >100ms p99
    price_divergence_bps: float = 50.0  # >50 bps between venues
    equity_drop_pct: float = 0.05  # >5% in single bar


@dataclass
class OrderRequest:
    """Order validation request."""
    strategy_id: str
    symbol: str
    side: str  # "buy", "sell", "short"
    quantity: float
    price: float
    leverage: float
    current_nav: float
    position_value: float
    timestamp: float


@dataclass
class RiskState:
    """Current risk state snapshot."""
    daily_loss_pct: float = 0.0
    current_drawdown_pct: float = 0.0
    drawdown_peak_nav: float = 0.0
    drawdown_start_time: Optional[float] = None
    total_exposure: float = 0.0
    positions: Dict[str, Dict] = None  # symbol -> position dict
    kill_switch_active: bool = False
    kill_switch_reason: Optional[str] = None
    last_data_update: float = 0.0
    api_latency_p99: float = 0.0
    funding_rate: float = 0.0
    price_divergence_bps: float = 0.0


class RiskService:
    """Out-of-process risk management service."""
    
    def __init__(self, limits: RiskLimits = None, kill_switch_thresholds: KillSwitchThresholds = None):
        self.limits = limits or RiskLimits()
        self.kill_switch_thresholds = kill_switch_thresholds or KillSwitchThresholds()
        
        # Thread safety: lock for all state modifications
        self.state_lock = threading.Lock()
        
        # Risk state
        self.risk_state = RiskState()
        self.risk_state.positions = {}
        
        # Daily tracking
        self.daily_start_nav = None
        self.daily_start_time = None
        self.daily_reset_time = "00:00"  # UTC
        
        # Strategy-specific limits (can override defaults)
        self.strategy_limits: Dict[str, RiskLimits] = {}
        
        # Kill switch state
        self.kill_switch_active = False
        self.kill_switch_reason = None
        
        logger.info(f"Risk Service initialized with limits: {asdict(self.limits)}")
    
    def validate_order(self, order: OrderRequest) -> Tuple[RiskStatus, str, Dict]:
        """
        Validate order against risk limits.
        
        Returns:
            (status, reason, details)
        """
        # Thread-safe state access
        with self.state_lock:
            # Input validation
            if order.quantity <= 0:
                return (
                    RiskStatus.REJECTED,
                    f"Invalid quantity: {order.quantity} (must be > 0)",
                    {"quantity": order.quantity}
                )
            
            if order.price <= 0:
                return (
                    RiskStatus.REJECTED,
                    f"Invalid price: {order.price} (must be > 0)",
                    {"price": order.price}
                )
            
            if order.leverage <= 0:
                return (
                    RiskStatus.REJECTED,
                    f"Invalid leverage: {order.leverage} (must be > 0)",
                    {"leverage": order.leverage}
                )
            
            if order.current_nav <= 0:
                return (
                    RiskStatus.REJECTED,
                    f"Invalid NAV: {order.current_nav} (must be > 0)",
                    {"current_nav": order.current_nav}
                )
            
            # Check kill switch first
            if self.kill_switch_active:
                return (
                    RiskStatus.KILL_SWITCH,
                    self.kill_switch_reason or "Kill switch active",
                    {"kill_switch": True}
                )
            
            # Check drawdown pause
            if self._is_in_drawdown_cooldown():
                return (
                    RiskStatus.REJECTED,
                    f"Drawdown cooldown active: {self.risk_state.current_drawdown_pct:.2f}% drawdown",
                    {"drawdown_pct": self.risk_state.current_drawdown_pct}
                )
            
            # Check daily loss limit
            if self.risk_state.daily_loss_pct >= self.limits.max_daily_loss_pct:
                return (
                    RiskStatus.REJECTED,
                    f"Daily loss limit exceeded: {self.risk_state.daily_loss_pct:.2f}% >= {self.limits.max_daily_loss_pct:.2f}%",
                    {"daily_loss_pct": self.risk_state.daily_loss_pct}
                )
            
            # Get strategy-specific limits
            strategy_limits = self.strategy_limits.get(order.strategy_id, self.limits)
            
            # Check position value limit (safe division - already validated current_nav > 0)
            position_value_pct = order.position_value / order.current_nav
            if position_value_pct > strategy_limits.max_position_value_pct:
                return (
                    RiskStatus.REJECTED,
                    f"Position value limit exceeded: {position_value_pct:.2f}% > {strategy_limits.max_position_value_pct:.2f}%",
                    {"position_value_pct": position_value_pct}
                )
            
            # Check leverage limit
            if order.leverage > strategy_limits.max_leverage:
                return (
                    RiskStatus.REJECTED,
                    f"Leverage limit exceeded: {order.leverage:.1f}x > {strategy_limits.max_leverage:.1f}x",
                    {"leverage": order.leverage}
                )
            
            # Check per-trade VaR (safe division - already validated current_nav > 0)
            trade_risk = abs(order.quantity * order.price) / order.current_nav
            if trade_risk > strategy_limits.per_trade_var_pct:
                return (
                    RiskStatus.REJECTED,
                    f"Per-trade VaR limit exceeded: {trade_risk:.4f} > {strategy_limits.per_trade_var_pct:.4f}",
                    {"trade_risk": trade_risk}
                )
            
            # Check total exposure (safe division - already validated current_nav > 0)
            total_exposure = self.risk_state.total_exposure + order.position_value
            exposure_pct = total_exposure / order.current_nav
            if exposure_pct > 1.0:  # Can't exceed 100% of NAV
                return (
                    RiskStatus.REJECTED,
                    f"Total exposure limit exceeded: {exposure_pct:.2f}% > 100%",
                    {"exposure_pct": exposure_pct}
                )
            
            # All checks passed
            return (
                RiskStatus.APPROVED,
                "Order approved",
                {
                    "position_value_pct": position_value_pct,
                    "leverage": order.leverage,
                    "trade_risk": trade_risk,
                    "exposure_pct": exposure_pct
                }
            )
    
    def check_kill_switches(self, market_data: Dict) -> bool:
        """
        Check kill switch conditions and update state.
        
        Returns:
            True if kill switch should be activated
        """
        with self.state_lock:
            current_time = time.time()
            reasons = []
            
            # Check exchange outage
            if current_time - self.risk_state.last_data_update > self.kill_switch_thresholds.exchange_outage_seconds:
                reasons.append(f"Exchange outage: {current_time - self.risk_state.last_data_update:.1f}s since last update")
            
            # Check funding rate spike
            if abs(self.risk_state.funding_rate * 10000) > self.kill_switch_thresholds.funding_spike_bps:
                reasons.append(f"Funding rate spike: {self.risk_state.funding_rate * 10000:.1f} bps")
            
            # Check API latency
            if self.risk_state.api_latency_p99 > self.kill_switch_thresholds.api_latency_ms_p99:
                reasons.append(f"API latency spike: {self.risk_state.api_latency_p99:.1f}ms p99")
            
            # Check price divergence
            if self.risk_state.price_divergence_bps > self.kill_switch_thresholds.price_divergence_bps:
                reasons.append(f"Price divergence: {self.risk_state.price_divergence_bps:.1f} bps")
            
            # Check equity drop (from market_data if provided)
            if market_data:
                equity_drop = market_data.get("equity_drop_pct", 0)
                if equity_drop > self.kill_switch_thresholds.equity_drop_pct:
                    reasons.append(f"Equity drop: {equity_drop:.2f}%")
            
            if reasons:
                self.kill_switch_active = True
                self.kill_switch_reason = "; ".join(reasons)
                self.risk_state.kill_switch_active = True
                self.risk_state.kill_switch_reason = self.kill_switch_reason
                logger.critical(f"KILL SWITCH ACTIVATED: {self.kill_switch_reason}")
                return True
            
            return False
    
    def update_market_data(self, market_data: Dict):
        """Update market data and check kill switches."""
        with self.state_lock:
            self.risk_state.last_data_update = time.time()
            
            if "funding_rate" in market_data:
                self.risk_state.funding_rate = market_data["funding_rate"]
            
            if "api_latency_p99" in market_data:
                self.risk_state.api_latency_p99 = market_data["api_latency_p99"]
            
            if "price_divergence_bps" in market_data:
                self.risk_state.price_divergence_bps = market_data["price_divergence_bps"]
        
        # Check kill switches (will acquire lock internally)
        self.check_kill_switches(market_data)
    
    def update_portfolio_state(self, nav: float, positions: Dict, daily_loss_pct: float = None):
        """Update portfolio state and calculate drawdown."""
        with self.state_lock:
            # Input validation
            if nav < 0:
                logger.warning(f"Negative NAV received: {nav}, setting to 0")
                nav = 0.0
            
            # Update daily loss
            if daily_loss_pct is not None:
                self.risk_state.daily_loss_pct = max(0.0, daily_loss_pct)  # Ensure non-negative
            else:
                # Calculate from NAV if daily_start_nav is set
                if self.daily_start_nav and nav > 0 and self.daily_start_nav > 0:
                    self.risk_state.daily_loss_pct = max(0, (self.daily_start_nav - nav) / self.daily_start_nav)
                elif self.daily_start_nav and self.daily_start_nav <= 0:
                    logger.warning(f"Invalid daily_start_nav: {self.daily_start_nav}")
            
            # Update drawdown
            if nav > 0:
                if not self.risk_state.drawdown_peak_nav or nav > self.risk_state.drawdown_peak_nav:
                    # New peak
                    self.risk_state.drawdown_peak_nav = nav
                    self.risk_state.drawdown_start_time = None
                    self.risk_state.current_drawdown_pct = 0.0
                else:
                    # Calculate drawdown from peak (safe: drawdown_peak_nav > 0 and nav > 0)
                    if self.risk_state.drawdown_peak_nav > 0:
                        self.risk_state.current_drawdown_pct = (self.risk_state.drawdown_peak_nav - nav) / self.risk_state.drawdown_peak_nav
                        if self.risk_state.drawdown_start_time is None:
                            self.risk_state.drawdown_start_time = time.time()
            
            # Update positions
            self.risk_state.positions = positions or {}
            
            # Calculate total exposure
            self.risk_state.total_exposure = sum(
                pos.get("notional_value", 0) or pos.get("value", 0)
                for pos in (positions or {}).values()
            )
    
    def _is_in_drawdown_cooldown(self) -> bool:
        """Check if we're in drawdown cooldown period."""
        # Must be called within state_lock context
        if self.risk_state.current_drawdown_pct < self.limits.max_drawdown_pct:
            return False
        
        if self.risk_state.drawdown_start_time is None:
            return False
        
        cooldown_seconds = self.limits.drawdown_cooldown_hours * 3600
        elapsed = time.time() - self.risk_state.drawdown_start_time
        
        return elapsed < cooldown_seconds
    
    def activate_kill_switch(self, reason: str = "Manual activation"):
        """Manually activate kill switch."""
        with self.state_lock:
            self.kill_switch_active = True
            self.kill_switch_reason = reason
            self.risk_state.kill_switch_active = True
            self.risk_state.kill_switch_reason = reason
        logger.critical(f"KILL SWITCH ACTIVATED (manual): {reason}")
    
    def deactivate_kill_switch(self):
        """Deactivate kill switch."""
        with self.state_lock:
            self.kill_switch_active = False
            self.kill_switch_reason = None
            self.risk_state.kill_switch_active = False
            self.risk_state.kill_switch_reason = None
        logger.info("Kill switch deactivated")
    
    def get_risk_state(self) -> Dict:
        """Get current risk state snapshot."""
        with self.state_lock:
            in_cooldown = self._is_in_drawdown_cooldown()
            return {
                "limits": asdict(self.limits),
                "kill_switch_thresholds": asdict(self.kill_switch_thresholds),
                "risk_state": asdict(self.risk_state),
                "kill_switch_active": self.kill_switch_active,
                "kill_switch_reason": self.kill_switch_reason,
                "in_drawdown_cooldown": in_cooldown
            }
    
    def calculate_volatility_targeted_size(
        self,
        risk_budget: float,
        atr: float,
        realized_vol: float,
        horizon_days: float = 1.0,
        current_price: float = None
    ) -> float:
        """
        Calculate position size using volatility targeting.
        
        Position size = risk_budget / (ATR or realized_vol * √horizon)
        """
        # Input validation
        if risk_budget <= 0:
            logger.warning(f"Invalid risk_budget: {risk_budget}, returning 0")
            return 0.0
        
        if horizon_days <= 0:
            logger.warning(f"Invalid horizon_days: {horizon_days}, using 1.0")
            horizon_days = 1.0
        
        # Use ATR if available, else fall back to realized vol
        vol_metric = atr if atr > 0 else (realized_vol * current_price if current_price and realized_vol > 0 else 0)
        
        if vol_metric <= 0:
            logger.warning("No volatility metric available, using default position size")
            return risk_budget
        
        # Calculate size
        vol_adjusted_size = risk_budget / (vol_metric * (horizon_days ** 0.5))
        
        return vol_adjusted_size


# Flask API
app = Flask(__name__)
CORS(app)

# Global risk service instance
risk_service = RiskService()


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "risk_service"}), 200


@app.route('/risk/validate_order', methods=['POST'])
def validate_order():
    """Validate order against risk limits."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Input validation
        required_fields = ["strategy_id", "symbol", "side", "quantity", "price", "leverage", "current_nav", "position_value"]
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({"error": f"Missing required fields: {missing_fields}"}), 400
        
        # Validate types and ranges
        try:
            quantity = float(data["quantity"])
            price = float(data["price"])
            leverage = float(data["leverage"])
            current_nav = float(data["current_nav"])
            position_value = float(data["position_value"])
        except (ValueError, TypeError) as e:
            return jsonify({"error": f"Invalid numeric values: {e}"}), 400
        
        if quantity <= 0:
            return jsonify({"error": "Quantity must be > 0"}), 400
        if price <= 0:
            return jsonify({"error": "Price must be > 0"}), 400
        if leverage <= 0:
            return jsonify({"error": "Leverage must be > 0"}), 400
        if current_nav <= 0:
            return jsonify({"error": "Current NAV must be > 0"}), 400
        if position_value < 0:
            return jsonify({"error": "Position value must be >= 0"}), 400
        
        # Validate side
        if data["side"] not in ["buy", "sell", "short"]:
            return jsonify({"error": f"Invalid side: {data['side']}. Must be 'buy', 'sell', or 'short'"}), 400
        
        order = OrderRequest(
            strategy_id=data.get("strategy_id", "default"),
            symbol=data.get("symbol"),
            side=data.get("side"),
            quantity=quantity,
            price=price,
            leverage=leverage,
            current_nav=current_nav,
            position_value=position_value,
            timestamp=time.time()
        )
        
        status, reason, details = risk_service.validate_order(order)
        
        return jsonify({
            "status": status.value,
            "approved": status == RiskStatus.APPROVED,
            "reason": reason,
            "details": details
        }), 200 if status == RiskStatus.APPROVED else 403
        
    except Exception as e:
        logger.error(f"Error validating order: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/risk/limits', methods=['GET'])
def get_limits():
    """Get current risk state and limits."""
    try:
        return jsonify(risk_service.get_risk_state()), 200
    except Exception as e:
        logger.error(f"Error getting limits: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/risk/kill_switch', methods=['POST'])
def kill_switch():
    """Activate or deactivate kill switch."""
    try:
        data = request.json
        action = data.get("action", "activate")
        reason = data.get("reason", "Manual activation")
        
        if action == "activate":
            risk_service.activate_kill_switch(reason)
        elif action == "deactivate":
            risk_service.deactivate_kill_switch()
        else:
            return jsonify({"error": "Invalid action. Use 'activate' or 'deactivate'"}), 400
        
        return jsonify({
            "kill_switch_active": risk_service.kill_switch_active,
            "reason": risk_service.kill_switch_reason
        }), 200
        
    except Exception as e:
        logger.error(f"Error managing kill switch: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/risk/update_market_data', methods=['POST'])
def update_market_data():
    """Update market data and check kill switches."""
    try:
        data = request.json
        risk_service.update_market_data(data)
        return jsonify({"status": "updated"}), 200
    except Exception as e:
        logger.error(f"Error updating market data: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/risk/update_portfolio', methods=['POST'])
def update_portfolio():
    """Update portfolio state."""
    try:
        data = request.json
        nav = float(data.get("nav", 0))
        positions = data.get("positions", {})
        daily_loss_pct = data.get("daily_loss_pct")
        
        risk_service.update_portfolio_state(nav, positions, daily_loss_pct)
        return jsonify({"status": "updated"}), 200
    except Exception as e:
        logger.error(f"Error updating portfolio: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route('/risk/volatility_targeted_size', methods=['POST'])
def volatility_targeted_size():
    """Calculate volatility-targeted position size."""
    try:
        data = request.json
        risk_budget = float(data.get("risk_budget", 0))
        atr = float(data.get("atr", 0))
        realized_vol = float(data.get("realized_vol", 0))
        horizon_days = float(data.get("horizon_days", 1.0))
        current_price = data.get("current_price")
        
        size = risk_service.calculate_volatility_targeted_size(
            risk_budget, atr, realized_vol, horizon_days, current_price
        )
        
        return jsonify({"size": size}), 200
    except Exception as e:
        logger.error(f"Error calculating volatility size: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    # Port configuration: Railway sets PORT automatically for healthchecks
    # Prioritize PORT (Railway's port) over RISK_SERVICE_PORT when PORT is set
    # This ensures Railway's healthcheck can reach the service
    # Falls back to RISK_SERVICE_PORT if PORT not set (local development)
    import os
    
    def get_port_value(env_var):
        """Get port value from environment variable, stripping quotes if present."""
        value = os.getenv(env_var)
        if value:
            # Strip quotes if Railway added them (though they shouldn't be there)
            value = value.strip('"\'')
            return int(value) if value else None
        return None
    
    railway_port = get_port_value('PORT')
    risk_service_port = get_port_value('RISK_SERVICE_PORT')
    
    # Use Railway's PORT if set (for healthchecks), otherwise use RISK_SERVICE_PORT or default
    if railway_port:
        port = railway_port
        logger.info(f"Risk service starting on Railway PORT: {port} (PORT={os.getenv('PORT')}, RISK_SERVICE_PORT={os.getenv('RISK_SERVICE_PORT')})")
    elif risk_service_port:
        port = risk_service_port
        logger.info(f"Risk service starting on RISK_SERVICE_PORT: {port} (RISK_SERVICE_PORT={os.getenv('RISK_SERVICE_PORT')}, PORT={os.getenv('PORT')})")
    else:
        port = 8003
        logger.info(f"Risk service starting on default port: {port} (no PORT or RISK_SERVICE_PORT set)")
    
    app.run(host='0.0.0.0', port=port, debug=False)
