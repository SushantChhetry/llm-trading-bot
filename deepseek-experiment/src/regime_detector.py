"""
Market Regime Detector

Detects market regimes (trending vs mean-reverting) using multiple indicators:
- ADX (Average Directional Index) for trend strength
- ATR-based volatility classification
- Price momentum vs moving average relationships
- Market structure analysis (higher highs/lower lows)
- Hurst exponent for trend vs mean-reversion
- Funding rate state for perpetual markets

Provides regime context to strategy controllers for adaptive trading.
"""

import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class RegimeType(Enum):
    """Market regime types."""

    TRENDING_BULLISH = "trending_bullish"
    TRENDING_BEARISH = "trending_bearish"
    MEAN_REVERTING = "mean_reverting"
    CHOPPY = "choppy"
    UNKNOWN = "unknown"


class VolatilityRegime(Enum):
    """Volatility regime classifications."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass
class RegimeState:
    """Current market regime state."""

    regime_type: RegimeType
    volatility_regime: VolatilityRegime
    confidence: float  # 0.0-1.0
    adx: float
    atr: float
    atr_pct: float  # ATR as % of price
    realized_vol: float
    trend_strength: float  # 0.0-1.0
    momentum: float  # Price momentum
    hurst_exponent: Optional[float] = None
    funding_rate: Optional[float] = None
    market_structure: str = ""  # "higher_highs", "lower_lows", "choppy", etc.


class RegimeDetector:
    """
    Detects market regimes using multiple technical indicators.

    Uses hysteresis and cooldowns to prevent thrashing between regime switches.
    """

    def __init__(
        self,
        adx_threshold: float = 25.0,  # ADX > 25 indicates strong trend
        atr_period: int = 14,
        volatility_percentiles: Tuple[float, float, float] = (0.33, 0.66, 0.9),
        hurst_window: int = 100,
        confirmation_bars: int = 3,  # Require N bars of confirmation
        cooldown_bars: int = 5,  # Cooldown after regime switch
    ):
        self.adx_threshold = adx_threshold
        self.atr_period = atr_period
        self.volatility_percentiles = volatility_percentiles
        self.hurst_window = hurst_window
        self.confirmation_bars = confirmation_bars
        self.cooldown_bars = cooldown_bars

        # Hysteresis state
        self.current_regime = RegimeType.UNKNOWN
        self.regime_confirmation_count = 0
        self.cooldown_remaining = 0
        self.regime_history: List[RegimeState] = []

        logger.info(
            f"Regime Detector initialized: adx_threshold={adx_threshold}, "
            f"confirmation_bars={confirmation_bars}, cooldown_bars={cooldown_bars}"
        )

    def detect_regime(
        self, prices: List[float], volumes: List[float] = None, funding_rate: float = None, timeframe_minutes: int = 5
    ) -> RegimeState:
        """
        Detect current market regime from price data.

        Args:
            prices: List of closing prices (most recent last)
            volumes: List of volumes (optional)
            funding_rate: Current funding rate (for perpetual markets)
            timeframe_minutes: Timeframe in minutes for calculations

        Returns:
            RegimeState with detected regime and confidence
        """
        if len(prices) < self.atr_period + 10:
            logger.warning(f"Insufficient price data: {len(prices)} < {self.atr_period + 10}")
            return RegimeState(
                regime_type=RegimeType.UNKNOWN,
                volatility_regime=VolatilityRegime.MEDIUM,
                confidence=0.0,
                adx=0.0,
                atr=0.0,
                atr_pct=0.0,
                realized_vol=0.0,
                trend_strength=0.0,
                momentum=0.0,
                funding_rate=funding_rate,
            )

        # Convert to pandas Series for easier calculations
        price_series = pd.Series(prices)

        # Validate data quality
        if price_series.isna().any() or np.isinf(price_series).any():
            logger.warning("Invalid price data (NaN/Inf) detected")
            return RegimeState(
                regime_type=RegimeType.UNKNOWN,
                volatility_regime=VolatilityRegime.MEDIUM,
                confidence=0.0,
                adx=0.0,
                atr=0.0,
                atr_pct=0.0,
                realized_vol=0.0,
                trend_strength=0.0,
                momentum=0.0,
                funding_rate=funding_rate,
            )

        # Calculate ADX (Average Directional Index)
        adx, trend_strength = self._calculate_adx(price_series)

        # Calculate ATR (Average True Range)
        atr, atr_pct = self._calculate_atr(price_series)

        # Calculate realized volatility (20-day rolling std)
        realized_vol = self._calculate_realized_volatility(price_series)

        # Classify volatility regime
        volatility_regime = self._classify_volatility(atr_pct, realized_vol)

        # Calculate momentum
        momentum = self._calculate_momentum(price_series)

        # Calculate Hurst exponent (trend vs mean-reversion)
        hurst = self._calculate_hurst(price_series[-self.hurst_window :]) if len(prices) >= self.hurst_window else None

        # Analyze market structure
        market_structure = self._analyze_market_structure(price_series)

        # Determine regime type
        regime_type = self._determine_regime_type(
            adx=adx, trend_strength=trend_strength, momentum=momentum, hurst=hurst, market_structure=market_structure
        )

        # Apply hysteresis (confirmation and cooldown)
        regime_type = self._apply_hysteresis(regime_type)

        # Calculate confidence
        confidence = self._calculate_confidence(
            adx=adx, trend_strength=trend_strength, volatility_regime=volatility_regime, hurst=hurst
        )

        regime_state = RegimeState(
            regime_type=regime_type,
            volatility_regime=volatility_regime,
            confidence=confidence,
            adx=adx,
            atr=atr,
            atr_pct=atr_pct,
            realized_vol=realized_vol,
            trend_strength=trend_strength,
            momentum=momentum,
            hurst_exponent=hurst,
            funding_rate=funding_rate,
            market_structure=market_structure,
        )

        # Store in history
        self.regime_history.append(regime_state)
        if len(self.regime_history) > 100:  # Keep last 100 states
            self.regime_history.pop(0)

        return regime_state

    def _calculate_adx(self, prices: pd.Series, period: int = 14) -> Tuple[float, float]:
        """Calculate ADX and trend strength."""
        try:
            # Calculate True Range
            high = prices  # Approximate high from close
            low = prices * 0.995  # Approximate low
            tr = high - low

            # Calculate +DM and -DM
            price_diff = prices.diff()
            plus_dm = price_diff.where(price_diff > 0, 0)
            minus_dm = -price_diff.where(price_diff < 0, 0)

            # Smooth TR, +DM, -DM
            atr = tr.rolling(window=period).mean().iloc[-1]
            plus_di = (plus_dm.rolling(window=period).mean() / atr * 100).iloc[-1]
            minus_di = (minus_dm.rolling(window=period).mean() / atr * 100).iloc[-1]

            # Calculate DX
            dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100 if (plus_di + minus_di) > 0 else 0

            # ADX is smoothed DX
            adx = dx  # Simplified - full ADX needs smoothing

            # Trend strength (0-1)
            trend_strength = min(1.0, adx / 50.0)  # Normalize to 0-1

            return float(adx), float(trend_strength)
        except Exception as e:
            logger.warning(f"Error calculating ADX: {e}")
            return 0.0, 0.0

    def _calculate_atr(self, prices: pd.Series, period: int = 14) -> Tuple[float, float]:
        """Calculate ATR and ATR as percentage of price."""
        try:
            # Simplified ATR calculation
            high = prices
            low = prices * 0.995
            tr = high - low
            atr = tr.rolling(window=period).mean().iloc[-1]

            current_price = prices.iloc[-1]
            atr_pct = (atr / current_price * 100) if current_price > 0 else 0

            return float(atr), float(atr_pct)
        except Exception as e:
            logger.warning(f"Error calculating ATR: {e}")
            return 0.0, 0.0

    def _calculate_realized_volatility(self, prices: pd.Series, window: int = 20) -> float:
        """Calculate realized volatility (rolling standard deviation of returns)."""
        try:
            returns = prices.pct_change().dropna()
            if len(returns) < window:
                window = len(returns)
            realized_vol = returns.tail(window).std() * np.sqrt(252)  # Annualized
            return float(realized_vol)
        except Exception as e:
            logger.warning(f"Error calculating realized volatility: {e}")
            return 0.0

    def _classify_volatility(self, atr_pct: float, realized_vol: float) -> VolatilityRegime:
        """Classify volatility regime."""
        # Use ATR% as primary indicator
        if atr_pct < self.volatility_percentiles[0]:
            return VolatilityRegime.LOW
        elif atr_pct < self.volatility_percentiles[1]:
            return VolatilityRegime.MEDIUM
        elif atr_pct < self.volatility_percentiles[2]:
            return VolatilityRegime.HIGH
        else:
            return VolatilityRegime.EXTREME

    def _calculate_momentum(self, prices: pd.Series, period: int = 10) -> float:
        """Calculate price momentum."""
        try:
            if len(prices) < period:
                return 0.0
            current = prices.iloc[-1]
            past = prices.iloc[-period]
            momentum = ((current - past) / past) * 100 if past > 0 else 0
            return float(momentum)
        except Exception as e:
            logger.warning(f"Error calculating momentum: {e}")
            return 0.0

    def _calculate_hurst(self, prices: pd.Series) -> Optional[float]:
        """
        Calculate Hurst exponent.
        H > 0.5: trending (persistent)
        H < 0.5: mean-reverting (anti-persistent)
        H ≈ 0.5: random walk
        """
        try:
            if len(prices) < 20:
                return None

            # Simplified Hurst calculation using R/S method
            returns = prices.pct_change().dropna()

            # Calculate R/S for different lags
            lags = range(2, min(20, len(returns) // 2))
            rs_values = []

            for lag in lags:
                # Rescale range
                mean_return = returns.mean()
                cumsum = (returns - mean_return).cumsum()
                R = cumsum.max() - cumsum.min()
                S = returns.std()
                if S > 0:
                    rs_values.append(R / S)

            if len(rs_values) < 2:
                return None

            # Fit log(R/S) vs log(lag) to get Hurst
            # Simplified: use average
            hurst = np.log(np.mean(rs_values)) / np.log(len(returns))
            hurst = max(0.0, min(1.0, hurst))  # Clamp to [0, 1]

            return float(hurst)
        except Exception as e:
            logger.warning(f"Error calculating Hurst: {e}")
            return None

    def _analyze_market_structure(self, prices: pd.Series, lookback: int = 20) -> str:
        """Analyze market structure (higher highs, lower lows, choppy)."""
        try:
            if len(prices) < lookback:
                lookback = len(prices)

            recent = prices.tail(lookback)

            # Count higher highs and lower lows
            higher_highs = 0
            lower_lows = 0

            for i in range(1, len(recent)):
                if recent.iloc[i] > recent.iloc[i - 1]:
                    higher_highs += 1
                elif recent.iloc[i] < recent.iloc[i - 1]:
                    lower_lows += 1

            hh_ratio = higher_highs / (higher_highs + lower_lows) if (higher_highs + lower_lows) > 0 else 0.5

            if hh_ratio > 0.6:
                return "higher_highs"
            elif hh_ratio < 0.4:
                return "lower_lows"
            else:
                return "choppy"
        except Exception as e:
            logger.warning(f"Error analyzing market structure: {e}")
            return "unknown"

    def _determine_regime_type(
        self, adx: float, trend_strength: float, momentum: float, hurst: Optional[float], market_structure: str
    ) -> RegimeType:
        """Determine regime type from indicators."""
        # Strong trend indicators
        strong_trend = adx > self.adx_threshold and trend_strength > 0.5

        # Direction indicators
        bullish = momentum > 0 and market_structure == "higher_highs"
        bearish = momentum < 0 and market_structure == "lower_lows"

        # Hurst-based confirmation
        if hurst is not None:
            if hurst > 0.6:  # Strong trending
                if bullish:
                    return RegimeType.TRENDING_BULLISH
                elif bearish:
                    return RegimeType.TRENDING_BEARISH
            elif hurst < 0.4:  # Mean-reverting
                return RegimeType.MEAN_REVERTING

        # ADX-based classification
        if strong_trend:
            if bullish:
                return RegimeType.TRENDING_BULLISH
            elif bearish:
                return RegimeType.TRENDING_BEARISH

        # Mean-reverting indicators
        if adx < 20 and abs(momentum) < 1.0:
            return RegimeType.MEAN_REVERTING

        # Choppy market
        if market_structure == "choppy" and adx < 25:
            return RegimeType.CHOPPY

        # Default
        return RegimeType.UNKNOWN

    def _apply_hysteresis(self, new_regime: RegimeType) -> RegimeType:
        """Apply hysteresis to prevent regime thrashing."""
        # Check cooldown
        if self.cooldown_remaining > 0:
            self.cooldown_remaining -= 1
            return self.current_regime

        # Check if regime changed
        if new_regime == self.current_regime:
            self.regime_confirmation_count = 0
            return self.current_regime

        # New regime detected - start confirmation
        self.regime_confirmation_count += 1

        if self.regime_confirmation_count >= self.confirmation_bars:
            # Regime switch confirmed
            old_regime = self.current_regime
            self.current_regime = new_regime
            self.regime_confirmation_count = 0
            self.cooldown_remaining = self.cooldown_bars

            logger.info(
                f"Regime switch confirmed: {old_regime.value} -> {new_regime.value} "
                f"(cooldown: {self.cooldown_bars} bars)"
            )

            return new_regime

        # Still confirming
        return self.current_regime

    def _calculate_confidence(
        self, adx: float, trend_strength: float, volatility_regime: VolatilityRegime, hurst: Optional[float]
    ) -> float:
        """Calculate confidence in regime detection (0.0-1.0)."""
        confidence = 0.5  # Base confidence

        # ADX contribution
        if adx > self.adx_threshold:
            confidence += 0.2

        # Trend strength contribution
        confidence += trend_strength * 0.2

        # Hurst contribution
        if hurst is not None:
            if hurst > 0.6 or hurst < 0.4:  # Clear signal
                confidence += 0.1

        # Volatility regime contribution
        if volatility_regime in [VolatilityRegime.LOW, VolatilityRegime.MEDIUM]:
            confidence += 0.1  # More reliable in lower vol

        return min(1.0, confidence)

    def get_regime_summary(self) -> Dict:
        """Get summary of current regime state."""
        if not self.regime_history:
            return {"regime": "unknown", "confidence": 0.0}

        latest = self.regime_history[-1]
        return {
            "regime": latest.regime_type.value,
            "volatility": latest.volatility_regime.value,
            "confidence": latest.confidence,
            "adx": latest.adx,
            "atr_pct": latest.atr_pct,
            "trend_strength": latest.trend_strength,
            "momentum": latest.momentum,
            "hurst": latest.hurst_exponent,
            "market_structure": latest.market_structure,
        }
