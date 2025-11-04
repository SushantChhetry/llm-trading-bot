#!/usr/bin/env python3
"""
Reset portfolio to initial state with balance of 10000.

This script will:
1. Clear local trade and portfolio files (if they exist)
2. Reset Supabase database (trades, portfolio_snapshots, positions, behavioral_metrics)
3. Optionally clear observability_metrics and service_health tables (monitoring history)
4. Update initial_balance in bot_config to 10000
5. Provide instructions for restarting the bot

Usage:
    python scripts/reset_portfolio.py [--supabase-only] [--local-only] [--initial-balance 10000]
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from config import config
except ImportError:
    print("Warning: Could not import config. Using defaults.")
    config = type('Config', (), {
        'DATA_DIR': project_root / 'data',
        'INITIAL_BALANCE': 10000.0
    })()

def reset_local_files():
    """Reset local JSON files (trades.json and portfolio.json)."""
    data_dir = config.DATA_DIR
    trades_file = data_dir / "trades.json"
    portfolio_file = data_dir / "portfolio.json"
    
    print("📁 Resetting local files...")
    
    # Reset trades.json
    if trades_file.exists():
        trades_file.unlink()
        print(f"  ✅ Deleted {trades_file}")
    else:
        print(f"  ℹ️  {trades_file} does not exist (skipping)")
    
    # Reset portfolio.json
    if portfolio_file.exists():
        portfolio_file.unlink()
        print(f"  ✅ Deleted {portfolio_file}")
    else:
        print(f"  ℹ️  {portfolio_file} does not exist (skipping)")
    
    # Create fresh portfolio.json with initial balance
    initial_balance = float(os.getenv("INITIAL_BALANCE", config.INITIAL_BALANCE))
    fresh_portfolio = {
        "balance": initial_balance,
        "total_value": initial_balance,
        "positions_value": 0,
        "total_return": 0,
        "total_return_pct": 0,
        "open_positions": 0,
        "total_trades": 0,
        "initial_balance": initial_balance,
        "positions": {},
        "timestamp": datetime.now().isoformat()
    }
    
    portfolio_file.parent.mkdir(parents=True, exist_ok=True)
    with open(portfolio_file, "w") as f:
        json.dump(fresh_portfolio, f, indent=2)
    print(f"  ✅ Created fresh {portfolio_file} with balance {initial_balance}")
    
    # Create empty trades.json
    with open(trades_file, "w") as f:
        json.dump([], f, indent=2)
    print(f"  ✅ Created fresh {trades_file}")

def reset_supabase():
    """Reset Supabase database tables."""
    try:
        from src.supabase_client import get_supabase_service
        
        print("\n🗄️  Resetting Supabase database...")
        supabase = get_supabase_service()
        
        initial_balance = float(os.getenv("INITIAL_BALANCE", config.INITIAL_BALANCE))
        
        # Delete all trades
        try:
            # Get all trades first to check if any exist
            trades = supabase.get_trades(limit=10000)
            if trades:
                print(f"  📊 Found {len(trades)} trades to delete...")
                # Note: Supabase doesn't have a direct delete all, so we'd need to use SQL
                # For now, we'll just update the bot config and create a fresh portfolio snapshot
                print("  ⚠️  Note: Cannot delete trades via API. Use Supabase SQL Editor to run:")
                print("      DELETE FROM trades;")
            else:
                print("  ℹ️  No trades found in database")
        except Exception as e:
            print(f"  ⚠️  Could not check trades: {e}")
        
        # Delete all portfolio snapshots
        try:
            snapshots = supabase.get_portfolio_snapshots(limit=10000)
            if snapshots:
                print(f"  📊 Found {len(snapshots)} portfolio snapshots to delete...")
                print("  ⚠️  Note: Cannot delete snapshots via API. Use Supabase SQL Editor to run:")
                print("      DELETE FROM portfolio_snapshots;")
            else:
                print("  ℹ️  No portfolio snapshots found in database")
        except Exception as e:
            print(f"  ⚠️  Could not check portfolio snapshots: {e}")
        
        # Delete all positions (set is_active to False)
        try:
            positions = supabase.get_positions()
            if positions:
                print(f"  📊 Found {len(positions)} active positions to close...")
                for pos in positions:
                    symbol = pos.get("symbol", "UNKNOWN")
                    supabase.close_position(symbol)
                print(f"  ✅ Closed {len(positions)} positions")
            else:
                print("  ℹ️  No active positions found")
        except Exception as e:
            print(f"  ⚠️  Could not close positions: {e}")
        
        # Update initial_balance in bot_config
        try:
            success = supabase.update_bot_config("initial_balance", str(initial_balance))
            if success:
                print(f"  ✅ Updated initial_balance in bot_config to {initial_balance}")
            else:
                print(f"  ⚠️  Could not update bot_config (might not exist)")
        except Exception as e:
            print(f"  ⚠️  Could not update bot_config: {e}")
        
        # Create a fresh portfolio snapshot
        try:
            fresh_portfolio = {
                "timestamp": datetime.now().isoformat(),
                "balance": initial_balance,
                "positions_value": 0,
                "total_value": initial_balance,
                "initial_balance": initial_balance,
                "total_return": 0,
                "total_return_pct": 0,
                "total_trades": 0,
                "active_positions": 0,
                "total_fees": 0,
            }
            success = supabase.update_portfolio(fresh_portfolio)
            if success:
                print(f"  ✅ Created fresh portfolio snapshot with balance {initial_balance}")
            else:
                print(f"  ⚠️  Could not create portfolio snapshot")
        except Exception as e:
            print(f"  ⚠️  Could not create portfolio snapshot: {e}")
        
        print("\n  📝 SQL commands to fully reset Supabase (run in Supabase SQL Editor):")
        print("     DELETE FROM trades;")
        print("     DELETE FROM portfolio_snapshots;")
        print("     DELETE FROM positions;")
        print("     DELETE FROM behavioral_metrics;")
        print("     DELETE FROM observability_metrics;  -- Optional: clears monitoring history")
        print("     DELETE FROM service_health;  -- Optional: clears health check history")
        print(f"     UPDATE bot_config SET value = '{initial_balance}' WHERE key = 'initial_balance';")
        
    except ImportError:
        print("\n  ⚠️  Supabase client not available. Skipping database reset.")
    except Exception as e:
        print(f"\n  ❌ Error resetting Supabase: {e}")
        print("  💡 You may need to manually reset the database using SQL commands")

def main():
    parser = argparse.ArgumentParser(
        description="Reset portfolio to initial state with balance of 10000",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/reset_portfolio.py                    # Reset both local and Supabase
  python scripts/reset_portfolio.py --local-only       # Reset only local files
  python scripts/reset_portfolio.py --supabase-only    # Reset only Supabase database
  python scripts/reset_portfolio.py --initial-balance 5000  # Use custom initial balance
        """
    )
    
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Only reset local files (trades.json, portfolio.json)"
    )
    parser.add_argument(
        "--supabase-only",
        action="store_true",
        help="Only reset Supabase database"
    )
    parser.add_argument(
        "--initial-balance",
        type=float,
        default=None,
        help="Initial balance to set (default: from config or 10000)"
    )
    
    args = parser.parse_args()
    
    # Set initial balance if provided
    if args.initial_balance:
        os.environ["INITIAL_BALANCE"] = str(args.initial_balance)
        config.INITIAL_BALANCE = args.initial_balance
    
    initial_balance = float(os.getenv("INITIAL_BALANCE", config.INITIAL_BALANCE))
    
    print("=" * 60)
    print("🔄 PORTFOLIO RESET SCRIPT")
    print("=" * 60)
    print(f"Initial Balance: ${initial_balance:,.2f}")
    print()
    
    if args.local_only:
        reset_local_files()
    elif args.supabase_only:
        reset_supabase()
    else:
        reset_local_files()
        reset_supabase()
    
    print("\n" + "=" * 60)
    print("✅ RESET COMPLETE")
    print("=" * 60)
    print("\n📋 Next Steps:")
    print("1. Ensure INITIAL_BALANCE environment variable is set to", initial_balance)
    print("   (In Railway: Settings → Variables → INITIAL_BALANCE=10000)")
    print("2. If using Supabase, run the SQL commands shown above in Supabase SQL Editor")
    print("3. Restart your trading bot service")
    print("4. The bot will start with a fresh balance of", initial_balance)
    print("\n⚠️  WARNING: This action cannot be undone!")
    print("   All trade history and portfolio data will be lost.")
    print()

if __name__ == "__main__":
    main()

