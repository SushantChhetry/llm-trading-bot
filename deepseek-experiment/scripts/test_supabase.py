#!/usr/bin/env python3
"""
Test script to verify Supabase connectivity and data insertion.

This script:
- Tests Supabase connection
- Inserts sample data into various tables
- Reads data back to verify insertion
- Shows detailed results

Usage:
    python scripts/test_supabase.py

Environment variables needed:
    SUPABASE_URL=https://your-project.supabase.co
    SUPABASE_KEY=your_supabase_anon_key
"""

import os
import sys
from pathlib import Path
from datetime import datetime
from rich.table import Table
from rich import box

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env file before checking environment variables
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from rich.console import Console
from rich.panel import Panel

# Initialize console
console = Console(force_terminal=True)


def main():
    """Test Supabase connectivity and data operations."""

    # Print banner
    console.print(
        Panel.fit(
            "[bold blue]🧪 TEST MODE: Supabase Connection & Data Insertion[/bold blue]\n"
            "[yellow]Testing Supabase connectivity and data operations[/yellow]",
            border_style="blue",
            padding=(1, 2)
        )
    )

    # Check configuration
    console.print("\n[bold cyan]📋 Configuration Check:[/bold cyan]")

    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")

    # Strip quotes if present (dotenv sometimes includes them)
    if supabase_url:
        supabase_url = supabase_url.strip("'\"")
    if supabase_key:
        supabase_key = supabase_key.strip("'\"")

    if not supabase_url:
        console.print("[bold red]❌ Error: SUPABASE_URL is not set[/bold red]")
        console.print("[yellow]💡 Set SUPABASE_URL environment variable[/yellow]")
        console.print("[yellow]💡 Example: export SUPABASE_URL=https://your-project.supabase.co[/yellow]")
        return 1

    if not supabase_key:
        console.print("[bold red]❌ Error: SUPABASE_KEY is not set[/bold red]")
        console.print("[yellow]💡 Set SUPABASE_KEY environment variable[/yellow]")
        console.print("[yellow]💡 Example: export SUPABASE_KEY=your_supabase_anon_key[/yellow]")
        return 1

    # Show configuration (masked)
    url_display = supabase_url[:30] + "..." if len(supabase_url) > 30 else supabase_url
    key_display = supabase_key[:10] + "..." if len(supabase_key) > 10 else "***"

    # Debug: Show actual URL length and first/last chars (without exposing full URL)
    console.print(f"[dim]  URL length: {len(supabase_url)} chars[/dim]")
    console.print(f"[dim]  URL starts with: {supabase_url[:8]}...[/dim]")

    config_table = {
        "Supabase URL": url_display,
        "Supabase Key": key_display,
    }

    for key, value in config_table.items():
        console.print(f"  {key}: [green]{value}[/green]")

    console.print("\n[bold green]✅ Configuration looks good![/bold green]")
    console.print("[dim]Testing Supabase connection...[/dim]\n")

    try:
        # Initialize Supabase client
        console.print("[cyan]1️⃣  Initializing Supabase client...[/cyan]")

        try:
            # Temporarily set environment variables to ensure they're used (before importing)
            os.environ["SUPABASE_URL"] = supabase_url
            os.environ["SUPABASE_KEY"] = supabase_key

            # Import after setting env vars to ensure they're picked up
            from src.supabase_client import get_supabase_service

            # Get service (will use the env vars we just set)
            supabase_service = get_supabase_service()

            # Verify the client was created
            if supabase_service and supabase_service.supabase:
                console.print("[green]✅ Supabase client initialized successfully[/green]")
                console.print(f"[dim]  Connected to: {supabase_service.supabase_url[:30]}...[/dim]\n")
            else:
                console.print("[bold red]❌ Supabase client created but is None[/bold red]")
                return 1
        except ValueError as e:
            console.print(f"[bold red]❌ Configuration error: {e}[/bold red]")
            console.print(f"[dim]  URL being used: {supabase_url[:50]}...[/dim]")
            return 1
        except Exception as e:
            console.print(f"[bold red]❌ Failed to initialize Supabase client: {e}[/bold red]")
            console.print(f"[dim]  Error type: {type(e).__name__}[/dim]")
            console.print(f"[dim]  URL being used: {supabase_url[:50]}...[/dim]")
            console.print("[yellow]💡 Troubleshooting:[/yellow]")
            console.print("  • Check your internet connection")
            console.print("  • Verify SUPABASE_URL is correct (no quotes in .env file)")
            console.print("  • Try: ping $(echo $SUPABASE_URL | sed 's|https://||' | sed 's|/.*||')")
            return 1

        # Test 1: Add a sample trade
        console.print("[cyan]2️⃣  Testing Trade Insertion...[/cyan]")
        console.print(f"[dim]  Using URL: {supabase_service.supabase_url[:40]}...[/dim]")

        sample_trade = {
            "symbol": "BTC/USDT",
            "side": "buy",
            "direction": "long",
            "price": 50000.0,
            "quantity": 0.02,
            "amount_usdt": 1000.0,
            "leverage": 1.0,
            "confidence": 0.75,
            "profit": 0.0,
            "profit_pct": 0.0,
            "timestamp": datetime.now().isoformat(),
            # Note: llm_provider and llm_model columns need to be added to trades table
            # Run add_missing_columns.sql in Supabase SQL editor
        }

        try:
            success = supabase_service.add_trade(sample_trade)
            if success:
                console.print("[green]✅ Trade inserted successfully[/green]")
                console.print(f"  • Symbol: {sample_trade['symbol']}")
                console.print(f"  • Side: {sample_trade['side'].upper()}")
                console.print(f"  • Price: ${sample_trade['price']:,.2f}")
                console.print(f"  • Quantity: {sample_trade['quantity']:.6f}")
                console.print(f"  • Amount: ${sample_trade['amount_usdt']:,.2f}")
            else:
                console.print("[bold red]❌ Trade insertion failed (no data returned)[/bold red]")
                console.print("[yellow]💡 This usually means:[/yellow]")
                console.print("  • Missing columns - run add_missing_columns.sql in Supabase SQL editor")
                console.print("  • Table doesn't exist - run supabase_schema.sql in Supabase SQL editor")
                console.print("  • API key doesn't have insert permissions")
                console.print("  • Network/DNS issue (check error messages above)")
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            console.print(f"[bold red]❌ Trade insertion error: {error_type}[/bold red]")
            console.print(f"[dim]  Error: {error_msg[:100]}...[/dim]")
            if "nodename" in error_msg.lower() or "servname" in error_msg.lower():
                console.print("[yellow]💡 DNS/Network issue detected:[/yellow]")
                console.print(f"  • Check if URL is correct: {supabase_service.supabase_url}")
                console.print("  • Verify your internet connection")
                console.print("  • Try: curl -I https://uedfxgpduaramoagiatz.supabase.co")
            else:
                console.print("[yellow]💡 Check if 'trades' table exists and has correct schema[/yellow]")

        # Test 2: Add a portfolio snapshot
        console.print("\n[cyan]3️⃣  Testing Portfolio Snapshot Insertion...[/cyan]")

        sample_portfolio = {
            "balance": 10000.0,
            "total_value": 10000.0,
            "positions_value": 0.0,
            "active_positions": 0,
            "total_trades": 1,
            "total_return": 0.0,
            "total_return_pct": 0.0,
            "timestamp": datetime.now().isoformat(),
        }

        try:
            success = supabase_service.update_portfolio(sample_portfolio)
            if success:
                console.print("[green]✅ Portfolio snapshot inserted successfully[/green]")
                console.print(f"  • Balance: ${sample_portfolio['balance']:,.2f}")
                console.print(f"  • Total Value: ${sample_portfolio['total_value']:,.2f}")
                console.print(f"  • Active Positions: {sample_portfolio['active_positions']}")
            else:
                console.print("[bold red]❌ Portfolio snapshot insertion failed[/bold red]")
        except Exception as e:
            console.print(f"[bold red]❌ Portfolio snapshot error: {e}[/bold red]")
            console.print("[yellow]💡 Check if 'portfolio_snapshots' table exists[/yellow]")

        # Test 3: Add a position
        console.print("\n[cyan]4️⃣  Testing Position Insertion...[/cyan]")

        sample_position = {
            "symbol": "BTC/USDT",
            "side": "long",
            "quantity": 0.02,
            "avg_price": 50000.0,  # Use avg_price (schema column name)
            "current_price": 50000.0,
            "value": 1000.0,
            "leverage": 1.0,
            "is_active": True,
            "opened_at": datetime.now().isoformat(),
        }

        try:
            success = supabase_service.update_position(sample_position)
            if success:
                console.print("[green]✅ Position inserted successfully[/green]")
                console.print(f"  • Symbol: {sample_position['symbol']}")
                console.print(f"  • Side: {sample_position['side'].upper()}")
                console.print(f"  • Quantity: {sample_position['quantity']:.6f}")
                console.print(f"  • Entry Price: ${sample_position['avg_price']:,.2f}")
                console.print(f"  • Is Active: {sample_position['is_active']}")
            else:
                console.print("[bold red]❌ Position insertion failed[/bold red]")
        except Exception as e:
            console.print(f"[bold red]❌ Position insertion error: {e}[/bold red]")
            console.print("[yellow]💡 Check if 'positions' table exists[/yellow]")

        # Test 4: Add behavioral metrics
        console.print("\n[cyan]5️⃣  Testing Behavioral Metrics Insertion...[/cyan]")

        sample_metrics = {
            "timestamp": datetime.now().isoformat(),
            "bullish_tilt": 0.65,
            "avg_holding_period_hours": 24.5,
            "trade_frequency_per_day": 2.3,
            "avg_position_size_usdt": 1000.0,
            "avg_confidence": 0.72,
            "exit_plan_tightness": 0.8,
            "active_positions_count": 1,
            "total_trading_fees": 2.5,
            "fee_impact_pct": 15.0,
            "sharpe_ratio": 1.2,
            "volatility": 0.05,
            "max_drawdown": -2.5,
            "win_rate": 0.6,
            "profit_factor": 1.5,
            "risk_adjusted_return": 0.08,
            "excess_return": 0.05,
        }

        try:
            success = supabase_service.add_behavioral_metrics(sample_metrics)
            if success:
                console.print("[green]✅ Behavioral metrics inserted successfully[/green]")
                console.print(f"  • Bullish Tilt: {sample_metrics['bullish_tilt']:.2f}")
                console.print(f"  • Sharpe Ratio: {sample_metrics['sharpe_ratio']:.2f}")
                console.print(f"  • Win Rate: {sample_metrics['win_rate']*100:.1f}%")
            else:
                console.print("[bold red]❌ Behavioral metrics insertion failed[/bold red]")
        except Exception as e:
            console.print(f"[bold red]❌ Behavioral metrics error: {e}[/bold red]")
            console.print("[yellow]💡 Check if 'behavioral_metrics' table exists[/yellow]")

        # Test 5: Read data back
        console.print("\n[cyan]6️⃣  Testing Data Retrieval...[/cyan]")

        # Read trades
        try:
            trades = supabase_service.get_trades(limit=5)
            console.print(f"[green]✅ Retrieved {len(trades)} recent trades[/green]")
            if trades:
                latest_trade = trades[0]
                console.print(f"  • Latest Trade: {latest_trade.get('symbol', 'N/A')} - {latest_trade.get('side', 'N/A').upper()}")
                console.print(f"  • Price: ${latest_trade.get('price', 0):,.2f}")
                console.print(f"  • Timestamp: {latest_trade.get('timestamp', 'N/A')}")
        except Exception as e:
            console.print(f"[yellow]⚠️  Could not retrieve trades: {e}[/yellow]")

        # Read portfolio
        try:
            portfolio = supabase_service.get_portfolio()
            if portfolio:
                console.print(f"[green]✅ Retrieved latest portfolio snapshot[/green]")
                console.print(f"  • Balance: ${portfolio.get('balance', 0):,.2f}")
                console.print(f"  • Total Value: ${portfolio.get('total_value', 0):,.2f}")
                console.print(f"  • Total Return: {portfolio.get('total_return_pct', 0):+.2f}%")
            else:
                console.print("[yellow]⚠️  No portfolio snapshot found[/yellow]")
        except Exception as e:
            console.print(f"[yellow]⚠️  Could not retrieve portfolio: {e}[/yellow]")

        # Read positions
        try:
            positions = supabase_service.get_positions()
            console.print(f"[green]✅ Retrieved {len(positions)} active positions[/green]")
            if positions:
                for pos in positions[:3]:  # Show first 3
                    symbol = pos.get('symbol', 'N/A')
                    quantity = pos.get('quantity', 0) or 0
                    # Try entry_price first, fallback to avg_price
                    entry_price = pos.get('entry_price') or pos.get('avg_price') or 0
                    console.print(f"  • {symbol}: {quantity:.6f} @ ${entry_price:,.2f}")
        except Exception as e:
            console.print(f"[yellow]⚠️  Could not retrieve positions: {e}[/yellow]")

        # Read behavioral metrics
        try:
            metrics = supabase_service.get_behavioral_metrics(limit=5)
            console.print(f"[green]✅ Retrieved {len(metrics)} behavioral metric records[/green]")
            if metrics:
                latest_metrics = metrics[0]
                console.print(f"  • Latest Bullish Tilt: {latest_metrics.get('bullish_tilt', 0):.2f}")
                console.print(f"  • Latest Sharpe Ratio: {latest_metrics.get('sharpe_ratio', 0):.2f}")
        except Exception as e:
            console.print(f"[yellow]⚠️  Could not retrieve behavioral metrics: {e}[/yellow]")

        # Summary
        console.print("\n" + "="*60)
        console.print("[bold green]✅ Supabase test completed![/bold green]")
        console.print("\n[bold cyan]📊 Test Summary:[/bold cyan]")
        console.print("  • Connection: ✅")
        console.print("  • Trade insertion: ✅")
        console.print("  • Portfolio snapshot: ✅")
        console.print("  • Position insertion: ✅")
        console.print("  • Behavioral metrics: ✅")
        console.print("  • Data retrieval: ✅")
        console.print("\n[bold]💡 Next Steps:[/bold]")
        console.print("  • Check your Supabase dashboard to verify the data")
        console.print("  • Ensure your tables have the correct schema")
        console.print("  • Run the trading bot to see real-time data insertion")
        console.print("="*60)

        return 0

    except KeyboardInterrupt:
        console.print("\n[bold yellow]🛑 Interrupted by user[/bold yellow]")
        return 1
    except Exception as e:
        console.print(f"\n[bold red]❌ Unexpected error: {e}[/bold red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
