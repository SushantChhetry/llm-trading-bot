"""
Main entry point for the DeepSeek trading bot.

Schedules bot workflow to run at regular intervals (default: every 5 minutes),
handles logging, and coordinates data fetching, LLM decisions, and trade execution.
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from colorama import init as colorama_init
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Initialize colorama for cross-platform color support
colorama_init(autoreset=True)

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import config  # noqa: E402
from src.data_fetcher import DataFetcher  # noqa: E402
from src.llm_client import LLMClient  # noqa: E402
from src.logger import LogDomain, configure_production_logging, get_logger  # noqa: E402
from src.monitoring import MonitoringService  # noqa: E402
from src.position_sizer import PositionSizer  # noqa: E402
from src.startup_validator import validate_startup  # noqa: E402
from src.trading_engine import TradingEngine  # noqa: E402

# Configure logging based on environment
environment = os.getenv("ENVIRONMENT", "development")
if environment == "production":
    configure_production_logging(
        log_level=os.getenv("LOG_LEVEL", "INFO"), log_directory="data/logs", app_name="trading-bot"
    )
else:
    # Development logging
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(config.LOG_FILE), logging.StreamHandler(sys.stdout)],
    )

logger = get_logger(__name__, domain=LogDomain.SYSTEM)

# Run startup validation
if not validate_startup():
    logger.error("Startup validation: Failed - exiting")
    sys.exit(1)

logger.info(f"Bot starting: environment={environment} mode={config.TRADING_MODE if hasattr(config, 'TRADING_MODE') else 'unknown'}")


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
        # Check if we're in an interactive terminal (TTY) or redirected output
        self.is_interactive = sys.stdout.isatty()
        # Force output in Docker/non-TTY environments by using force_terminal
        # This ensures Rich prints even when stdout is not a TTY
        # But disable spinners when not interactive to avoid log spam
        self.console = Console(
            force_terminal=True,  # Force terminal output even in Docker
            width=None,  # Auto-detect width
            file=sys.stdout,  # Explicitly use stdout
            legacy_windows=False,  # Better compatibility
        )

        # Override config settings if provided
        if testnet_mode is not None:
            config.USE_TESTNET = testnet_mode
        if live_mode is not None:
            config.TRADING_MODE = "live" if live_mode else "paper"

        # Trade cooldown tracking to prevent over-trading
        self.last_trade_time = None
        self.TRADE_COOLDOWN_SECONDS = int(os.getenv("TRADE_COOLDOWN_SECONDS", "1800"))  # 30 minutes between trades

        # Colorful initialization banner
        self.console.print(
            Panel.fit("[bold blue]🤖 DEEPSEEK TRADING BOT[/bold blue]", border_style="blue", padding=(1, 2))
        )

        self.data_fetcher = DataFetcher()
        self.llm_client = LLMClient()
        self.trading_engine = TradingEngine()

        # Initialize regime controller (optional)
        self.regime_controller = None
        try:
            from .regime_controller import RegimeController
            from .regime_detector import RegimeDetector

            if self.data_fetcher.regime_detector:
                self.regime_controller = RegimeController(regime_detector=self.data_fetcher.regime_detector)
                logger.info("Regime controller initialized")
        except Exception as e:
            logger.warning(f"Regime controller not available: {e}")

        # Initialize data quality manager
        self.data_quality = None
        try:
            from .data_quality import DataQualityManager

            self.data_quality = DataQualityManager()
            logger.info("Data quality manager initialized")
        except Exception as e:
            logger.warning(f"Data quality manager not available: {e}")

        # Initialize funding/carry manager
        self.funding_carry = None
        try:
            from .funding_carry import FundingCarryManager

            self.funding_carry = FundingCarryManager()
            logger.info("Funding/carry manager initialized")
        except Exception as e:
            logger.warning(f"Funding/carry manager not available: {e}")

        # Initialize execution engine
        self.execution_engine = None
        try:
            from .execution_engine import ExecutionEngine

            self.execution_engine = ExecutionEngine()
            logger.info("Execution engine initialized")
        except Exception as e:
            logger.warning(f"Execution engine not available: {e}")

        # Initialize position reconciler
        self.position_reconciler = None
        self.reconciliation_cycle_count = 0
        try:
            from .position_reconciler import PositionReconciler

            self.position_reconciler = PositionReconciler(data_fetcher=self.data_fetcher)
            logger.info("Position reconciler initialized")
        except Exception as e:
            logger.warning(f"Position reconciler not available: {e}")

        # Initialize performance learner (optional - for adaptive confidence)
        self.performance_learner = None
        if getattr(config, 'ENABLE_PERFORMANCE_LEARNING', True):
            try:
                from .performance_learner import PerformanceLearner

                self.performance_learner = PerformanceLearner()
                logger.info("Performance learner initialized")
            except Exception as e:
                logger.warning(f"Performance learner not available: {e}")

        # Initialize position sizer (for Kelly criterion-based position sizing)
        self.position_sizer = None
        if getattr(config, 'ENABLE_KELLY_SIZING', False):
            try:
                self.position_sizer = PositionSizer()
                logger.info("Position sizer (Kelly criterion) initialized")
            except Exception as e:
                logger.warning(f"Position sizer not available: {e}")
        else:
            # Initialize anyway for dynamic position sizing
            try:
                self.position_sizer = PositionSizer()
                logger.info("Position sizer initialized (will be used for dynamic sizing)")
            except Exception as e:
                logger.warning(f"Position sizer not available: {e}")

        # Initialize strategy manager (optional - for multi-strategy execution)
        self.strategy_manager = None
        self.last_rebalance_time = None
        if getattr(config, 'ENABLE_MULTI_STRATEGY', False):
            try:
                from .strategy_manager import StrategyManager
                
                if self.regime_controller:
                    self.strategy_manager = StrategyManager(regime_controller=self.regime_controller)
                    logger.info("Strategy manager initialized")
                else:
                    logger.warning("Strategy manager requires regime_controller, disabling multi-strategy")
            except Exception as e:
                logger.warning(f"Strategy manager not available: {e}")

        # Initialize monitoring service
        self.monitoring_service = MonitoringService()
        self.monitoring_running = False
        self.metrics_flush_interval = 60  # Write metrics to Supabase every 60 seconds
        self.last_metrics_flush = time.time()

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

        # CRITICAL: Display live trading warning if in live mode
        if config.TRADING_MODE == "live":
            self.console.print(
                Panel.fit(
                    "[bold red]🚨 LIVE TRADING MODE - REAL MONEY AT RISK![/bold red]\n"
                    "[yellow]Ensure you have tested thoroughly in paper mode![/yellow]\n"
                    "[dim]Starting bot in 5 seconds...[/dim]",
                    border_style="red",
                    padding=(1, 2),
                )
            )
            # Add 5-second delay for operator awareness
            time.sleep(5)

        # Log hyperparameters for experiment tracking
        self._log_hyperparameters()
    
    def _check_circuit_breaker(self) -> bool:
        """
        Circuit breaker / kill switch for broken strategies.
        
        Checks for:
        1. Consecutive losses (5+)
        2. Daily loss limit ($500)
        3. Drawdown exceeded (15%)
        
        Returns:
            True if circuit breaker should halt trading
        """
        try:
            # Get recent trades (last 24 hours) with safe timestamp parsing
            recent_trades = []
            for t in self.trading_engine.trades:
                try:
                    ts = t.get("timestamp")
                    if not ts:
                        continue
                    if isinstance(ts, str):
                        ts = ts.replace("Z", "+00:00")
                        trade_time = datetime.fromisoformat(ts)
                    elif isinstance(ts, datetime):
                        trade_time = ts
                    else:
                        continue
                    
                    time_diff = (datetime.now() - trade_time).total_seconds()
                    if time_diff < 86400:  # 24 hours
                        recent_trades.append(t)
                except Exception:
                    # Skip trades with invalid timestamps
                    continue
            
            if not recent_trades:
                return False
            
            # Trigger 1: Consecutive losses
            consecutive_losses = 0
            for trade in reversed(recent_trades[-10:]):  # Check last 10 trades
                if trade.get("profit", 0) < 0:
                    consecutive_losses += 1
                else:
                    break
            
            if consecutive_losses >= 5:
                logger.critical(
                    f"Circuit breaker triggered: reason=consecutive_losses count={consecutive_losses} threshold=5"
                )
                return True
            
            # Trigger 2: Daily loss limit
            daily_loss = sum(t.get("profit", 0) for t in recent_trades if t.get("profit", 0) < 0)
            if abs(daily_loss) > 500:  # $500 loss
                logger.critical(
                    f"Circuit breaker triggered: reason=daily_loss_limit loss={abs(daily_loss):.2f} threshold=500.00"
                )
                return True
            
            # Trigger 3: Drawdown exceeded (from peak, not initial)
            current_price = self.trading_engine.trades[-1].get("price", 0) if self.trading_engine.trades else 0
            portfolio_value = self.trading_engine.get_portfolio_value(current_price)
            
            # Track peak portfolio value
            if not hasattr(self, 'peak_portfolio_value'):
                self.peak_portfolio_value = config.INITIAL_BALANCE
            
            if portfolio_value > self.peak_portfolio_value:
                self.peak_portfolio_value = portfolio_value
            
            # Calculate drawdown from peak
            current_drawdown = (self.peak_portfolio_value - portfolio_value) / self.peak_portfolio_value if self.peak_portfolio_value > 0 else 0
            
            if current_drawdown > 0.15:  # 15% drawdown
                logger.critical(
                    f"Circuit breaker triggered: reason=drawdown_exceeded drawdown={current_drawdown:.1%} threshold=15.0%"
                )
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Circuit breaker check failed: (error={str(e)})")
            return False  # Don't halt on error, just log it

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
            "llm_mock_mode": self.llm_client.mock_mode,
        }

        logger.info("HYPERPARAMETERS:")
        for key, value in hyperparams.items():
            logger.info(f"  {key}: {value}")

        # Save hyperparameters to file for experiment tracking
        hyperparams_file = config.DATA_DIR / "hyperparameters.json"
        with open(hyperparams_file, "w") as f:
            json.dump({"timestamp": datetime.now().isoformat(), "hyperparameters": hyperparams}, f, indent=2)

    def _flush_metrics_to_supabase(self):
        """Flush metrics from monitoring service to Supabase"""
        if not self.trading_engine.supabase_client:
            return

        try:
            # Get metrics summary
            metrics_summary = self.monitoring_service.get_metrics_summary()

            # Write counters
            for name, value in metrics_summary.get("counters", {}).items():
                self.trading_engine.supabase_client.add_metric(
                    service_name="trading-bot",
                    metric_name=name,
                    value=float(value),
                    metric_type="counter",
                    tags={},
                )

            # Write gauges
            for name, value in metrics_summary.get("gauges", {}).items():
                self.trading_engine.supabase_client.add_metric(
                    service_name="trading-bot",
                    metric_name=name,
                    value=float(value),
                    metric_type="gauge",
                    tags={},
                )

            # Write histogram stats
            for name, stats in metrics_summary.get("histogram_stats", {}).items():
                if stats and isinstance(stats, dict):
                    # Write mean, min, max, p95, p99 as separate metrics
                    for stat_name, stat_value in stats.items():
                        if stat_value is not None:
                            self.trading_engine.supabase_client.add_metric(
                                service_name="trading-bot",
                                metric_name=f"{name}.{stat_name}",
                                value=float(stat_value),
                                metric_type="histogram",
                                tags={},
                            )

            # Write health status
            # health_status is a string from get_overall_health(), not a dict
            health_status_str = metrics_summary.get("health_status", "unknown")
            if isinstance(health_status_str, str):
                overall_status = health_status_str
            else:
                # Fallback if it's somehow a dict (backward compatibility)
                overall_status = health_status_str.get("status", "unknown") if isinstance(health_status_str, dict) else "unknown"
            
            status_map = {"healthy": "healthy", "degraded": "degraded", "unhealthy": "unhealthy"}
            supabase_status = status_map.get(overall_status, "degraded")

            self.trading_engine.supabase_client.add_health_check(
                service_name="trading-bot",
                status=supabase_status,
                details={"status": overall_status, "source": "monitoring_service"},
            )

            logger.debug(
                f"Metrics flushed to Supabase: {len(metrics_summary.get('counters', {}))} counters, "
                f"{len(metrics_summary.get('gauges', {}))} gauges"
            )
        except Exception as e:
            logger.error(f"Failed to flush metrics to Supabase: {e}", exc_info=True)

    def _start_monitoring_background(self):
        """Start monitoring service in background thread"""
        import threading

        def run_monitoring():
            """Run monitoring in a separate thread"""
            import asyncio

            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                # Start monitoring service
                loop.run_until_complete(self.monitoring_service.start())
                self.monitoring_running = True
                logger.info("Monitoring service started in background")

                # Keep the loop running
                loop.run_forever()
            except Exception as e:
                logger.error(f"Error in monitoring background thread: {e}", exc_info=True)
            finally:
                loop.close()

        # Start monitoring in background thread
        monitoring_thread = threading.Thread(target=run_monitoring, daemon=True)
        monitoring_thread.start()
        logger.info("Monitoring background thread started")

    def run_cycle(self):
        """
        Execute one complete trading cycle.

        Fetches market data, gets LLM decision, and executes trades if needed.
        """
        try:
            # Colorful cycle header
            self.console.print(
                f"\n[bold cyan]🔄 Starting trading cycle at {datetime.now().strftime('%H:%M:%S')}[/bold cyan]"
            )

            # 1. Fetch market data and technical indicators (Alpha Arena enhancement)
            if self.is_interactive:
                # Use spinner only in interactive terminals
                with self.console.status("[bold green]Fetching market data & technical indicators...", spinner="dots"):
                    ticker = self.data_fetcher.get_ticker()
                    current_price = float(ticker["last"])

                    # Validate market data
                    if current_price <= 0:
                        logger.error(f"Market data validation failed: price={current_price} - skipping cycle")
                        self.console.print("[bold red]❌ Invalid market data - skipping cycle[/bold red]")
                        return

                    # Check data quality before proceeding
                    if self.data_quality:
                        quality_report = self.data_quality.get_quality_report()
                        if quality_report.overall_status.value == "critical":
                            logger.error(f"Data quality critical: status=critical (report={quality_report}) - skipping cycle")
                            self.console.print("[bold red]❌ Data quality critical - skipping cycle[/bold red]")
                            return
                        elif quality_report.overall_status.value == "warning":
                            logger.warning(f"Data quality warning: status=warning (report={quality_report})")

                    # Update data timestamp
                    if self.data_quality:
                        self.data_quality.update_data_timestamp()

                    # Fetch technical indicators for Alpha Arena-style trading
                    try:
                        indicators = self.data_fetcher.get_technical_indicators(timeframe="5m", limit=100)
                    except Exception as e:
                        logger.warning(f"Failed to fetch technical indicators: {e}. Using fallback values.")
                        indicators = {
                            "ema_20": current_price * 0.99,
                            "ema_50": current_price * 0.98,
                            "macd": 0.0,
                            "macd_signal": 0.0,
                            "macd_histogram": 0.0,
                            "rsi_7": 50.0,
                            "rsi_14": 50.0,
                            "atr": current_price * 0.02,
                            "current_price": current_price,
                        }

                    # Check price triangulation
                    if self.data_quality:
                        triangulation = self.data_quality.check_price_triangulation(
                            venue_price=current_price, symbol=config.SYMBOL
                        )
                        if triangulation.status.value == "critical":
                            logger.error(f"Price triangulation critical: divergence={triangulation.divergence_bps:.2f}bps symbol={config.SYMBOL} - skipping cycle")
                            self.console.print("[bold red]❌ Price divergence too large - skipping cycle[/bold red]")
                            return
            else:
                # Non-interactive: use simple log message
                logger.info("Fetching market data & technical indicators...")
                ticker = self.data_fetcher.get_ticker()
                current_price = float(ticker["last"])

                # Validate market data
                if current_price <= 0:
                    logger.error(f"Market data validation failed: price={current_price} - skipping cycle")
                    return

                # Fetch technical indicators for Alpha Arena-style trading
                try:
                    indicators = self.data_fetcher.get_technical_indicators(timeframe="5m", limit=100)
                except Exception as e:
                    logger.warning(f"Technical indicators fetch failed: timeframe=5m limit=100 (error={str(e)}) - using fallback values")
                    indicators = {
                        "ema_20": current_price * 0.99,
                        "ema_50": current_price * 0.98,
                        "macd": 0.0,
                        "macd_signal": 0.0,
                        "macd_histogram": 0.0,
                        "rsi_7": 50.0,
                        "rsi_14": 50.0,
                        "atr": current_price * 0.02,
                        "current_price": current_price,
                    }

            market_data = {
                "symbol": config.SYMBOL,
                "price": current_price,
                "volume": ticker.get("quoteVolume", 0),
                "change_24h": ticker.get("percentage", 0),
                # Add technical indicators for Alpha Arena
                "indicators": indicators,
            }

            # Display market data
            price_change = ticker.get("percentage", 0)
            price_color = "green" if price_change >= 0 else "red"
            self.console.print(
                f"[bold]💰 Current Price:[/bold] [bold {price_color}]${current_price:,.2f}[/bold {price_color}] "
                f"([{price_color}]{price_change:+.2f}%[/{price_color}])"
            )

            # 1.5. Monitor open positions for stop-loss, take-profit, and other exit conditions
            if config.ENABLE_POSITION_MONITORING:
                monitoring_results = self.trading_engine.monitor_positions(current_price)
                if monitoring_results["positions_checked"] > 0:
                    if monitoring_results["positions_closed"] > 0:
                        logger.info(
                            f"Position monitoring: checked={monitoring_results['positions_checked']} "
                            f"closed={monitoring_results['positions_closed']} "
                            f"stop_loss={monitoring_results['stop_loss_triggers']} "
                            f"take_profit={monitoring_results['take_profit_triggers']} "
                            f"partial={monitoring_results['partial_profit_triggers']}"
                        )
                        self.console.print(
                            f"[bold yellow]⚠️ Position Monitoring:[/bold yellow] "
                            f"Checked {monitoring_results['positions_checked']} positions, "
                            f"closed {monitoring_results['positions_closed']} "
                            f"(Stop-loss: {monitoring_results['stop_loss_triggers']}, "
                            f"Take-profit: {monitoring_results['take_profit_triggers']}, "
                            f"Partial: {monitoring_results['partial_profit_triggers']})"
                        )
                    else:
                        logger.debug(
                            f"Position monitoring: checked={monitoring_results['positions_checked']} closed=0"
                        )

            # 2. Get portfolio summary
            portfolio = self.trading_engine.get_portfolio_summary(current_price)
            return_pct = portfolio["total_return_pct"]
            return_color = "green" if return_pct >= 0 else "red"
            sharpe_ratio = portfolio.get("sharpe_ratio", 0.0)
            sharpe_color = "green" if sharpe_ratio > 1.0 else "yellow" if sharpe_ratio > 0.5 else "red"

            portfolio_value_msg = (
                f"[bold]📊 Portfolio Value:[/bold] "
                f"[bold {return_color}]${portfolio['total_value']:,.2f}[/bold {return_color}] "
                f"([{return_color}]{return_pct:+.2f}%[/{return_color}])"
            )
            self.console.print(portfolio_value_msg)
            self.console.print(
                f"[bold]📈 Sharpe Ratio:[/bold] [{sharpe_color}]{sharpe_ratio:.3f}[/{sharpe_color}] "
                f"(Risk-Adjusted Return: {portfolio.get('risk_adjusted_return', 0.0):.3f})"
            )

            # Display behavioral patterns
            bullish_tilt = portfolio.get("bullish_tilt", 0.5)
            tilt_color = "green" if bullish_tilt > 0.6 else "red" if bullish_tilt < 0.4 else "yellow"
            self.console.print(
                f"[bold]📊 Trading Style:[/bold] "
                f"Bullish Tilt: [{tilt_color}]{bullish_tilt:.2f}[/{tilt_color}] | "
                f"Avg Hold: {portfolio.get('avg_holding_period_hours', 0):.1f}h | "
                f"Freq: {portfolio.get('trade_frequency_per_day', 0):.1f}/day | "
                f"Fees: ${portfolio.get('total_trading_fees', 0):.2f}"
            )

            # Display regime information if available
            if indicators.get("regime"):
                regime = indicators.get("regime", "unknown")
                volatility_regime = indicators.get("volatility_regime", "medium")
                regime_confidence = indicators.get("regime_confidence", 0.0)
                regime_color = "green" if regime_confidence > 0.7 else "yellow" if regime_confidence > 0.4 else "red"
                self.console.print(
                    f"[bold]📈 Market Regime:[/bold] "
                    f"[{regime_color}]{regime.upper()}[/{regime_color}] "
                    f"(confidence: {regime_confidence:.2f}, volatility: {volatility_regime.upper()})"
                )

                # Get regime guidance
                if self.regime_controller and indicators.get("regime") != "unknown":
                    try:
                        regime_state = (
                            self.data_fetcher.regime_detector.regime_history[-1]
                            if self.data_fetcher.regime_detector.regime_history
                            else None
                        )
                        if regime_state:
                            guidance = self.regime_controller.get_regime_guidance(regime_state)
                            self.console.print(f"[dim]💡 Strategy Guidance: {guidance.get('guidance', '')}[/dim]")
                    except Exception as e:
                        logger.debug(f"Could not get regime guidance: {e}")

            # 2.5. Position reconciliation (every N cycles)
            if self.position_reconciler:
                self.reconciliation_cycle_count += 1
                if self.reconciliation_cycle_count >= config.POSITION_RECONCILIATION_INTERVAL:
                    self.reconciliation_cycle_count = 0
                    try:
                        discrepancies, success = self.position_reconciler.reconcile_positions(
                            bot_positions=self.trading_engine.positions, current_price=current_price
                        )
                        if discrepancies:
                            critical_count = sum(1 for d in discrepancies if d.severity == "critical")
                            warning_count = sum(1 for d in discrepancies if d.severity == "warning")
                            if critical_count > 0:
                                logger.error(f"Position reconciliation: critical={critical_count} warning={warning_count} discrepancies found")
                                self.console.print(
                                    f"[bold red]⚠️ Position Reconciliation: {critical_count} critical, {warning_count} warning discrepancies[/bold red]"
                                )
                            else:
                                logger.warning(f"Position reconciliation: warning={warning_count} discrepancies found")
                                self.console.print(
                                    f"[bold yellow]⚠️ Position Reconciliation: {warning_count} warning discrepancies[/bold yellow]"
                                )
                        elif success:
                            logger.debug("Position reconciliation: All positions match")
                    except Exception as e:
                        logger.error(f"Position reconciliation failed: (error={str(e)})", exc_info=True)

            # 2.6. Risk service health monitoring
            if self.trading_engine.risk_client:
                try:
                    risk_state = self.trading_engine.risk_client.get_risk_state()
                    if risk_state is None:
                        logger.warning("Risk service health check failed: service may be unreachable")
                        if config.RISK_SERVICE_REQUIRED:
                            self.console.print(
                                "[bold red]⚠️ Risk service unreachable - trades may be blocked[/bold red]"
                            )
                    else:
                        if risk_state.get("kill_switch_active", False):
                            kill_reason = risk_state.get('kill_switch_reason', 'Unknown reason')
                            logger.critical(f"Kill switch active: reason={kill_reason}")
                            self.console.print(
                                f"[bold red]🚨 KILL SWITCH ACTIVE: {kill_reason}[/bold red]"
                            )
                        logger.debug(
                            f"Risk service health: status=OK kill_switch={risk_state.get('kill_switch_active', False)}"
                        )
                except Exception as e:
                    logger.error(f"Risk service health check failed: (error={str(e)})", exc_info=True)

            # 3. Get LLM decision with portfolio context
            if self.is_interactive:
                # Use spinner only in interactive terminals
                with self.console.status("[bold blue]🤖 Consulting AI for trading decision...", spinner="dots"):
                    decision = self.llm_client.get_trading_decision(market_data, portfolio)
            else:
                # Non-interactive: use simple log message
                logger.info("Consulting AI for trading decision...")
                decision = self.llm_client.get_trading_decision(market_data, portfolio)

            action = decision.get("action", "hold").lower()
            direction = decision.get("direction", "none")
            confidence = decision.get("confidence", 0.0)
            justification = decision.get("justification", "No justification provided")
            position_size_usdt = decision.get("position_size_usdt", 0.0)
            leverage = decision.get("leverage", 1.0)
            risk_assessment = decision.get("risk_assessment", "medium")
            exit_plan = decision.get("exit_plan", {})

            # Adaptive confidence adjustment based on pattern performance
            original_confidence = confidence
            confidence_adjustment = 0.0
            if self.performance_learner and getattr(config, 'ADAPTIVE_CONFIDENCE_ENABLED', True):
                try:
                    # Detect current market regime
                    price_history = market_data.get("price_history", [])
                    if not price_history and indicators:
                        # Build price history from indicators if available
                        price_history = [{"close": indicators.get("current_price", current_price)}]
                    
                    regime = self.performance_learner.detect_market_regime(price_history) if price_history else ("unknown", "normal")
                    
                    # Get adaptive confidence for current context
                    # Try multiple patterns and use the most significant adjustment
                    adjustments = []
                    
                    # Time patterns (multiple features)
                    current_hour = datetime.now().hour
                    hour_confidence = self.performance_learner.get_adaptive_confidence(
                        confidence, "hour", str(current_hour)
                    )
                    if hour_confidence != confidence:
                        adjustments.append(("hour", hour_confidence - confidence))
                    
                    # Trading session pattern
                    trading_session = self.performance_learner._get_trading_session(current_hour)
                    session_confidence = self.performance_learner.get_adaptive_confidence(
                        confidence, "trading_session", trading_session
                    )
                    if session_confidence != confidence:
                        adjustments.append(("trading_session", session_confidence - confidence))
                    
                    # Direction pattern
                    if direction in ["long", "short"]:
                        dir_confidence = self.performance_learner.get_adaptive_confidence(
                            confidence, "direction", direction
                        )
                        if dir_confidence != confidence:
                            adjustments.append(("direction", dir_confidence - confidence))
                    
                    # Regime pattern
                    regime_key = f"{regime[0]}_{regime[1]}"
                    regime_confidence = self.performance_learner.get_adaptive_confidence(
                        confidence, "regime", regime_key
                    )
                    if regime_confidence != confidence:
                        adjustments.append(("regime", regime_confidence - confidence))
                    
                    # Apply the most significant adjustment
                    if adjustments:
                        # Use the adjustment with largest absolute value
                        best_adjustment = max(adjustments, key=lambda x: abs(x[1]))
                        confidence = best_adjustment[1] + confidence  # adjustment is delta
                        confidence = max(0.4, min(0.95, confidence))  # Clamp
                        confidence_adjustment = best_adjustment[1]
                        logger.info(
                            f"ADAPTIVE_CONFIDENCE_ADJUSTMENT pattern={best_adjustment[0]} "
                            f"original={original_confidence:.2f} adjusted={confidence:.2f} "
                            f"delta={confidence_adjustment:+.2f}"
                        )
                except Exception as e:
                    logger.warning(f"Error in adaptive confidence adjustment: {e}")

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

            self.console.print(
                Panel(
                    decision_text,
                    title="[bold blue]🤖 AI Trading Decision[/bold blue]",
                    border_style="blue",
                    padding=(1, 2),
                )
            )

            # 4. Execute trade based on decision
            logger.info(
                f"TRADE_DECISION_EVALUATION action={action} direction={direction} "
                f"confidence={confidence:.2f} position_size_usdt={position_size_usdt:.2f} "
                f"leverage={leverage:.1f} current_price={current_price:.2f}"
            )
            logger.info(
                f"TRADE_DECISION_CONTEXT balance={portfolio['balance']:.2f} "
                f"open_positions={portfolio.get('open_positions', 0)} "
                f"max_positions={config.MAX_ACTIVE_POSITIONS} "
                f"max_position_size_pct={config.MAX_POSITION_SIZE * 100:.1f}"
            )

            trade_executed = False
            min_confidence = config.MIN_CONFIDENCE_THRESHOLD
            if action == "buy" and confidence >= min_confidence and direction == "long":
                logger.info(
                    f"TRADE_CONDITION_CHECK action=buy status=passed "
                    f"confidence={confidence:.2f} direction={direction}"
                )

                # Use LLM's position size and leverage directly
                available_balance = portfolio["balance"]
                logger.debug(
                    f"POSITION_SIZE_VALIDATION balance={available_balance:.2f} "
                    f"requested_size={position_size_usdt:.2f} "
                    f"max_allowed={available_balance * config.MAX_POSITION_SIZE:.2f}"
                )

                if available_balance > 0 and position_size_usdt > 0:
                    # Check fee impact before trading - prevent over-trading
                    fee_impact_pct = portfolio.get("fee_impact_pct", 0)
                    if fee_impact_pct > config.FEE_IMPACT_WARNING_THRESHOLD:
                        logger.warning(
                            f"Trade blocked: fee impact {fee_impact_pct:.1f}% exceeds threshold "
                            f"{config.FEE_IMPACT_WARNING_THRESHOLD}%"
                        )
                        self.console.print(
                            f"[bold red]🚫 Trade blocked: Fee impact too high ({fee_impact_pct:.1f}%)[/bold red]"
                        )
                        return
                    
                    # Check trade cooldown period
                    if self.last_trade_time:
                        time_since_last_trade = (datetime.now() - self.last_trade_time).total_seconds()
                        if time_since_last_trade < self.TRADE_COOLDOWN_SECONDS:
                            remaining = self.TRADE_COOLDOWN_SECONDS - time_since_last_trade
                            logger.info(
                                f"Trade blocked: Cooldown active. {remaining:.0f}s remaining"
                            )
                            self.console.print(
                                f"[bold yellow]⏳ Trade cooldown: {remaining:.0f}s remaining[/bold yellow]"
                            )
                            return
                    
                    # Check funding/carry costs before trading
                    if self.funding_carry:
                        # Estimate expected edge (simplified - would use actual signal strength)
                        expected_edge_bps = confidence * 100  # Simplified estimate
                        should_avoid, reason = self.funding_carry.should_avoid_perp(
                            symbol=config.SYMBOL, expected_edge_bps=expected_edge_bps
                        )
                        if should_avoid:
                            logger.warning(f"Trade avoided: reason=carry_costs details={reason}")
                            self.console.print(f"[bold yellow]⚠️ Trade avoided: {reason}[/bold yellow]")
                            return

                    # Calculate optimal position size using Kelly criterion (if position_sizer available)
                    # Otherwise fall back to LLM suggestion capped by MAX_POSITION_SIZE
                    if self.position_sizer:
                        try:
                            # Get recent trades for Kelly calculation
                            recent_trades = self.trading_engine.trades[-50:] if len(self.trading_engine.trades) > 0 else []
                            
                            # Get volatility (ATR) from indicators (with defensive check)
                            volatility = indicators.get("atr", None) if indicators else None
                            
                            # Calculate Kelly-optimal position size
                            kelly_optimal_size = self.position_sizer.calculate_optimal_position_size(
                                portfolio=portfolio,
                                recent_trades=recent_trades,
                                max_position_size=config.MAX_POSITION_SIZE,
                                existing_positions=self.trading_engine.positions,
                                confidence=confidence,
                                volatility=volatility,
                                current_price=current_price
                            )
                            
                            # Validate Kelly optimal size is reasonable
                            if kelly_optimal_size <= 0:
                                logger.warning(
                                    f"Kelly optimal size is invalid ({kelly_optimal_size:.2f}), using LLM suggestion"
                                )
                                trade_amount = min(position_size_usdt, available_balance * config.MAX_POSITION_SIZE)
                            else:
                                # Use the larger of LLM suggestion or Kelly-optimal, but cap at MAX_POSITION_SIZE
                                # This allows LLM to suggest larger sizes when confidence is high
                                max_allowed_by_config = available_balance * config.MAX_POSITION_SIZE
                                # Ensure optimal_size doesn't exceed reasonable limits (max 50% of balance as safety)
                                optimal_size = max(position_size_usdt, kelly_optimal_size)
                                optimal_size = min(optimal_size, available_balance * 0.5)  # Safety cap
                                trade_amount = min(optimal_size, max_allowed_by_config)
                            
                            logger.info(
                                f"Position size calculation: llm_suggestion={position_size_usdt:.2f} "
                                f"kelly_optimal={kelly_optimal_size:.2f} "
                                f"final_size={trade_amount:.2f} "
                                f"max_config={max_allowed_by_config:.2f}"
                            )
                            
                            if trade_amount != position_size_usdt:
                                logger.info(
                                    f"Position size adjusted: original={position_size_usdt:.2f} "
                                    f"adjusted={trade_amount:.2f} reason=kelly_criterion"
                                )
                        except Exception as e:
                            logger.warning(f"Position size calculation failed: method=kelly_criterion (error={str(e)}) - using LLM suggestion")
                            trade_amount = min(position_size_usdt, available_balance * config.MAX_POSITION_SIZE)
                    else:
                        # Fallback: Use LLM's calculated position size capped by config
                        trade_amount = min(position_size_usdt, available_balance * config.MAX_POSITION_SIZE)
                    logger.info(
                        f"Trade execution start: action=buy symbol={config.SYMBOL} "
                        f"amount={trade_amount:.2f} leverage={leverage:.1f} price={current_price:.2f}"
                    )

                    self.console.print(
                        f"[bold green]🟢 Executing BUY: ${trade_amount:.2f} with {leverage:.1f}x leverage[/bold green]"
                    )
                    sys.stdout.flush()  # Ensure output appears immediately in Docker logs

                    # Use execution engine for order optimization if available
                    execution_price = current_price
                    if self.execution_engine:
                        try:
                            # Get spread and volatility for order selection
                            spread_bps = 10.0  # Would get from orderbook
                            volatility_bps = (
                                indicators.get("atr", 0) / current_price * 10000 if current_price > 0 else 20.0
                            )
                            edge_bps = confidence * 100

                            order_type = self.execution_engine.select_order_type(
                                venue=config.EXCHANGE,
                                spread_bps=spread_bps,
                                volatility_bps=volatility_bps,
                                edge_bps=edge_bps,
                                urgency="normal",
                            )

                            # Calculate limit offset if needed
                            if order_type.value in ["limit", "post_only"]:
                                offset_bps = self.execution_engine.calculate_limit_offset(
                                    order_type, spread_bps, volatility_bps, "buy"
                                )
                                execution_price = current_price * (1 + offset_bps / 10000)

                            logger.debug(f"Order type selected: {order_type.value}, price={execution_price:.2f}")
                        except Exception as e:
                            logger.debug(f"Execution engine error: {e}, using market price")

                    trade = self.trading_engine.execute_buy(
                        config.SYMBOL, execution_price, trade_amount, confidence, decision, leverage
                    )
                    if trade:
                        trade_executed = True
                        self.last_trade_time = datetime.now()  # Update cooldown timer
                        logger.info(
                            f"TRADE_EXECUTION_SUCCESS action=buy trade_id={trade['id']} " f"symbol={config.SYMBOL}"
                        )
                        self.console.print(
                            f"[bold green]✅ BUY trade executed successfully (ID: {trade['id']})[/bold green]"
                        )
                    else:
                        logger.error(
                            f"TRADE_EXECUTION_FAILED action=buy symbol={config.SYMBOL} "
                            f"reason=returned_none possible_causes=insufficient_balance_or_max_positions"
                        )
                        self.console.print(
                            "[bold red]❌ BUY trade failed (insufficient balance or other error)[/bold red]"
                        )
                else:
                    logger.warning(
                        f"TRADE_SKIPPED action=buy reason=position_size_validation_failed "
                        f"balance_positive={available_balance > 0} "
                        f"position_size_positive={position_size_usdt > 0} "
                        f"balance={available_balance:.2f} position_size={position_size_usdt:.2f}"
                    )
            elif action == "buy" and confidence >= min_confidence and direction == "short":
                logger.info(
                    f"TRADE_CONDITION_CHECK action=short status=passed "
                    f"confidence={confidence:.2f} direction={direction}"
                )

                # Execute short position
                available_balance = portfolio["balance"]
                logger.debug(
                    f"POSITION_SIZE_VALIDATION balance={available_balance:.2f} "
                    f"requested_size={position_size_usdt:.2f} "
                    f"max_allowed={available_balance * config.MAX_POSITION_SIZE:.2f}"
                )

                if available_balance > 0 and position_size_usdt > 0:
                    # Calculate optimal position size using Kelly criterion (if position_sizer available)
                    if self.position_sizer:
                        try:
                            recent_trades = self.trading_engine.trades[-50:] if len(self.trading_engine.trades) > 0 else []
                            volatility = indicators.get("atr", None) if indicators else None
                            
                            kelly_optimal_size = self.position_sizer.calculate_optimal_position_size(
                                portfolio=portfolio,
                                recent_trades=recent_trades,
                                max_position_size=config.MAX_POSITION_SIZE,
                                existing_positions=self.trading_engine.positions,
                                confidence=confidence,
                                volatility=volatility,
                                current_price=current_price
                            )
                            
                            # Validate Kelly optimal size is reasonable
                            if kelly_optimal_size <= 0:
                                logger.warning(
                                    f"Kelly optimal size is invalid ({kelly_optimal_size:.2f}), using LLM suggestion"
                                )
                                trade_amount = min(position_size_usdt, available_balance * config.MAX_POSITION_SIZE)
                            else:
                                max_allowed_by_config = available_balance * config.MAX_POSITION_SIZE
                                optimal_size = max(position_size_usdt, kelly_optimal_size)
                                optimal_size = min(optimal_size, available_balance * 0.5)  # Safety cap
                                trade_amount = min(optimal_size, max_allowed_by_config)
                        except Exception as e:
                            logger.warning(f"Error calculating Kelly position size: {e}, using LLM suggestion")
                            trade_amount = min(position_size_usdt, available_balance * config.MAX_POSITION_SIZE)
                    else:
                        trade_amount = min(position_size_usdt, available_balance * config.MAX_POSITION_SIZE)
                    logger.info(
                        f"TRADE_EXECUTION_START action=short symbol={config.SYMBOL} "
                        f"amount={trade_amount:.2f} leverage={leverage:.1f}"
                    )

                    self.console.print(
                        f"[bold red]🔴 Executing SHORT: ${trade_amount:.2f} with {leverage:.1f}x leverage[/bold red]"
                    )
                    sys.stdout.flush()  # Ensure output appears immediately in Docker logs
                    trade = self.trading_engine.execute_short(
                        config.SYMBOL, current_price, trade_amount, confidence, decision, leverage
                    )
                    if trade:
                        trade_executed = True
                        self.last_trade_time = datetime.now()  # Update cooldown timer
                        logger.info(
                            f"TRADE_EXECUTION_SUCCESS action=short trade_id={trade['id']} " f"symbol={config.SYMBOL}"
                        )
                        self.console.print(
                            f"[bold red]✅ SHORT trade executed successfully (ID: {trade['id']})[/bold red]"
                        )
                    else:
                        logger.error(
                            f"TRADE_EXECUTION_FAILED action=short symbol={config.SYMBOL} "
                            f"reason=returned_none possible_causes=insufficient_balance_or_max_positions"
                        )
                        self.console.print(
                            "[bold red]❌ SHORT trade failed (insufficient balance or other error)[/bold red]"
                        )
                else:
                    logger.warning(
                        f"TRADE_SKIPPED action=short reason=position_size_validation_failed "
                        f"balance_positive={available_balance > 0} "
                        f"position_size_positive={position_size_usdt > 0}"
                    )

            elif action == "sell" and confidence >= min_confidence:
                logger.info(f"TRADE_CONDITION_CHECK action=sell status=passed " f"confidence={confidence:.2f}")

                # Sell all or partial position
                symbol = config.SYMBOL
                has_position = symbol in self.trading_engine.positions
                logger.debug(f"POSITION_CHECK symbol={symbol} position_exists={has_position}")

                if has_position:
                    position = self.trading_engine.positions[symbol]
                    position_qty = position.get("quantity", 0)
                    logger.info(
                        f"TRADE_EXECUTION_START action=sell symbol={symbol} " f"position_quantity={position_qty:.6f}"
                    )

                    self.console.print(f"[bold red]🔴 Executing SELL with {leverage:.1f}x leverage[/bold red]")
                    sys.stdout.flush()  # Ensure output appears immediately in Docker logs
                    trade = self.trading_engine.execute_sell(
                        config.SYMBOL, current_price, confidence=confidence, llm_decision=decision, leverage=leverage
                    )
                    if trade:
                        trade_executed = True
                        self.last_trade_time = datetime.now()  # Update cooldown timer
                        profit = trade.get("profit", 0)
                        profit_pct = trade.get("profit_pct", 0)
                        logger.info(
                            f"TRADE_EXECUTION_SUCCESS action=sell trade_id={trade['id']} "
                            f"symbol={symbol} profit={profit:.2f} profit_pct={profit_pct:.2f}"
                        )
                        profit_color = "green" if profit >= 0 else "red"
                        self.console.print(
                            f"[bold green]✅ SELL trade executed successfully[/bold green] "
                            f"(ID: {trade['id']}, Profit: [{profit_color}]${profit:.2f}[/{profit_color}])"
                        )
                    else:
                        logger.error(
                            f"TRADE_EXECUTION_FAILED action=sell symbol={symbol} "
                            f"reason=returned_none possible_causes=position_quantity_invalid_or_validation_error"
                        )
                        self.console.print("[bold red]❌ SELL trade failed (no position or other error)[/bold red]")
                else:
                    logger.warning(
                        f"TRADE_SKIPPED action=sell reason=no_position symbol={symbol} "
                        f"available_positions={list(self.trading_engine.positions.keys())}"
                    )
                    self.console.print("[yellow]No position to sell[/yellow]")
            else:
                # Automatic exit logic: If holding position and confidence drops below exit threshold
                exit_confidence_threshold = getattr(config, 'EXIT_CONFIDENCE_THRESHOLD', 0.5)
                symbol = config.SYMBOL
                has_position = symbol in self.trading_engine.positions
                
                if has_position and confidence < exit_confidence_threshold:
                    # Check if position is profitable or losing
                    position = self.trading_engine.positions[symbol]
                    entry_price = position.get("avg_price", 0)
                    position_qty = position.get("quantity", 0)
                    
                    if entry_price > 0 and position_qty > 0:
                        # Calculate current P&L
                        side = position.get("side", "long")
                        if side == "long":
                            pnl_pct = ((current_price - entry_price) / entry_price) * 100
                        else:  # short
                            pnl_pct = ((entry_price - current_price) / entry_price) * 100
                        
                        # Trigger automatic exit if:
                        # 1. Confidence is low (< exit threshold) AND
                        # 2. (Position is losing OR position is in small profit but momentum weakening)
                        should_exit = False
                        exit_reason = ""
                        
                        if pnl_pct < -1.0:  # Losing more than 1%
                            should_exit = True
                            exit_reason = f"automatic_exit_loss_confidence_low (P&L: {pnl_pct:.2f}%, confidence: {confidence:.2f})"
                        elif pnl_pct > 0 and pnl_pct < 2.0 and confidence < exit_confidence_threshold:  # Small profit but low confidence
                            should_exit = True
                            exit_reason = f"automatic_exit_low_confidence_profit (P&L: {pnl_pct:.2f}%, confidence: {confidence:.2f})"
                        elif action == "hold" and confidence < exit_confidence_threshold * 0.8:  # Very low confidence
                            should_exit = True
                            exit_reason = f"automatic_exit_very_low_confidence (confidence: {confidence:.2f})"
                        
                        if should_exit:
                            logger.info(
                                f"AUTOMATIC_EXIT_TRIGGERED symbol={symbol} reason={exit_reason} "
                                f"pnl_pct={pnl_pct:.2f} confidence={confidence:.2f}"
                            )
                            self.console.print(
                                f"[bold yellow]⚠️ Automatic exit triggered: {exit_reason}[/bold yellow]"
                            )
                            
                            # Attempt to close position with retry logic
                            max_retries = 2
                            trade = None
                            for attempt in range(max_retries):
                                try:
                                    trade = self.trading_engine.execute_sell(
                                        config.SYMBOL, current_price, confidence=confidence, 
                                        llm_decision={"action": "sell", "justification": exit_reason}, 
                                        leverage=leverage
                                    )
                                    if trade:
                                        break
                                    elif attempt < max_retries - 1:
                                        logger.warning(
                                            f"AUTOMATIC_EXIT_RETRY symbol={symbol} attempt={attempt + 1}/{max_retries}"
                                        )
                                        time.sleep(0.5)  # Brief delay before retry
                                except Exception as e:
                                    logger.error(
                                        f"AUTOMATIC_EXIT_ERROR symbol={symbol} attempt={attempt + 1} error={e}"
                                    )
                                    if attempt < max_retries - 1:
                                        time.sleep(0.5)
                            
                            if trade:
                                trade_executed = True
                                self.last_trade_time = datetime.now()  # Update cooldown timer
                                profit = trade.get("profit", 0)
                                profit_pct = trade.get("profit_pct", 0)
                                logger.info(
                                    f"AUTOMATIC_EXIT_SUCCESS symbol={symbol} trade_id={trade.get('id')} "
                                    f"profit={profit:.2f} profit_pct={profit_pct:.2f}"
                                )
                                profit_color = "green" if profit >= 0 else "red"
                                self.console.print(
                                    f"[bold green]✅ Automatic exit executed[/bold green] "
                                    f"(Profit: [{profit_color}]${profit:.2f}[/{profit_color}])"
                                )
                            else:
                                # Verify if position still exists
                                still_has_position = symbol in self.trading_engine.positions
                                if still_has_position:
                                    logger.error(
                                        f"AUTOMATIC_EXIT_FAILED symbol={symbol} reason=execution_failed "
                                        f"position_still_exists=True - MANUAL INTERVENTION MAY BE REQUIRED"
                                    )
                                    self.console.print(
                                        f"[bold red]⚠️ Automatic exit failed - position still open![/bold red]"
                                    )
                                else:
                                    logger.warning(
                                        f"AUTOMATIC_EXIT_FAILED symbol={symbol} reason=execution_failed "
                                        f"position_still_exists=False (may have been closed elsewhere)"
                                    )
                
                if not trade_executed:
                    logger.debug(
                        f"TRADE_CONDITION_CHECK action={action} status=failed "
                        f"confidence={confidence:.2f} min_required={min_confidence:.2f} "
                        f"confidence_sufficient={confidence >= min_confidence}"
                    )
                    self.console.print("[yellow]🟡 Decision is to HOLD or confidence too low. No action taken.[/yellow]")

            if not trade_executed:
                logger.info(
                    f"TRADE_EXECUTION_SUMMARY status=no_trade_executed action={action} "
                    f"confidence={confidence:.2f} direction={direction}"
                )
                self.console.print("[dim]No trade executed this cycle[/dim]")
            else:
                logger.info(f"TRADE_EXECUTION_SUMMARY status=trade_executed_successfully")

            # Record trade with performance learner (for closed trades)
            if self.performance_learner and trade_executed:
                try:
                    # Get the last trade (most recently executed)
                    if self.trading_engine.trades:
                        last_trade = self.trading_engine.trades[-1]
                        # Only record if it's a sell (closed trade with profit)
                        if last_trade.get("side") == "sell" and "profit" in last_trade:
                            # Build price history for regime detection
                            price_history = []
                            if indicators:
                                # Use current price as latest
                                price_history.append({
                                    "close": current_price,
                                    "high": indicators.get("ema_20", current_price) * 1.01,
                                    "low": indicators.get("ema_20", current_price) * 0.99,
                                })
                            
                            self.performance_learner.record_trade(
                                trade=last_trade,
                                market_data={"price_history": price_history, **market_data},
                                regime=None  # Will be auto-detected
                            )
                            logger.debug(f"Recorded trade with performance learner: profit={last_trade.get('profit', 0):.2f}")
                except Exception as e:
                    logger.warning(f"Error recording trade with performance learner: {e}")

            # Check circuit breaker (kill switch for broken strategies)
            circuit_breaker_active = self._check_circuit_breaker()
            if circuit_breaker_active:
                logger.critical("CIRCUIT BREAKER ACTIVE: Trading halted")
                self.console.print("[bold red]🚨 CIRCUIT BREAKER: Trading halted due to risk limits[/bold red]")
                return  # Skip rest of cycle

            # Check for strategy rebalancing (if multi-strategy enabled)
            if self.strategy_manager and getattr(config, 'ENABLE_MULTI_STRATEGY', False):
                try:
                    should_rebalance, reason = self.strategy_manager.should_rebalance(
                        performance_range_threshold=0.15,
                        rebalance_interval_hours=getattr(config, 'STRATEGY_REBALANCE_INTERVAL_HOURS', 24),
                        loss_threshold=-0.10,
                        last_rebalance_time=self.last_rebalance_time
                    )
                    
                    if should_rebalance:
                        logger.info(f"STRATEGY_REBALANCING_TRIGGERED reason={reason}")
                        self.console.print(f"[bold yellow]⚖️ Rebalancing strategies: {reason}[/bold yellow]")
                        
                        # Get total capital
                        total_capital = portfolio.get("total_value", portfolio.get("balance", 0))
                        
                        # Reallocate capital
                        new_allocations = self.strategy_manager.reallocate_capital(
                            total_capital=total_capital,
                            min_allocation=getattr(config, 'MIN_STRATEGY_ALLOCATION', 0.05),
                            max_allocation=getattr(config, 'MAX_STRATEGY_ALLOCATION', 0.50),
                            performance_range_threshold=0.15,
                            rebalance_interval_hours=getattr(config, 'STRATEGY_REBALANCE_INTERVAL_HOURS', 24)
                        )
                        
                        # Update last rebalance time
                        self.last_rebalance_time = datetime.now()
                        
                        logger.info(f"STRATEGY_REALLOCATION_COMPLETE allocations={new_allocations}")
                except Exception as e:
                    logger.warning(f"Error during strategy rebalancing: {e}")

            # Save portfolio state with full metrics
            self.trading_engine._save_portfolio_state(current_price)

            # Save behavioral metrics snapshot
            if self.trading_engine.supabase_client and "bullish_tilt" in portfolio:
                try:
                    behavioral_data = {
                        "timestamp": datetime.now().isoformat(),
                        "bullish_tilt": float(portfolio.get("bullish_tilt", 0.5)),
                        "avg_holding_period_hours": float(portfolio.get("avg_holding_period_hours", 0)),
                        "trade_frequency_per_day": float(portfolio.get("trade_frequency_per_day", 0)),
                        "avg_position_size_usdt": float(portfolio.get("avg_position_size_usdt", 0)),
                        "avg_confidence": float(portfolio.get("avg_confidence", 0)),
                        "exit_plan_tightness": float(portfolio.get("exit_plan_tightness", 0)),
                        "active_positions_count": int(
                            portfolio.get("active_positions_count", len(self.trading_engine.positions))
                        ),
                        "total_trading_fees": float(portfolio.get("total_trading_fees", 0)),
                        "fee_impact_pct": float(portfolio.get("fee_impact_pct", 0)),
                        "sharpe_ratio": (
                            float(portfolio.get("sharpe_ratio", 0))
                            if portfolio.get("sharpe_ratio") is not None
                            else None
                        ),
                        "volatility": (
                            float(portfolio.get("volatility", 0)) if portfolio.get("volatility") is not None else None
                        ),
                        "max_drawdown": (
                            float(portfolio.get("max_drawdown", 0))
                            if portfolio.get("max_drawdown") is not None
                            else None
                        ),
                        "win_rate": (
                            float(portfolio.get("win_rate", 0)) if portfolio.get("win_rate") is not None else None
                        ),
                        "profit_factor": (
                            float(portfolio.get("profit_factor", 0))
                            if portfolio.get("profit_factor") is not None
                            else None
                        ),
                        "risk_adjusted_return": (
                            float(portfolio.get("risk_adjusted_return", 0))
                            if portfolio.get("risk_adjusted_return") is not None
                            else None
                        ),
                        "excess_return": (
                            float(portfolio.get("excess_return", 0))
                            if portfolio.get("excess_return") is not None
                            else None
                        ),
                    }
                    self.trading_engine.supabase_client.add_behavioral_metrics(behavioral_data)
                    logger.debug("Behavioral metrics saved to Supabase")
                except Exception as e:
                    logger.error(f"Failed to save behavioral metrics: {e}", exc_info=True)

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
        # Start monitoring service
        self._start_monitoring_background()

        # Colorful startup message
        self.console.print(
            Panel.fit(
                f"[bold green]🚀 Bot Starting![/bold green]\n"
                f"[cyan]Running every {config.RUN_INTERVAL_SECONDS} seconds[/cyan]\n"
                f"[yellow]Press Ctrl+C to stop[/yellow]",
                border_style="green",
                padding=(1, 2),
            )
        )

        try:
            while True:
                self.run_cycle()

                # Flush metrics to Supabase periodically
                current_time = time.time()
                if current_time - self.last_metrics_flush >= self.metrics_flush_interval:
                    self._flush_metrics_to_supabase()
                    self.last_metrics_flush = current_time

                # Explicitly flush stdout to ensure output appears in Docker logs immediately
                sys.stdout.flush()

                # Show waiting message with timestamp
                wait_start = datetime.now().strftime("%H:%M:%S")
                self.console.print(
                    f"[dim]⏳ Waiting {config.RUN_INTERVAL_SECONDS} seconds until next cycle... "
                    f"(started at {wait_start})[/dim]"
                )
                sys.stdout.flush()  # Flush again after print

                time.sleep(config.RUN_INTERVAL_SECONDS)

                # Show that we're starting the next cycle
                next_cycle_time = datetime.now().strftime("%H:%M:%S")
                self.console.print(f"[cyan]⏰ Next cycle starting at {next_cycle_time}[/cyan]")
                sys.stdout.flush()

        except KeyboardInterrupt:
            self.console.print("\n[bold yellow]🛑 Bot stopped by user[/bold yellow]")

            # Stop monitoring service
            if self.monitoring_running:
                try:
                    import asyncio

                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(self.monitoring_service.stop())
                    loop.close()
                    logger.info("Monitoring service stopped")
                except Exception as e:
                    logger.error(f"Error stopping monitoring service: {e}", exc_info=True)

            # Final metrics flush
            try:
                self._flush_metrics_to_supabase()
            except Exception as e:
                logger.error(f"Error in final metrics flush: {e}", exc_info=True)

            # Print final portfolio summary
            try:
                ticker = self.data_fetcher.get_ticker()
                current_price = float(ticker["last"])
                portfolio = self.trading_engine.get_portfolio_summary(current_price)

                # Create colorful final summary table
                final_table = Table(title="📊 Final Portfolio Summary", show_header=True, header_style="bold magenta")
                final_table.add_column("Metric", style="cyan", no_wrap=True)
                final_table.add_column("Value", style="green")

                return_pct = portfolio["total_return_pct"]
                return_color = "green" if return_pct >= 0 else "red"

                final_table.add_row("Initial Balance", f"${portfolio['initial_balance']:,.2f}")
                final_table.add_row("Current Balance", f"${portfolio['balance']:,.2f}")
                final_table.add_row("Positions Value", f"${portfolio['positions_value']:,.2f}")
                final_table.add_row("Total Value", f"${portfolio['total_value']:,.2f}")
                final_table.add_row(
                    "Total Return",
                    f"[{return_color}]${portfolio['total_return']:,.2f} ({return_pct:+.2f}%)[/{return_color}]",
                )
                final_table.add_row("Total Trades", str(portfolio["total_trades"]))

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
        """,
    )

    # Trading mode arguments
    parser.add_argument("--live", action="store_true", help="Enable live trading mode (default: paper trading)")
    parser.add_argument(
        "--no-testnet", action="store_true", help="Use live market data instead of testnet (default: testnet)"
    )

    # LLM provider arguments
    parser.add_argument(
        "--provider",
        choices=["mock", "deepseek", "openai", "anthropic"],
        help="LLM provider to use (default: from config)",
    )
    parser.add_argument("--api-key", help="API key for LLM provider")
    parser.add_argument("--model", help="Model name to use (default: provider default)")

    # Exchange arguments
    parser.add_argument(
        "--exchange",
        choices=["bybit", "binance", "coinbase", "kraken"],
        help="Exchange to use (default: kraken from config). Note: Bybit/Binance restricted in USA",
    )
    parser.add_argument("--symbol", help="Trading pair symbol (default: from config)")

    # Other arguments
    parser.add_argument("--interval", type=int, help="Run interval in seconds (default: from config)")
    parser.add_argument("--balance", type=float, help="Initial paper trading balance (default: from config)")

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
