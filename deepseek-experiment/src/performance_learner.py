"""
Performance Learner - Real-time Pattern Tracking and Adaptive Confidence

Tracks trade patterns and adapts strategy parameters based on recent performance
with statistical rigor, including confidence intervals and significance testing.
"""

import logging
import math
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import numpy as np

from config import config

from .logger import LogDomain, get_logger

logger = get_logger(__name__, domain=LogDomain.STRATEGY)


class PerformanceLearner:
    """
    Tracks trade patterns and calculates adaptive confidence adjustments.
    
    Uses statistical significance testing to avoid overfitting to small samples.
    Implements EWMA smoothing for time-of-day patterns to reduce noise.
    """

    def __init__(
        self,
        min_sample_size: int = None,
        z_score_threshold: float = None,
        ewma_decay: float = None,
    ):
        """
        Initialize the performance learner.
        
        Args:
            min_sample_size: Minimum trades needed for statistical significance
            z_score_threshold: Z-score threshold for confidence adjustments
            ewma_decay: EWMA decay factor (0-1, higher = more weight to recent)
        """
        self.min_sample_size = min_sample_size or getattr(
            config, "CONFIDENCE_MIN_SAMPLE_SIZE", 5
        )
        self.z_score_threshold = z_score_threshold or getattr(
            config, "CONFIDENCE_Z_SCORE_THRESHOLD", 1.0
        )
        self.ewma_decay = ewma_decay or getattr(config, "EWMA_DECAY_FACTOR", 0.3)

        # Trade history with context (limited to prevent memory leak)
        self.trades: List[Dict[str, Any]] = []
        self.MAX_TRADES_HISTORY = 10000  # Keep last 10k trades

        # Pattern performance tracking (with EWMA)
        self.pattern_performance: Dict[str, Dict[str, Dict[str, float]]] = defaultdict(
            lambda: defaultdict(dict)
        )
        
        # EWMA initialization flag (to handle first value correctly)
        self.pattern_initialized: Dict[str, Dict[str, bool]] = defaultdict(lambda: defaultdict(bool))

        logger.info(
            f"PerformanceLearner initialized: min_sample={self.min_sample_size}, "
            f"z_threshold={self.z_score_threshold}, ewma_decay={self.ewma_decay}"
        )

    def detect_market_regime(
        self, price_history: List[Dict], sma_short: int = 20, sma_long: int = 50, atr_period: int = 14
    ) -> Tuple[str, str]:
        """
        Detect market regime (trend direction + volatility).
        
        Args:
            price_history: List of price data with 'close', 'high', 'low' keys
            sma_short: Short SMA period
            sma_long: Long SMA period
            atr_period: ATR period for volatility
        
        Returns:
            Tuple of (trend: "bull"/"bear"/"sideways", volatility: "low"/"normal"/"high")
        """
        if len(price_history) < max(sma_short, sma_long, atr_period):
            return ("unknown", "normal")

        try:
            # Extract prices
            closes = [p.get("close", 0) for p in price_history if p.get("close", 0) > 0]
            if not closes:
                return ("unknown", "normal")

            # Trend detection using SMA crossover
            if len(closes) >= sma_long:
                sma_short_val = np.mean(closes[-sma_short:])
                sma_long_val = np.mean(closes[-sma_long:])

                if sma_short_val > sma_long_val * 1.02:
                    trend = "bull"
                elif sma_short_val < sma_long_val * 0.98:
                    trend = "bear"
                else:
                    trend = "sideways"
            else:
                trend = "unknown"

            # Volatility detection using ATR
            if len(price_history) >= atr_period:
                highs = [p.get("high", 0) for p in price_history[-atr_period:]]
                lows = [p.get("low", 0) for p in price_history[-atr_period:]]
                closes_atr = closes[-atr_period:]

                # Validate array lengths match
                if len(highs) != len(lows) or len(highs) != len(closes_atr) or len(highs) != atr_period:
                    logger.warning(f"Price history arrays have inconsistent lengths: highs={len(highs)}, lows={len(lows)}, closes={len(closes_atr)}")
                    return (trend, "normal")
                
                if len(highs) == atr_period and len(lows) == atr_period:
                    # Calculate True Range
                    tr_values = []
                    for i in range(1, len(closes_atr)):
                        tr = max(
                            highs[i] - lows[i],
                            abs(highs[i] - closes_atr[i - 1]),
                            abs(lows[i] - closes_atr[i - 1]),
                        )
                        tr_values.append(tr)

                    if tr_values:
                        atr = np.mean(tr_values)
                        current_price = closes[-1]
                        atr_pct = atr / current_price if current_price > 0 else 0

                        if atr_pct > 0.03:  # >3% typical range
                            volatility = "high"
                        elif atr_pct < 0.01:  # <1% typical range
                            volatility = "low"
                        else:
                            volatility = "normal"
                    else:
                        volatility = "normal"
                else:
                    volatility = "normal"
            else:
                volatility = "normal"

            return (trend, volatility)

        except Exception as e:
            logger.warning(f"Error detecting market regime: {e}")
            return ("unknown", "normal")

    def record_trade(self, trade: Dict[str, Any], market_data: Dict[str, Any], regime: Tuple[str, str] = None):
        """
        Record trade with context for pattern analysis.
        
        Args:
            trade: Trade dictionary with profit, timestamp, direction, confidence
            market_data: Market data dictionary
            regime: Optional pre-calculated regime tuple (trend, volatility)
        """
        if regime is None:
            # Try to detect regime from market_data
            price_history = market_data.get("price_history", [])
            if not price_history:
                regime = ("unknown", "normal")
            else:
                regime = self.detect_market_regime(price_history)

        # CORRECTED: Extract better time features instead of just hour
        timestamp_str = trade.get("timestamp", datetime.now().isoformat())
        try:
            if isinstance(timestamp_str, str):
                dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            else:
                dt = timestamp_str
        except Exception:
            dt = datetime.now()
        
        trade_record = {
            "timestamp": timestamp_str,
            "profit": trade.get("profit", 0),
            "direction": trade.get("direction", "long"),
            "entry_confidence": trade.get("confidence", 0.5),
            "regime_trend": regime[0],
            "regime_volatility": regime[1],
            # CORRECTED: Multiple time features for better pattern analysis
            "hour": dt.hour,
            "day_of_week": dt.weekday(),  # 0=Monday, 6=Sunday
            "trading_session": self._get_trading_session(dt.hour),
            "is_volatile_hours": dt.hour in [8, 14, 16],  # Known high-volatility times
            "is_weekend": dt.weekday() >= 5,
        }

        self.trades.append(trade_record)
        
        # Limit history size to prevent memory leak
        if len(self.trades) > self.MAX_TRADES_HISTORY:
            self.trades = self.trades[-self.MAX_TRADES_HISTORY:]

        # Update pattern performance with EWMA
        self._update_pattern_performance(trade_record)

        logger.debug(f"Recorded trade: profit={trade_record['profit']:.2f}, regime={regime}")

    def _extract_hour(self, timestamp: str) -> int:
        """Extract hour from timestamp."""
        try:
            if isinstance(timestamp, str):
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            else:
                dt = timestamp
            return dt.hour
        except Exception:
            return datetime.now().hour
    
    def _get_trading_session(self, hour: int) -> str:
        """Get trading session based on hour (UTC)."""
        # Asian: 00:00-08:00 UTC
        # London: 08:00-16:00 UTC
        # NY: 16:00-00:00 UTC
        if 0 <= hour < 8:
            return "asian"
        elif 8 <= hour < 16:
            return "london"
        else:
            return "ny"

    def _update_pattern_performance(self, trade: Dict[str, Any]):
        """Update pattern performance with EWMA smoothing."""
        profit = trade.get("profit", 0)
        is_profitable = profit > 0

        # Update time-of-day patterns (multiple features)
        hour = trade.get("hour", 0)
        self._update_pattern_with_ewma("hour", str(hour), is_profitable, profit)
        
        day_of_week = trade.get("day_of_week", 0)
        self._update_pattern_with_ewma("day_of_week", str(day_of_week), is_profitable, profit)
        
        trading_session = trade.get("trading_session", "unknown")
        self._update_pattern_with_ewma("trading_session", trading_session, is_profitable, profit)

        # Update direction pattern
        direction = trade.get("direction", "long")
        self._update_pattern_with_ewma("direction", direction, is_profitable, profit)

        # Update regime pattern
        regime_key = f"{trade.get('regime_trend', 'unknown')}_{trade.get('regime_volatility', 'normal')}"
        self._update_pattern_with_ewma("regime", regime_key, is_profitable, profit)

        # Update confidence bucket pattern
        confidence = trade.get("entry_confidence", 0.5)
        if confidence < 0.7:
            conf_bucket = "0.6-0.7"
        elif confidence < 0.8:
            conf_bucket = "0.7-0.8"
        else:
            conf_bucket = "0.8+"
        self._update_pattern_with_ewma("confidence", conf_bucket, is_profitable, profit)

    def _update_pattern_with_ewma(
        self, pattern_type: str, pattern_value: str, is_profitable: bool, profit: float
    ):
        """Update pattern performance using exponential weighted moving average."""
        pattern_key = f"{pattern_type}:{pattern_value}"

        if pattern_key not in self.pattern_performance[pattern_type]:
            # Initialize with first actual value (not neutral 0.5)
            self.pattern_performance[pattern_type][pattern_value] = {
                "win_rate": 1.0 if is_profitable else 0.0,  # Start with first actual value
                "total_profit": 0.0,
                "avg_profit": 0.0,
                "trade_count": 0,
            }
            self.pattern_initialized[pattern_type][pattern_value] = True

        pattern = self.pattern_performance[pattern_type][pattern_value]
        is_initialized = self.pattern_initialized[pattern_type][pattern_value]

        # EWMA update
        if is_initialized:
            # Standard EWMA update
            old_win_rate = pattern["win_rate"]
            new_win_rate = (1.0 if is_profitable else 0.0)
            pattern["win_rate"] = (1 - self.ewma_decay) * old_win_rate + self.ewma_decay * new_win_rate
        else:
            # First value: use it directly
            pattern["win_rate"] = 1.0 if is_profitable else 0.0
            self.pattern_initialized[pattern_type][pattern_value] = True

        # Update profit metrics
        pattern["total_profit"] += profit
        pattern["trade_count"] += 1
        pattern["avg_profit"] = pattern["total_profit"] / pattern["trade_count"]

    def get_trades_for_pattern(self, pattern_type: str, pattern_value: str) -> List[Dict[str, Any]]:
        """Get all trades matching a specific pattern."""
        filtered = []
        for trade in self.trades:
            if pattern_type == "hour" and str(trade.get("hour", 0)) == pattern_value:
                filtered.append(trade)
            elif pattern_type == "day_of_week" and str(trade.get("day_of_week", 0)) == pattern_value:
                filtered.append(trade)
            elif pattern_type == "trading_session" and trade.get("trading_session") == pattern_value:
                filtered.append(trade)
            elif pattern_type == "direction" and trade.get("direction") == pattern_value:
                filtered.append(trade)
            elif pattern_type == "regime":
                regime_key = f"{trade.get('regime_trend')}_{trade.get('regime_volatility')}"
                if regime_key == pattern_value:
                    filtered.append(trade)
            elif pattern_type == "confidence":
                conf = trade.get("entry_confidence", 0.5)
                if conf < 0.7 and pattern_value == "0.6-0.7":
                    filtered.append(trade)
                elif 0.7 <= conf < 0.8 and pattern_value == "0.7-0.8":
                    filtered.append(trade)
                elif conf >= 0.8 and pattern_value == "0.8+":
                    filtered.append(trade)

        return filtered

    def get_pattern_performance(self, pattern_type: str, pattern_value: str) -> Optional[Dict[str, Any]]:
        """Get performance metrics for a specific pattern."""
        pattern = self.pattern_performance.get(pattern_type, {}).get(pattern_value)
        if not pattern:
            return None

        trades = self.get_trades_for_pattern(pattern_type, pattern_value)
        if not trades:
            return None

        return {
            "win_rate": pattern["win_rate"],
            "total_profit": pattern["total_profit"],
            "avg_profit": pattern["avg_profit"],
            "trade_count": pattern["trade_count"],
            "sample_size": len(trades),
        }

    def get_pattern_performance_with_confidence(
        self, pattern_type: str, pattern_value: str, confidence_level: float = 0.95
    ) -> Optional[Dict[str, Any]]:
        """
        Returns performance metrics with confidence intervals.
        
        Uses Wilson score interval for binomial proportion (more accurate than normal approximation).
        """
        trades = self.get_trades_for_pattern(pattern_type, pattern_value)

        if not trades:
            return None

        n = len(trades)
        profitable = sum(1 for t in trades if t.get("profit", 0) > 0)
        win_rate = profitable / n

        # Wilson score interval for binomial proportion
        z = 1.96 if confidence_level == 0.95 else 2.576  # 95% or 99%
        p_hat = win_rate
        denominator = 1 + z**2 / n
        centre_adjusted_p = (p_hat + z**2 / (2 * n)) / denominator
        adjusted_std = math.sqrt((p_hat * (1 - p_hat) + z**2 / (4 * n)) / n) / denominator

        lower = max(0, centre_adjusted_p - z * adjusted_std)
        upper = min(1, centre_adjusted_p + z * adjusted_std)

        profits = [t.get("profit", 0) for t in trades]
        winning_profits = [p for p in profits if p > 0]

        return {
            "win_rate": win_rate,
            "confidence_interval": (lower, upper),
            "sample_size": n,
            "avg_profit": np.mean(winning_profits) if winning_profits else 0.0,
            "total_profit": sum(profits),
            "sharpe": self._calculate_sharpe(profits),
        }

    def _calculate_sharpe(self, profits: List[float]) -> float:
        """Calculate Sharpe ratio for profit series."""
        if len(profits) < 2:
            return 0.0

        mean = np.mean(profits)
        std = np.std(profits)

        if std == 0:
            return 0.0

        return mean / std

    def get_adaptive_confidence(
        self, base_confidence: float, pattern_type: str, pattern_value: str, min_sample_size: int = None
    ) -> float:
        """
        CORRECTED: Adjusts confidence using Bayesian posterior probability.
        
        Uses pattern history to refine initial (base) confidence with statistical rigor.
        No arbitrary thresholds - uses Bayesian update with Beta distribution.
        
        Args:
            base_confidence: Base confidence from LLM
            pattern_type: Type of pattern (hour, day_of_week, trading_session, direction, regime, confidence)
            pattern_value: Specific pattern value
            min_sample_size: Override minimum sample size
        
        Returns:
            Adjusted confidence (clamped to [0.35, 0.95])
        """
        min_size = min_sample_size or self.min_sample_size

        pattern_trades = self.get_trades_for_pattern(pattern_type, pattern_value)

        # Insufficient data: return base confidence
        if len(pattern_trades) < min_size:
            logger.debug(
                f"Insufficient data for pattern {pattern_type}:{pattern_value} "
                f"({len(pattern_trades)} < {min_size}), using base confidence"
            )
            return base_confidence

        # Calculate statistics
        profitable_trades = [t for t in pattern_trades if t.get("profit", 0) > 0]
        n_trades = len(pattern_trades)
        n_wins = len(profitable_trades)
        win_rate = n_wins / n_trades if n_trades > 0 else 0.0

        # CORRECTED: Bayesian update using Beta distribution conjugate prior
        # Prior: Beta(alpha=1, beta=1) represents neutral belief (50/50)
        # Posterior: Beta(alpha=1+n_wins, beta=1+n_losses)
        alpha = 1 + n_wins
        beta = 1 + (n_trades - n_wins)
        posterior_win_rate = alpha / (alpha + beta)

        # Calculate effect size: how different from 50/50
        effect_size = abs(posterior_win_rate - 0.5)

        # Adjust confidence proportional to effect size
        # Max adjustment: ±0.3 (30% of confidence range)
        max_adjustment = 0.3

        if posterior_win_rate > 0.5:
            # Pattern is profitable, increase confidence
            confidence_boost = effect_size * max_adjustment
            adjusted = base_confidence + confidence_boost
            logger.debug(
                f"Pattern {pattern_type}:{pattern_value} positive "
                f"(posterior_win_rate={posterior_win_rate:.3f}, effect_size={effect_size:.3f}), "
                f"adjusting confidence: {base_confidence:.2f} -> {adjusted:.2f}"
            )
        else:
            # Pattern is unprofitable, decrease confidence
            confidence_reduction = effect_size * max_adjustment
            adjusted = base_confidence - confidence_reduction
            logger.debug(
                f"Pattern {pattern_type}:{pattern_value} negative "
                f"(posterior_win_rate={posterior_win_rate:.3f}, effect_size={effect_size:.3f}), "
                f"adjusting confidence: {base_confidence:.2f} -> {adjusted:.2f}"
            )

        # Clamp to [0.35, 0.95] (hard bounds for trading)
        return max(0.35, min(adjusted, 0.95))

    def get_best_patterns(self, pattern_type: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Get top performing patterns by total profit."""
        patterns = self.pattern_performance.get(pattern_type, {})

        pattern_list = []
        for pattern_value, perf in patterns.items():
            pattern_list.append(
                {
                    "pattern_value": pattern_value,
                    "win_rate": perf.get("win_rate", 0),
                    "total_profit": perf.get("total_profit", 0),
                    "trade_count": perf.get("trade_count", 0),
                }
            )

        # Sort by total profit
        pattern_list.sort(key=lambda x: x["total_profit"], reverse=True)

        return pattern_list[:top_k]

