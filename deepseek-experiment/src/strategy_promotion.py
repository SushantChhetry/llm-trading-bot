"""
Strategy Promotion Ladder - Research → Paper → Canary → Prod

Implements a strict promotion ladder with auto-deallocation:
- Research: Strategy development and testing
- Paper: Paper trading for 30-45 days
- Canary: Limited production (≤2% NAV) with performance monitoring
- Prod: Full production with gradual ramp-up

Auto-deallocation if canary underperforms its backtest IQR.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from config import config

logger = logging.getLogger(__name__)


class StrategyStage(Enum):
    """Strategy promotion stages."""

    RESEARCH = "research"
    PAPER = "paper"
    CANARY = "canary"
    PRODUCTION = "production"
    DEALLOCATED = "deallocated"


@dataclass
class StrategyMetrics:
    """Strategy performance metrics."""

    sharpe_ratio: float
    total_return_pct: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    days_active: int


@dataclass
class PromotionCriteria:
    """Criteria for stage promotion."""

    min_sharpe_ratio: float = 1.0
    min_days_paper: int = 30
    max_days_paper: int = 45
    max_canary_nav_pct: float = 0.02  # 2% of NAV
    min_backtest_sharpe: float = 1.0
    max_drawdown_vs_backtest: float = 1.5  # Max 1.5x backtest drawdown
    min_win_rate: float = 0.45
    min_profit_factor: float = 1.2


class StrategyPromotion:
    """
    Manages strategy promotion ladder with auto-deallocation.
    """

    def __init__(
        self,
        strategy_id: str,
        backtest_metrics: Optional[StrategyMetrics] = None,
        promotion_file: Optional[Path] = None,
    ):
        self.strategy_id = strategy_id
        self.backtest_metrics = backtest_metrics
        self.promotion_file = promotion_file or config.DATA_DIR / f"strategy_{strategy_id}_promotion.json"

        # Load promotion state
        self.state = self._load_state()

        # Promotion criteria
        self.criteria = PromotionCriteria()

        logger.info(f"Strategy Promotion initialized: {strategy_id}, stage={self.state.get('stage', 'research')}")

    def _load_state(self) -> Dict:
        """Load promotion state from file."""
        if self.promotion_file.exists():
            try:
                with open(self.promotion_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error loading promotion state: {e}")

        # Default state
        return {
            "stage": "research",
            "entered_stage_date": datetime.utcnow().isoformat(),
            "days_in_stage": 0,
            "canary_allocation_pct": 0.0,
            "production_allocation_pct": 0.0,
            "deallocation_reason": None,
            "performance_history": [],
        }

    def _save_state(self):
        """Save promotion state to file."""
        try:
            with open(self.promotion_file, "w") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving promotion state: {e}")

    def update_performance(self, metrics: StrategyMetrics):
        """Update strategy performance metrics."""
        # Record performance snapshot
        snapshot = {
            "timestamp": datetime.utcnow().isoformat(),
            "stage": self.state["stage"],
            "sharpe_ratio": metrics.sharpe_ratio,
            "total_return_pct": metrics.total_return_pct,
            "max_drawdown": metrics.max_drawdown,
            "win_rate": metrics.win_rate,
            "profit_factor": metrics.profit_factor,
            "total_trades": metrics.total_trades,
        }

        self.state["performance_history"].append(snapshot)

        # Keep only last 100 snapshots
        if len(self.state["performance_history"]) > 100:
            self.state["performance_history"] = self.state["performance_history"][-100:]

        # Update days in stage
        entered_date = datetime.fromisoformat(self.state["entered_stage_date"])
        self.state["days_in_stage"] = (datetime.utcnow() - entered_date).days

        # Check for promotion/deallocation
        self._check_promotion(metrics)
        self._check_deallocation(metrics)

        self._save_state()

    def _check_promotion(self, metrics: StrategyMetrics):
        """Check if strategy should be promoted to next stage."""
        current_stage = StrategyStage(self.state["stage"])
        days_in_stage = self.state["days_in_stage"]

        # Research → Paper: Always allowed (manual promotion)
        if current_stage == StrategyStage.RESEARCH:
            return  # Manual promotion required

        # Paper → Canary: After min_days_paper with good performance
        if current_stage == StrategyStage.PAPER:
            if days_in_stage >= self.criteria.min_days_paper:
                if (
                    metrics.sharpe_ratio >= self.criteria.min_sharpe_ratio
                    and metrics.win_rate >= self.criteria.min_win_rate
                    and metrics.profit_factor >= self.criteria.min_profit_factor
                ):

                    self._promote_to_stage(StrategyStage.CANARY)
                    logger.info(f"Strategy {self.strategy_id} promoted to CANARY")

        # Canary → Production: After 30 days with stable performance
        elif current_stage == StrategyStage.CANARY:
            if days_in_stage >= 30:
                # Check if performance matches backtest expectations
                if self.backtest_metrics:
                    backtest_sharpe = self.backtest_metrics.sharpe_ratio
                    if (
                        metrics.sharpe_ratio >= backtest_sharpe * 0.8  # At least 80% of backtest
                        and metrics.max_drawdown
                        <= self.backtest_metrics.max_drawdown * self.criteria.max_drawdown_vs_backtest
                    ):

                        self._promote_to_stage(StrategyStage.PRODUCTION)
                        logger.info(f"Strategy {self.strategy_id} promoted to PRODUCTION")

    def _check_deallocation(self, metrics: StrategyMetrics):
        """Check if strategy should be deallocated."""
        current_stage = StrategyStage(self.state["stage"])

        # Canary: Auto-deallocate if underperforming backtest IQR
        if current_stage == StrategyStage.CANARY:
            if self.backtest_metrics:
                # Calculate backtest IQR (Interquartile Range)
                # Simplified: use backtest metrics as baseline
                backtest_sharpe = self.backtest_metrics.sharpe_ratio
                backtest_drawdown = self.backtest_metrics.max_drawdown

                # Check if current performance is significantly worse
                sharpe_ratio = metrics.sharpe_ratio / backtest_sharpe if backtest_sharpe > 0 else 0
                drawdown_ratio = metrics.max_drawdown / backtest_drawdown if backtest_drawdown > 0 else float("inf")

                # Deallocate if Sharpe < 50% of backtest OR drawdown > 2x backtest
                if sharpe_ratio < 0.5 or drawdown_ratio > 2.0:
                    reason = (
                        f"Underperforming backtest: Sharpe ratio {sharpe_ratio:.2f}x, drawdown {drawdown_ratio:.2f}x"
                    )
                    self._deallocate(reason)
                    logger.warning(f"Strategy {self.strategy_id} deallocated: {reason}")

        # Production: Deallocate if critical metrics fail
        elif current_stage == StrategyStage.PRODUCTION:
            # Deallocate if Sharpe drops below 0.5 or drawdown exceeds 15%
            if metrics.sharpe_ratio < 0.5 or metrics.max_drawdown > 0.15:
                reason = (
                    f"Performance degradation: Sharpe={metrics.sharpe_ratio:.2f}, Drawdown={metrics.max_drawdown:.2%}"
                )
                self._deallocate(reason)
                logger.warning(f"Strategy {self.strategy_id} deallocated: {reason}")

    def _promote_to_stage(self, new_stage: StrategyStage):
        """Promote strategy to new stage."""
        self.state["stage"] = new_stage.value
        self.state["entered_stage_date"] = datetime.utcnow().isoformat()
        self.state["days_in_stage"] = 0

        # Set allocation limits
        if new_stage == StrategyStage.CANARY:
            self.state["canary_allocation_pct"] = self.criteria.max_canary_nav_pct
        elif new_stage == StrategyStage.PRODUCTION:
            self.state["production_allocation_pct"] = 0.05  # Start at 5%, ramp up gradually

    def _deallocate(self, reason: str):
        """Deallocate strategy."""
        self.state["stage"] = StrategyStage.DEALLOCATED.value
        self.state["deallocation_reason"] = reason
        self.state["canary_allocation_pct"] = 0.0
        self.state["production_allocation_pct"] = 0.0

    def get_allocation_limit(self) -> float:
        """Get current allocation limit for strategy."""
        stage = StrategyStage(self.state["stage"])

        if stage == StrategyStage.CANARY:
            return self.state.get("canary_allocation_pct", 0.0)
        elif stage == StrategyStage.PRODUCTION:
            return self.state.get("production_allocation_pct", 0.0)
        else:
            return 0.0

    def can_trade(self) -> bool:
        """Check if strategy is allowed to trade."""
        stage = StrategyStage(self.state["stage"])
        return stage in [StrategyStage.PAPER, StrategyStage.CANARY, StrategyStage.PRODUCTION]

    def get_stage(self) -> StrategyStage:
        """Get current strategy stage."""
        return StrategyStage(self.state["stage"])

    def get_summary(self) -> Dict:
        """Get promotion summary."""
        return {
            "strategy_id": self.strategy_id,
            "stage": self.state["stage"],
            "days_in_stage": self.state["days_in_stage"],
            "allocation_limit": self.get_allocation_limit(),
            "can_trade": self.can_trade(),
            "deallocation_reason": self.state.get("deallocation_reason"),
            "backtest_metrics": (
                {
                    "sharpe_ratio": self.backtest_metrics.sharpe_ratio if self.backtest_metrics else None,
                    "max_drawdown": self.backtest_metrics.max_drawdown if self.backtest_metrics else None,
                }
                if self.backtest_metrics
                else None
            ),
        }
