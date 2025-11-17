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

    def calculate_performance_score(self, strategy_id: str, lookback_trades: int = 20) -> float:
        """
        CORRECTED: Calculate normalized performance score (0-1 scale).
        
        Uses z-score normalization across strategies for fair comparison.
        No arbitrary scaling factors - proper statistical normalization.
        
        Args:
            strategy_id: Strategy identifier
            lookback_trades: Number of recent trades to consider
        
        Returns:
            Performance score (0-1, higher is better)
        """
        if strategy_id not in self.strategies:
            return 0.5  # Default for new strategy
        
        strategy = self.strategies[strategy_id]
        
        # Calculate recent metrics
        recent_trades = strategy.pnl_history[-lookback_trades:] if len(strategy.pnl_history) > lookback_trades else strategy.pnl_history
        recent_profit = sum(recent_trades) if recent_trades else 0.0
        recent_win_rate = sum(1 for p in recent_trades if p > 0) / len(recent_trades) if recent_trades else 0.5
        
        # Calculate recent Sharpe
        if len(recent_trades) > 1:
            mean_pnl = np.mean(recent_trades)
            std_pnl = np.std(recent_trades)
            recent_sharpe = mean_pnl / std_pnl if std_pnl > 0 else 0.0
        else:
            recent_sharpe = 0.0
        
        # Get all strategies' metrics for normalization (z-score)
        all_strategy_ids = list(self.strategies.keys())
        all_recent_profits = []
        all_sharpes = []
        
        for sid in all_strategy_ids:
            s = self.strategies[sid]
            s_recent = s.pnl_history[-lookback_trades:] if len(s.pnl_history) > lookback_trades else s.pnl_history
            all_recent_profits.append(sum(s_recent) if s_recent else 0.0)
            
            if len(s_recent) > 1:
                s_mean = np.mean(s_recent)
                s_std = np.std(s_recent)
                all_sharpes.append(s_mean / s_std if s_std > 0 else 0.0)
            else:
                all_sharpes.append(0.0)
        
        # Normalize using z-score
        pnl_mean, pnl_std = np.mean(all_recent_profits), np.std(all_recent_profits)
        sharpe_mean, sharpe_std = np.mean(all_sharpes), np.std(all_sharpes)
        
        # Z-scores (handle zero std - if all strategies identical, use neutral score)
        if pnl_std < 1e-6:  # All strategies have same profit
            pnl_score = 0.5  # Neutral score
        else:
            recent_pnl_zscore = (recent_profit - pnl_mean) / pnl_std
            # Convert z-scores to 0-1 range using sigmoid
            def zscore_to_prob(z):
                return 1 / (1 + np.exp(-z))
            pnl_score = zscore_to_prob(recent_pnl_zscore)
        
        if sharpe_std < 1e-6:  # All strategies have same Sharpe
            sharpe_score = 0.5  # Neutral score
        else:
            recent_sharpe_zscore = (recent_sharpe - sharpe_mean) / sharpe_std
            def zscore_to_prob(z):
                return 1 / (1 + np.exp(-z))
            sharpe_score = zscore_to_prob(recent_sharpe_zscore)
        win_rate_score = recent_win_rate  # Already 0-1
        
        # Weighted combination (interpretable as probability)
        final_score = (pnl_score * 0.4) + (sharpe_score * 0.3) + (win_rate_score * 0.3)
        
        # Penalize strategies with high drawdown
        max_dd = strategy.max_drawdown
        if max_dd > 0:
            drawdown_penalty = min(max_dd * 0.5, 0.4)  # Penalty up to 0.4
            final_score = final_score * (1 - drawdown_penalty)
        
        final_score = max(0.0, min(final_score, 1.0))
        
        logger.debug(
            f"Performance score for {strategy_id}: {final_score:.3f} "
            f"(pnl_z={recent_pnl_zscore:.2f}, sharpe_z={recent_sharpe_zscore:.2f}, "
            f"win_rate={recent_win_rate:.2f})"
        )
        
        return final_score

    def reallocate_capital(
        self,
        total_capital: float,
        min_allocation: float = 0.05,
        max_allocation: float = 0.50,
        performance_range_threshold: float = 0.15,
        rebalance_interval_hours: int = 24,
    ) -> Dict[str, float]:
        """
        Reallocate capital based on performance scores.
        
        Args:
            total_capital: Total capital to allocate
            min_allocation: Minimum allocation per strategy (as fraction of total)
            max_allocation: Maximum allocation per strategy (as fraction of total)
            performance_range_threshold: Performance gap threshold to trigger rebalancing (15% default)
            rebalance_interval_hours: Minimum hours between rebalancing
        
        Returns:
            Dictionary mapping strategy_id to allocated capital
        """
        if not self.strategies:
            return {}
        
        # Calculate performance scores for all strategies
        scores = {}
        for strategy_id in self.strategies.keys():
            scores[strategy_id] = self.calculate_performance_score(strategy_id)
        
        # Check if rebalancing is needed
        if scores:
            max_score = max(scores.values())
            min_score = min(scores.values())
            performance_range = (max_score - min_score) / (abs(max_score) + 1e-10)  # Normalized range
            
            # Check if performance gap exceeds threshold
            if performance_range < performance_range_threshold:
                logger.debug(
                    f"Performance range {performance_range:.2f} < threshold {performance_range_threshold}, "
                    f"skipping rebalancing"
                )
                # Return current allocations
                return {sid: strat.current_capital for sid, strat in self.strategies.items()}
        
        # Normalize scores to probabilities (softmax-like)
        # Use exponential to emphasize differences
        exp_scores = {sid: max(0, score) ** 2 for sid, score in scores.items()}  # Square to emphasize differences
        total_exp = sum(exp_scores.values())
        
        if total_exp == 0:
            # All scores are negative or zero, use equal allocation
            equal_allocation = total_capital / len(self.strategies)
            allocations = {sid: equal_allocation for sid in self.strategies.keys()}
        else:
            # Allocate based on normalized scores
            allocations = {}
            for strategy_id, exp_score in exp_scores.items():
                # Base allocation from score
                base_allocation = total_capital * (exp_score / total_exp)
                
                # Apply min/max constraints
                min_cap = total_capital * min_allocation
                max_cap = total_capital * max_allocation
                
                allocations[strategy_id] = max(min_cap, min(base_allocation, max_cap))
        
        # Normalize to ensure total doesn't exceed capital
        total_allocated = sum(allocations.values())
        if total_allocated > total_capital:
            scale_factor = total_capital / total_allocated
            allocations = {k: v * scale_factor for k, v in allocations.items()}
        elif total_allocated < total_capital:
            # Distribute remaining capital proportionally
            remaining = total_capital - total_allocated
            if allocations:
                scale_factor = 1 + (remaining / total_allocated)
                allocations = {k: v * scale_factor for k, v in allocations.items()}
        
        # Update strategy capitals
        for strategy_id, capital in allocations.items():
            if strategy_id in self.strategies:
                self.strategies[strategy_id].current_capital = capital
        
        logger.info(
            f"Capital reallocated: total={total_capital:.2f}, "
            f"allocations={allocations}, performance_range={performance_range:.2f}"
        )
        
        return allocations

    def should_rebalance(
        self,
        performance_range_threshold: float = 0.15,
        rebalance_interval_hours: int = 24,
        loss_threshold: float = -0.10,
        last_rebalance_time: Optional[datetime] = None,
    ) -> Tuple[bool, str]:
        """
        CORRECTED: Determine if rebalancing is needed with concrete trigger logic.
        
        Uses adaptive trigger logic based on:
        1. Time interval (minimum 24 hours)
        2. Performance divergence (allocation drift > 15%)
        3. Scheduled rebalance (7 days)
        4. Emergency trigger (strategy severely underperforming)
        
        Args:
            performance_range_threshold: Performance gap threshold (15% default)
            rebalance_interval_hours: Minimum hours between rebalancing
            loss_threshold: Recent loss threshold to trigger quick rebalancing (-10% default)
            last_rebalance_time: Timestamp of last rebalancing
        
        Returns:
            Tuple of (should_rebalance: bool, reason: str)
        """
        if not self.strategies:
            return False, "no_strategies"
        
        # Check time interval
        if last_rebalance_time:
            time_since_rebalance = (datetime.now() - last_rebalance_time).total_seconds() / 3600
            if time_since_rebalance < rebalance_interval_hours:
                return False, f"too_recent ({time_since_rebalance:.1f}h < {rebalance_interval_hours}h)"
        
        # Calculate current vs target allocations
        total_capital = sum(s.current_capital for s in self.strategies.values())
        if total_capital == 0:
            return False, "no_capital"
        
        # Get performance scores and calculate target allocations
        scores = {sid: self.calculate_performance_score(sid) for sid in self.strategies.keys()}
        
        if not scores or sum(scores.values()) == 0:
            return False, "insufficient_data"
        
        # Normalize scores to get target allocations
        # Handle negative scores by shifting to positive
        min_score = min(scores.values())
        if min_score < 0:
            # Shift all scores to be positive
            scores = {sid: score - min_score + 0.01 for sid, score in scores.items()}
        
        total_score = sum(scores.values())
        if total_score == 0:
            # All scores are zero or negative, use equal allocation
            equal_allocation = total_capital / len(self.strategies) if self.strategies else 0
            return {sid: equal_allocation for sid in self.strategies.keys()}
        
        target_allocations = {
            sid: (score / total_score) * total_capital 
            for sid, score in scores.items()
        }
        
        # Calculate current allocations
        current_allocations = {
            sid: strategy.current_capital 
            for sid, strategy in self.strategies.items()
        }
        
        # Calculate allocation drift
        allocation_drift = {}
        for strategy_id in target_allocations:
            target = target_allocations[strategy_id]
            current = current_allocations.get(strategy_id, 0)
            drift = abs(target - current) / max(target, 0.01)  # Percentage drift
            allocation_drift[strategy_id] = drift
        
        max_drift = max(allocation_drift.values()) if allocation_drift else 0
        
        # Trigger 1: Performance divergence (>15% drift)
        if max_drift > performance_range_threshold:
            return True, f"performance_divergence (max_drift={max_drift:.1%})"
        
        # Trigger 2: Scheduled rebalance (7 days)
        if last_rebalance_time:
            hours_since = (datetime.now() - last_rebalance_time).total_seconds() / 3600
            if hours_since > 7 * 24:
                return True, "scheduled_rebalance"
        
        # Trigger 3: Emergency trigger (strategy severely underperforming)
        for strategy_id, drift in allocation_drift.items():
            if drift > 0.25:  # >25% drift on single strategy
                strategy = self.strategies[strategy_id]
                if len(strategy.pnl_history) >= 5:
                    recent_pnl = sum(strategy.pnl_history[-5:])
                    if recent_pnl < -500:  # Lost >$500 in recent trades
                        return True, f"strategy_{strategy_id}_emergency"
        
        return False, "no_rebalance_needed"

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
                    "performance_score": self.calculate_performance_score(sid),
                }
                for sid, strat in self.strategies.items()
            },
            "correlation_matrix": {f"{k[0]}-{k[1]}": v for k, v in self.correlation_matrix.items()},
        }
