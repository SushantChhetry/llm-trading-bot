"""
Main entry point for the DeepSeek trading bot.

Schedules bot workflow to run at regular intervals (default: every 5 minutes),
handles logging, and coordinates data fetching, LLM decisions, and trade execution.
"""

import logging
import time
import sys
import argparse
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich import box
import colorama
from colorama import Fore, Back, Style

# Initialize colorama for cross-platform color support
colorama.init(autoreset=True)

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import config
from src.data_fetcher import DataFetcher
from src.llm_client import LLMClient
from src.trading_engine import TradingEngine
from src.logger import configure_production_logging, get_logger

# Configure logging based on environment
environment = os.getenv("ENVIRONMENT", "development")
if environment == "production":
    configure_production_logging(
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_directory="data/logs",
        app_name="trading-bot"
    )
else:
    # Development logging
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(config.LOG_FILE),
            logging.StreamHandler(sys.stdout)
        ]
    )

logger = get_logger(__name__)
logger.info(f"Starting trading bot in {environment} mode")


class TradingBot:
    """
    Main trading bot that coordinates all components.
    
    Orchestrates the workflow: fetch data -> get LLM decision -> execute trade.
    Runs on a schedule defined by config.RUN_INTERVAL_SECONDS.
    """
    
    def __init__(self, testnet_mode: bool = None, live_mode: bool = None):
        """
        Initialize all bot components.
        
        Args:
            testnet_mode: Override testnet setting from config
            live_mode: Override live trading setting from config
        """
        # Initialize colorful console
        self.console = Console()
        
        # Override config settings if provided
        if testnet_mode is not None:
            config.USE_TESTNET = testnet_mode
        if live_mode is not None:
            config.TRADING_MODE = "live" if live_mode else "paper"
        
        # Colorful initialization banner
        self.console.print(Panel.fit(
            "[bold blue]🤖 DEEPSEEK TRADING BOT[/bold blue]",
            border_style="blue",
            padding=(1, 2)
        ))
        
        self.data_fetcher = DataFetcher()
        self.llm_client = LLMClient()
        self.trading_engine = TradingEngine()
        
        # Create colorful status table
        status_table = Table(title="Bot Configuration", show_header=True, header_style="bold magenta")
        status_table.add_column("Setting", style="cyan", no_wrap=True)
        status_table.add_column("Value", style="green")
        
        # Enhanced logging with clear mode indicators
        mode_indicator = "🔴 LIVE" if config.TRADING_MODE == "live" else "🟡 PAPER"
        testnet_indicator = "🧪 TESTNET" if config.USE_TESTNET else "🌐 LIVE DATA"
        llm_indicator = f"🤖 {config.LLM_PROVIDER.upper()}" + (" (MOCK)" if self.llm_client.mock_mode else " (LIVE)")
        
        status_table.add_row("Trading Mode", mode_indicator)
        status_table.add_row("Data Source", testnet_indicator)
        status_table.add_row("LLM Provider", llm_indicator)
        status_table.add_row("Exchange", config.EXCHANGE.upper())
        status_table.add_row("Symbol", config.SYMBOL)
        status_table.add_row("Run Interval", f"{config.RUN_INTERVAL_SECONDS} seconds")
        status_table.add_row("Initial Balance", f"${config.INITIAL_BALANCE:,.2f}")
        
        self.console.print(status_table)
        
        # Log hyperparameters for experiment tracking
        self._log_hyperparameters()
        
        logger.info("=" * 60)
    
    def _log_hyperparameters(self):
        """Log all hyperparameters for experiment tracking."""
        hyperparams = {
            "trading_mode": config.TRADING_MODE,
            "use_testnet": config.USE_TESTNET,
            "llm_provider": config.LLM_PROVIDER,
            "llm_model": config.LLM_MODEL,
            "exchange": config.EXCHANGE,
            "symbol": config.SYMBOL,
            "initial_balance": config.INITIAL_BALANCE,
            "max_position_size": config.MAX_POSITION_SIZE,
            "stop_loss_percent": config.STOP_LOSS_PERCENT,
            "take_profit_percent": config.TAKE_PROFIT_PERCENT,
            "run_interval_seconds": config.RUN_INTERVAL_SECONDS,
            "llm_mock_mode": self.llm_client.mock_mode
        }
        
        logger.info("HYPERPARAMETERS:")
        for key, value in hyperparams.items():
            logger.info(f"  {key}: {value}")
        
        # Save hyperparameters to file for experiment tracking
        hyperparams_file = config.DATA_DIR / "hyperparameters.json"
        with open(hyperparams_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "hyperparameters": hyperparams
            }, f, indent=2)
    
    def run_cycle(self):
        """
        Execute one complete trading cycle.
        
        Fetches market data, gets LLM decision, and executes trades if needed.
        """
        try:
            # Colorful cycle header
            self.console.print(f"\n[bold cyan]🔄 Starting trading cycle at {datetime.now().strftime('%H:%M:%S')}[/bold cyan]")
            
            # 1. Fetch market data
            with self.console.status("[bold green]Fetching market data...", spinner="dots"):
                ticker = self.data_fetcher.get_ticker()
                current_price = float(ticker["last"])
                
                # Validate market data
                if current_price <= 0:
                    logger.error("Invalid market price received")
                    self.console.print("[bold red]❌ Invalid market data - skipping cycle[/bold red]")
                    return
            
            market_data = {
                "symbol": config.SYMBOL,
                "price": current_price,
                "volume": ticker.get("quoteVolume", 0),
                "change_24h": ticker.get("percentage", 0)
            }
            
            # Display market data
            price_change = ticker.get("percentage", 0)
            price_color = "green" if price_change >= 0 else "red"
            self.console.print(f"[bold]💰 Current Price:[/bold] [bold {price_color}]${current_price:,.2f}[/bold {price_color}] "
                             f"([{price_color}]{price_change:+.2f}%[/{price_color}])")
            
            # 2. Get portfolio summary
            portfolio = self.trading_engine.get_portfolio_summary(current_price)
            return_pct = portfolio['total_return_pct']
            return_color = "green" if return_pct >= 0 else "red"
            sharpe_ratio = portfolio.get('sharpe_ratio', 0.0)
            sharpe_color = "green" if sharpe_ratio > 1.0 else "yellow" if sharpe_ratio > 0.5 else "red"
            
            self.console.print(f"[bold]📊 Portfolio Value:[/bold] [bold {return_color}]${portfolio['total_value']:,.2f}[/bold {return_color}] "
                             f"([{return_color}]{return_pct:+.2f}%[/{return_color}])")
            self.console.print(f"[bold]📈 Sharpe Ratio:[/bold] [{sharpe_color}]{sharpe_ratio:.3f}[/{sharpe_color}] "
                             f"(Risk-Adjusted Return: {portfolio.get('risk_adjusted_return', 0.0):.3f})")
            
            # Display behavioral patterns
            bullish_tilt = portfolio.get('bullish_tilt', 0.5)
            tilt_color = "green" if bullish_tilt > 0.6 else "red" if bullish_tilt < 0.4 else "yellow"
            self.console.print(f"[bold]📊 Trading Style:[/bold] "
                             f"Bullish Tilt: [{tilt_color}]{bullish_tilt:.2f}[/{tilt_color}] | "
                             f"Avg Hold: {portfolio.get('avg_holding_period_hours', 0):.1f}h | "
                             f"Freq: {portfolio.get('trade_frequency_per_day', 0):.1f}/day | "
                             f"Fees: ${portfolio.get('total_trading_fees', 0):.2f}")
            
            # 3. Get LLM decision with portfolio context
            with self.console.status("[bold blue]🤖 Consulting AI for trading decision...", spinner="dots"):
                decision = self.llm_client.get_trading_decision(market_data, portfolio)
            
            action = decision.get("action", "hold").lower()
            direction = decision.get("direction", "none")
            confidence = decision.get("confidence", 0.0)
            justification = decision.get("justification", "No justification provided")
            position_size_usdt = decision.get("position_size_usdt", 0.0)
            leverage = decision.get("leverage", 1.0)
            risk_assessment = decision.get("risk_assessment", "medium")
            exit_plan = decision.get("exit_plan", {})
            
            # Create colorful decision panel
            action_emoji = {"buy": "🟢", "sell": "🔴", "hold": "🟡"}.get(action, "❓")
            action_color = {"buy": "green", "sell": "red", "hold": "yellow"}.get(action, "white")
            confidence_color = "green" if confidence > 0.7 else "yellow" if confidence > 0.4 else "red"
            risk_color = {"low": "green", "medium": "yellow", "high": "red"}.get(risk_assessment.lower(), "white")
            
            decision_text = f"""
[bold]Action:[/bold] [{action_color}]{action_emoji} {action.upper()}[/{action_color}] ({direction.upper()})
[bold]Confidence:[/bold] [{confidence_color}]{confidence:.2f}[/{confidence_color}]
[bold]Position Size:[/bold] ${position_size_usdt:.2f}
[bold]Leverage:[/bold] {leverage:.1f}x
[bold]Risk Assessment:[/bold] [{risk_color}]{risk_assessment.upper()}[/{risk_color}]
[bold]Justification:[/bold] {justification}
[bold]Exit Plan:[/bold] Profit Target: ${exit_plan.get('profit_target', 0):.2f}, Stop Loss: ${exit_plan.get('stop_loss', 0):.2f}
            """.strip()
            
            self.console.print(Panel(
                decision_text,
                title="[bold blue]🤖 AI Trading Decision[/bold blue]",
                border_style="blue",
                padding=(1, 2)
            ))
            
            # 4. Execute trade based on decision
            trade_executed = False
            if action == "buy" and confidence > 0.6 and direction == "long":
                # Use LLM's position size and leverage directly
                available_balance = portfolio["balance"]
                if available_balance > 0 and position_size_usdt > 0:
                    # Use LLM's calculated position size
                    trade_amount = min(position_size_usdt, available_balance * config.MAX_POSITION_SIZE)
                    
                    self.console.print(f"[bold green]🟢 Executing BUY: ${trade_amount:.2f} with {leverage:.1f}x leverage[/bold green]")
                    trade = self.trading_engine.execute_buy(
                        config.SYMBOL,
                        current_price,
                        trade_amount,
                        confidence,
                        decision,
                        leverage
                    )
                    if trade:
                        trade_executed = True
                        self.console.print(f"[bold green]✅ BUY trade executed successfully (ID: {trade['id']})[/bold green]")
                    else:
                        self.console.print("[bold red]❌ BUY trade failed (insufficient balance or other error)[/bold red]")
                        
            elif action == "buy" and confidence > 0.6 and direction == "short":
                # Execute short position
                available_balance = portfolio["balance"]
                if available_balance > 0 and position_size_usdt > 0:
                    trade_amount = min(position_size_usdt, available_balance * config.MAX_POSITION_SIZE)
                    
                    self.console.print(f"[bold red]🔴 Executing SHORT: ${trade_amount:.2f} with {leverage:.1f}x leverage[/bold red]")
                    trade = self.trading_engine.execute_short(
                        config.SYMBOL,
                        current_price,
                        trade_amount,
                        confidence,
                        decision,
                        leverage
                    )
                    if trade:
                        trade_executed = True
                        self.console.print(f"[bold red]✅ SHORT trade executed successfully (ID: {trade['id']})[/bold red]")
                    else:
                        self.console.print("[bold red]❌ SHORT trade failed (insufficient balance or other error)[/bold red]")
                        
            elif action == "sell" and confidence > 0.6:
                # Sell all or partial position
                if config.SYMBOL in self.trading_engine.positions:
                    self.console.print(f"[bold red]🔴 Executing SELL with {leverage:.1f}x leverage[/bold red]")
                    trade = self.trading_engine.execute_sell(
                        config.SYMBOL,
                        current_price,
                        confidence=confidence,
                        llm_decision=decision,
                        leverage=leverage
                    )
                    if trade:
                        trade_executed = True
                        profit = trade.get('profit', 0)
                        profit_color = "green" if profit >= 0 else "red"
                        self.console.print(f"[bold green]✅ SELL trade executed successfully[/bold green] "
                                         f"(ID: {trade['id']}, Profit: [{profit_color}]${profit:.2f}[/{profit_color}])")
                    else:
                        self.console.print("[bold red]❌ SELL trade failed (no position or other error)[/bold red]")
                else:
                    self.console.print("[yellow]No position to sell[/yellow]")
            else:
                self.console.print("[yellow]🟡 Decision is to HOLD or confidence too low. No action taken.[/yellow]")
            
            if not trade_executed:
                self.console.print("[dim]No trade executed this cycle[/dim]")
            
            self.console.print("[bold green]✅ Trading cycle completed successfully[/bold green]")
            
        except ValueError as e:
            self.console.print(f"[bold red]❌ Data validation error: {e}[/bold red]")
            logger.error(f"Data validation error in trading cycle: {e}")
        except ConnectionError as e:
            self.console.print(f"[bold red]❌ Network error: {e}[/bold red]")
            logger.error(f"Network error in trading cycle: {e}")
        except Exception as e:
            self.console.print(f"[bold red]❌ Unexpected error in trading cycle: {e}[/bold red]")
            logger.error(f"Unexpected error in trading cycle: {e}", exc_info=True)
            # Continue running despite errors
    
    def run(self):
        """
        Run the bot continuously on a schedule.
        
        Executes trading cycles at intervals defined by config.RUN_INTERVAL_SECONDS.
        Can be stopped with Ctrl+C.
        """
        # Colorful startup message
        self.console.print(Panel.fit(
            f"[bold green]🚀 Bot Starting![/bold green]\n"
            f"[cyan]Running every {config.RUN_INTERVAL_SECONDS} seconds[/cyan]\n"
            f"[yellow]Press Ctrl+C to stop[/yellow]",
            border_style="green",
            padding=(1, 2)
        ))
        
        try:
            while True:
                self.run_cycle()
                self.console.print(f"[dim]⏳ Waiting {config.RUN_INTERVAL_SECONDS} seconds until next cycle...[/dim]")
                time.sleep(config.RUN_INTERVAL_SECONDS)
                
        except KeyboardInterrupt:
            self.console.print("\n[bold yellow]🛑 Bot stopped by user[/bold yellow]")
            
            # Print final portfolio summary
            try:
                ticker = self.data_fetcher.get_ticker()
                current_price = float(ticker["last"])
                portfolio = self.trading_engine.get_portfolio_summary(current_price)
                
                # Create colorful final summary table
                final_table = Table(title="📊 Final Portfolio Summary", show_header=True, header_style="bold magenta")
                final_table.add_column("Metric", style="cyan", no_wrap=True)
                final_table.add_column("Value", style="green")
                
                return_pct = portfolio['total_return_pct']
                return_color = "green" if return_pct >= 0 else "red"
                
                final_table.add_row("Initial Balance", f"${portfolio['initial_balance']:,.2f}")
                final_table.add_row("Current Balance", f"${portfolio['balance']:,.2f}")
                final_table.add_row("Positions Value", f"${portfolio['positions_value']:,.2f}")
                final_table.add_row("Total Value", f"${portfolio['total_value']:,.2f}")
                final_table.add_row("Total Return", f"[{return_color}]${portfolio['total_return']:,.2f} ({return_pct:+.2f}%)[/{return_color}]")
                final_table.add_row("Total Trades", str(portfolio['total_trades']))
                
                self.console.print(final_table)
                
            except Exception as e:
                self.console.print(f"[bold red]❌ Error generating final summary: {e}[/bold red]")
            
            sys.exit(0)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="DeepSeek Trading Bot - AI-powered cryptocurrency trading",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main                    # Run with default settings (testnet + mock)
  python -m src.main --live             # Enable live trading mode
  python -m src.main --no-testnet       # Use live market data
  python -m src.main --provider deepseek --api-key YOUR_KEY  # Use DeepSeek API
  python -m src.main --provider openai --api-key YOUR_KEY    # Use OpenAI API
        """
    )
    
    # Trading mode arguments
    parser.add_argument(
        "--live", 
        action="store_true", 
        help="Enable live trading mode (default: paper trading)"
    )
    parser.add_argument(
        "--no-testnet", 
        action="store_true", 
        help="Use live market data instead of testnet (default: testnet)"
    )
    
    # LLM provider arguments
    parser.add_argument(
        "--provider", 
        choices=["mock", "deepseek", "openai", "anthropic"],
        help="LLM provider to use (default: from config)"
    )
    parser.add_argument(
        "--api-key", 
        help="API key for LLM provider"
    )
    parser.add_argument(
        "--model", 
        help="Model name to use (default: provider default)"
    )
    
    # Exchange arguments
    parser.add_argument(
        "--exchange", 
        choices=["bybit", "binance", "coinbase", "kraken"],
        help="Exchange to use (default: from config). Note: Bybit/Binance restricted in USA"
    )
    parser.add_argument(
        "--symbol", 
        help="Trading pair symbol (default: from config)"
    )
    
    # Other arguments
    parser.add_argument(
        "--interval", 
        type=int,
        help="Run interval in seconds (default: from config)"
    )
    parser.add_argument(
        "--balance", 
        type=float,
        help="Initial paper trading balance (default: from config)"
    )
    
    return parser.parse_args()


def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Override config with command line arguments
    if args.live:
        config.TRADING_MODE = "live"
    if args.no_testnet:
        config.USE_TESTNET = False
    if args.provider:
        config.LLM_PROVIDER = args.provider
    if args.api_key:
        config.LLM_API_KEY = args.api_key
    if args.model:
        config.LLM_MODEL = args.model
    if args.exchange:
        config.EXCHANGE = args.exchange
    if args.symbol:
        config.SYMBOL = args.symbol
    if args.interval:
        config.RUN_INTERVAL_SECONDS = args.interval
    if args.balance:
        config.INITIAL_BALANCE = args.balance
    
    # Initialize and run bot
    bot = TradingBot()
    bot.run()


if __name__ == "__main__":
    main()

