"""
Regime Controller - Meta-Policy State Machine

A small, interpretable meta-policy that re-weights strategies based on market regime
rather than flipping a single model on/off. Uses hysteresis and cooldowns to prevent thrashing.

Strategies:
- Momentum (trending markets)
- Mean Reversion (choppy/mean-reverting markets)
- Breakout (volatile markets)
- Carry (funding-based strategies)
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from .logger import LogDomain, get_logger
from .regime_detector import RegimeDetector, RegimeState, RegimeType, VolatilityRegime

logger = get_logger(__name__, domain=LogDomain.REGIME)


class StrategyType(Enum):
    """Strategy types."""

    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    BREAKOUT = "breakout"
    CARRY = "carry"
    NEUTRAL = "neutral"


@dataclass
class StrategyWeight:
    """Strategy weight configuration."""

    strategy: StrategyType
    weight: float  # 0.0-1.0, sum should be 1.0
    min_weight: float = 0.0
    max_weight: float = 1.0


@dataclass
class StrategyAllocation:
    """Current strategy allocation."""

    weights: Dict[StrategyType, float]
    total_capital: float
    allocations: Dict[StrategyType, float]  # Capital allocated to each strategy


class RegimeController:
    """
    Meta-policy controller that re-weights strategies based on market regime.

    Uses a state machine with hysteresis to prevent thrashing between regime switches.
    """

    def __init__(self, regime_detector: RegimeDetector, base_allocation: Dict[StrategyType, float] = None):
        self.regime_detector = regime_detector

        # Base allocation (equal weights by default)
        if base_allocation is None:
            base_allocation = {
                StrategyType.MOMENTUM: 0.25,
                StrategyType.MEAN_REVERSION: 0.25,
                StrategyType.BREAKOUT: 0.25,
                StrategyType.CARRY: 0.25,
            }
        self.base_allocation = base_allocation

        # Strategy weights per regime
        self.regime_weights = self._initialize_regime_weights()

        # Current allocation
        self.current_allocation: Optional[StrategyAllocation] = None

        logger.info(f"Regime Controller initialized with base allocation: {base_allocation}")

    def _initialize_regime_weights(self) -> Dict[RegimeType, Dict[StrategyType, float]]:
        """Initialize strategy weights for each regime."""
        return {
            RegimeType.TRENDING_BULLISH: {
                StrategyType.MOMENTUM: 0.60,  # High weight for trending
                StrategyType.BREAKOUT: 0.20,
                StrategyType.MEAN_REVERSION: 0.10,
                StrategyType.CARRY: 0.10,
            },
            RegimeType.TRENDING_BEARISH: {
                StrategyType.MOMENTUM: 0.60,  # High weight for trending (short)
                StrategyType.BREAKOUT: 0.20,
                StrategyType.MEAN_REVERSION: 0.10,
                StrategyType.CARRY: 0.10,
            },
            RegimeType.MEAN_REVERTING: {
                StrategyType.MEAN_REVERSION: 0.60,  # High weight for mean reversion
                StrategyType.MOMENTUM: 0.15,
                StrategyType.BREAKOUT: 0.15,
                StrategyType.CARRY: 0.10,
            },
            RegimeType.CHOPPY: {
                StrategyType.MEAN_REVERSION: 0.40,
                StrategyType.BREAKOUT: 0.30,  # Breakouts can work in choppy markets
                StrategyType.MOMENTUM: 0.15,
                StrategyType.CARRY: 0.15,
            },
            RegimeType.UNKNOWN: {
                # Default to equal weights when regime is unknown
                StrategyType.MOMENTUM: 0.25,
                StrategyType.MEAN_REVERSION: 0.25,
                StrategyType.BREAKOUT: 0.25,
                StrategyType.CARRY: 0.25,
            },
        }

    def update_allocation(self, total_capital: float, regime_state: Optional[RegimeState] = None) -> StrategyAllocation:
        """
        Update strategy allocation based on current regime.

        Args:
            total_capital: Total capital available
            regime_state: Current regime state (if None, will detect from history)

        Returns:
            StrategyAllocation with updated weights and capital allocations
        """
        # Get current regime
        if regime_state is None:
            if not self.regime_detector.regime_history:
                # Use base allocation if no regime history
                weights = self.base_allocation.copy()
            else:
                latest_regime = self.regime_detector.regime_history[-1]
                regime_type = latest_regime.regime_type
                weights = self.regime_weights.get(regime_type, self.base_allocation).copy()
        else:
            regime_type = regime_state.regime_type
            weights = self.regime_weights.get(regime_type, self.base_allocation).copy()

        # Normalize weights to sum to 1.0
        total_weight = sum(weights.values())
        if total_weight > 0:
            weights = {k: v / total_weight for k, v in weights.items()}
        else:
            weights = self.base_allocation.copy()

        # Calculate capital allocations
        allocations = {strategy: total_capital * weight for strategy, weight in weights.items()}

        # Create allocation object
        self.current_allocation = StrategyAllocation(
            weights=weights, total_capital=total_capital, allocations=allocations
        )

        logger.debug(
            f"Strategy allocation updated: regime={regime_type.value if regime_state else 'unknown'}, "
            f"weights={weights}, total_capital={total_capital:.2f}"
        )

        return self.current_allocation

    def get_strategy_weights(self) -> Dict[StrategyType, float]:
        """Get current strategy weights."""
        if self.current_allocation:
            return self.current_allocation.weights.copy()
        return self.base_allocation.copy()

    def get_capital_allocation(self, strategy: StrategyType) -> float:
        """Get capital allocated to a specific strategy."""
        if self.current_allocation:
            return self.current_allocation.allocations.get(strategy, 0.0)
        return self.base_allocation.get(strategy, 0.0) * (
            self.current_allocation.total_capital if self.current_allocation else 0.0
        )

    def should_activate_strategy(self, strategy: StrategyType, regime_state: Optional[RegimeState] = None) -> bool:
        """
        Determine if a strategy should be activated based on regime.

        Args:
            strategy: Strategy to check
            regime_state: Current regime state

        Returns:
            True if strategy should be active
        """
        if regime_state is None:
            if not self.regime_detector.regime_history:
                return True  # Activate all by default if no regime info
            regime_state = self.regime_detector.regime_history[-1]

        regime_type = regime_state.regime_type
        weights = self.regime_weights.get(regime_type, self.base_allocation)

        # Strategy is active if weight > 0
        return weights.get(strategy, 0.0) > 0.0

    def get_regime_guidance(self, regime_state: Optional[RegimeState] = None) -> Dict:
        """
        Get trading guidance based on current regime.

        Returns:
            Dictionary with regime-based guidance for LLM/system
        """
        if regime_state is None:
            if not self.regime_detector.regime_history:
                return {
                    "regime": "unknown",
                    "guidance": "No regime information available. Use conservative position sizing.",
                    "recommended_strategies": ["neutral"],
                    "position_sizing_multiplier": 0.5,  # Conservative
                }
            regime_state = self.regime_detector.regime_history[-1]

        regime_type = regime_state.regime_type
        volatility = regime_state.volatility_regime

        # Get active strategies
        active_strategies = [
            strat.value
            for strat, weight in self.get_strategy_weights().items()
            if weight > 0.1  # Only strategies with >10% allocation
        ]

        # Generate guidance
        guidance_map = {
            RegimeType.TRENDING_BULLISH: {
                "guidance": "Strong uptrend detected. Focus on momentum strategies. Consider higher leverage for long positions.",
                "recommended_strategies": ["momentum", "breakout"],
                "position_sizing_multiplier": 1.0,
                "leverage_multiplier": 1.2,  # Slightly higher leverage in trends
            },
            RegimeType.TRENDING_BEARISH: {
                "guidance": "Strong downtrend detected. Focus on momentum strategies (short). Reduce long exposure.",
                "recommended_strategies": ["momentum", "breakout"],
                "position_sizing_multiplier": 0.8,  # Slightly reduced
                "leverage_multiplier": 1.0,
            },
            RegimeType.MEAN_REVERTING: {
                "guidance": "Mean-reverting market. Focus on mean reversion strategies. Use tighter stops.",
                "recommended_strategies": ["mean_reversion"],
                "position_sizing_multiplier": 0.7,  # Reduced size
                "leverage_multiplier": 0.8,  # Lower leverage
            },
            RegimeType.CHOPPY: {
                "guidance": "Choppy market conditions. Use mean reversion and breakout strategies. Reduce position sizes.",
                "recommended_strategies": ["mean_reversion", "breakout"],
                "position_sizing_multiplier": 0.6,  # Significantly reduced
                "leverage_multiplier": 0.7,  # Lower leverage
            },
            RegimeType.UNKNOWN: {
                "guidance": "Regime unclear. Use conservative position sizing and diversified strategies.",
                "recommended_strategies": ["neutral"],
                "position_sizing_multiplier": 0.5,  # Very conservative
                "leverage_multiplier": 0.8,
            },
        }

        guidance = guidance_map.get(regime_type, guidance_map[RegimeType.UNKNOWN])

        # Adjust for volatility
        if volatility == VolatilityRegime.HIGH or volatility == VolatilityRegime.EXTREME:
            guidance["position_sizing_multiplier"] *= 0.7  # Reduce size in high vol
            guidance["leverage_multiplier"] *= 0.8

        return {
            "regime": regime_type.value,
            "volatility": volatility.value,
            "confidence": regime_state.confidence,
            "active_strategies": active_strategies,
            **guidance,
        }
