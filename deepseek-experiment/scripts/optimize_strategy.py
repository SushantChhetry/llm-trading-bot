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
                         top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Find the best performing configurations.
        
        Args:
            metric: Metric to optimize for
            top_k: Number of top configurations to return
            
        Returns:
            List of best configurations
        """
        if not self.optimization_results:
            logger.warning("No optimization results available")
            return []
        
        # Sort by metric (higher is better for most metrics)
        sorted_results = sorted(
            self.optimization_results, 
            key=lambda x: x.get("metrics", {}).get(metric, 0), 
            reverse=True
        )
        
        self.best_configs = sorted_results[:top_k]
        
        logger.info(f"Top {top_k} configurations by {metric}:")
        for i, config in enumerate(self.best_configs):
            metric_value = config.get("metrics", {}).get(metric, 0)
            logger.info(f"  {i+1}. {config['config_id']}: {metric} = {metric_value:.4f}")
        
        return self.best_configs
    
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
    best_configs = optimizer.find_best_configs(args.metric, args.top_k)
    
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
