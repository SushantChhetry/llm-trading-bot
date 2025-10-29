#!/usr/bin/env python3
"""
Results Comparison Tool for DeepSeek Trading Bot Experiments

Compares multiple experiment results and generates comparative analysis
including tables, plots, and statistical comparisons.
"""

import json
import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class ExperimentComparator:
    """
    Compares multiple experiment results and generates analysis.
    
    Supports:
    - Loading experiment results from multiple sources
    - Statistical comparison across parameters
    - Visual analysis with plots and charts
    - Export to CSV and image formats
    """
    
    def __init__(self, experiments_dir: Path = None):
        """
        Initialize the experiment comparator.
        
        Args:
            experiments_dir: Directory containing experiment results
        """
        self.experiments_dir = experiments_dir or Path("data/experiments")
        self.results = []
        self.comparison_data = None
        
    def load_experiments(self, 
                        experiment_ids: List[str] = None,
                        sweep_files: List[str] = None,
                        results_dir: str = None) -> List[Dict[str, Any]]:
        """
        Load experiment results from various sources.
        
        Args:
            experiment_ids: List of specific experiment IDs to load
            sweep_files: List of sweep result files to load
            results_dir: Directory containing individual experiment results
            
        Returns:
            List of loaded experiment results
        """
        self.results = []
        
        # Load individual experiments
        if experiment_ids:
            for exp_id in experiment_ids:
                result = self._load_single_experiment(exp_id)
                if result:
                    self.results.append(result)
        
        # Load sweep results
        if sweep_files:
            for sweep_file in sweep_files:
                sweep_results = self._load_sweep_results(sweep_file)
                self.results.extend(sweep_results)
        
        # Load all experiments from directory
        if results_dir:
            results_path = Path(results_dir)
            if results_path.exists():
                for exp_dir in results_path.iterdir():
                    if exp_dir.is_dir():
                        result = self._load_single_experiment(exp_dir.name)
                        if result:
                            self.results.append(result)
        
        print(f"Loaded {len(self.results)} experiment results")
        return self.results
    
    def compare_by_parameter(self, 
                           parameter: str,
                           metrics: List[str] = None) -> pd.DataFrame:
        """
        Compare experiments grouped by a specific parameter.
        
        Args:
            parameter: Parameter to group by (e.g., 'llm_provider', 'max_position_size')
            metrics: List of metrics to compare (default: all available)
            
        Returns:
            DataFrame with comparison results
        """
        if not self.results:
            print("No experiment results loaded")
            return pd.DataFrame()
        
        # Default metrics
        if metrics is None:
            metrics = [
                'total_trades', 'total_profit', 'win_rate', 'max_drawdown',
                'sharpe_ratio', 'volatility', 'avg_trade_duration'
            ]
        
        # Group results by parameter
        grouped_data = defaultdict(list)
        for result in self.results:
            param_value = result.get('parameters', {}).get(parameter, 'Unknown')
            grouped_data[param_value].append(result)
        
        # Calculate statistics for each group
        comparison_data = []
        for param_value, group_results in grouped_data.items():
            group_metrics = self._calculate_group_metrics(group_results, metrics)
            group_metrics['parameter'] = parameter
            group_metrics['parameter_value'] = param_value
            group_metrics['experiment_count'] = len(group_results)
            comparison_data.append(group_metrics)
        
        self.comparison_data = pd.DataFrame(comparison_data)
        return self.comparison_data
    
    def generate_comparison_plots(self, 
                                parameter: str,
                                metrics: List[str] = None,
                                save_path: str = None) -> None:
        """
        Generate comparison plots for experiments.
        
        Args:
            parameter: Parameter to compare by
            metrics: Metrics to plot (default: key metrics)
            save_path: Path to save plots (default: display)
        """
        if self.comparison_data is None:
            self.compare_by_parameter(parameter, metrics)
        
        if metrics is None:
            metrics = ['total_profit', 'win_rate', 'sharpe_ratio', 'max_drawdown']
        
        # Set up the plotting style
        plt.style.use('seaborn-v0_8')
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle(f'Experiment Comparison by {parameter.replace("_", " ").title()}', 
                     fontsize=16, fontweight='bold')
        
        # Plot each metric
        for i, metric in enumerate(metrics[:4]):  # Limit to 4 plots
            ax = axes[i // 2, i % 2]
            
            if metric in self.comparison_data.columns:
                # Bar plot
                bars = ax.bar(self.comparison_data['parameter_value'], 
                            self.comparison_data[metric])
                ax.set_title(f'{metric.replace("_", " ").title()}')
                ax.set_xlabel(parameter.replace('_', ' ').title())
                ax.set_ylabel(metric.replace('_', ' ').title())
                
                # Add value labels on bars
                for bar, value in zip(bars, self.comparison_data[metric]):
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{value:.2f}', ha='center', va='bottom')
                
                # Rotate x-axis labels if needed
                if len(self.comparison_data['parameter_value'].iloc[0]) > 10:
                    ax.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Comparison plots saved to {save_path}")
        else:
            plt.show()
    
    def generate_correlation_analysis(self, 
                                    save_path: str = None) -> pd.DataFrame:
        """
        Generate correlation analysis between parameters and metrics.
        
        Args:
            save_path: Path to save correlation matrix plot
            
        Returns:
            Correlation matrix DataFrame
        """
        if not self.results:
            print("No experiment results loaded")
            return pd.DataFrame()
        
        # Prepare data for correlation analysis
        analysis_data = []
        for result in self.results:
            row = {}
            
            # Add parameters
            params = result.get('parameters', {})
            for key, value in params.items():
                if isinstance(value, (int, float)):
                    row[f'param_{key}'] = value
                elif isinstance(value, str):
                    # Convert string parameters to numeric for correlation
                    if value in ['deepseek', 'openai', 'anthropic']:
                        row[f'param_{key}'] = ['deepseek', 'openai', 'anthropic'].index(value)
                    elif value in ['paper', 'live']:
                        row[f'param_{key}'] = 0 if value == 'paper' else 1
                    elif value in ['true', 'false']:
                        row[f'param_{key}'] = 1 if value == 'true' else 0
            
            # Add metrics
            metrics = result.get('metrics', {})
            for key, value in metrics.items():
                if isinstance(value, (int, float)):
                    row[f'metric_{key}'] = value
            
            analysis_data.append(row)
        
        df = pd.DataFrame(analysis_data)
        
        if df.empty:
            print("No numeric data available for correlation analysis")
            return pd.DataFrame()
        
        # Calculate correlation matrix
        correlation_matrix = df.corr()
        
        # Plot correlation heatmap
        if save_path:
            plt.figure(figsize=(12, 10))
            sns.heatmap(correlation_matrix, 
                       annot=True, 
                       cmap='coolwarm', 
                       center=0,
                       fmt='.2f')
            plt.title('Parameter-Metric Correlation Matrix')
            plt.tight_layout()
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Correlation analysis saved to {save_path}")
        
        return correlation_matrix
    
    def export_comparison_table(self, 
                              output_file: str,
                              format: str = 'csv') -> None:
        """
        Export comparison results to file.
        
        Args:
            output_file: Output file path
            format: Output format ('csv', 'json', 'excel')
        """
        if self.comparison_data is None:
            print("No comparison data available. Run compare_by_parameter first.")
            return
        
        output_path = Path(output_file)
        
        if format.lower() == 'csv':
            self.comparison_data.to_csv(output_path, index=False)
        elif format.lower() == 'json':
            self.comparison_data.to_json(output_path, orient='records', indent=2)
        elif format.lower() == 'excel':
            self.comparison_data.to_excel(output_path, index=False)
        else:
            print(f"Unsupported format: {format}")
            return
        
        print(f"Comparison table exported to {output_file}")
    
    def print_summary_statistics(self) -> None:
        """Print summary statistics for all loaded experiments."""
        if not self.results:
            print("No experiment results loaded")
            return
        
        print("\n" + "="*60)
        print("EXPERIMENT SUMMARY STATISTICS")
        print("="*60)
        
        # Overall statistics
        total_experiments = len(self.results)
        successful_experiments = len([r for r in self.results if r.get('success', False)])
        
        print(f"Total Experiments: {total_experiments}")
        print(f"Successful: {successful_experiments}")
        print(f"Success Rate: {successful_experiments/total_experiments*100:.1f}%")
        
        # Parameter distribution
        print("\nParameter Distribution:")
        param_counts = defaultdict(int)
        for result in self.results:
            params = result.get('parameters', {})
            for key, value in params.items():
                param_counts[f"{key}: {value}"] += 1
        
        for param, count in sorted(param_counts.items()):
            print(f"  {param}: {count}")
        
        # Metric statistics
        print("\nMetric Statistics:")
        all_metrics = defaultdict(list)
        for result in self.results:
            if result.get('success', False):
                metrics = result.get('metrics', {})
                for key, value in metrics.items():
                    if isinstance(value, (int, float)):
                        all_metrics[key].append(value)
        
        for metric, values in all_metrics.items():
            if values:
                print(f"  {metric}:")
                print(f"    Mean: {sum(values)/len(values):.2f}")
                print(f"    Min: {min(values):.2f}")
                print(f"    Max: {max(values):.2f}")
                print(f"    Std: {(sum((x - sum(values)/len(values))**2 for x in values) / len(values))**0.5:.2f}")
    
    def _load_single_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """Load a single experiment result."""
        exp_dir = self.experiments_dir / "logs" / experiment_id
        results_file = exp_dir / "results.json"
        
        if not results_file.exists():
            print(f"Experiment {experiment_id} not found")
            return None
        
        try:
            with open(results_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading experiment {experiment_id}: {e}")
            return None
    
    def _load_sweep_results(self, sweep_file: str) -> List[Dict[str, Any]]:
        """Load results from a sweep file."""
        try:
            with open(sweep_file, 'r') as f:
                sweep_data = json.load(f)
                return sweep_data.get('results', [])
        except Exception as e:
            print(f"Error loading sweep file {sweep_file}: {e}")
            return []
    
    def _calculate_group_metrics(self, 
                               group_results: List[Dict[str, Any]], 
                               metrics: List[str]) -> Dict[str, Any]:
        """Calculate statistics for a group of experiments."""
        group_metrics = {}
        
        for metric in metrics:
            values = []
            for result in group_results:
                if result.get('success', False):
                    metric_value = result.get('metrics', {}).get(metric)
                    if metric_value is not None:
                        values.append(metric_value)
            
            if values:
                group_metrics[f'{metric}_mean'] = sum(values) / len(values)
                group_metrics[f'{metric}_std'] = (sum((x - sum(values)/len(values))**2 for x in values) / len(values))**0.5
                group_metrics[f'{metric}_min'] = min(values)
                group_metrics[f'{metric}_max'] = max(values)
            else:
                group_metrics[f'{metric}_mean'] = 0
                group_metrics[f'{metric}_std'] = 0
                group_metrics[f'{metric}_min'] = 0
                group_metrics[f'{metric}_max'] = 0
        
        return group_metrics


def main():
    """Main entry point for results comparison."""
    parser = argparse.ArgumentParser(
        description="Compare trading bot experiment results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Compare by LLM provider
  python scripts/compare_results.py --parameter llm_provider

  # Compare by position size
  python scripts/compare_results.py --parameter max_position_size

  # Load specific experiments
  python scripts/compare_results.py --experiments exp1,exp2,exp3 --parameter llm_provider

  # Generate plots and export results
  python scripts/compare_results.py --parameter llm_provider --plot --export results.csv
        """
    )
    
    parser.add_argument(
        "--parameter", 
        required=True,
        help="Parameter to compare by (e.g., llm_provider, max_position_size)"
    )
    parser.add_argument(
        "--experiments", 
        help="Comma-separated list of experiment IDs to compare"
    )
    parser.add_argument(
        "--sweep-files", 
        help="Comma-separated list of sweep result files to load"
    )
    parser.add_argument(
        "--results-dir", 
        help="Directory containing experiment results"
    )
    parser.add_argument(
        "--metrics", 
        help="Comma-separated list of metrics to compare"
    )
    parser.add_argument(
        "--plot", 
        action="store_true",
        help="Generate comparison plots"
    )
    parser.add_argument(
        "--correlation", 
        action="store_true",
        help="Generate correlation analysis"
    )
    parser.add_argument(
        "--export", 
        help="Export results to file (CSV, JSON, or Excel)"
    )
    parser.add_argument(
        "--output-dir", 
        default="comparison_results",
        help="Directory to save output files"
    )
    
    args = parser.parse_args()
    
    # Initialize comparator
    comparator = ExperimentComparator()
    
    # Load experiments
    experiment_ids = args.experiments.split(",") if args.experiments else None
    sweep_files = args.sweep_files.split(",") if args.sweep_files else None
    metrics = args.metrics.split(",") if args.metrics else None
    
    comparator.load_experiments(
        experiment_ids=experiment_ids,
        sweep_files=sweep_files,
        results_dir=args.results_dir
    )
    
    if not comparator.results:
        print("No experiment results loaded. Exiting.")
        return
    
    # Print summary
    comparator.print_summary_statistics()
    
    # Compare by parameter
    comparison_df = comparator.compare_by_parameter(args.parameter, metrics)
    print(f"\nComparison by {args.parameter}:")
    print(comparison_df.to_string(index=False))
    
    # Generate plots
    if args.plot:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(exist_ok=True)
        
        plot_file = output_dir / f"comparison_{args.parameter}.png"
        comparator.generate_comparison_plots(args.parameter, metrics, str(plot_file))
    
    # Generate correlation analysis
    if args.correlation:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(exist_ok=True)
        
        corr_file = output_dir / "correlation_analysis.png"
        comparator.generate_correlation_analysis(str(corr_file))
    
    # Export results
    if args.export:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(exist_ok=True)
        
        export_path = output_dir / args.export
        format_type = export_path.suffix[1:] if export_path.suffix else 'csv'
        comparator.export_comparison_table(str(export_path), format_type)


if __name__ == "__main__":
    main()
