#!/usr/bin/env python3
"""
Automated Hyperparameter Optimization for Trading Strategies

Performs systematic optimization of trading strategy parameters using grid search
or random search to find optimal configurations for LLM-driven trading strategies.
"""

import json
import time
import argparse
import hashlib
import random
import itertools
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.experiment_runner import ExperimentRunner
from config import config


class StrategyOptimizer:
    """
    Automated hyperparameter optimization for trading strategies.
    
    Supports:
    - Grid search and random search
    - Multi-run averaging for statistical significance
    - Comprehensive metrics collection
    - Reproducible results with seed tracking
    - Export to CSV for further analysis
    """
    
    def __init__(self, optimization_dir: Path = None):
        """
        Initialize the strategy optimizer.
        
        Args:
            optimization_dir: Directory to store optimization results
        """
        self.optimization_dir = optimization_dir or config.DATA_DIR / "optimization"
        self.optimization_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (self.optimization_dir / "runs").mkdir(exist_ok=True)
        (self.optimization_dir / "results").mkdir(exist_ok=True)
        (self.optimization_dir / "plots").mkdir(exist_ok=True)
        
        # Initialize experiment runner
        self.experiment_runner = ExperimentRunner()
        
        # Results storage
        self.optimization_results = []
        self.best_configs = []
        
    def grid_search(self, 
                   param_grid: Dict[str, List[Any]], 
                   duration_minutes: int = 30,
                   n_runs: int = 3,
                   seed: int = None) -> List[Dict[str, Any]]:
        """
        Perform grid search optimization over parameter space.
        
        Args:
            param_grid: Dictionary mapping parameter names to lists of values
            duration_minutes: Duration for each experiment run
            n_runs: Number of runs per configuration for averaging
            seed: Random seed for reproducibility
            
        Returns:
            List of optimization results
        """
        if seed is not None:
            random.seed(seed)
            config.RANDOM_SEED = seed
        
        logger.info(f"Starting grid search optimization")
        logger.info(f"Parameter grid: {param_grid}")
        logger.info(f"Duration per run: {duration_minutes} minutes")
        logger.info(f"Runs per config: {n_runs}")
        
        # Generate all parameter combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combinations = list(itertools.product(*param_values))
        
        logger.info(f"Total configurations to test: {len(combinations)}")
        logger.info(f"Total runs: {len(combinations) * n_runs}")
        
        # Run optimization
        results = []
        for i, combination in enumerate(combinations):
            param_dict = dict(zip(param_names, combination))
            config_id = self._generate_config_id(param_dict, seed)
            
            logger.info(f"Testing configuration {i+1}/{len(combinations)}: {config_id}")
            
            # Run multiple times for statistical significance
            config_results = []
            for run in range(n_runs):
                run_id = f"{config_id}_run_{run+1}"
                logger.info(f"  Run {run+1}/{n_runs}")
                
                try:
                    result = self.experiment_runner.run_single_experiment(
                        param_dict, 
                        duration_minutes, 
                        run_id,
                        seed
                    )
                    config_results.append(result)
                except Exception as e:
                    logger.error(f"Run {run_id} failed: {e}")
                    continue
            
            if config_results:
                # Calculate averaged metrics
                avg_result = self._calculate_averaged_result(param_dict, config_results, config_id)
                results.append(avg_result)
                self.optimization_results.append(avg_result)
                
                # Save individual run results
                self._save_config_results(config_id, config_results, avg_result)
        
        # Save optimization summary
        self._save_optimization_summary(results, "grid_search", param_grid)
        
        logger.info(f"Grid search completed. Tested {len(results)} configurations.")
        return results
    
    def random_search(self, 
                     param_space: Dict[str, Any], 
                     n_trials: int = 50,
                     duration_minutes: int = 30,
                     n_runs: int = 3,
                     seed: int = None) -> List[Dict[str, Any]]:
        """
        Perform random search optimization over parameter space.
        
        Args:
            param_space: Dictionary mapping parameter names to value ranges
            n_trials: Number of random configurations to test
            duration_minutes: Duration for each experiment run
            n_runs: Number of runs per configuration for averaging
            seed: Random seed for reproducibility
            
        Returns:
            List of optimization results
        """
        if seed is not None:
            random.seed(seed)
            config.RANDOM_SEED = seed
        
        logger.info(f"Starting random search optimization")
        logger.info(f"Parameter space: {param_space}")
        logger.info(f"Number of trials: {n_trials}")
        logger.info(f"Duration per run: {duration_minutes} minutes")
        logger.info(f"Runs per config: {n_runs}")
        
        # Generate random parameter combinations
        results = []
        for i in range(n_trials):
            param_dict = self._sample_parameters(param_space)
            config_id = self._generate_config_id(param_dict, seed, i)
            
            logger.info(f"Testing configuration {i+1}/{n_trials}: {config_id}")
            
            # Run multiple times for statistical significance
            config_results = []
            for run in range(n_runs):
                run_id = f"{config_id}_run_{run+1}"
                logger.info(f"  Run {run+1}/{n_runs}")
                
                try:
                    result = self.experiment_runner.run_single_experiment(
                        param_dict, 
                        duration_minutes, 
                        run_id,
                        seed
                    )
                    config_results.append(result)
                except Exception as e:
                    logger.error(f"Run {run_id} failed: {e}")
                    continue
            
            if config_results:
                # Calculate averaged metrics
                avg_result = self._calculate_averaged_result(param_dict, config_results, config_id)
                results.append(avg_result)
                self.optimization_results.append(avg_result)
                
                # Save individual run results
                self._save_config_results(config_id, config_results, avg_result)
        
        # Save optimization summary
        self._save_optimization_summary(results, "random_search", param_space)
        
        logger.info(f"Random search completed. Tested {len(results)} configurations.")
        return results
    
    def find_best_configs(self, 
                         metric: str = "sharpe_ratio",
                         optimization_mode: str = "balanced",
                         top_k: int = 5,
                         max_drawdown_threshold: float = None,
                         min_sharpe_threshold: float = None,
                         min_win_rate_threshold: float = None,
                         relax_constraints: bool = False) -> List[Dict[str, Any]]:
        """
        Find the best performing configurations with mode-dependent optimization.
        
        Args:
            metric: Base metric to optimize for (used in balanced mode)
            optimization_mode: Optimization mode - "profit", "sharpe", or "balanced"
            top_k: Number of top configurations to return
            max_drawdown_threshold: Override max drawdown threshold (None = use mode default)
            min_sharpe_threshold: Override min Sharpe threshold (None = use mode default)
            min_win_rate_threshold: Override min win rate threshold (None = use mode default)
            relax_constraints: If True, reduce all constraints by 50% (for testing)
            
        Returns:
            List of best configurations
        """
        if not self.optimization_results:
            logger.warning("No optimization results available")
            return []
        
        # Get mode-specific constraints
        constraints = self._get_mode_constraints(
            optimization_mode, max_drawdown_threshold, min_sharpe_threshold, 
            min_win_rate_threshold, relax_constraints
        )
        
        # Filter results by risk constraints
        filtered_results = self._apply_risk_constraints(self.optimization_results, constraints)
        
        if not filtered_results:
            logger.warning("No configurations passed risk constraints")
            return []
        
        # Calculate optimization score based on mode
        for result in filtered_results:
            result["_optimization_score"] = self._calculate_optimization_score(
                result, optimization_mode, metric
            )
        
        # Sort by optimization score
        sorted_results = sorted(
            filtered_results,
            key=lambda x: x.get("_optimization_score", 0),
            reverse=True
        )
        
        self.best_configs = sorted_results[:top_k]
        
        logger.info(f"Top {top_k} configurations by {optimization_mode} mode:")
        for i, config in enumerate(self.best_configs):
            score = config.get("_optimization_score", 0)
            metrics = config.get("metrics", {})
            logger.info(
                f"  {i+1}. {config['config_id']}: score={score:.4f} "
                f"(profit={metrics.get('total_profit_mean', 0):.2f}, "
                f"sharpe={metrics.get('sharpe_ratio_mean', 0):.4f}, "
                f"win_rate={metrics.get('win_rate_mean', 0):.2f}%)"
            )
        
        return self.best_configs
    
    def _get_mode_constraints(self, 
                             mode: str,
                             max_drawdown_override: float = None,
                             min_sharpe_override: float = None,
                             min_win_rate_override: float = None,
                             relax: bool = False) -> Dict[str, float]:
        """Get risk constraints for optimization mode."""
        # Mode-specific defaults
        if mode == "profit":
            constraints = {
                "max_drawdown": 0.25,
                "min_sharpe": 0.3,
                "min_win_rate": 0.35,
            }
        elif mode == "sharpe":
            constraints = {
                "max_drawdown": 0.15,
                "min_sharpe": 0.5,
                "min_win_rate": 0.40,
            }
        else:  # balanced
            constraints = {
                "max_drawdown": 0.20,
                "min_sharpe": 0.4,
                "min_win_rate": 0.38,
            }
        
        # Apply overrides
        if max_drawdown_override is not None:
            constraints["max_drawdown"] = max_drawdown_override
        if min_sharpe_override is not None:
            constraints["min_sharpe"] = min_sharpe_override
        if min_win_rate_override is not None:
            constraints["min_win_rate"] = min_win_rate_override
        
        # Apply relaxation if requested
        if relax:
            constraints["max_drawdown"] *= 1.5  # Allow 50% more drawdown
            constraints["min_sharpe"] *= 0.5     # Allow 50% lower Sharpe
            constraints["min_win_rate"] *= 0.5   # Allow 50% lower win rate
        
        return constraints
    
    def _apply_risk_constraints(self, 
                                results: List[Dict[str, Any]], 
                                constraints: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Filter results by risk constraints.
        
        CORRECTED LOGIC:
        - Reject if max_drawdown EXCEEDS threshold (too risky)
        - Reject if sharpe_ratio BELOW threshold (too risky)
        - Reject if win_rate BELOW threshold (unreliable)
        - Reject if NOT profitable (hard requirement)
        """
        filtered = []
        violations_log = []
        
        for result in results:
            metrics = result.get("metrics", {})
            
            # Extract metric values (handle both mean and direct values)
            max_drawdown = metrics.get("max_drawdown_mean", metrics.get("max_drawdown", 0))
            sharpe_ratio = metrics.get("sharpe_ratio_mean", metrics.get("sharpe_ratio", 0))
            win_rate = metrics.get("win_rate_mean", metrics.get("win_rate", 0))
            total_profit = metrics.get("total_profit_mean", metrics.get("total_profit", 0))
            
            # Track violations for logging
            violations = []
            
            # CORRECTED: Reject if max_drawdown EXCEEDS threshold (too risky)
            if max_drawdown > constraints["max_drawdown"]:
                violations.append(f"Drawdown {max_drawdown:.2%} exceeds {constraints['max_drawdown']:.2%}")
            
            # CORRECTED: Reject if sharpe_ratio BELOW threshold (too risky)
            if sharpe_ratio < constraints["min_sharpe"]:
                violations.append(f"Sharpe {sharpe_ratio:.2f} below {constraints['min_sharpe']:.2f}")
            
            # CORRECTED: Reject if win_rate BELOW threshold (unreliable)
            if win_rate < constraints["min_win_rate"]:
                violations.append(f"Win rate {win_rate:.2%} below {constraints['min_win_rate']:.2%}")
            
            # Hard requirement: must be profitable
            if total_profit <= 0:
                violations.append(f"Total profit {total_profit:.2f} not positive")
            
            if violations:
                violations_log.append({
                    "config_id": result.get("config_id", "unknown"),
                    "violations": violations
                })
                continue
            
            filtered.append(result)
        
        logger.info(f"Filtered {len(results)} results to {len(filtered)} passing constraints")
        if violations_log:
            logger.debug(f"Rejected {len(violations_log)} configs due to constraint violations")
        
        return filtered
    
    def _calculate_optimization_score(self, 
                                     result: Dict[str, Any], 
                                     mode: str, 
                                     base_metric: str) -> float:
        """Calculate optimization score based on mode."""
        metrics = result.get("metrics", {})
        
        if mode == "profit":
            # Optimize for total profit or total return percentage
            profit = metrics.get("total_profit_mean", metrics.get("total_profit", 0))
            return_pct = metrics.get("total_return_pct_mean", metrics.get("total_return_pct", 0))
            # Use return percentage if available, otherwise profit
            return return_pct if return_pct != 0 else profit
        
        elif mode == "sharpe":
            # Optimize for Sharpe ratio
            sharpe = metrics.get("sharpe_ratio_mean", metrics.get("sharpe_ratio", 0))
            return sharpe
        
        else:  # balanced
            # Weighted combination: profit * 0.7 + sharpe * 0.3
            profit = metrics.get("total_profit_mean", metrics.get("total_profit", 0))
            sharpe = metrics.get("sharpe_ratio_mean", metrics.get("sharpe_ratio", 0))
            
            # Normalize profit to 0-1 scale (assuming max reasonable profit of 10000)
            normalized_profit = min(profit / 10000.0, 1.0) if profit > 0 else 0.0
            # Normalize Sharpe to 0-1 scale (assuming max reasonable Sharpe of 3.0)
            normalized_sharpe = min(max(sharpe, 0) / 3.0, 1.0)
            
            return (normalized_profit * 0.7) + (normalized_sharpe * 0.3)
    
    def validate_strategy_generalization(
        self,
        config: Dict[str, Any],
        train_results: List[Dict[str, Any]],
        test_results: List[Dict[str, Any]],
        degradation_threshold: float = 0.30
    ) -> Dict[str, Any]:
        """
        Walk-forward validation to prevent over-optimization.
        
        CRITICAL: Must be done BEFORE deploying strategy.
        Compares performance on training vs test data to detect overfitting.
        
        Args:
            config: Configuration being validated
            train_results: Results from training data (what optimizer saw)
            test_results: Results from test data (unseen by optimizer)
            degradation_threshold: Max acceptable degradation (default: 30%)
        
        Returns:
            Dictionary with validation results and warnings
        """
        if not train_results or not test_results:
            return {
                "is_valid": False,
                "reason": "Insufficient data for validation",
                "degradation": 1.0
            }
        
        # Calculate average metrics
        train_metrics = self._calculate_averaged_result(
            config, train_results, "train"
        )
        test_metrics = self._calculate_averaged_result(
            config, test_results, "test"
        )
        
        if not train_metrics or not test_metrics:
            return {
                "is_valid": False,
                "reason": "Failed to calculate metrics",
                "degradation": 1.0
            }
        
        train_sharpe = train_metrics.get("metrics", {}).get("sharpe_ratio_mean", 0)
        test_sharpe = test_metrics.get("metrics", {}).get("sharpe_ratio_mean", 0)
        
        train_profit = train_metrics.get("metrics", {}).get("total_profit_mean", 0)
        test_profit = test_metrics.get("metrics", {}).get("total_profit_mean", 0)
        
        # Calculate degradation
        sharpe_degradation = 0.0
        if train_sharpe > 0:
            sharpe_degradation = (train_sharpe - test_sharpe) / train_sharpe
        
        profit_degradation = 0.0
        if train_profit > 0:
            profit_degradation = (train_profit - test_profit) / train_profit
        
        max_degradation = max(sharpe_degradation, profit_degradation)
        
        is_valid = max_degradation <= degradation_threshold
        
        result = {
            "is_valid": is_valid,
            "degradation": max_degradation,
            "sharpe_degradation": sharpe_degradation,
            "profit_degradation": profit_degradation,
            "train_sharpe": train_sharpe,
            "test_sharpe": test_sharpe,
            "train_profit": train_profit,
            "test_profit": test_profit,
        }
        
        if not is_valid:
            result["warning"] = (
                f"Config shows {max_degradation:.1%} degradation on test set. "
                f"Train Sharpe: {train_sharpe:.2f}, Test Sharpe: {test_sharpe:.2f}. "
                f"Train Profit: ${train_profit:.2f}, Test Profit: ${test_profit:.2f}"
            )
            logger.warning(f"OVER-OPTIMIZATION DETECTED: {result['warning']}")
        else:
            logger.info(
                f"Validation passed: {max_degradation:.1%} degradation "
                f"(threshold: {degradation_threshold:.1%})"
            )
        
        return result
    
    def calculate_realistic_profit(
        self,
        backtest_profit: float,
        num_trades: int,
        avg_position_size: float,
        slippage_pct: float = 0.001,
        trading_fee_pct: float = 0.001
    ) -> Dict[str, Any]:
        """
        Adjusts backtest profit for real-world trading costs.
        
        Accounts for:
        - Slippage (entry + exit)
        - Trading fees (entry + exit)
        
        Args:
            backtest_profit: Gross profit from backtest
            num_trades: Number of trades executed
            avg_position_size: Average position size in USDT
            slippage_pct: Slippage percentage per trade (default: 0.1%)
            trading_fee_pct: Trading fee percentage per trade (default: 0.1%)
        
        Returns:
            Dictionary with cost breakdown and realistic profit
        """
        # Total cost per trade: slippage (entry + exit) + fees (entry + exit)
        cost_per_trade_pct = (slippage_pct * 2) + (trading_fee_pct * 2)
        cost_per_trade = avg_position_size * cost_per_trade_pct
        
        total_costs = cost_per_trade * num_trades
        realistic_profit = backtest_profit - total_costs
        
        cost_impact_pct = (1 - realistic_profit / backtest_profit) * 100 if backtest_profit > 0 else 100
        
        return {
            "backtest_profit": backtest_profit,
            "total_costs": total_costs,
            "slippage_cost": slippage_pct * 2 * avg_position_size * num_trades,
            "trading_fees": trading_fee_pct * 2 * avg_position_size * num_trades,
            "realistic_profit": realistic_profit,
            "cost_impact_pct": cost_impact_pct,
            "num_trades": num_trades,
            "avg_position_size": avg_position_size
        }
    
    def export_results(self, 
                      output_file: str = None, 
                      format: str = "csv") -> str:
        """
        Export optimization results to file.
        
        Args:
            output_file: Output file path
            format: Export format ("csv", "json", "excel")
            
        Returns:
            Path to exported file
        """
        if not self.optimization_results:
            logger.warning("No results to export")
            return None
        
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"optimization_results_{timestamp}.{format}"
        
        output_path = self.optimization_dir / "results" / output_file
        
        # Prepare data for export
        export_data = []
        for result in self.optimization_results:
            row = {
                "config_id": result["config_id"],
                "parameters": json.dumps(result["parameters"]),
                **result["metrics"]
            }
            export_data.append(row)
        
        # Export based on format
        if format.lower() == "csv":
            try:
                import pandas as pd
                df = pd.DataFrame(export_data)
                df.to_csv(output_path, index=False)
            except ImportError:
                # Fallback to manual CSV writing
                with open(output_path, 'w') as f:
                    if export_data:
                        # Write header
                        f.write(",".join(export_data[0].keys()) + "\n")
                        # Write data
                        for row in export_data:
                            f.write(",".join(str(v) for v in row.values()) + "\n")
        elif format.lower() == "json":
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2)
        elif format.lower() == "excel":
            try:
                import pandas as pd
                df = pd.DataFrame(export_data)
                df.to_excel(output_path, index=False)
            except ImportError:
                logger.warning("pandas not available for Excel export, falling back to JSON")
                output_path = output_path.with_suffix('.json')
                with open(output_path, 'w') as f:
                    json.dump(export_data, f, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Results exported to {output_path}")
        return str(output_path)
    
    def _generate_config_id(self, 
                           params: Dict[str, Any], 
                           seed: int = None, 
                           trial: int = None) -> str:
        """Generate unique configuration ID."""
        # Create deterministic hash from parameters
        param_str = json.dumps(params, sort_keys=True)
        if seed is not None:
            param_str += f"_seed_{seed}"
        if trial is not None:
            param_str += f"_trial_{trial}"
        
        return hashlib.md5(param_str.encode()).hexdigest()[:12]
    
    def _sample_parameters(self, param_space: Dict[str, Any]) -> Dict[str, Any]:
        """Sample parameters from parameter space."""
        sampled = {}
        for param, space in param_space.items():
            if isinstance(space, list):
                # Discrete values
                sampled[param] = random.choice(space)
            elif isinstance(space, dict) and "min" in space and "max" in space:
                # Continuous range
                if "type" in space and space["type"] == "int":
                    sampled[param] = random.randint(space["min"], space["max"])
                else:
                    sampled[param] = random.uniform(space["min"], space["max"])
            elif isinstance(space, dict) and "choices" in space:
                # Choice from list
                sampled[param] = random.choice(space["choices"])
            else:
                # Single value
                sampled[param] = space
        
        return sampled
    
    def _calculate_averaged_result(self, 
                                 params: Dict[str, Any], 
                                 config_results: List[Dict[str, Any]], 
                                 config_id: str) -> Dict[str, Any]:
        """Calculate averaged metrics across multiple runs."""
        if not config_results:
            return None
        
        # Extract metrics from all runs
        all_metrics = [result.get("metrics", {}) for result in config_results if result.get("success", False)]
        
        if not all_metrics:
            return None
        
        # Calculate averaged metrics
        avg_metrics = {}
        for metric in all_metrics[0].keys():
            values = [m.get(metric, 0) for m in all_metrics]
            avg_metrics[f"{metric}_mean"] = sum(values) / len(values)
            avg_metrics[f"{metric}_std"] = (sum((x - avg_metrics[f"{metric}_mean"])**2 for x in values) / len(values))**0.5
            avg_metrics[f"{metric}_min"] = min(values)
            avg_metrics[f"{metric}_max"] = max(values)
        
        # Add run count and success rate
        avg_metrics["n_runs"] = len(config_results)
        avg_metrics["success_rate"] = len(all_metrics) / len(config_results)
        
        return {
            "config_id": config_id,
            "parameters": params,
            "metrics": avg_metrics,
            "individual_runs": config_results,
            "timestamp": datetime.now().isoformat()
        }
    
    def _save_config_results(self, 
                           config_id: str, 
                           config_results: List[Dict[str, Any]], 
                           avg_result: Dict[str, Any]):
        """Save results for a specific configuration."""
        config_file = self.optimization_dir / "runs" / f"{config_id}.json"
        with open(config_file, 'w') as f:
            json.dump({
                "config_id": config_id,
                "individual_runs": config_results,
                "averaged_result": avg_result
            }, f, indent=2)
    
    def _save_optimization_summary(self, 
                                 results: List[Dict[str, Any]], 
                                 method: str, 
                                 param_space: Dict[str, Any]):
        """Save optimization summary."""
        summary = {
            "method": method,
            "param_space": param_space,
            "total_configurations": len(results),
            "timestamp": datetime.now().isoformat(),
            "results": results
        }
        
        summary_file = self.optimization_dir / "results" / f"{method}_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Optimization summary saved to {summary_file}")


def create_parameter_spaces() -> Dict[str, Dict[str, Any]]:
    """Create predefined parameter spaces for common optimization scenarios."""
    return {
        "conservative": {
            "max_position_size": [0.01, 0.02, 0.03, 0.05],
            "stop_loss_percent": [1.0, 2.0, 3.0],
            "take_profit_percent": [2.0, 3.0, 5.0],
            "confidence_threshold": [0.7, 0.8, 0.9]
        },
        "moderate": {
            "max_position_size": [0.05, 0.08, 0.10, 0.15],
            "stop_loss_percent": [2.0, 3.0, 5.0],
            "take_profit_percent": [5.0, 8.0, 10.0],
            "confidence_threshold": [0.6, 0.7, 0.8]
        },
        "aggressive": {
            "max_position_size": [0.10, 0.15, 0.20, 0.25],
            "stop_loss_percent": [3.0, 5.0, 8.0],
            "take_profit_percent": [8.0, 12.0, 15.0],
            "confidence_threshold": [0.5, 0.6, 0.7]
        },
        "llm_comparison": {
            "llm_provider": ["deepseek", "openai", "anthropic"],
            "max_position_size": [0.05, 0.10],
            "stop_loss_percent": [3.0, 5.0],
            "take_profit_percent": [8.0, 12.0],
            "confidence_threshold": [0.6, 0.7]
        },
        "timeframe_optimization": {
            "run_interval": [180, 300, 600, 900],  # 3min, 5min, 10min, 15min
            "max_position_size": [0.05, 0.10],
            "stop_loss_percent": [3.0, 5.0],
            "take_profit_percent": [8.0, 12.0]
        }
    }


def main():
    """Main entry point for strategy optimization."""
    parser = argparse.ArgumentParser(
        description="Automated hyperparameter optimization for trading strategies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Grid search with predefined conservative parameters
  python scripts/optimize_strategy.py --method grid --preset conservative --duration 30

  # Random search with custom parameters
  python scripts/optimize_strategy.py --method random --trials 50 --duration 45

  # LLM provider comparison
  python scripts/optimize_strategy.py --method grid --preset llm_comparison --runs 5

  # Custom parameter grid
  python scripts/optimize_strategy.py --method grid --max-position-size 0.05,0.10 --stop-loss 2.0,5.0
        """
    )
    
    # Optimization method
    parser.add_argument(
        "--method", 
        choices=["grid", "random"], 
        default="grid",
        help="Optimization method (default: grid)"
    )
    
    # Preset parameter spaces
    parser.add_argument(
        "--preset", 
        choices=["conservative", "moderate", "aggressive", "llm_comparison", "timeframe_optimization"],
        help="Use predefined parameter space"
    )
    
    # Custom parameters
    parser.add_argument(
        "--max-position-size", 
        help="Comma-separated list of position sizes"
    )
    parser.add_argument(
        "--stop-loss", 
        help="Comma-separated list of stop loss percentages"
    )
    parser.add_argument(
        "--take-profit", 
        help="Comma-separated list of take profit percentages"
    )
    parser.add_argument(
        "--confidence-threshold", 
        help="Comma-separated list of confidence thresholds"
    )
    parser.add_argument(
        "--llm-provider", 
        help="Comma-separated list of LLM providers"
    )
    parser.add_argument(
        "--run-interval", 
        help="Comma-separated list of run intervals (seconds)"
    )
    
    # Optimization settings
    parser.add_argument(
        "--trials", 
        type=int, 
        default=50,
        help="Number of trials for random search (default: 50)"
    )
    parser.add_argument(
        "--duration", 
        type=int, 
        default=30,
        help="Duration per experiment in minutes (default: 30)"
    )
    parser.add_argument(
        "--runs", 
        type=int, 
        default=3,
        help="Number of runs per configuration (default: 3)"
    )
    parser.add_argument(
        "--seed", 
        type=int,
        help="Random seed for reproducibility"
    )
    
    # Output settings
    parser.add_argument(
        "--export", 
        help="Export results to file (CSV, JSON, or Excel)"
    )
    parser.add_argument(
        "--top-k", 
        type=int, 
        default=5,
        help="Number of top configurations to show (default: 5)"
    )
    parser.add_argument(
        "--metric", 
        default="sharpe_ratio",
        help="Metric to optimize for (default: sharpe_ratio)"
    )
    parser.add_argument(
        "--optimization-mode",
        choices=["profit", "sharpe", "balanced"],
        default="balanced",
        help="Optimization mode: profit (maximize profit), sharpe (maximize Sharpe), balanced (weighted) (default: balanced)"
    )
    parser.add_argument(
        "--max-drawdown-threshold",
        type=float,
        help="Override max drawdown threshold (overrides mode default)"
    )
    parser.add_argument(
        "--min-sharpe-threshold",
        type=float,
        help="Override min Sharpe threshold (overrides mode default)"
    )
    parser.add_argument(
        "--min-win-rate-threshold",
        type=float,
        help="Override min win rate threshold (overrides mode default)"
    )
    parser.add_argument(
        "--relax-constraints",
        action="store_true",
        help="Relax all constraints by 50% (for testing)"
    )
    
    args = parser.parse_args()
    
    # Initialize optimizer
    optimizer = StrategyOptimizer()
    
    # Determine parameter space
    if args.preset:
        param_spaces = create_parameter_spaces()
        param_space = param_spaces[args.preset]
    else:
        # Build custom parameter space
        param_space = {}
        
        if args.max_position_size:
            param_space["max_position_size"] = [float(x) for x in args.max_position_size.split(",")]
        if args.stop_loss:
            param_space["stop_loss_percent"] = [float(x) for x in args.stop_loss.split(",")]
        if args.take_profit:
            param_space["take_profit_percent"] = [float(x) for x in args.take_profit.split(",")]
        if args.confidence_threshold:
            param_space["confidence_threshold"] = [float(x) for x in args.confidence_threshold.split(",")]
        if args.llm_provider:
            param_space["llm_provider"] = args.llm_provider.split(",")
        if args.run_interval:
            param_space["run_interval"] = [int(x) for x in args.run_interval.split(",")]
        
        if not param_space:
            logger.error("No parameters specified. Use --preset or specify custom parameters.")
            return
    
    # Run optimization
    if args.method == "grid":
        results = optimizer.grid_search(
            param_space, 
            args.duration, 
            args.runs, 
            args.seed
        )
    else:  # random
        results = optimizer.random_search(
            param_space, 
            args.trials, 
            args.duration, 
            args.runs, 
            args.seed
        )
    
    # Find best configurations
    best_configs = optimizer.find_best_configs(
        metric=args.metric,
        optimization_mode=args.optimization_mode,
        top_k=args.top_k,
        max_drawdown_threshold=args.max_drawdown_threshold,
        min_sharpe_threshold=args.min_sharpe_threshold,
        min_win_rate_threshold=args.min_win_rate_threshold,
        relax_constraints=args.relax_constraints
    )
    
    # Export results
    if args.export:
        output_file = optimizer.export_results(args.export)
        print(f"Results exported to {output_file}")
    
    print(f"\nOptimization completed! Tested {len(results)} configurations.")
    print(f"Top configuration: {best_configs[0]['config_id'] if best_configs else 'None'}")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    main()
