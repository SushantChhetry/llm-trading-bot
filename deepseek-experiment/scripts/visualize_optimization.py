#!/usr/bin/env python3
"""
Visualization Tools for Hyperparameter Optimization Results

Creates heatmaps, scatter plots, and other visualizations to analyze
the impact of different parameters on trading strategy performance.
"""

import json
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns
    import numpy as np
    from matplotlib.colors import LinearSegmentedColormap
except ImportError as e:
    print(f"Required packages not installed: {e}")
    print("Install with: pip install pandas matplotlib seaborn numpy")
    sys.exit(1)

logger = logging.getLogger(__name__)


class OptimizationVisualizer:
    """
    Creates visualizations for hyperparameter optimization results.
    
    Supports:
    - Parameter impact heatmaps
    - Scatter plots for parameter relationships
    - Performance distribution plots
    - Best configuration analysis
    """
    
    def __init__(self, optimization_dir: Path = None):
        """
        Initialize the optimization visualizer.
        
        Args:
            optimization_dir: Directory containing optimization results
        """
        self.optimization_dir = optimization_dir or Path("data/optimization")
        self.results_df = None
        self.best_configs = None
        
        # Set up plotting style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
    
    def load_results(self, results_file: str = None) -> pd.DataFrame:
        """
        Load optimization results from file.
        
        Args:
            results_file: Path to results file (CSV, JSON, or Excel)
            
        Returns:
            DataFrame with optimization results
        """
        if results_file is None:
            # Find the most recent results file
            results_files = list(self.optimization_dir.glob("results/*.csv"))
            if not results_files:
                results_files = list(self.optimization_dir.glob("results/*.json"))
            if not results_files:
                raise FileNotFoundError("No results files found in optimization directory")
            
            results_file = max(results_files, key=lambda x: x.stat().st_mtime)
        
        results_path = Path(results_file)
        
        # Load based on file extension
        if results_path.suffix.lower() == '.csv':
            self.results_df = pd.read_csv(results_path)
        elif results_path.suffix.lower() == '.json':
            with open(results_path, 'r') as f:
                data = json.load(f)
            self.results_df = pd.DataFrame(data)
        elif results_path.suffix.lower() in ['.xlsx', '.xls']:
            self.results_df = pd.read_excel(results_path)
        else:
            raise ValueError(f"Unsupported file format: {results_path.suffix}")
        
        logger.info(f"Loaded {len(self.results_df)} optimization results")
        return self.results_df
    
    def create_parameter_heatmap(self, 
                               param1: str, 
                               param2: str, 
                               metric: str = "sharpe_ratio",
                               save_path: str = None) -> None:
        """
        Create heatmap showing parameter interaction effects.
        
        Args:
            param1: First parameter for x-axis
            param2: Second parameter for y-axis
            metric: Performance metric to visualize
            save_path: Path to save the plot
        """
        if self.results_df is None:
            raise ValueError("No results loaded. Call load_results() first.")
        
        # Pivot data for heatmap
        heatmap_data = self.results_df.pivot_table(
            values=f"{metric}_mean", 
            index=param2, 
            columns=param1, 
            aggfunc='mean'
        )
        
        # Create heatmap
        plt.figure(figsize=(12, 8))
        sns.heatmap(
            heatmap_data, 
            annot=True, 
            fmt='.3f', 
            cmap='RdYlBu_r',
            center=heatmap_data.values.mean(),
            cbar_kws={'label': f'{metric} (mean)'}
        )
        
        plt.title(f'Parameter Interaction: {param1} vs {param2}\nPerformance Metric: {metric}')
        plt.xlabel(param1)
        plt.ylabel(param2)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Heatmap saved to {save_path}")
        else:
            plt.show()
    
    def create_scatter_plot(self, 
                          param: str, 
                          metric: str = "sharpe_ratio",
                          color_by: str = None,
                          save_path: str = None) -> None:
        """
        Create scatter plot showing parameter vs performance relationship.
        
        Args:
            param: Parameter to plot on x-axis
            metric: Performance metric to plot on y-axis
            color_by: Parameter to use for coloring points
            save_path: Path to save the plot
        """
        if self.results_df is None:
            raise ValueError("No results loaded. Call load_results() first.")
        
        plt.figure(figsize=(10, 6))
        
        if color_by and color_by in self.results_df.columns:
            scatter = plt.scatter(
                self.results_df[param], 
                self.results_df[f"{metric}_mean"],
                c=self.results_df[color_by],
                cmap='viridis',
                alpha=0.7,
                s=60
            )
            plt.colorbar(scatter, label=color_by)
        else:
            plt.scatter(
                self.results_df[param], 
                self.results_df[f"{metric}_mean"],
                alpha=0.7,
                s=60
            )
        
        plt.xlabel(param)
        plt.ylabel(f'{metric} (mean)')
        plt.title(f'Parameter Impact: {param} vs {metric}')
        plt.grid(True, alpha=0.3)
        
        # Add trend line
        z = np.polyfit(self.results_df[param], self.results_df[f"{metric}_mean"], 1)
        p = np.poly1d(z)
        plt.plot(self.results_df[param], p(self.results_df[param]), "r--", alpha=0.8)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Scatter plot saved to {save_path}")
        else:
            plt.show()
    
    def create_performance_distribution(self, 
                                      metric: str = "sharpe_ratio",
                                      save_path: str = None) -> None:
        """
        Create distribution plot of performance metrics.
        
        Args:
            metric: Performance metric to visualize
            save_path: Path to save the plot
        """
        if self.results_df is None:
            raise ValueError("No results loaded. Call load_results() first.")
        
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        
        # Histogram
        axes[0].hist(
            self.results_df[f"{metric}_mean"], 
            bins=20, 
            alpha=0.7, 
            edgecolor='black'
        )
        axes[0].set_xlabel(f'{metric} (mean)')
        axes[0].set_ylabel('Frequency')
        axes[0].set_title(f'Distribution of {metric}')
        axes[0].grid(True, alpha=0.3)
        
        # Box plot
        axes[1].boxplot(self.results_df[f"{metric}_mean"])
        axes[1].set_ylabel(f'{metric} (mean)')
        axes[1].set_title(f'{metric} Distribution (Box Plot)')
        axes[1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Distribution plot saved to {save_path}")
        else:
            plt.show()
    
    def create_parameter_importance_plot(self, 
                                       metrics: List[str] = None,
                                       save_path: str = None) -> None:
        """
        Create plot showing parameter importance across different metrics.
        
        Args:
            metrics: List of metrics to analyze
            save_path: Path to save the plot
        """
        if self.results_df is None:
            raise ValueError("No results loaded. Call load_results() first.")
        
        if metrics is None:
            metrics = ["sharpe_ratio", "win_rate", "total_profit", "max_drawdown"]
        
        # Get numeric parameter columns
        param_cols = [col for col in self.results_df.columns 
                     if col not in ['config_id', 'parameters'] and 
                     not col.endswith('_mean') and 
                     not col.endswith('_std') and 
                     not col.endswith('_min') and 
                     not col.endswith('_max') and
                     not col.endswith('_n_runs') and
                     not col.endswith('_success_rate')]
        
        # Calculate correlations
        correlations = {}
        for metric in metrics:
            if f"{metric}_mean" in self.results_df.columns:
                correlations[metric] = self.results_df[param_cols].corrwith(
                    self.results_df[f"{metric}_mean"]
                ).abs()
        
        # Create correlation heatmap
        corr_df = pd.DataFrame(correlations).T
        corr_df = corr_df.fillna(0)
        
        plt.figure(figsize=(12, 8))
        sns.heatmap(
            corr_df, 
            annot=True, 
            fmt='.3f', 
            cmap='YlOrRd',
            cbar_kws={'label': 'Absolute Correlation'}
        )
        
        plt.title('Parameter Importance Across Metrics')
        plt.xlabel('Parameters')
        plt.ylabel('Performance Metrics')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Parameter importance plot saved to {save_path}")
        else:
            plt.show()
    
    def create_best_configs_analysis(self, 
                                   top_k: int = 5,
                                   metric: str = "sharpe_ratio",
                                   save_path: str = None) -> None:
        """
        Create analysis of best performing configurations.
        
        Args:
            top_k: Number of top configurations to analyze
            metric: Metric to rank by
            save_path: Path to save the plot
        """
        if self.results_df is None:
            raise ValueError("No results loaded. Call load_results() first.")
        
        # Get top configurations
        top_configs = self.results_df.nlargest(top_k, f"{metric}_mean")
        
        # Create subplot
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle(f'Top {top_k} Configurations Analysis', fontsize=16)
        
        # 1. Performance comparison
        axes[0, 0].barh(
            range(len(top_configs)), 
            top_configs[f"{metric}_mean"],
            xerr=top_configs[f"{metric}_std"]
        )
        axes[0, 0].set_yticks(range(len(top_configs)))
        axes[0, 0].set_yticklabels([f"Config {i+1}" for i in range(len(top_configs))])
        axes[0, 0].set_xlabel(f'{metric} (mean ± std)')
        axes[0, 0].set_title(f'Top {top_k} by {metric}')
        axes[0, 0].grid(True, alpha=0.3)
        
        # 2. Parameter values heatmap
        param_cols = [col for col in top_configs.columns 
                     if col not in ['config_id', 'parameters'] and 
                     not col.endswith('_mean') and 
                     not col.endswith('_std') and 
                     not col.endswith('_min') and 
                     not col.endswith('_max') and
                     not col.endswith('_n_runs') and
                     not col.endswith('_success_rate')]
        
        if param_cols:
            param_data = top_configs[param_cols].T
            sns.heatmap(
                param_data, 
                annot=True, 
                fmt='.3f', 
                cmap='Blues',
                ax=axes[0, 1],
                cbar_kws={'label': 'Parameter Value'}
            )
            axes[0, 1].set_title('Parameter Values')
            axes[0, 1].set_xlabel('Configuration')
        
        # 3. Multiple metrics comparison
        metrics_to_plot = ["sharpe_ratio", "win_rate", "total_profit"]
        available_metrics = [m for m in metrics_to_plot if f"{m}_mean" in top_configs.columns]
        
        if available_metrics:
            x = np.arange(len(top_configs))
            width = 0.25
            
            for i, metric in enumerate(available_metrics):
                axes[1, 0].bar(
                    x + i * width, 
                    top_configs[f"{metric}_mean"],
                    width, 
                    label=metric,
                    alpha=0.8
                )
            
            axes[1, 0].set_xlabel('Configuration')
            axes[1, 0].set_ylabel('Metric Value')
            axes[1, 0].set_title('Multiple Metrics Comparison')
            axes[1, 0].set_xticks(x + width)
            axes[1, 0].set_xticklabels([f"Config {i+1}" for i in range(len(top_configs))])
            axes[1, 0].legend()
            axes[1, 0].grid(True, alpha=0.3)
        
        # 4. Risk-return scatter
        if "max_drawdown_mean" in top_configs.columns and f"{metric}_mean" in top_configs.columns:
            scatter = axes[1, 1].scatter(
                top_configs["max_drawdown_mean"],
                top_configs[f"{metric}_mean"],
                s=100,
                alpha=0.7,
                c=range(len(top_configs)),
                cmap='viridis'
            )
            axes[1, 1].set_xlabel('Max Drawdown (mean)')
            axes[1, 1].set_ylabel(f'{metric} (mean)')
            axes[1, 1].set_title('Risk vs Return')
            axes[1, 1].grid(True, alpha=0.3)
            
            # Add configuration labels
            for i, (_, config) in enumerate(top_configs.iterrows()):
                axes[1, 1].annotate(
                    f"C{i+1}", 
                    (config["max_drawdown_mean"], config[f"{metric}_mean"]),
                    xytext=(5, 5), 
                    textcoords='offset points',
                    fontsize=8
                )
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"Best configs analysis saved to {save_path}")
        else:
            plt.show()
    
    def create_comprehensive_report(self, 
                                  output_dir: str = None,
                                  top_k: int = 5) -> None:
        """
        Create comprehensive visualization report.
        
        Args:
            output_dir: Directory to save all plots
            top_k: Number of top configurations to analyze
        """
        if self.results_df is None:
            raise ValueError("No results loaded. Call load_results() first.")
        
        if output_dir is None:
            output_dir = self.optimization_dir / "plots"
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        logger.info(f"Creating comprehensive report in {output_path}")
        
        # Get numeric parameter columns
        param_cols = [col for col in self.results_df.columns 
                     if col not in ['config_id', 'parameters'] and 
                     not col.endswith('_mean') and 
                     not col.endswith('_std') and 
                     not col.endswith('_min') and 
                     not col.endswith('_max') and
                     not col.endswith('_n_runs') and
                     not col.endswith('_success_rate')]
        
        # 1. Performance distribution
        self.create_performance_distribution(
            save_path=str(output_path / "performance_distribution.png")
        )
        
        # 2. Parameter importance
        self.create_parameter_importance_plot(
            save_path=str(output_path / "parameter_importance.png")
        )
        
        # 3. Best configurations analysis
        self.create_best_configs_analysis(
            top_k=top_k,
            save_path=str(output_path / "best_configs_analysis.png")
        )
        
        # 4. Parameter interaction heatmaps (if we have enough data)
        if len(param_cols) >= 2:
            for i, param1 in enumerate(param_cols[:3]):  # Limit to first 3 params
                for param2 in param_cols[i+1:4]:  # Limit to next 3 params
                    try:
                        self.create_parameter_heatmap(
                            param1, param2,
                            save_path=str(output_path / f"heatmap_{param1}_vs_{param2}.png")
                        )
                    except Exception as e:
                        logger.warning(f"Could not create heatmap for {param1} vs {param2}: {e}")
        
        # 5. Individual parameter scatter plots
        for param in param_cols[:6]:  # Limit to first 6 params
            try:
                self.create_scatter_plot(
                    param,
                    save_path=str(output_path / f"scatter_{param}.png")
                )
            except Exception as e:
                logger.warning(f"Could not create scatter plot for {param}: {e}")
        
        logger.info(f"Comprehensive report created in {output_path}")


def main():
    """Main entry point for optimization visualization."""
    parser = argparse.ArgumentParser(
        description="Visualize hyperparameter optimization results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create comprehensive report
  python scripts/visualize_optimization.py --comprehensive

  # Create specific heatmap
  python scripts/visualize_optimization.py --heatmap max_position_size stop_loss_percent

  # Analyze best configurations
  python scripts/visualize_optimization.py --best-configs --top-k 10

  # Parameter importance analysis
  python scripts/visualize_optimization.py --importance
        """
    )
    
    parser.add_argument(
        "--results-file", 
        help="Path to optimization results file"
    )
    parser.add_argument(
        "--optimization-dir", 
        help="Directory containing optimization results"
    )
    
    # Specific visualizations
    parser.add_argument(
        "--heatmap", 
        nargs=2, 
        metavar=('PARAM1', 'PARAM2'),
        help="Create heatmap for two parameters"
    )
    parser.add_argument(
        "--scatter", 
        help="Create scatter plot for a parameter"
    )
    parser.add_argument(
        "--distribution", 
        help="Create performance distribution plot"
    )
    parser.add_argument(
        "--importance", 
        action="store_true",
        help="Create parameter importance plot"
    )
    parser.add_argument(
        "--best-configs", 
        action="store_true",
        help="Create best configurations analysis"
    )
    parser.add_argument(
        "--comprehensive", 
        action="store_true",
        help="Create comprehensive visualization report"
    )
    
    # Analysis settings
    parser.add_argument(
        "--metric", 
        default="sharpe_ratio",
        help="Performance metric to analyze (default: sharpe_ratio)"
    )
    parser.add_argument(
        "--top-k", 
        type=int, 
        default=5,
        help="Number of top configurations to analyze (default: 5)"
    )
    parser.add_argument(
        "--output-dir", 
        help="Directory to save plots"
    )
    
    args = parser.parse_args()
    
    # Initialize visualizer
    optimization_dir = Path(args.optimization_dir) if args.optimization_dir else None
    visualizer = OptimizationVisualizer(optimization_dir)
    
    # Load results
    try:
        visualizer.load_results(args.results_file)
    except Exception as e:
        logger.error(f"Failed to load results: {e}")
        return
    
    # Create visualizations
    if args.comprehensive:
        visualizer.create_comprehensive_report(args.output_dir, args.top_k)
    else:
        if args.heatmap:
            visualizer.create_parameter_heatmap(
                args.heatmap[0], args.heatmap[1], args.metric
            )
        
        if args.scatter:
            visualizer.create_scatter_plot(args.scatter, args.metric)
        
        if args.distribution:
            visualizer.create_performance_distribution(args.metric)
        
        if args.importance:
            visualizer.create_parameter_importance_plot()
        
        if args.best_configs:
            visualizer.create_best_configs_analysis(args.top_k, args.metric)


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    main()
