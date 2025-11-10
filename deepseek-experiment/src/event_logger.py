"""
Event Logger - Structured Event Logging for Explainability

Stores structured event logs with full context for post-mortem analysis.
Event log schema: {ts, venue, signal_vector, features, forecast, confidence,
risk_limits_snapshot, order_intent, fill, pnl_attrib}

Provides flight recorder-like logging for debugging and learning.
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import config

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Event types for structured logging."""

    MARKET_DATA = "market_data"
    SIGNAL_GENERATION = "signal_generation"
    REGIME_DETECTION = "regime_detection"
    RISK_CHECK = "risk_check"
    ORDER_INTENT = "order_intent"
    ORDER_FILL = "order_fill"
    POSITION_UPDATE = "position_update"
    STOP_LOSS_TRIGGER = "stop_loss_trigger"
    TAKE_PROFIT_TRIGGER = "take_profit_trigger"
    PORTFOLIO_UPDATE = "portfolio_update"
    ERROR = "error"


@dataclass
class EventLog:
    """Structured event log entry."""

    ts: str  # ISO timestamp
    event_type: str
    venue: Optional[str] = None
    signal_vector: Optional[Dict[str, float]] = None  # Technical indicators, features
    features: Optional[Dict[str, Any]] = None  # Raw features used
    forecast: Optional[Dict[str, Any]] = None  # LLM forecast/decision
    confidence: Optional[float] = None
    risk_limits_snapshot: Optional[Dict[str, Any]] = None
    order_intent: Optional[Dict[str, Any]] = None
    fill: Optional[Dict[str, Any]] = None
    pnl_attrib: Optional[Dict[str, float]] = None  # PnL attribution
    regime_state: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class EventLogger:
    """
    Structured event logger for trading bot explainability.

    Provides flight recorder-like logging with full context for post-mortem analysis.
    """

    def __init__(self, log_file: Optional[Path] = None, max_entries: int = 10000):
        self.log_file = log_file or config.DATA_DIR / "event_log.jsonl"
        self.max_entries = max_entries
        self.events: List[EventLog] = []

        # Ensure log directory exists
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Event Logger initialized: {self.log_file}")

    def log_event(
        self,
        event_type: EventType,
        venue: Optional[str] = None,
        signal_vector: Optional[Dict[str, float]] = None,
        features: Optional[Dict[str, Any]] = None,
        forecast: Optional[Dict[str, Any]] = None,
        confidence: Optional[float] = None,
        risk_limits_snapshot: Optional[Dict[str, Any]] = None,
        order_intent: Optional[Dict[str, Any]] = None,
        fill: Optional[Dict[str, Any]] = None,
        pnl_attrib: Optional[Dict[str, float]] = None,
        regime_state: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Log a structured event."""
        event = EventLog(
            ts=datetime.utcnow().isoformat() + "Z",
            event_type=event_type.value,
            venue=venue,
            signal_vector=signal_vector,
            features=features,
            forecast=forecast,
            confidence=confidence,
            risk_limits_snapshot=risk_limits_snapshot,
            order_intent=order_intent,
            fill=fill,
            pnl_attrib=pnl_attrib,
            regime_state=regime_state,
            error=error,
            metadata=metadata,
        )

        self.events.append(event)

        # Write to file (append mode for JSONL)
        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(asdict(event), default=str) + "\n")
        except Exception as e:
            logger.error(f"Error writing event log: {e}")

        # Keep only recent events in memory
        if len(self.events) > self.max_entries:
            self.events = self.events[-self.max_entries :]

    def log_market_data(self, market_data: Dict, venue: str = None):
        """Log market data event."""
        self.log_event(
            event_type=EventType.MARKET_DATA,
            venue=venue,
            signal_vector={
                "price": market_data.get("price", 0),
                "volume": market_data.get("volume", 0),
                "change_24h": market_data.get("change_24h", 0),
            },
            features=market_data.get("indicators", {}),
            metadata={"symbol": market_data.get("symbol")},
        )

    def log_signal_generation(
        self,
        signal_vector: Dict[str, float],
        forecast: Dict[str, Any],
        confidence: float,
        regime_state: Optional[Dict] = None,
    ):
        """Log signal generation event."""
        self.log_event(
            event_type=EventType.SIGNAL_GENERATION,
            signal_vector=signal_vector,
            forecast=forecast,
            confidence=confidence,
            regime_state=regime_state,
        )

    def log_risk_check(
        self, order_intent: Dict[str, Any], risk_limits: Dict[str, Any], approved: bool, reason: str = None
    ):
        """Log risk check event."""
        self.log_event(
            event_type=EventType.RISK_CHECK,
            order_intent=order_intent,
            risk_limits_snapshot=risk_limits,
            metadata={"approved": approved, "reason": reason},
        )

    def log_order_fill(
        self,
        order_intent: Dict[str, Any],
        fill: Dict[str, Any],
        pnl_attrib: Optional[Dict[str, float]] = None,
        venue: str = None,
    ):
        """Log order fill event."""
        self.log_event(
            event_type=EventType.ORDER_FILL, venue=venue, order_intent=order_intent, fill=fill, pnl_attrib=pnl_attrib
        )

    def log_regime_detection(self, regime_state: Dict[str, Any]):
        """Log regime detection event."""
        self.log_event(event_type=EventType.REGIME_DETECTION, regime_state=regime_state)

    def log_stop_loss_trigger(
        self, symbol: str, entry_price: float, stop_price: float, current_price: float, pnl: float
    ):
        """Log stop-loss trigger event."""
        self.log_event(
            event_type=EventType.STOP_LOSS_TRIGGER,
            order_intent={"symbol": symbol, "entry_price": entry_price, "stop_price": stop_price},
            fill={"price": current_price, "pnl": pnl},
            metadata={"reason": "stop_loss_triggered"},
        )

    def get_recent_events(self, event_type: Optional[EventType] = None, limit: int = 100) -> List[Dict]:
        """Get recent events, optionally filtered by type."""
        events = self.events

        if event_type:
            events = [e for e in events if e.event_type == event_type.value]

        return [asdict(e) for e in events[-limit:]]

    def export_events(self, output_file: Path, event_type: Optional[EventType] = None):
        """Export events to JSON file."""
        events = self.get_recent_events(event_type=event_type, limit=self.max_entries)

        try:
            with open(output_file, "w") as f:
                json.dump(events, f, indent=2, default=str)
            logger.info(f"Exported {len(events)} events to {output_file}")
        except Exception as e:
            logger.error(f"Error exporting events: {e}")
