#!/usr/bin/env python3
"""
Test script to run a single trading cycle with real LLM and Kraken exchange.

This script:
- Uses real LLM provider (not mock mode)
- Connects to Kraken exchange
- Runs a single trading cycle with actual trade execution
- Shows detailed decision-making process

Usage:
    python scripts/test_real_llm_kraken.py

Environment variables needed:
    LLM_PROVIDER=deepseek (or openai, anthropic)
    LLM_API_KEY=your-api-key
    EXCHANGE=kraken
    EXCHANGE_API_KEY=your-kraken-key (optional for paper trading)
    EXCHANGE_API_SECRET=your-kraken-secret (optional for paper trading)
"""

import os
import sys
from pathlib import Path
from rich.table import Table
from rich import box

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import config
from src.data_fetcher import DataFetcher
from src.llm_client import LLMClient
from src.logger import get_logger
from src.trading_engine import TradingEngine
from rich.console import Console
from rich.panel import Panel
from datetime import datetime

# Initialize logger
logger = get_logger(__name__)
console = Console(force_terminal=True)


def main():
    """Run a single trading cycle with real LLM and Kraken."""

    # Print banner
    console.print(
        Panel.fit(
            "[bold blue]🧪 TEST MODE: Real LLM + Kraken[/bold blue]\n"
            "[yellow]Running a single trading cycle to see what happens[/yellow]",
            border_style="blue",
            padding=(1, 2)
        )
    )

    # Check configuration
    console.print("\n[bold cyan]📋 Configuration Check:[/bold cyan]")

    # Override config to ensure we're using real LLM and Kraken
    llm_provider = os.getenv("LLM_PROVIDER", config.LLM_PROVIDER)
    if llm_provider == "mock":
        console.print("[bold red]❌ Error: LLM_PROVIDER is set to 'mock'[/bold red]")
        console.print("[yellow]💡 Set LLM_PROVIDER environment variable to 'deepseek', 'openai', or 'anthropic'[/yellow]")
        console.print("[yellow]💡 Example: export LLM_PROVIDER=deepseek[/yellow]")
        return 1

    llm_api_key = os.getenv("LLM_API_KEY", config.LLM_API_KEY)
    if not llm_api_key:
        console.print("[bold red]❌ Error: LLM_API_KEY is not set[/bold red]")
        console.print("[yellow]💡 Set your LLM API key: export LLM_API_KEY=your-api-key[/yellow]")
        return 1

    exchange = os.getenv("EXCHANGE", config.EXCHANGE)
    if exchange.lower() != "kraken":
        console.print(f"[yellow]⚠️  Warning: EXCHANGE is set to '{exchange}', but this script is for Kraken[/yellow]")
        console.print("[yellow]💡 Set EXCHANGE=kraken to use Kraken[/yellow]")

    # Show configuration
    config_table = {
        "LLM Provider": f"{llm_provider.upper()} (LIVE)",
        "LLM API Key": f"{llm_api_key[:10]}..." if len(llm_api_key) > 10 else "***",
        "Exchange": exchange.upper(),
        "Symbol": os.getenv("SYMBOL", config.SYMBOL),
        "Trading Mode": os.getenv("TRADING_MODE", config.TRADING_MODE),
    }

    for key, value in config_table.items():
        console.print(f"  {key}: [green]{value}[/green]")

    console.print("\n[bold green]✅ Configuration looks good![/bold green]")
    console.print("[dim]Starting trading cycle...[/dim]\n")

    try:
        # Initialize components
        console.print("[cyan]1️⃣  Initializing components...[/cyan]")

        data_fetcher = DataFetcher()
        llm_client = LLMClient(provider=llm_provider, api_key=llm_api_key, mock_mode=False)
        trading_engine = TradingEngine()

        # Check if LLM is actually in live mode
        if llm_client.mock_mode:
            console.print("[bold red]❌ Error: LLM client is in mock mode despite having API key[/bold red]")
            console.print("[yellow]💡 Check your API key format[/yellow]")
            return 1

        console.print(f"[green]✅ LLM Client: {llm_provider.upper()} (LIVE)[/green]")
        console.print(f"[green]✅ Data Fetcher: {exchange.upper()}[/green]")
        console.print(f"[green]✅ Trading Engine: Initialized[/green]\n")

        # Fetch market data
        console.print("[cyan]2️⃣  Fetching market data from Kraken...[/cyan]")
        try:
            ticker = data_fetcher.get_ticker()
            current_price = float(ticker["last"])
            price_change = ticker.get("percentage", 0)
            volume = ticker.get("quoteVolume", 0)

            # Display detailed market data
            price_color = "green" if price_change >= 0 else "red"
            console.print(f"[green]✅ Current Price:[/green] [bold {price_color}]${current_price:,.2f}[/bold {price_color}]")
            console.print(f"[green]✅ 24h Change:[/green] [{price_color}]{price_change:+.2f}%[/{price_color}]")
            console.print(f"[green]✅ 24h Volume:[/green] ${volume:,.2f}")
        except Exception as e:
            console.print(f"[bold red]❌ Failed to fetch market data: {e}[/bold red]")
            logger.error(f"Market data fetch error: {e}", exc_info=True)
            return 1

        # Fetch technical indicators
        console.print("\n[cyan]2️⃣.1️⃣  Fetching technical indicators...[/cyan]")
        try:
            indicators = data_fetcher.get_technical_indicators(timeframe="5m", limit=100)
            console.print(f"[green]✅ Technical indicators fetched[/green]")

            # Display technical indicators in a table
            indicators_table = Table(title="📊 Technical Indicators Analysis", box=box.ROUNDED, show_header=True, header_style="bold cyan")
            indicators_table.add_column("Indicator", style="cyan")
            indicators_table.add_column("Value", style="green")
            indicators_table.add_column("Signal", style="yellow")

            # EMA analysis
            ema_20 = indicators.get("ema_20", current_price)
            ema_50 = indicators.get("ema_50", current_price)
            ema_signal = "🟢 Bullish" if current_price > ema_20 > ema_50 else "🔴 Bearish" if current_price < ema_20 < ema_50 else "🟡 Neutral"
            indicators_table.add_row("EMA 20", f"${ema_20:,.2f}", "")
            indicators_table.add_row("EMA 50", f"${ema_50:,.2f}", "")
            indicators_table.add_row("Price vs EMAs", f"${current_price:,.2f}", ema_signal)

            # RSI analysis
            rsi_14 = indicators.get("rsi_14", 50.0)
            rsi_signal = "🔴 Overbought" if rsi_14 > 70 else "🟢 Oversold" if rsi_14 < 30 else "🟡 Neutral"
            indicators_table.add_row("RSI 14", f"{rsi_14:.2f}", rsi_signal)

            # MACD analysis
            macd = indicators.get("macd", 0.0)
            macd_signal = indicators.get("macd_signal", 0.0)
            macd_hist = indicators.get("macd_histogram", 0.0)
            macd_trend = "🟢 Bullish" if macd_hist > 0 and macd > macd_signal else "🔴 Bearish" if macd_hist < 0 else "🟡 Neutral"
            indicators_table.add_row("MACD", f"{macd:.4f}", "")
            indicators_table.add_row("MACD Signal", f"{macd_signal:.4f}", "")
            indicators_table.add_row("MACD Histogram", f"{macd_hist:.4f}", macd_trend)

            # ATR (volatility)
            atr = indicators.get("atr", current_price * 0.02)
            atr_pct = (atr / current_price) * 100
            volatility_signal = "🔴 High" if atr_pct > 3 else "🟢 Low" if atr_pct < 1 else "🟡 Medium"
            indicators_table.add_row("ATR (Volatility)", f"${atr:,.2f} ({atr_pct:.2f}%)", volatility_signal)

            console.print(indicators_table)

        except Exception as e:
            console.print(f"[yellow]⚠️  Could not fetch technical indicators: {e}[/yellow]")
            indicators = {
                "ema_20": current_price * 0.99,
                "ema_50": current_price * 0.98,
                "rsi_14": 50.0,
                "macd": 0.0,
                "macd_signal": 0.0,
                "macd_histogram": 0.0,
                "atr": current_price * 0.02,
                "current_price": current_price,
            }

        market_data = {
            "symbol": config.SYMBOL,
            "price": current_price,
            "volume": ticker.get("quoteVolume", 0),
            "change_24h": ticker.get("percentage", 0),
            "indicators": indicators,
        }

        # Get portfolio summary
        console.print("\n[cyan]3️⃣  Analyzing portfolio state...[/cyan]")
        portfolio = trading_engine.get_portfolio_summary(current_price)

        # Display detailed portfolio information
        portfolio_table = Table(title="💼 Portfolio State", box=box.ROUNDED, show_header=True, header_style="bold magenta")
        portfolio_table.add_column("Metric", style="cyan")
        portfolio_table.add_column("Value", style="green")

        return_pct = portfolio["total_return_pct"]
        return_color = "green" if return_pct >= 0 else "red"

        portfolio_table.add_row("Initial Balance", f"${portfolio.get('initial_balance', config.INITIAL_BALANCE):,.2f}")
        portfolio_table.add_row("Available Balance", f"${portfolio['balance']:,.2f}")
        portfolio_table.add_row("Positions Value", f"${portfolio.get('positions_value', 0):,.2f}")
        portfolio_table.add_row("Total Portfolio Value", f"${portfolio['total_value']:,.2f}")
        portfolio_table.add_row("Total Return", f"[{return_color}]{return_pct:+.2f}%[/{return_color}]")
        portfolio_table.add_row("Open Positions", str(portfolio.get('open_positions', 0)))
        portfolio_table.add_row("Total Trades", str(portfolio.get('total_trades', 0)))

        sharpe_ratio = portfolio.get("sharpe_ratio", 0.0)
        sharpe_color = "green" if sharpe_ratio > 1.0 else "yellow" if sharpe_ratio > 0.5 else "red"
        if sharpe_ratio is not None:
            portfolio_table.add_row("Sharpe Ratio", f"[{sharpe_color}]{sharpe_ratio:.3f}[/{sharpe_color}]")

        win_rate = portfolio.get("win_rate", 0.0)
        if win_rate is not None:
            portfolio_table.add_row("Win Rate", f"{win_rate*100:.1f}%")

        console.print(portfolio_table)

        # Display behavioral metrics if available
        if "bullish_tilt" in portfolio:
            console.print("\n[bold]📊 Trading Behavior Analysis:[/bold]")
            bullish_tilt = portfolio.get("bullish_tilt", 0.5)
            tilt_color = "green" if bullish_tilt > 0.6 else "red" if bullish_tilt < 0.4 else "yellow"
            console.print(f"  • Bullish Tilt: [{tilt_color}]{bullish_tilt:.2f}[/{tilt_color}] (0=bearish, 1=bullish)")
            console.print(f"  • Avg Holding Period: {portfolio.get('avg_holding_period_hours', 0):.1f} hours")
            console.print(f"  • Trade Frequency: {portfolio.get('trade_frequency_per_day', 0):.1f} trades/day")
            console.print(f"  • Total Trading Fees: ${portfolio.get('total_trading_fees', 0):.2f}")

        # Get LLM decision
        console.print("\n[cyan]4️⃣  Getting AI trading decision from real LLM...[/cyan]")
        console.print("[dim]Analyzing market data, technical indicators, and portfolio state...[/dim]")
        console.print("[dim]This may take a few seconds...[/dim]\n")

        # Show what data is being sent to LLM
        console.print("[bold]📤 Input to LLM:[/bold]")
        console.print(f"  • Market Price: ${current_price:,.2f}")
        console.print(f"  • 24h Change: {ticker.get('percentage', 0):+.2f}%")
        console.print(f"  • Technical Indicators: EMA, RSI, MACD, ATR")
        console.print(f"  • Portfolio Balance: ${portfolio['balance']:,.2f}")
        console.print(f"  • Open Positions: {portfolio.get('open_positions', 0)}")
        console.print(f"  • Portfolio Return: {return_pct:+.2f}%")
        console.print("")

        try:
            decision = llm_client.get_trading_decision(market_data, portfolio)

            action = decision.get("action", "hold").lower()
            direction = decision.get("direction", "none")
            confidence = decision.get("confidence", 0.0)
            justification = decision.get("justification", "No justification provided")
            position_size_usdt = decision.get("position_size_usdt", 0.0)
            leverage = decision.get("leverage", 1.0)
            risk_assessment = decision.get("risk_assessment", "medium")
            exit_plan = decision.get("exit_plan", {})

            # Display decision with full details
            action_emoji = {"buy": "🟢", "sell": "🔴", "hold": "🟡"}.get(action, "❓")
            action_color = {"buy": "green", "sell": "red", "hold": "yellow"}.get(action, "white")
            confidence_color = "green" if confidence > 0.7 else "yellow" if confidence > 0.4 else "red"
            risk_color = {"low": "green", "medium": "yellow", "high": "red"}.get(risk_assessment.lower(), "white")

            # Calculate position size percentage
            position_pct = (position_size_usdt / portfolio['balance'] * 100) if portfolio['balance'] > 0 else 0.0

            decision_text = f"""
[bold]Action:[/bold] [{action_color}]{action_emoji} {action.upper()}[/{action_color}] ({direction.upper()})
[bold]Confidence:[/bold] [{confidence_color}]{confidence:.2f}[/{confidence_color}] {'(High)' if confidence > 0.7 else '(Medium)' if confidence > 0.4 else '(Low)'}
[bold]Position Size:[/bold] ${position_size_usdt:,.2f} ({position_pct:.1f}% of balance)
[bold]Leverage:[/bold] {leverage:.1f}x
[bold]Risk Assessment:[/bold] [{risk_color}]{risk_assessment.upper()}[/{risk_color}]
[bold]Exit Plan:[/bold] Profit Target: ${exit_plan.get('profit_target', 0):,.2f}, Stop Loss: ${exit_plan.get('stop_loss', 0):,.2f}
[bold]Justification:[/bold] {justification}
            """.strip()

            console.print(
                Panel(
                    decision_text,
                    title="[bold blue]🤖 AI Trading Decision (Real LLM)[/bold blue]",
                    border_style="blue",
                    padding=(1, 2),
                )
            )

        except Exception as e:
            console.print(f"[bold red]❌ Failed to get LLM decision: {e}[/bold red]")
            logger.error(f"LLM decision error: {e}", exc_info=True)
            return 1

        # Execute trade if conditions are met
        console.print("\n[cyan]5️⃣  Trade Execution...[/cyan]")

        trade_executed = False
        trade_result = None

        # Check execution conditions
        min_confidence = config.MIN_CONFIDENCE_THRESHOLD
        console.print(f"[dim]Minimum confidence threshold: {min_confidence:.2f}[/dim]")
        console.print(f"[dim]Current confidence: {confidence:.2f}[/dim]")
        console.print(f"[dim]Available balance: ${portfolio['balance']:,.2f}[/dim]")

        if action == "buy" and confidence > min_confidence and direction == "long":
            if portfolio["balance"] > 0 and position_size_usdt > 0:
                # Calculate actual trade amount (respecting max position size)
                available_balance = portfolio["balance"]
                trade_amount = min(position_size_usdt, available_balance * config.MAX_POSITION_SIZE)

                console.print(f"\n[bold green]🟢 Executing BUY order...[/bold green]")
                console.print(f"  • Amount: ${trade_amount:,.2f}")
                console.print(f"  • Price: ${current_price:,.2f}")
                console.print(f"  • Leverage: {leverage:.1f}x")
                console.print(f"  • Confidence: {confidence:.2f}")

                try:
                    trade_result = trading_engine.execute_buy(
                        config.SYMBOL, current_price, trade_amount, confidence, decision, leverage
                    )
                    if trade_result:
                        trade_executed = True
                        console.print(f"[bold green]✅ BUY trade executed successfully![/bold green]")
                        console.print(f"  • Trade ID: {trade_result.get('id', 'N/A')}")
                        console.print(f"  • Quantity: {trade_result.get('quantity', 0):.6f} {config.SYMBOL.split('/')[0]}")
                        console.print(f"  • Entry Price: ${trade_result.get('price', 0):,.2f}")
                    else:
                        console.print("[bold red]❌ BUY trade failed (insufficient balance or validation error)[/bold red]")
                except Exception as e:
                    console.print(f"[bold red]❌ BUY trade error: {e}[/bold red]")
                    logger.error(f"Trade execution error: {e}", exc_info=True)
            else:
                console.print("[yellow]⚠️  Trade conditions met but insufficient balance or invalid position size[/yellow]")
                console.print(f"  • Balance: ${portfolio['balance']:,.2f}")
                console.print(f"  • Requested size: ${position_size_usdt:,.2f}")

        elif action == "buy" and confidence > min_confidence and direction == "short":
            if portfolio["balance"] > 0 and position_size_usdt > 0:
                available_balance = portfolio["balance"]
                trade_amount = min(position_size_usdt, available_balance * config.MAX_POSITION_SIZE)

                console.print(f"\n[bold red]🔴 Executing SHORT order...[/bold red]")
                console.print(f"  • Amount: ${trade_amount:,.2f}")
                console.print(f"  • Price: ${current_price:,.2f}")
                console.print(f"  • Leverage: {leverage:.1f}x")
                console.print(f"  • Confidence: {confidence:.2f}")

                try:
                    trade_result = trading_engine.execute_short(
                        config.SYMBOL, current_price, trade_amount, confidence, decision, leverage
                    )
                    if trade_result:
                        trade_executed = True
                        console.print(f"[bold red]✅ SHORT trade executed successfully![/bold red]")
                        console.print(f"  • Trade ID: {trade_result.get('id', 'N/A')}")
                        console.print(f"  • Quantity: {trade_result.get('quantity', 0):.6f} {config.SYMBOL.split('/')[0]}")
                        console.print(f"  • Entry Price: ${trade_result.get('price', 0):,.2f}")
                    else:
                        console.print("[bold red]❌ SHORT trade failed (insufficient balance or validation error)[/bold red]")
                except Exception as e:
                    console.print(f"[bold red]❌ SHORT trade error: {e}[/bold red]")
                    logger.error(f"Trade execution error: {e}", exc_info=True)
            else:
                console.print("[yellow]⚠️  Trade conditions met but insufficient balance or invalid position size[/yellow]")

        elif action == "sell" and confidence > min_confidence:
            if config.SYMBOL in trading_engine.positions:
                position = trading_engine.positions[config.SYMBOL]
                console.print(f"\n[bold red]🔴 Executing SELL order...[/bold red]")
                console.print(f"  • Position: {position.get('quantity', 0):.6f} {config.SYMBOL.split('/')[0]}")
                console.print(f"  • Entry Price: ${position.get('entry_price', 0):,.2f}")
                console.print(f"  • Current Price: ${current_price:,.2f}")
                console.print(f"  • Leverage: {leverage:.1f}x")

                try:
                    trade_result = trading_engine.execute_sell(
                        config.SYMBOL, current_price, confidence=confidence, llm_decision=decision, leverage=leverage
                    )
                    if trade_result:
                        trade_executed = True
                        profit = trade_result.get("profit", 0)
                        profit_pct = trade_result.get("profit_pct", 0)
                        profit_color = "green" if profit >= 0 else "red"
                        console.print(f"[bold green]✅ SELL trade executed successfully![/bold green]")
                        console.print(f"  • Trade ID: {trade_result.get('id', 'N/A')}")
                        console.print(f"  • Profit: [{profit_color}]${profit:,.2f} ({profit_pct:+.2f}%)[/{profit_color}]")
                    else:
                        console.print("[bold red]❌ SELL trade failed (no position or validation error)[/bold red]")
                except Exception as e:
                    console.print(f"[bold red]❌ SELL trade error: {e}[/bold red]")
                    logger.error(f"Trade execution error: {e}", exc_info=True)
            else:
                console.print("[yellow]⚠️  Trade conditions met but no position to sell[/yellow]")
                console.print(f"  • Open positions: {list(trading_engine.positions.keys())}")
        else:
            reason = []
            if action != "buy" and action != "sell":
                reason.append(f"action={action}")
            if confidence <= min_confidence:
                reason.append(f"confidence {confidence:.2f} <= {min_confidence:.2f}")
            if action == "buy" and direction != "long" and direction != "short":
                reason.append(f"direction={direction}")
            console.print(f"[yellow]⚠️  Trade will NOT execute: {', '.join(reason) if reason else 'conditions not met'}[/yellow]")

        # Get updated portfolio after trade
        if trade_executed:
            console.print("\n[cyan]📊 Updated Portfolio State:[/cyan]")
            updated_portfolio = trading_engine.get_portfolio_summary(current_price)
            console.print(f"  • New Balance: ${updated_portfolio['balance']:,.2f}")
            console.print(f"  • Portfolio Value: ${updated_portfolio['total_value']:,.2f}")
            console.print(f"  • Total Return: {updated_portfolio['total_return_pct']:+.2f}%")
            console.print(f"  • Open Positions: {updated_portfolio.get('open_positions', 0)}")

        # Summary
        console.print("\n" + "="*60)
        console.print("[bold green]✅ Test cycle completed successfully![/bold green]")
        console.print("\n[bold cyan]📊 Final Summary:[/bold cyan]")
        console.print(f"  • Market data fetched from Kraken: ✅")
        console.print(f"  • LLM decision received from {llm_provider.upper()}: ✅")
        console.print(f"  • Decision: {action.upper()} (confidence: {confidence:.2f})")
        console.print(f"  • Trade executed: {'✅ Yes' if trade_executed else '❌ No'}")
        if trade_executed and trade_result:
            console.print(f"  • Trade ID: {trade_result.get('id', 'N/A')}")
        console.print("="*60)

        return 0

    except KeyboardInterrupt:
        console.print("\n[bold yellow]🛑 Interrupted by user[/bold yellow]")
        return 1
    except Exception as e:
        console.print(f"\n[bold red]❌ Unexpected error: {e}[/bold red]")
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
