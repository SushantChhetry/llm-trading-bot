#!/usr/bin/env python3
"""
Live Monitoring Dashboard for DeepSeek Trading Bot

Provides real-time monitoring of trading bot performance, LLM decisions,
and alerts for dangerous patterns or anomalies.
"""

import json
import time
import argparse
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import os

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import config


class TradingMonitor:
    """
    Live monitoring dashboard for trading bot performance.
    
    Tracks:
    - Latest trades and P&L
    - LLM decision patterns
    - Risk metrics and alerts
    - Performance trends
    """
    
    def __init__(self, data_dir: Path = None, refresh_interval: int = 5):
        """
        Initialize the trading monitor.
        
        Args:
            data_dir: Directory containing bot data
            refresh_interval: Refresh interval in seconds
        """
        self.data_dir = data_dir or config.DATA_DIR
        self.refresh_interval = refresh_interval
        self.trades_file = self.data_dir / "trades.json"
        self.portfolio_file = self.data_dir / "portfolio.json"
        self.log_file = self.data_dir / "logs" / "bot.log"
        
        # Alert thresholds
        self.alert_config = {
            "max_consecutive_losses": 5,
            "min_confidence_threshold": 0.3,
            "max_confidence_threshold": 0.95,
            "max_drawdown_percent": 10.0,
            "min_trade_interval_minutes": 1
        }
        
        # State tracking
        self.last_trade_count = 0
        self.consecutive_losses = 0
        self.last_alert_time = {}
        
    def start_monitoring(self, duration_minutes: int = None):
        """
        Start live monitoring dashboard.
        
        Args:
            duration_minutes: How long to monitor (None for indefinite)
        """
        print("🔍 Starting Trading Bot Monitor")
        print("=" * 60)
        print(f"Data Directory: {self.data_dir}")
        print(f"Refresh Interval: {self.refresh_interval}s")
        print("Press Ctrl+C to stop")
        print("=" * 60)
        
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes) if duration_minutes else None
        
        try:
            while True:
                if end_time and datetime.now() > end_time:
                    print("\n⏰ Monitoring duration completed")
                    break
                
                self._display_status()
                self._check_alerts()
                time.sleep(self.refresh_interval)
                
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")
    
    def _display_status(self):
        """Display current bot status."""
        # Clear screen (works on most terminals)
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("🤖 DEEPSEEK TRADING BOT - LIVE MONITOR")
        print("=" * 60)
        print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Portfolio status
        portfolio = self._load_portfolio()
        if portfolio:
            print("💰 PORTFOLIO STATUS")
            print("-" * 30)
            print(f"Balance: ${portfolio.get('balance', 0):,.2f}")
            print(f"Total Value: ${portfolio.get('total_value', 0):,.2f}")
            print(f"Open Positions: {portfolio.get('open_positions', 0)}")
            print()
        
        # Recent trades
        trades = self._load_trades()
        if trades:
            print("📊 RECENT TRADES (Last 10)")
            print("-" * 30)
            recent_trades = trades[-10:]
            for trade in recent_trades:
                side_emoji = "🟢" if trade.get("side") == "buy" else "🔴"
                profit_str = ""
                if "profit" in trade:
                    profit_str = f" (P&L: ${trade['profit']:.2f})"
                
                print(f"{side_emoji} {trade.get('timestamp', 'N/A')[:19]} | "
                      f"{trade.get('side', 'N/A').upper()} | "
                      f"${trade.get('price', 0):,.2f} | "
                      f"Conf: {trade.get('confidence', 0):.2f}{profit_str}")
            print()
        
        # Performance metrics
        if trades:
            metrics = self._calculate_metrics(trades)
            print("📈 PERFORMANCE METRICS")
            print("-" * 30)
            print(f"Total Trades: {metrics['total_trades']}")
            print(f"Win Rate: {metrics['win_rate']:.1f}%")
            print(f"Total P&L: ${metrics['total_profit']:.2f}")
            print(f"Max Drawdown: ${metrics['max_drawdown']:.2f}")
            print(f"Avg Confidence: {metrics['avg_confidence']:.2f}")
            print()
        
        # LLM decision patterns
        llm_patterns = self._analyze_llm_patterns(trades)
        if llm_patterns:
            print("🤖 LLM DECISION PATTERNS")
            print("-" * 30)
            print(f"Buy Decisions: {llm_patterns['buy_count']}")
            print(f"Sell Decisions: {llm_patterns['sell_count']}")
            print(f"Hold Decisions: {llm_patterns['hold_count']}")
            print(f"Avg Confidence: {llm_patterns['avg_confidence']:.2f}")
            print(f"Risk Distribution: {llm_patterns['risk_distribution']}")
            print()
        
        # System status
        print("⚙️  SYSTEM STATUS")
        print("-" * 30)
        print(f"Trading Mode: {config.TRADING_MODE.upper()}")
        print(f"Data Source: {'TESTNET' if config.USE_TESTNET else 'LIVE'}")
        print(f"LLM Provider: {config.LLM_PROVIDER.upper()}")
        print(f"Exchange: {config.EXCHANGE.upper()}")
        print(f"Symbol: {config.SYMBOL}")
        print()
    
    def _check_alerts(self):
        """Check for dangerous patterns and generate alerts."""
        trades = self._load_trades()
        if not trades:
            return
        
        current_time = datetime.now()
        
        # Check consecutive losses
        recent_trades = trades[-10:]  # Last 10 trades
        sell_trades = [t for t in recent_trades if t.get("side") == "sell"]
        
        if sell_trades:
            consecutive_losses = 0
            for trade in reversed(sell_trades):
                if trade.get("profit", 0) < 0:
                    consecutive_losses += 1
                else:
                    break
            
            if consecutive_losses >= self.alert_config["max_consecutive_losses"]:
                self._trigger_alert("consecutive_losses", 
                                  f"⚠️  ALERT: {consecutive_losses} consecutive losses!")
        
        # Check LLM confidence patterns
        recent_decisions = [t for t in recent_trades if "confidence" in t]
        if recent_decisions:
            avg_confidence = sum(t["confidence"] for t in recent_decisions) / len(recent_decisions)
            
            if avg_confidence < self.alert_config["min_confidence_threshold"]:
                self._trigger_alert("low_confidence", 
                                  f"⚠️  ALERT: Low LLM confidence ({avg_confidence:.2f})")
            elif avg_confidence > self.alert_config["max_confidence_threshold"]:
                self._trigger_alert("high_confidence", 
                                  f"⚠️  ALERT: Unusually high LLM confidence ({avg_confidence:.2f})")
        
        # Check drawdown
        if len(trades) > 5:
            profits = [t.get("profit", 0) for t in trades if t.get("side") == "sell"]
            if profits:
                max_drawdown = self._calculate_max_drawdown(profits)
                total_value = self._get_total_value()
                drawdown_percent = (max_drawdown / total_value * 100) if total_value > 0 else 0
                
                if drawdown_percent > self.alert_config["max_drawdown_percent"]:
                    self._trigger_alert("high_drawdown", 
                                      f"⚠️  ALERT: High drawdown ({drawdown_percent:.1f}%)")
    
    def _trigger_alert(self, alert_type: str, message: str):
        """Trigger an alert if not recently triggered."""
        current_time = datetime.now()
        last_alert = self.last_alert_time.get(alert_type)
        
        # Rate limit alerts (max once per 5 minutes)
        if last_alert and (current_time - last_alert).seconds < 300:
            return
        
        self.last_alert_time[alert_type] = current_time
        print(f"\n🚨 {message}")
        
        # Log alert
        alert_log = self.data_dir / "alerts.log"
        with open(alert_log, "a") as f:
            f.write(f"{current_time.isoformat()} - {alert_type.upper()}: {message}\n")
    
    def _load_trades(self) -> List[Dict[str, Any]]:
        """Load trades from file."""
        if not self.trades_file.exists():
            return []
        
        try:
            with open(self.trades_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading trades: {e}")
            return []
    
    def _load_portfolio(self) -> Optional[Dict[str, Any]]:
        """Load portfolio state from file."""
        if not self.portfolio_file.exists():
            return None
        
        try:
            with open(self.portfolio_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading portfolio: {e}")
            return None
    
    def _calculate_metrics(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate performance metrics from trades."""
        if not trades:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "total_profit": 0.0,
                "max_drawdown": 0.0,
                "avg_confidence": 0.0
            }
        
        sell_trades = [t for t in trades if t.get("side") == "sell"]
        total_trades = len(trades)
        
        # Win rate
        profitable_trades = len([t for t in sell_trades if t.get("profit", 0) > 0])
        win_rate = (profitable_trades / len(sell_trades) * 100) if sell_trades else 0
        
        # Total profit
        total_profit = sum(t.get("profit", 0) for t in sell_trades)
        
        # Max drawdown
        profits = [t.get("profit", 0) for t in sell_trades]
        max_drawdown = self._calculate_max_drawdown(profits)
        
        # Average confidence
        confidences = [t.get("confidence", 0) for t in trades if "confidence" in t]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            "total_trades": total_trades,
            "win_rate": win_rate,
            "total_profit": total_profit,
            "max_drawdown": max_drawdown,
            "avg_confidence": avg_confidence
        }
    
    def _analyze_llm_patterns(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze LLM decision patterns."""
        if not trades:
            return {}
        
        buy_count = len([t for t in trades if t.get("side") == "buy"])
        sell_count = len([t for t in trades if t.get("side") == "sell"])
        hold_count = len(trades) - buy_count - sell_count
        
        confidences = [t.get("confidence", 0) for t in trades if "confidence" in t]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        # Risk assessment distribution
        risk_counts = {}
        for trade in trades:
            risk = trade.get("llm_risk_assessment", "unknown")
            risk_counts[risk] = risk_counts.get(risk, 0) + 1
        
        return {
            "buy_count": buy_count,
            "sell_count": sell_count,
            "hold_count": hold_count,
            "avg_confidence": avg_confidence,
            "risk_distribution": risk_counts
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
    
    def _get_total_value(self) -> float:
        """Get current total portfolio value."""
        portfolio = self._load_portfolio()
        return portfolio.get("total_value", 0) if portfolio else 0


def main():
    """Main entry point for monitoring dashboard."""
    parser = argparse.ArgumentParser(
        description="Live monitoring dashboard for trading bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Monitor indefinitely
  python scripts/monitor_dashboard.py

  # Monitor for 60 minutes
  python scripts/monitor_dashboard.py --duration 60

  # Custom refresh interval
  python scripts/monitor_dashboard.py --refresh-interval 10

  # Custom data directory
  python scripts/monitor_dashboard.py --data-dir /path/to/data
        """
    )
    
    parser.add_argument(
        "--duration", 
        type=int, 
        help="Monitoring duration in minutes (default: indefinite)"
    )
    parser.add_argument(
        "--refresh-interval", 
        type=int, 
        default=5, 
        help="Refresh interval in seconds (default: 5)"
    )
    parser.add_argument(
        "--data-dir", 
        help="Directory containing bot data (default: project data dir)"
    )
    parser.add_argument(
        "--max-consecutive-losses", 
        type=int, 
        default=5, 
        help="Alert threshold for consecutive losses (default: 5)"
    )
    parser.add_argument(
        "--max-drawdown-percent", 
        type=float, 
        default=10.0, 
        help="Alert threshold for drawdown percentage (default: 10.0)"
    )
    
    args = parser.parse_args()
    
    # Initialize monitor
    data_dir = Path(args.data_dir) if args.data_dir else None
    monitor = TradingMonitor(data_dir, args.refresh_interval)
    
    # Update alert configuration
    monitor.alert_config["max_consecutive_losses"] = args.max_consecutive_losses
    monitor.alert_config["max_drawdown_percent"] = args.max_drawdown_percent
    
    # Start monitoring
    monitor.start_monitoring(args.duration)


if __name__ == "__main__":
    main()
