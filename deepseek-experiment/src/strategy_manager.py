"""
Strategy Manager - Multi-Strategy Coordination with Orthogonality Checks

Manages multiple trading strategies (momentum, mean-reversion, breakout, carry)
with orthogonality checks to ensure strategies are not highly correlated.
Tracks pairwise P&L correlations and caps capital to any one cluster.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np

from .regime_controller import RegimeController, StrategyType

logger = logging.getLogger(__name__)


@dataclass
class StrategyPerformance:
    """Performance metrics for a strategy."""

    strategy_id: str
    strategy_type: StrategyType
    total_pnl: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    avg_profit: float = 0.0
    avg_loss: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    current_capital: float = 0.0
    pnl_history: List[float] = None  # List of P&L per trade

    def __post_init__(self):
        if self.pnl_history is None:
            self.pnl_history = []


class StrategyManager:
    """
    Manages multiple trading strategies with orthogonality checks.

    Tracks pairwise P&L correlations and caps capital allocation to correlated clusters.
    """

    def __init__(
        self,
        regime_controller: RegimeController,
        max_correlation: float = 0.7,  # Max correlation between strategies
        min_orthogonal_count: int = 2,  # Minimum number of orthogonal strategies required
    ):
        self.regime_controller = regime_controller
        self.max_correlation = max_correlation
        self.min_orthogonal_count = min_orthogonal_count

        # Strategy performance tracking
        self.strategies: Dict[str, StrategyPerformance] = {}

        # Correlation matrix (pairwise P&L correlations)
        self.correlation_matrix: Dict[Tuple[str, str], float] = {}

        # Strategy clusters (groups of correlated strategies)
        self.clusters: List[List[str]] = []

        logger.info(f"Strategy Manager initialized: max_correlation={max_correlation}")

    def register_strategy(self, strategy_id: str, strategy_type: StrategyType, initial_capital: float = 0.0):
        """Register a new strategy."""
        self.strategies[strategy_id] = StrategyPerformance(
            strategy_id=strategy_id, strategy_type=strategy_type, current_capital=initial_capital
        )
        logger.info(f"Registered strategy: {strategy_id} ({strategy_type.value})")

    def update_strategy_performance(self, strategy_id: str, pnl: float, trade_id: Optional[str] = None):
        """Update strategy performance with new P&L."""
        if strategy_id not in self.strategies:
            logger.warning(f"Strategy {strategy_id} not registered")
            return

        strategy = self.strategies[strategy_id]
        strategy.total_pnl += pnl
        strategy.total_trades += 1
        strategy.pnl_history.append(pnl)

        if pnl > 0:
            strategy.winning_trades += 1
            if strategy.avg_profit == 0:
                strategy.avg_profit = pnl
            else:
                strategy.avg_profit = (
                    strategy.avg_profit * (strategy.winning_trades - 1) + pnl
                ) / strategy.winning_trades
        else:
            strategy.losing_trades += 1
            if strategy.avg_loss == 0:
                strategy.avg_loss = pnl
            else:
                strategy.avg_loss = (strategy.avg_loss * (strategy.losing_trades - 1) + pnl) / strategy.losing_trades

        strategy.win_rate = strategy.winning_trades / strategy.total_trades if strategy.total_trades > 0 else 0.0

        # Calculate Sharpe ratio
        if len(strategy.pnl_history) > 1:
            mean_pnl = np.mean(strategy.pnl_history)
            std_pnl = np.std(strategy.pnl_history)
            strategy.sharpe_ratio = mean_pnl / std_pnl if std_pnl > 0 else 0.0

        # Update max drawdown
        if len(strategy.pnl_history) > 1:
            cumulative = np.cumsum(strategy.pnl_history)
            peak = np.maximum.accumulate(cumulative)
            drawdown = peak - cumulative
            strategy.max_drawdown = float(np.max(drawdown))

    def calculate_correlation(self, strategy_id_1: str, strategy_id_2: str) -> float:
        """Calculate correlation between two strategies' P&L."""
        if strategy_id_1 not in self.strategies or strategy_id_2 not in self.strategies:
            return 0.0

        strat1 = self.strategies[strategy_id_1]
        strat2 = self.strategies[strategy_id_2]

        if len(strat1.pnl_history) < 10 or len(strat2.pnl_history) < 10:
            return 0.0  # Not enough data

        # Align histories (use minimum length)
        min_len = min(len(strat1.pnl_history), len(strat2.pnl_history))
        pnl1 = strat1.pnl_history[-min_len:]
        pnl2 = strat2.pnl_history[-min_len:]

        # Calculate correlation
        correlation = np.corrcoef(pnl1, pnl2)[0, 1]

        # Store in matrix
        key = tuple(sorted([strategy_id_1, strategy_id_2]))
        self.correlation_matrix[key] = float(correlation)

        return float(correlation)

    def identify_clusters(self) -> List[List[str]]:
        """
        Identify clusters of correlated strategies.

        Uses hierarchical clustering based on correlation matrix.
        """
        if len(self.strategies) < 2:
            return []

        # Build correlation matrix
        strategy_ids = list(self.strategies.keys())
        n = len(strategy_ids)
        corr_matrix = np.eye(n)  # Identity matrix (self-correlation = 1.0)

        for i in range(n):
            for j in range(i + 1, n):
                corr = self.calculate_correlation(strategy_ids[i], strategy_ids[j])
                corr_matrix[i, j] = corr
                corr_matrix[j, i] = corr

        # Simple clustering: group strategies with correlation > max_correlation
        clusters = []
        unassigned = set(strategy_ids)

        while unassigned:
            # Start new cluster with first unassigned strategy
            cluster = [unassigned.pop()]
            i = strategy_ids.index(cluster[0])

            # Find all strategies correlated with this one
            for j, other_id in enumerate(strategy_ids):
                if other_id in unassigned and corr_matrix[i, j] > self.max_correlation:
                    cluster.append(other_id)
                    unassigned.remove(other_id)

            clusters.append(cluster)

        self.clusters = clusters
        logger.debug(f"Identified {len(clusters)} strategy clusters: {clusters}")

        return clusters

    def check_orthogonality(self, strategy_id_1: str, strategy_id_2: str) -> Tuple[bool, float]:
        """
        Check if two strategies are orthogonal (low correlation).

        Returns:
            (is_orthogonal, correlation)
        """
        correlation = abs(self.calculate_correlation(strategy_id_1, strategy_id_2))
        is_orthogonal = correlation <= self.max_correlation

        return is_orthogonal, correlation

    def allocate_capital(
        self, total_capital: float, strategy_weights: Optional[Dict[StrategyType, float]] = None
    ) -> Dict[str, float]:
        """
        Allocate capital to strategies with orthogonality constraints.

        Caps capital to any one cluster to prevent over-concentration.
        """
        if strategy_weights is None:
            # Get weights from regime controller
            allocation = self.regime_controller.update_allocation(total_capital)
            strategy_weights = allocation.weights

        # Identify clusters
        clusters = self.identify_clusters()

        # Calculate base allocations
        base_allocations: Dict[str, float] = {}

        for strategy_id, strategy in self.strategies.items():
            strategy_type = strategy.strategy_type
            weight = strategy_weights.get(strategy_type, 0.0)
            base_allocations[strategy_id] = total_capital * weight

        # Apply cluster caps (max 40% of capital per cluster)
        cluster_cap_pct = 0.40
        cluster_cap = total_capital * cluster_cap_pct

        capped_allocations = base_allocations.copy()

        for cluster in clusters:
            cluster_total = sum(base_allocations.get(sid, 0) for sid in cluster)

            if cluster_total > cluster_cap:
                # Scale down allocations in this cluster
                scale_factor = cluster_cap / cluster_total
                for sid in cluster:
                    if sid in capped_allocations:
                        capped_allocations[sid] *= scale_factor

        # Normalize to ensure total doesn't exceed capital
        total_allocated = sum(capped_allocations.values())
        if total_allocated > total_capital:
            scale_factor = total_capital / total_allocated
            capped_allocations = {k: v * scale_factor for k, v in capped_allocations.items()}

        # Update strategy capitals
        for strategy_id, capital in capped_allocations.items():
            if strategy_id in self.strategies:
                self.strategies[strategy_id].current_capital = capital

        logger.debug(
            f"Capital allocated: total={total_capital:.2f}, "
            f"allocations={capped_allocations}, clusters={len(clusters)}"
        )

        return capped_allocations

    def get_strategy_summary(self) -> Dict:
        """Get summary of all strategies."""
        clusters = self.identify_clusters()

        return {
            "total_strategies": len(self.strategies),
            "clusters": clusters,
            "strategies": {
                sid: {
                    "type": strat.strategy_type.value,
                    "total_pnl": strat.total_pnl,
                    "total_trades": strat.total_trades,
                    "win_rate": strat.win_rate,
                    "sharpe_ratio": strat.sharpe_ratio,
                    "max_drawdown": strat.max_drawdown,
                    "current_capital": strat.current_capital,
                }
                for sid, strat in self.strategies.items()
            },
            "correlation_matrix": {f"{k[0]}-{k[1]}": v for k, v in self.correlation_matrix.items()},
        }
