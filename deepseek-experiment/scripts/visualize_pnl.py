#!/usr/bin/env python3
"""
P&L Visualization Script for DeepSeek Trading Bot

Analyzes trade history and portfolio data to create visualizations
showing trading performance, P&L trends, and LLM decision patterns.
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from typing import Dict, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import config


class PnLAnalyzer:
    """Analyzes trading data and creates visualizations."""
    
    def __init__(self, data_dir: Path = None):
        """
        Initialize the P&L analyzer.
        
        Args:
            data_dir: Directory containing trade and portfolio data
        """
        self.data_dir = data_dir or config.DATA_DIR
        self.trades_file = self.data_dir / "trades.json"
        self.portfolio_file = self.data_dir / "portfolio.json"
        
        self.trades = []
        self.portfolio_history = []
        
        self._load_data()
    
    def _load_data(self):
        """Load trade and portfolio data from files."""
        # Load trades
        if self.trades_file.exists():
            try:
                with open(self.trades_file, 'r') as f:
                    self.trades = json.load(f)
                print(f"✅ Loaded {len(self.trades)} trades from {self.trades_file}")
            except Exception as e:
                print(f"❌ Error loading trades: {e}")
        else:
            print(f"⚠️  No trades file found at {self.trades_file}")
        
        # Load portfolio history (if available)
        if self.portfolio_file.exists():
            try:
                with open(self.portfolio_file, 'r') as f:
                    portfolio_data = json.load(f)
                    self.portfolio_history = [portfolio_data]  # Single snapshot for now
                print(f"✅ Loaded portfolio data from {self.portfolio_file}")
            except Exception as e:
                print(f"❌ Error loading portfolio: {e}")
    
    def analyze_trades(self) -> Dict:
        """Analyze trade data and return summary statistics."""
        if not self.trades:
            return {"error": "No trades found"}
        
        df = pd.DataFrame(self.trades)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Basic statistics
        total_trades = len(df)
        buy_trades = len(df[df['side'] == 'buy'])
        sell_trades = len(df[df['side'] == 'sell'])
        
        # P&L analysis
        sell_df = df[df['side'] == 'sell'].copy()
        total_profit = sell_df['profit'].sum() if 'profit' in sell_df.columns else 0
        avg_profit_per_trade = total_profit / sell_trades if sell_trades > 0 else 0
        
        # Win rate
        profitable_trades = len(sell_df[sell_df['profit'] > 0]) if 'profit' in sell_df.columns else 0
        win_rate = (profitable_trades / sell_trades * 100) if sell_trades > 0 else 0
        
        # LLM analysis
        avg_confidence = df['confidence'].mean() if 'confidence' in df.columns else 0
        risk_distribution = df['llm_risk_assessment'].value_counts().to_dict() if 'llm_risk_assessment' in df.columns else {}
        
        return {
            "total_trades": total_trades,
            "buy_trades": buy_trades,
            "sell_trades": sell_trades,
            "total_profit": total_profit,
            "avg_profit_per_trade": avg_profit_per_trade,
            "win_rate": win_rate,
            "avg_confidence": avg_confidence,
            "risk_distribution": risk_distribution
        }
    
    def plot_pnl_timeline(self, save_path: str = None):
        """Create P&L timeline visualization."""
        if not self.trades:
            print("❌ No trades to visualize")
            return
        
        df = pd.DataFrame(self.trades)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Calculate cumulative P&L
        sell_df = df[df['side'] == 'sell'].copy()
        if 'profit' in sell_df.columns:
            sell_df = sell_df.sort_values('timestamp')
            sell_df['cumulative_profit'] = sell_df['profit'].cumsum()
            
            # Create plot
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
            
            # P&L timeline
            ax1.plot(sell_df['timestamp'], sell_df['cumulative_profit'], 
                    marker='o', linewidth=2, markersize=4)
            ax1.axhline(y=0, color='r', linestyle='--', alpha=0.7)
            ax1.set_title('Cumulative P&L Over Time', fontsize=14, fontweight='bold')
            ax1.set_ylabel('Cumulative Profit ($)')
            ax1.grid(True, alpha=0.3)
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
            ax1.xaxis.set_major_locator(mdates.HourLocator(interval=2))
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
            
            # Individual trade profits
            colors = ['green' if p > 0 else 'red' for p in sell_df['profit']]
            ax2.bar(range(len(sell_df)), sell_df['profit'], color=colors, alpha=0.7)
            ax2.axhline(y=0, color='black', linestyle='-', alpha=0.5)
            ax2.set_title('Individual Trade Profits', fontsize=14, fontweight='bold')
            ax2.set_ylabel('Profit per Trade ($)')
            ax2.set_xlabel('Trade Number')
            ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                print(f"📊 P&L chart saved to {save_path}")
            else:
                plt.show()
        else:
            print("❌ No profit data found in trades")
    
    def plot_llm_analysis(self, save_path: str = None):
        """Create LLM decision analysis visualization."""
        if not self.trades:
            print("❌ No trades to analyze")
            return
        
        df = pd.DataFrame(self.trades)
        
        # Check if we have LLM data
        if 'llm_risk_assessment' not in df.columns:
            print("❌ No LLM data found in trades")
            return
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        # Risk assessment distribution
        risk_counts = df['llm_risk_assessment'].value_counts()
        ax1.pie(risk_counts.values, labels=risk_counts.index, autopct='%1.1f%%', startangle=90)
        ax1.set_title('LLM Risk Assessment Distribution', fontweight='bold')
        
        # Confidence distribution
        if 'confidence' in df.columns:
            ax2.hist(df['confidence'], bins=20, alpha=0.7, color='skyblue', edgecolor='black')
            ax2.set_title('LLM Confidence Distribution', fontweight='bold')
            ax2.set_xlabel('Confidence Score')
            ax2.set_ylabel('Frequency')
            ax2.grid(True, alpha=0.3)
        
        # Action distribution
        action_counts = df['side'].value_counts()
        ax3.bar(action_counts.index, action_counts.values, color=['green', 'red'], alpha=0.7)
        ax3.set_title('Trading Actions Distribution', fontweight='bold')
        ax3.set_ylabel('Number of Trades')
        
        # Position size distribution
        if 'llm_position_size' in df.columns:
            ax4.hist(df['llm_position_size'], bins=20, alpha=0.7, color='orange', edgecolor='black')
            ax4.set_title('LLM Position Size Distribution', fontweight='bold')
            ax4.set_xlabel('Position Size')
            ax4.set_ylabel('Frequency')
            ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"📊 LLM analysis chart saved to {save_path}")
        else:
            plt.show()
    
    def print_summary(self):
        """Print a summary of trading performance."""
        analysis = self.analyze_trades()
        
        if "error" in analysis:
            print(f"❌ {analysis['error']}")
            return
        
        print("\n" + "="*60)
        print("📊 TRADING PERFORMANCE SUMMARY")
        print("="*60)
        print(f"Total Trades: {analysis['total_trades']}")
        print(f"Buy Trades: {analysis['buy_trades']}")
        print(f"Sell Trades: {analysis['sell_trades']}")
        print(f"Total Profit: ${analysis['total_profit']:.2f}")
        print(f"Average Profit per Trade: ${analysis['avg_profit_per_trade']:.2f}")
        print(f"Win Rate: {analysis['win_rate']:.1f}%")
        print(f"Average LLM Confidence: {analysis['avg_confidence']:.2f}")
        
        if analysis['risk_distribution']:
            print("\nRisk Assessment Distribution:")
            for risk, count in analysis['risk_distribution'].items():
                print(f"  {risk.upper()}: {count} trades")
        
        print("="*60)


def main():
    """Main entry point for the visualization script."""
    parser = argparse.ArgumentParser(
        description="Visualize trading bot P&L and performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/visualize_pnl.py                    # Show summary and charts
  python scripts/visualize_pnl.py --save-charts     # Save charts to files
  python scripts/visualize_pnl.py --summary-only    # Show only summary
        """
    )
    
    parser.add_argument(
        "--data-dir",
        help="Directory containing trade data (default: project data dir)"
    )
    parser.add_argument(
        "--save-charts",
        action="store_true",
        help="Save charts to files instead of displaying"
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Show only summary statistics"
    )
    
    args = parser.parse_args()
    
    # Initialize analyzer
    data_dir = Path(args.data_dir) if args.data_dir else None
    analyzer = PnLAnalyzer(data_dir)
    
    # Print summary
    analyzer.print_summary()
    
    if not args.summary_only:
        # Generate charts
        if args.save_charts:
            charts_dir = Path("charts")
            charts_dir.mkdir(exist_ok=True)
            
            pnl_path = charts_dir / "pnl_timeline.png"
            llm_path = charts_dir / "llm_analysis.png"
            
            analyzer.plot_pnl_timeline(str(pnl_path))
            analyzer.plot_llm_analysis(str(llm_path))
        else:
            analyzer.plot_pnl_timeline()
            analyzer.plot_llm_analysis()


if __name__ == "__main__":
    main()
