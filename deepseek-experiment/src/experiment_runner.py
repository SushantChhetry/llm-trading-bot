"""
Experiment Runner for DeepSeek Trading Bot

Supports running parameter sweeps and systematic testing of trading strategies
and LLM behaviors with comprehensive logging and metrics tracking.
"""

import json
import yaml
import hashlib
import logging
import argparse
import time
import random
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import itertools

from config import config
from src.main import TradingBot
from src.llm_client import LLMClient
from src.trading_engine import TradingEngine

logger = logging.getLogger(__name__)


class ExperimentRunner:
    """
    Runs systematic experiments with parameter sweeps and comprehensive logging.
    
    Supports testing different combinations of:
    - LLM providers and models
    - Risk levels and position sizes
    - Prompt templates and trading strategies
    - Market conditions and timeframes
    """
    
    def __init__(self, experiments_dir: Path = None):
        """
        Initialize the experiment runner.
        
        Args:
            experiments_dir: Directory to store experiment results
        """
        self.experiments_dir = experiments_dir or config.DATA_DIR / "experiments"
        self.experiments_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (self.experiments_dir / "logs").mkdir(exist_ok=True)
        (self.experiments_dir / "results").mkdir(exist_ok=True)
        (self.experiments_dir / "configs").mkdir(exist_ok=True)
    
    def generate_experiment_id(self, params: Dict[str, Any]) -> str:
        """
        Generate a unique experiment ID based on parameters.
        
        Args:
            params: Experiment parameters
            
        Returns:
            Unique experiment identifier
        """
        # Create a deterministic hash from sorted parameters
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(param_str.encode()).hexdigest()[:8]
    
    def run_single_experiment(self, 
                            experiment_params: Dict[str, Any],
                            duration_minutes: int = 30,
                            run_id: str = None,
                            seed: int = None) -> Dict[str, Any]:
        """
        Run a single experiment with given parameters.
        
        Args:
            experiment_params: Parameters for this experiment
            duration_minutes: How long to run the experiment
            run_id: Optional run identifier
            
        Returns:
            Experiment results dictionary
        """
        if run_id is None:
            run_id = self.generate_experiment_id(experiment_params)
        
        logger.info(f"Starting experiment {run_id}")
        logger.info(f"Parameters: {experiment_params}")
        
        # Set random seed for reproducibility
        if seed is not None:
            random.seed(seed)
            os.environ['PYTHONHASHSEED'] = str(seed)
            logger.info(f"Random seed set to: {seed}")
        
        # Create experiment directory
        exp_dir = self.experiments_dir / "logs" / run_id
        exp_dir.mkdir(exist_ok=True)
        
        # Save experiment configuration with metadata
        experiment_metadata = {
            "parameters": experiment_params,
            "duration_minutes": duration_minutes,
            "seed": seed,
            "timestamp": datetime.now().isoformat(),
            "python_hashseed": os.environ.get('PYTHONHASHSEED'),
            "random_state": random.getstate() if seed is not None else None
        }
        
        config_file = exp_dir / "experiment_config.json"
        with open(config_file, 'w') as f:
            json.dump(experiment_metadata, f, indent=2)
        
        # Override config with experiment parameters
        original_config = self._backup_config()
        self._apply_experiment_params(experiment_params)
        
        try:
            # Initialize bot with experiment parameters
            bot = TradingBot()
            
            # Set up experiment-specific logging
            exp_log_file = exp_dir / "experiment.log"
            exp_handler = logging.FileHandler(exp_log_file)
            exp_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            logger.addHandler(exp_handler)
            
            # Run experiment
            start_time = datetime.now()
            results = self._run_experiment_bot(bot, duration_minutes)
            end_time = datetime.now()
            
            # Calculate metrics
            metrics = self._calculate_experiment_metrics(results, start_time, end_time)
            
            # Store results
            results_file = exp_dir / "results.json"
            with open(results_file, 'w') as f:
                json.dump({
                    "experiment_id": run_id,
                    "parameters": experiment_params,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_minutes": duration_minutes,
                    "metrics": metrics,
                    "trades": results.get("trades", []),
                    "llm_decisions": results.get("llm_decisions", [])
                }, f, indent=2)
            
            logger.info(f"Experiment {run_id} completed successfully")
            logger.info(f"Final P&L: ${metrics.get('total_profit', 0):.2f}")
            logger.info(f"Win Rate: {metrics.get('win_rate', 0):.1f}%")
            
            return {
                "experiment_id": run_id,
                "parameters": experiment_params,
                "metrics": metrics,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Experiment {run_id} failed: {e}")
            return {
                "experiment_id": run_id,
                "parameters": experiment_params,
                "error": str(e),
                "success": False
            }
        finally:
            # Restore original config
            self._restore_config(original_config)
            logger.removeHandler(exp_handler)
    
    def run_parameter_sweep(self, 
                           sweep_config: Dict[str, Any],
                           duration_minutes: int = 30) -> List[Dict[str, Any]]:
        """
        Run a parameter sweep experiment.
        
        Args:
            sweep_config: Configuration defining parameter ranges to sweep
            duration_minutes: Duration for each experiment
            
        Returns:
            List of experiment results
        """
        logger.info("Starting parameter sweep experiment")
        logger.info(f"Sweep config: {sweep_config}")
        
        # Generate parameter combinations
        param_combinations = self._generate_parameter_combinations(sweep_config)
        
        logger.info(f"Generated {len(param_combinations)} parameter combinations")
        
        results = []
        for i, params in enumerate(param_combinations):
            logger.info(f"Running experiment {i+1}/{len(param_combinations)}")
            result = self.run_single_experiment(params, duration_minutes)
            results.append(result)
            
            # Brief pause between experiments
            time.sleep(5)
        
        # Save sweep summary
        sweep_summary = {
            "sweep_config": sweep_config,
            "total_experiments": len(param_combinations),
            "duration_per_experiment": duration_minutes,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
        
        sweep_file = self.experiments_dir / "results" / f"sweep_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(sweep_file, 'w') as f:
            json.dump(sweep_summary, f, indent=2)
        
        logger.info(f"Parameter sweep completed. Results saved to {sweep_file}")
        return results
    
    def _backup_config(self) -> Dict[str, Any]:
        """Backup current config state."""
        return {
            "LLM_PROVIDER": config.LLM_PROVIDER,
            "LLM_API_KEY": config.LLM_API_KEY,
            "LLM_MODEL": config.LLM_MODEL,
            "MAX_POSITION_SIZE": config.MAX_POSITION_SIZE,
            "STOP_LOSS_PERCENT": config.STOP_LOSS_PERCENT,
            "TAKE_PROFIT_PERCENT": config.TAKE_PROFIT_PERCENT,
            "RUN_INTERVAL_SECONDS": config.RUN_INTERVAL_SECONDS,
            "USE_TESTNET": config.USE_TESTNET,
            "TRADING_MODE": config.TRADING_MODE
        }
    
    def _restore_config(self, original_config: Dict[str, Any]):
        """Restore original config state."""
        for key, value in original_config.items():
            setattr(config, key, value)
    
    def _apply_experiment_params(self, params: Dict[str, Any]):
        """Apply experiment parameters to config."""
        param_mapping = {
            "llm_provider": "LLM_PROVIDER",
            "llm_model": "LLM_MODEL",
            "max_position_size": "MAX_POSITION_SIZE",
            "stop_loss_percent": "STOP_LOSS_PERCENT",
            "take_profit_percent": "TAKE_PROFIT_PERCENT",
            "run_interval": "RUN_INTERVAL_SECONDS",
            "use_testnet": "USE_TESTNET",
            "trading_mode": "TRADING_MODE"
        }
        
        for param_key, config_key in param_mapping.items():
            if param_key in params:
                setattr(config, config_key, params[param_key])
    
    def _generate_parameter_combinations(self, sweep_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate all parameter combinations for sweep."""
        # Extract parameter ranges
        param_ranges = {}
        for param, values in sweep_config.items():
            if isinstance(values, list):
                param_ranges[param] = values
            else:
                param_ranges[param] = [values]
        
        # Generate all combinations
        param_names = list(param_ranges.keys())
        param_values = list(param_ranges.values())
        
        combinations = []
        for combo in itertools.product(*param_values):
            param_dict = dict(zip(param_names, combo))
            combinations.append(param_dict)
        
        return combinations
    
    def _run_experiment_bot(self, bot: TradingBot, duration_minutes: int) -> Dict[str, Any]:
        """Run the bot for the specified duration and collect results."""
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        trades = []
        llm_decisions = []
        
        try:
            while time.time() < end_time:
                # Run one cycle
                bot.run_cycle()
                
                # Collect data
                if hasattr(bot.trading_engine, 'trades'):
                    trades = bot.trading_engine.trades.copy()
                
                # Brief pause
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Experiment interrupted by user")
        
        return {
            "trades": trades,
            "llm_decisions": llm_decisions
        }
    
    def _calculate_experiment_metrics(self, 
                                    results: Dict[str, Any],
                                    start_time: datetime,
                                    end_time: datetime) -> Dict[str, Any]:
        """Calculate comprehensive metrics for the experiment."""
        trades = results.get("trades", [])
        
        if not trades:
            return {
                "total_trades": 0,
                "total_profit": 0.0,
                "win_rate": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
                "volatility": 0.0,
                "avg_trade_duration": 0.0
            }
        
        # Basic metrics
        total_trades = len(trades)
        sell_trades = [t for t in trades if t.get("side") == "sell"]
        
        # P&L metrics
        total_profit = sum(t.get("profit", 0) for t in sell_trades)
        profitable_trades = len([t for t in sell_trades if t.get("profit", 0) > 0])
        win_rate = (profitable_trades / len(sell_trades) * 100) if sell_trades else 0
        
        # Risk metrics
        profits = [t.get("profit", 0) for t in sell_trades]
        if profits:
            max_drawdown = self._calculate_max_drawdown(profits)
            volatility = self._calculate_volatility(profits)
            sharpe_ratio = self._calculate_sharpe_ratio(profits)
        else:
            max_drawdown = 0.0
            volatility = 0.0
            sharpe_ratio = 0.0
        
        # Time metrics
        duration_hours = (end_time - start_time).total_seconds() / 3600
        avg_trade_duration = duration_hours / total_trades if total_trades > 0 else 0
        
        return {
            "total_trades": total_trades,
            "total_profit": total_profit,
            "win_rate": win_rate,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "volatility": volatility,
            "avg_trade_duration": avg_trade_duration,
            "duration_hours": duration_hours
        }
    
    def _calculate_max_drawdown(self, profits: List[float]) -> float:
        """Calculate maximum drawdown from profit series."""
        if not profits:
            return 0.0
        
        cumulative = []
        running_sum = 0
        for profit in profits:
            running_sum += profit
            cumulative.append(running_sum)
        
        peak = cumulative[0]
        max_dd = 0
        for value in cumulative:
            if value > peak:
                peak = value
            drawdown = peak - value
            if drawdown > max_dd:
                max_dd = drawdown
        
        return max_dd
    
    def _calculate_volatility(self, profits: List[float]) -> float:
        """Calculate volatility (standard deviation) of profits."""
        if len(profits) < 2:
            return 0.0
        
        mean = sum(profits) / len(profits)
        variance = sum((p - mean) ** 2 for p in profits) / (len(profits) - 1)
        return variance ** 0.5
    
    def _calculate_sharpe_ratio(self, profits: List[float]) -> float:
        """Calculate Sharpe ratio (assuming risk-free rate = 0)."""
        if not profits:
            return 0.0
        
        mean_return = sum(profits) / len(profits)
        volatility = self._calculate_volatility(profits)
        
        if volatility == 0:
            return 0.0
        
        return mean_return / volatility


def load_experiment_config(config_file: str) -> Dict[str, Any]:
    """Load experiment configuration from YAML or JSON file."""
    config_path = Path(config_file)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")
    
    with open(config_path, 'r') as f:
        if config_path.suffix.lower() in ['.yaml', '.yml']:
            return yaml.safe_load(f)
        else:
            return json.load(f)


def main():
    """Main entry point for experiment runner."""
    parser = argparse.ArgumentParser(
        description="Run trading bot experiments with parameter sweeps",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run single experiment
  python -m src.experiment_runner --llm-provider deepseek --max-position-size 0.05

  # Run parameter sweep
  python -m src.experiment_runner --config experiments/risk_sweep.yaml

  # Run provider comparison
  python -m src.experiment_runner --provider-sweep deepseek,openai,anthropic
        """
    )
    
    # Single experiment parameters
    parser.add_argument("--llm-provider", help="LLM provider to use")
    parser.add_argument("--llm-model", help="LLM model to use")
    parser.add_argument("--max-position-size", type=float, help="Maximum position size")
    parser.add_argument("--stop-loss-percent", type=float, help="Stop loss percentage")
    parser.add_argument("--take-profit-percent", type=float, help="Take profit percentage")
    parser.add_argument("--run-interval", type=int, help="Run interval in seconds")
    
    # Sweep parameters
    parser.add_argument("--config", help="Experiment configuration file (YAML/JSON)")
    parser.add_argument("--provider-sweep", help="Comma-separated list of providers to test")
    parser.add_argument("--risk-sweep", help="Comma-separated list of position sizes to test")
    
    # Experiment settings
    parser.add_argument("--duration", type=int, default=30, help="Experiment duration in minutes")
    parser.add_argument("--experiments-dir", help="Directory to store experiment results")
    
    args = parser.parse_args()
    
    # Initialize experiment runner
    experiments_dir = Path(args.experiments_dir) if args.experiments_dir else None
    runner = ExperimentRunner(experiments_dir)
    
    if args.config:
        # Load configuration from file
        sweep_config = load_experiment_config(args.config)
        results = runner.run_parameter_sweep(sweep_config, args.duration)
    else:
        # Generate configuration from command line arguments
        if args.provider_sweep or args.risk_sweep:
            # Parameter sweep
            sweep_config = {}
            
            if args.provider_sweep:
                sweep_config["llm_provider"] = args.provider_sweep.split(",")
            
            if args.risk_sweep:
                sweep_config["max_position_size"] = [float(x) for x in args.risk_sweep.split(",")]
            
            results = runner.run_parameter_sweep(sweep_config, args.duration)
        else:
            # Single experiment
            experiment_params = {}
            
            if args.llm_provider:
                experiment_params["llm_provider"] = args.llm_provider
            if args.llm_model:
                experiment_params["llm_model"] = args.llm_model
            if args.max_position_size:
                experiment_params["max_position_size"] = args.max_position_size
            if args.stop_loss_percent:
                experiment_params["stop_loss_percent"] = args.stop_loss_percent
            if args.take_profit_percent:
                experiment_params["take_profit_percent"] = args.take_profit_percent
            if args.run_interval:
                experiment_params["run_interval"] = args.run_interval
            
            result = runner.run_single_experiment(experiment_params, args.duration)
            print(f"Experiment completed: {result}")


if __name__ == "__main__":
    main()
