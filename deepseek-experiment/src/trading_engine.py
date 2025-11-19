"""
Trading engine for paper trading simulation.

Records paper trades, tracks portfolio balance, and can be upgraded to live trading
by modifying the execution methods (see config.TRADING_MODE).
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from config import config

from .logger import LogDomain, get_logger
from .resilience import CircuitBreakerConfig, RetryConfig, circuit_breaker, retry
from .risk_client import OrderValidationResult, RiskClient
from .security import SecurityManager, validate_trading_inputs

logger = get_logger(__name__, domain=LogDomain.TRADING)


class TradingEngine:
    """
    Simulates trading execution and tracks paper trading portfolio.

    Records all trades to a JSON file and maintains portfolio state.
    Designed to easily upgrade to live trading by modifying execute_order methods.

    Attributes:
        balance: Current available balance (not in positions)
        positions: Dictionary of current open positions
        trades_file: Path to JSON file storing trade history
        trades: List of all executed trades
    """

    def __init__(self, initial_balance: float = None):
        """
        Initialize the trading engine.

        Args:
            initial_balance: Starting balance for paper trading. Defaults to config.
        """
        self.balance = initial_balance or config.INITIAL_BALANCE
        self.positions = {}  # symbol -> position dict
        self.trades_file = config.DATA_DIR / "trades.json"
        self.trades = []

        # Initialize security manager
        self.security_manager = SecurityManager()

        # Initialize database manager
        self.db_manager = None

        # Initialize Supabase client for production
        self.supabase_client = None
        try:
            from .supabase_client import get_supabase_service

            self.supabase_client = get_supabase_service()
            logger.info("Component initialized: component=supabase_client status=success")
        except ImportError as e:
            logger.warning(f"Component unavailable: component=supabase_client reason=import_error (error={str(e)})")
        except Exception as e:
            logger.warning(f"Component initialization failed: component=supabase_client (error={str(e)})")

        # Initialize risk client (optional - will fail gracefully if service unavailable)
        self.risk_client = None
        try:
            risk_service_url = os.getenv("RISK_SERVICE_URL", "http://localhost:8003")
            self.risk_client = RiskClient(risk_service_url=risk_service_url)
            logger.info(f"Component initialized: component=risk_client url={risk_service_url}")
        except Exception as e:
            logger.warning(f"Component unavailable: component=risk_client reason=service_down (error={str(e)})")

        # Initialize event logger (optional)
        self.event_logger = None
        try:
            from .event_logger import EventLogger

            self.event_logger = EventLogger()
            logger.info("Component initialized: component=event_logger status=success")
        except Exception as e:
            logger.warning(f"Component unavailable: component=event_logger (error={str(e)})")

        # Initialize position sizer (optional - for Kelly Criterion sizing)
        self.position_sizer = None
        if getattr(config, 'ENABLE_KELLY_SIZING', False):
            try:
                from .position_sizer import PositionSizer

                self.position_sizer = PositionSizer()
                logger.info("Component initialized: component=position_sizer type=Kelly_Criterion")
            except Exception as e:
                logger.warning(f"Component unavailable: component=position_sizer (error={str(e)})")

        # Daily loss tracking
        self.daily_start_nav = None
        self.daily_start_time = None
        self._initialize_daily_tracking()

        # Load existing trades if file exists
        self._load_trades()

        # Load portfolio state including positions
        self._load_portfolio_state()

        logger.info(f"Engine initialized: component=trading_engine balance={self.balance:.2f} mode={config.TRADING_MODE}")

    def _load_trades(self):
        """Load trade history from file."""
        if self.trades_file.exists():
            try:
                with open(self.trades_file, "r") as f:
                    self.trades = json.load(f)
                logger.info(f"Trades loaded: count={len(self.trades)} file={self.trades_file}")
            except Exception as e:
                logger.error(f"Trades load failed: file={self.trades_file} (error={str(e)})")
                self.trades = []

    def _load_portfolio_state(self):
        """Load portfolio state including positions from file."""
        portfolio_file = config.DATA_DIR / "portfolio.json"
        if not portfolio_file.exists():
            logger.debug("Portfolio state file does not exist, starting with empty positions")
            return

        try:
            with open(portfolio_file, "r") as f:
                state = json.load(f)

            # Restore positions if they exist and are valid
            if "positions" in state and isinstance(state["positions"], dict):
                restored_positions = {}
                for symbol, position_data in state["positions"].items():
                    # Validate position data has required fields
                    if isinstance(position_data, dict) and "quantity" in position_data and "avg_price" in position_data:
                        # Ensure trailing stop tracking fields exist
                        if "highest_price" not in position_data:
                            position_data["highest_price"] = position_data.get("avg_price", 0)
                        if "lowest_price" not in position_data:
                            position_data["lowest_price"] = position_data.get("avg_price", 0)
                        restored_positions[symbol] = position_data

                self.positions = restored_positions
                logger.info(f"Restored {len(self.positions)} positions from portfolio state")

                # Log position details for audit trail
                for symbol, pos in self.positions.items():
                    logger.debug(
                        f"Restored position: {symbol} side={pos.get('side', 'long')} "
                        f"quantity={pos.get('quantity', 0):.6f} avg_price={pos.get('avg_price', 0):.2f}"
                    )

            # Restore balance if available and valid
            if "balance" in state:
                try:
                    restored_balance = float(state["balance"])
                    if restored_balance >= 0:
                        self.balance = restored_balance
                        logger.info(f"Restored balance: ${self.balance:.2f}")
                    else:
                        logger.warning(f"Invalid balance in portfolio state: {restored_balance}, using default")
                except (ValueError, TypeError) as e:
                    logger.warning(f"Could not restore balance from portfolio state: {e}")

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in portfolio state file: {e}")
        except Exception as e:
            logger.error(f"Error loading portfolio state: {e}", exc_info=True)

    def _initialize_daily_tracking(self):
        """Initialize daily loss tracking with current NAV and time."""
        from datetime import datetime, timezone

        current_time = datetime.now(timezone.utc)
        # Set to start of current day in UTC
        self.daily_start_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        # Will be set when we have a price
        self.daily_start_nav = None
        logger.debug(f"Daily tracking initialized: start_time={self.daily_start_time.isoformat()}")

    def _check_and_reset_daily_tracking(self, current_nav: float):
        """Check if we need to reset daily tracking at midnight UTC."""
        from datetime import datetime, timezone

        current_time = datetime.now(timezone.utc)

        # Check if we've crossed midnight UTC
        if self.daily_start_time is None:
            self._initialize_daily_tracking()

        # Calculate days difference
        days_diff = (current_time.date() - self.daily_start_time.date()).days

        if days_diff > 0:
            # New day - reset tracking
            logger.info(f"Daily tracking reset: new day detected (days_diff={days_diff})")
            self.daily_start_nav = current_nav
            self.daily_start_time = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        elif self.daily_start_nav is None:
            # First time setting daily start NAV
            self.daily_start_nav = current_nav
            logger.debug(f"Daily start NAV set: {self.daily_start_nav:.2f}")

    def _calculate_daily_loss_pct(self, current_nav: float) -> float:
        """Calculate daily loss percentage."""
        if self.daily_start_nav is None or self.daily_start_nav <= 0:
            return 0.0

        if current_nav >= self.daily_start_nav:
            # No loss or profit
            return 0.0

        # Calculate loss percentage
        daily_loss_pct = (self.daily_start_nav - current_nav) / self.daily_start_nav
        return max(0.0, daily_loss_pct)  # Ensure non-negative

    def _save_trades(self):
        """Save trade history to file."""
        try:
            # Clean trades to remove non-serializable objects (like MagicMock from tests)
            def clean_value(value):
                """Recursively clean non-serializable values."""
                # Keep None as-is
                if value is None:
                    return None
                # Check if it's a mock object (has mock attributes)
                if hasattr(value, "_mock_name") or hasattr(value, "_mock_children"):
                    # Return a sentinel to indicate this should be skipped
                    return "__SKIP_MOCK__"
                # Handle dicts
                if isinstance(value, dict):
                    cleaned = {}
                    for k, v in value.items():
                        cleaned_v = clean_value(v)
                        # Skip mock objects but keep None values
                        if cleaned_v != "__SKIP_MOCK__":
                            cleaned[k] = cleaned_v
                    return cleaned
                # Handle lists
                if isinstance(value, list):
                    cleaned = []
                    for v in value:
                        cleaned_v = clean_value(v)
                        # Skip mock objects but keep None values
                        if cleaned_v != "__SKIP_MOCK__":
                            cleaned.append(cleaned_v)
                    return cleaned
                # Test if value is JSON serializable
                try:
                    json.dumps(value)
                    return value
                except (TypeError, ValueError):
                    # Convert non-serializable to string representation
                    return str(value)

            cleaned_trades = [clean_value(trade) for trade in self.trades]

            with open(self.trades_file, "w") as f:
                json.dump(cleaned_trades, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving trades: {e}")

    def _save_portfolio_state(self, current_price: float = None):
        """Save current portfolio state to file and database."""
        logger.debug(f"PORTFOLIO_STATE_SAVE_START current_price={current_price}")

        # Get full portfolio summary with all metrics
        if current_price is not None:
            portfolio_summary = self.get_portfolio_summary(current_price)
            current_nav = portfolio_summary.get("total_value", self.balance)

            # Check and reset daily tracking if needed
            self._check_and_reset_daily_tracking(current_nav)

            # Calculate daily loss percentage
            daily_loss_pct = self._calculate_daily_loss_pct(current_nav)
            logger.debug(
                f"Daily loss tracking: start_nav={self.daily_start_nav:.2f} current_nav={current_nav:.2f} daily_loss_pct={daily_loss_pct:.4f}"
            )
        else:
            # Fallback if no price provided
            portfolio_summary = {
                "balance": self.balance,
                "positions_value": 0,
                "total_value": self.balance,
                "initial_balance": config.INITIAL_BALANCE,
                "total_return": 0,
                "total_return_pct": 0,
                "open_positions": len(self.positions),
                "total_trades": len(self.trades),
            }
            current_nav = self.balance
            daily_loss_pct = None

        logger.debug(
            f"PORTFOLIO_STATE_SUMMARY balance={portfolio_summary.get('balance', 0):.2f} "
            f"open_positions={portfolio_summary.get('open_positions', 0)} "
            f"total_value={portfolio_summary.get('total_value', 0):.2f} "
            f"total_trades={portfolio_summary.get('total_trades', 0)}"
        )

        portfolio_file = config.DATA_DIR / "portfolio.json"

        # Prepare state for file storage
        state = {
            "balance": self.balance,
            "positions": self.positions,
            "timestamp": datetime.now().isoformat(),
            **portfolio_summary,
        }

        try:
            with open(portfolio_file, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving portfolio state: {e}")

        # Prepare full metrics for Supabase
        if self.supabase_client and current_price is not None:
            try:
                portfolio_snapshot = {
                    "timestamp": datetime.now().isoformat(),
                    "balance": float(portfolio_summary.get("balance", 0)),
                    "positions_value": float(portfolio_summary.get("positions_value", 0)),
                    "total_value": float(portfolio_summary.get("total_value", 0)),
                    "initial_balance": float(portfolio_summary.get("initial_balance", config.INITIAL_BALANCE)),
                    "total_return": float(portfolio_summary.get("total_return", 0)),
                    "total_return_pct": float(portfolio_summary.get("total_return_pct", 0)),
                    "total_trades": int(portfolio_summary.get("total_trades", 0)),
                    "active_positions": int(portfolio_summary.get("open_positions", 0)),
                    "total_fees": float(portfolio_summary.get("total_trading_fees", 0)),
                    "sharpe_ratio": (
                        float(portfolio_summary.get("sharpe_ratio", 0))
                        if portfolio_summary.get("sharpe_ratio") is not None
                        else None
                    ),
                    "volatility": (
                        float(portfolio_summary.get("volatility", 0))
                        if portfolio_summary.get("volatility") is not None
                        else None
                    ),
                    "max_drawdown": (
                        float(portfolio_summary.get("max_drawdown", 0))
                        if portfolio_summary.get("max_drawdown") is not None
                        else None
                    ),
                    "win_rate": (
                        float(portfolio_summary.get("win_rate", 0))
                        if portfolio_summary.get("win_rate") is not None
                        else None
                    ),
                    "profit_factor": (
                        float(portfolio_summary.get("profit_factor", 0))
                        if portfolio_summary.get("profit_factor") is not None
                        else None
                    ),
                    "risk_adjusted_return": (
                        float(portfolio_summary.get("risk_adjusted_return", 0))
                        if portfolio_summary.get("risk_adjusted_return") is not None
                        else None
                    ),
                    "excess_return": (
                        float(portfolio_summary.get("excess_return", 0))
                        if portfolio_summary.get("excess_return") is not None
                        else None
                    ),
                    "avg_profit_per_trade": (
                        float(portfolio_summary.get("avg_profit_per_trade", 0))
                        if portfolio_summary.get("avg_profit_per_trade") is not None
                        else None
                    ),
                    "avg_trade_duration_hours": (
                        float(portfolio_summary.get("avg_trade_duration_hours", 0))
                        if portfolio_summary.get("avg_trade_duration_hours") is not None
                        else None
                    ),
                    "max_consecutive_wins": (
                        int(portfolio_summary.get("max_consecutive_wins", 0))
                        if portfolio_summary.get("max_consecutive_wins") is not None
                        else None
                    ),
                    "max_consecutive_losses": (
                        int(portfolio_summary.get("max_consecutive_losses", 0))
                        if portfolio_summary.get("max_consecutive_losses") is not None
                        else None
                    ),
                }

                success = self.supabase_client.update_portfolio(portfolio_snapshot)
                if success:
                    logger.debug("Portfolio snapshot with full metrics saved to Supabase")
                else:
                    logger.warning("Failed to save portfolio snapshot to Supabase")
            except Exception as e:
                logger.error(f"Failed to save portfolio to Supabase: {e}", exc_info=True)

    def get_portfolio_value(self, current_price: float) -> float:
        """
        Calculate total portfolio value including open positions.

        Args:
            current_price: Current market price of the asset

        Returns:
            Total portfolio value
        """
        position_value = 0.0
        for symbol, position in self.positions.items():
            if position["side"] == "long":
                # Long position: profit/loss from price appreciation
                position_value += position["quantity"] * current_price
            elif position["side"] == "short":
                # Short position: profit/loss from price decline
                # Short profit = (entry_price - current_price) * quantity
                entry_value = position["quantity"] * position["avg_price"]
                current_value = position["quantity"] * current_price
                short_pnl = entry_value - current_value  # Profit when price goes down
                position_value += entry_value + short_pnl  # Original value + PnL
            else:
                # Fallback for other position types
                position_value += position.get("value", 0)

        return self.balance + position_value

    # Error Handling Note:
    # - Circuit breaker: Prevents cascading failures (5 failures = 30s timeout)
    # - Retry logic: Retries up to 3 times with exponential backoff
    # - For live trading: Additional error handling will be needed for:
    #   * Exchange API errors (order rejection, insufficient margin, rate limits)
    #   * Network errors (timeouts, connection failures)
    #   * Order status verification (partial fills, cancellations)
    #   * Exchange-specific error codes and handling
    @validate_trading_inputs
    @circuit_breaker(CircuitBreakerConfig(failure_threshold=5, recovery_timeout=30))
    @retry(RetryConfig(max_attempts=3, base_delay=0.5, max_delay=5.0))
    def execute_buy(
        self,
        symbol: str,
        price: float,
        amount_usdt: float,
        confidence: float,
        llm_decision: Dict = None,
        leverage: float = 1.0,
    ) -> Optional[Dict]:
        """
        Execute a buy order (paper trading) with leverage support.

        Args:
            symbol: Trading pair symbol
            price: Execution price
            amount_usdt: Amount in USDT to spend (notional value)
            confidence: LLM confidence score
            llm_decision: Full LLM decision dict for additional context
            leverage: Leverage multiplier (1.0-10.0)

        Returns:
            Trade dictionary if successful, None otherwise
        """
        logger.info(
            f"TRADE_EXECUTION_START action=buy symbol={symbol} price={price:.2f} amount_usdt={amount_usdt:.2f} "
            f"confidence={confidence:.2f} leverage={leverage:.1f}"
        )
        logger.info(
            f"TRADE_EXECUTION_CONTEXT symbol={symbol} balance={self.balance:.2f} "
            f"active_positions={len(self.positions)} existing_position={symbol in self.positions}"
        )
        if symbol in self.positions:
            pos = self.positions[symbol]
            logger.info(
                f"EXISTING_POSITION symbol={symbol} quantity={pos.get('quantity', 0):.6f} "
                f"avg_price={pos.get('avg_price', 0):.2f} margin_used={pos.get('margin_used', 0):.2f}"
            )

        # CRITICAL: Risk validation BEFORE trade execution
        if self.risk_client:
            try:
                current_nav = self.get_portfolio_value(price)
                quantity = amount_usdt / price
                position_value = amount_usdt  # Notional value for new position

                # If position exists, add to existing position value
                if symbol in self.positions:
                    existing_pos = self.positions[symbol]
                    position_value = existing_pos.get("notional_value", 0) + amount_usdt

                validation_result = self.risk_client.validate_order(
                    strategy_id="default",
                    symbol=symbol,
                    side="buy",
                    quantity=quantity,
                    price=price,
                    leverage=leverage,
                    current_nav=current_nav,
                    position_value=position_value,
                )

                if not validation_result.approved:
                    logger.error(
                        f"TRADE_REJECTED reason=risk_validation_failed symbol={symbol} "
                        f"status={validation_result.status} reason={validation_result.reason}"
                    )
                    return None

                logger.info(f"RISK_VALIDATION_PASSED symbol={symbol} status={validation_result.status}")
            except Exception as e:
                logger.error(f"Error during risk validation: {e}", exc_info=True)
                # If risk service is required and validation fails, reject trade
                if config.RISK_SERVICE_REQUIRED:
                    logger.critical(f"Risk validation failed and RISK_SERVICE_REQUIRED=true - REJECTING trade")
                    return None
                # Otherwise, log warning but continue (for paper trading)
                logger.warning(f"Risk validation error but continuing (RISK_SERVICE_REQUIRED=false)")

        # Kelly Criterion position sizing (if enabled) - for buy orders
        original_amount_usdt = amount_usdt
        if self.position_sizer and (getattr(config, 'ENABLE_KELLY_SIZING', False) or (llm_decision and llm_decision.get("use_kelly_sizing", False))):
            try:
                portfolio = {
                    "balance": self.balance,
                    "total_value": self.get_portfolio_value(price),
                }
                # Get recent trades for Kelly calculation
                recent_trades = self.trades[-getattr(config, 'KELLY_LOOKBACK_TRADES', 30):] if len(self.trades) > 0 else []
                
                kelly_size = self.position_sizer.calculate_optimal_position_size(
                    portfolio=portfolio,
                    recent_trades=recent_trades,
                    max_position_size=config.MAX_POSITION_SIZE,
                    existing_positions=self.positions
                )
                
                if kelly_size > 0:
                    # Override amount_usdt with Kelly-calculated size
                    amount_usdt = kelly_size
                    logger.info(
                        f"KELLY_SIZING_APPLIED symbol={symbol} "
                        f"llm_suggested={original_amount_usdt:.2f} kelly_calculated={kelly_size:.2f} "
                        f"override={amount_usdt:.2f}"
                    )
                else:
                    logger.debug(f"Kelly sizing returned 0, using LLM suggested size: {original_amount_usdt:.2f}")
            except Exception as e:
                logger.warning(f"Error calculating Kelly position size: {e}, using LLM suggested size")
                amount_usdt = original_amount_usdt

        # Validate leverage
        original_leverage = leverage
        leverage = max(1.0, min(leverage, config.MAX_LEVERAGE))  # Clamp between 1.0 and MAX_LEVERAGE
        if leverage != original_leverage:
            logger.warning(
                f"LEVERAGE_ADJUSTED symbol={symbol} original={original_leverage:.1f} "
                f"adjusted={leverage:.1f} max_leverage={config.MAX_LEVERAGE}"
            )

        # Calculate required margin (amount_usdt / leverage)
        required_margin = amount_usdt / leverage
        logger.debug(
            f"MARGIN_CALCULATION symbol={symbol} amount_usdt={amount_usdt:.2f} leverage={leverage:.1f} "
            f"required_margin={required_margin:.2f}"
        )

        # Check if we have enough balance for margin
        if required_margin > self.balance:
            logger.error(
                f"TRADE_REJECTED reason=insufficient_balance symbol={symbol} "
                f"available_balance={self.balance:.2f} required_margin={required_margin:.2f} "
                f"shortfall={required_margin - self.balance:.2f}"
            )
            return None

        # Check position limits (Alpha Arena constraint)
        if len(self.positions) >= config.MAX_ACTIVE_POSITIONS:
            logger.error(
                f"TRADE_REJECTED reason=max_positions_reached symbol={symbol} "
                f"current_positions={len(self.positions)} max_allowed={config.MAX_ACTIVE_POSITIONS} "
                f"position_symbols={list(self.positions.keys())}"
            )
            return None

        # Apply position size limit based on margin
        max_margin = self.balance * config.MAX_POSITION_SIZE
        logger.debug(
            f"POSITION_SIZE_LIMIT symbol={symbol} max_margin_allowed={max_margin:.2f} "
            f"max_position_size_pct={config.MAX_POSITION_SIZE * 100:.1f}"
        )
        original_required_margin = required_margin
        required_margin = min(required_margin, max_margin)
        if required_margin != original_required_margin:
            logger.warning(
                f"MARGIN_CAPPED symbol={symbol} original={original_required_margin:.2f} "
                f"capped={required_margin:.2f} reason=position_size_limit"
            )
        amount_usdt = required_margin * leverage
        logger.debug(
            f"POSITION_SIZE_FINAL symbol={symbol} amount_usdt={amount_usdt:.2f} "
            f"margin={required_margin:.2f} leverage={leverage:.1f}"
        )

        quantity = amount_usdt / price
        logger.debug(
            f"QUANTITY_CALCULATED symbol={symbol} quantity={quantity:.6f} "
            f"amount_usdt={amount_usdt:.2f} price={price:.2f}"
        )

        # Calculate trading fees
        trading_fee = amount_usdt * (config.TRADING_FEE_PERCENT / 100)
        total_cost = required_margin + trading_fee
        logger.debug(
            f"FEE_CALCULATION symbol={symbol} trading_fee={trading_fee:.2f} "
            f"fee_percent={config.TRADING_FEE_PERCENT} total_cost={total_cost:.2f}"
        )

        # Extract LLM context for storage
        # Note: llm_decision may be None if not provided, or may be sanitized by @validate_trading_inputs decorator
        llm_prompt = llm_decision.get("_prompt", "") if llm_decision else ""
        llm_raw_response = llm_decision.get("_raw_response", "") if llm_decision else ""
        llm_parsed_decision = {k: v for k, v in (llm_decision or {}).items() if not k.startswith("_")}

        # Record trade with enhanced LLM context
        # Safely extract justification - handle both None and dict cases
        justification = ""
        if llm_decision:
            if isinstance(llm_decision, dict):
                justification = llm_decision.get("justification", "")
            else:
                logger.warning(f"llm_decision is not a dict: {type(llm_decision)}")

        trade = {
            "id": len(self.trades) + 1,
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "side": "buy",
            "direction": "long",
            "price": price,
            "quantity": quantity,
            "amount_usdt": amount_usdt,
            "leverage": leverage,
            "margin_used": required_margin,
            "trading_fee": trading_fee,
            "confidence": confidence,
            "mode": config.TRADING_MODE,
            "llm_prompt": llm_prompt,
            "llm_raw_response": llm_raw_response,
            "llm_parsed_decision": llm_parsed_decision,
            "llm_justification": justification,
            "llm_reasoning": justification,
            "llm_risk_assessment": (
                llm_decision.get("risk_assessment", "medium")
                if llm_decision and isinstance(llm_decision, dict)
                else "medium"
            ),
            "llm_position_size_usdt": (
                llm_decision.get("position_size_usdt", 0.0) if llm_decision and isinstance(llm_decision, dict) else 0.0
            ),
            "exit_plan": llm_decision.get("exit_plan", {}) if llm_decision and isinstance(llm_decision, dict) else {},
        }

        # Update balance and positions (deduct margin + fees)
        balance_before = self.balance
        self.balance -= required_margin + trading_fee
        balance_after = self.balance
        logger.debug(
            f"BALANCE_UPDATE symbol={symbol} balance_before={balance_before:.2f} "
            f"balance_after={balance_after:.2f} deduction={required_margin + trading_fee:.2f}"
        )

        if symbol in self.positions:
            # Average in if position exists
            pos = self.positions[symbol]
            old_quantity = pos["quantity"]
            old_avg_price = pos["avg_price"]
            old_margin = pos.get("margin_used", 0)

            total_cost = (pos["quantity"] * pos["avg_price"]) + amount_usdt
            total_quantity = pos["quantity"] + quantity
            total_margin = pos.get("margin_used", 0) + required_margin
            new_avg_price = total_cost / total_quantity

            logger.info(
                f"POSITION_AVERAGING symbol={symbol} operation=add_to_existing "
                f"old_quantity={old_quantity:.6f} old_avg_price={old_avg_price:.2f} "
                f"old_margin={old_margin:.2f} add_quantity={quantity:.6f} add_price={price:.2f} "
                f"new_quantity={total_quantity:.6f} new_avg_price={new_avg_price:.2f} "
                f"new_margin={total_margin:.2f}"
            )

            # Update trailing stop tracking when averaging positions
            existing_highest = pos.get("highest_price", old_avg_price)
            existing_lowest = pos.get("lowest_price", old_avg_price)

            # Preserve existing highest/lowest if better than current price
            new_highest = max(existing_highest, price)
            new_lowest = min(existing_lowest, price)

            self.positions[symbol] = {
                "side": "long",
                "quantity": total_quantity,
                "avg_price": new_avg_price,
                "value": amount_usdt,
                "leverage": leverage,
                "margin_used": total_margin,
                "notional_value": total_quantity * price,
                "highest_price": new_highest,  # Preserve trailing stop tracking
                "lowest_price": new_lowest,  # Preserve trailing stop tracking
                # Preserve existing stop-loss, take-profit, and exit plan if they exist
                "stop_loss": pos.get("stop_loss", 0),
                "take_profit": pos.get("take_profit", 0),
                "exit_plan": pos.get("exit_plan", {}),
                "partial_profit_taken": pos.get("partial_profit_taken", False),
            }
        else:
            logger.info(
                f"POSITION_CREATED symbol={symbol} operation=new_position quantity={quantity:.6f} "
                f"entry_price={price:.2f} margin_used={required_margin:.2f} "
                f"notional_value={quantity * price:.2f}"
            )

            # Store stop-loss and take-profit from exit plan
            exit_plan = llm_decision.get("exit_plan", {}) if llm_decision else {}
            stop_loss = exit_plan.get("stop_loss", 0)
            take_profit = exit_plan.get("profit_target", 0)

            self.positions[symbol] = {
                "side": "long",
                "quantity": quantity,
                "avg_price": price,
                "value": amount_usdt,
                "leverage": leverage,
                "margin_used": required_margin,
                "notional_value": quantity * price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "exit_plan": exit_plan,
                "highest_price": price,  # For trailing stop-loss
                "lowest_price": price,  # For trailing stop-loss (shorts)
            }

        logger.debug(f"TRADE_PERSISTENCE_START symbol={symbol} trade_id={trade['id']}")
        self.trades.append(trade)
        self._save_trades()
        logger.debug(
            f"TRADE_PERSISTENCE_COMPLETE symbol={symbol} trade_id={trade['id']} "
            f"total_trades={len(self.trades)} storage=local_file"
        )

        self._save_portfolio_state()
        logger.debug(
            f"PORTFOLIO_STATE_SAVED symbol={symbol} balance={self.balance:.2f} " f"positions={len(self.positions)}"
        )

        # Update risk service with portfolio state
        if self.risk_client:
            try:
                current_nav = self.get_portfolio_value(price)
                # Calculate daily loss percentage
                self._check_and_reset_daily_tracking(current_nav)
                daily_loss_pct = self._calculate_daily_loss_pct(current_nav)
                self.risk_client.update_portfolio(
                    nav=current_nav, positions=self.positions, daily_loss_pct=daily_loss_pct
                )
                logger.debug(
                    f"Risk service updated with portfolio state: nav={current_nav:.2f} daily_loss_pct={daily_loss_pct:.4f}"
                )
            except Exception as e:
                logger.warning(f"Failed to update risk service: {e}")

        # Save to Supabase if available (synchronous call - CRITICAL FIX)
        if self.supabase_client:
            try:
                success = self.supabase_client.add_trade(trade)
                if success:
                    logger.info(
                        f"TRADE_PERSISTENCE_COMPLETE symbol={symbol} trade_id={trade['id']} "
                        f"storage=supabase status=success"
                    )
                else:
                    logger.error(
                        f"TRADE_PERSISTENCE_FAILED symbol={symbol} trade_id={trade['id']} "
                        f"storage=supabase status=false_received reason=unknown"
                    )
            except Exception as e:
                logger.error(
                    f"TRADE_PERSISTENCE_FAILED symbol={symbol} trade_id={trade['id']} "
                    f"storage=supabase exception_type={type(e).__name__} error={str(e)}",
                    exc_info=True,
                )
        else:
            logger.debug(
                f"TRADE_PERSISTENCE_SKIPPED symbol={symbol} trade_id={trade['id']} "
                f"storage=supabase reason=client_not_available"
            )

        logger.info(
            f"TRADE_EXECUTION_COMPLETE action=buy symbol={symbol} trade_id={trade['id']} "
            f"quantity={quantity:.6f} price={price:.2f} amount_usdt={amount_usdt:.2f} "
            f"leverage={leverage:.1f} margin_used={required_margin:.2f} fee={trading_fee:.2f} "
            f"balance_remaining={self.balance:.2f} total_positions={len(self.positions)}"
        )

        # Log order fill event
        if self.event_logger:
            try:
                self.event_logger.log_order_fill(
                    order_intent={
                        "symbol": symbol,
                        "side": "buy",
                        "quantity": quantity,
                        "price": price,
                        "leverage": leverage,
                    },
                    fill={
                        "trade_id": trade["id"],
                        "price": price,
                        "quantity": quantity,
                        "amount_usdt": amount_usdt,
                        "fee": trading_fee,
                        "margin_used": required_margin,
                    },
                    venue=config.EXCHANGE,
                )
            except Exception as e:
                logger.debug(f"Error logging order fill: {e}")

        return trade

    @validate_trading_inputs
    @circuit_breaker(CircuitBreakerConfig(failure_threshold=5, recovery_timeout=30))
    @retry(RetryConfig(max_attempts=3, base_delay=0.5, max_delay=5.0))
    def execute_sell(
        self,
        symbol: str,
        price: float,
        quantity: float = None,
        confidence: float = 0.0,
        llm_decision: Dict = None,
        leverage: float = 1.0,
    ) -> Optional[Dict]:
        """
        Execute a sell order (paper trading) with leverage support.

        Args:
            symbol: Trading pair symbol
            price: Execution price
            quantity: Quantity to sell (None to sell entire position)
            confidence: LLM confidence score
            llm_decision: Full LLM decision dict for additional context
            leverage: Leverage multiplier (1.0-10.0)

        Returns:
            Trade dictionary if successful, None otherwise
        """
        logger.info(
            f"TRADE_EXECUTION_START action=sell symbol={symbol} price={price:.2f} "
            f"requested_quantity={quantity if quantity else 'ALL'} confidence={confidence:.2f} "
            f"leverage={leverage:.1f}"
        )
        logger.info(
            f"TRADE_EXECUTION_CONTEXT symbol={symbol} balance={self.balance:.2f} "
            f"active_positions={len(self.positions)} position_exists={symbol in self.positions}"
        )

        # Check if we have a position
        if symbol not in self.positions or self.positions[symbol]["quantity"] <= 0:
            logger.error(
                f"TRADE_REJECTED reason=no_position_to_sell symbol={symbol} "
                f"position_exists={symbol in self.positions} "
                f"available_positions={list(self.positions.keys())}"
            )
            if symbol in self.positions:
                pos = self.positions[symbol]
                logger.error(f"TRADE_REJECTED_DETAIL symbol={symbol} position_quantity={pos.get('quantity', 0):.6f}")
            return None

        position = self.positions[symbol]
        position_quantity = position["quantity"]
        position_avg_price = position["avg_price"]
        position_margin = position.get("margin_used", 0)

        logger.info(
            f"EXISTING_POSITION symbol={symbol} quantity={position_quantity:.6f} "
            f"avg_price={position_avg_price:.2f} margin_used={position_margin:.2f} "
            f"leverage={position.get('leverage', 1.0):.1f}"
        )

        sell_quantity = quantity if quantity else position_quantity

        # CRITICAL: Risk validation BEFORE trade execution
        if self.risk_client:
            try:
                current_nav = self.get_portfolio_value(price)
                # For sell, position_value is the remaining position value after selling
                remaining_quantity = position_quantity - sell_quantity
                position_value = remaining_quantity * price if remaining_quantity > 0 else 0

                validation_result = self.risk_client.validate_order(
                    strategy_id="default",
                    symbol=symbol,
                    side="sell",
                    quantity=sell_quantity,
                    price=price,
                    leverage=position.get("leverage", 1.0),
                    current_nav=current_nav,
                    position_value=position_value,
                )

                if not validation_result.approved:
                    logger.error(
                        f"TRADE_REJECTED reason=risk_validation_failed symbol={symbol} "
                        f"status={validation_result.status} reason={validation_result.reason}"
                    )
                    return None

                logger.info(f"RISK_VALIDATION_PASSED symbol={symbol} status={validation_result.status}")
            except Exception as e:
                logger.error(f"Error during risk validation: {e}", exc_info=True)
                # If risk service is required and validation fails, reject trade
                if config.RISK_SERVICE_REQUIRED:
                    logger.critical(f"Risk validation failed and RISK_SERVICE_REQUIRED=true - REJECTING trade")
                    return None
                # Otherwise, log warning but continue (for paper trading)
                logger.warning(f"Risk validation error but continuing (RISK_SERVICE_REQUIRED=false)")
        logger.debug(
            f"SELL_QUANTITY_DETERMINED symbol={symbol} requested={quantity if quantity else 'ALL'} "
            f"final={sell_quantity:.6f}"
        )

        if sell_quantity > position_quantity:
            logger.warning(
                f"QUANTITY_CAPPED symbol={symbol} requested={sell_quantity:.6f} "
                f"available={position_quantity:.6f} reason=insufficient_quantity"
            )
            sell_quantity = position_quantity

        amount_usdt = sell_quantity * price
        position_side = position.get("side", "long")

        # Calculate profit based on position side
        if position_side == "long":
            # Long position: profit when price goes up
            profit = (price - position_avg_price) * sell_quantity
            profit_pct = ((price - position_avg_price) / position_avg_price) * 100 if position_avg_price > 0 else 0
        else:  # short
            # Short position: profit when price goes down
            profit = (position_avg_price - price) * sell_quantity
            profit_pct = ((position_avg_price - price) / position_avg_price) * 100 if position_avg_price > 0 else 0

        logger.debug(
            f"SELL_CALCULATION symbol={symbol} sell_quantity={sell_quantity:.6f} "
            f"sell_price={price:.2f} amount_usdt={amount_usdt:.2f} entry_price={position_avg_price:.2f} "
            f"profit={profit:.2f} profit_pct={profit_pct:.2f}"
        )

        # Calculate trading fees
        trading_fee = amount_usdt * (config.TRADING_FEE_PERCENT / 100)
        logger.debug(
            f"FEE_CALCULATION symbol={symbol} trading_fee={trading_fee:.2f} "
            f"fee_percent={config.TRADING_FEE_PERCENT} amount_usdt={amount_usdt:.2f}"
        )

        # Calculate margin to return (proportional to quantity sold)
        margin_returned = (position_margin * sell_quantity) / position_quantity
        net_gain = profit - trading_fee
        logger.debug(
            f"MARGIN_CALCULATION symbol={symbol} margin_returned={margin_returned:.2f} "
            f"profit={profit:.2f} fee={trading_fee:.2f} net_gain={net_gain:.2f}"
        )

        # Extract LLM context for storage
        # Note: llm_decision may be None if not provided, or may be sanitized by @validate_trading_inputs decorator
        llm_prompt = llm_decision.get("_prompt", "") if llm_decision else ""
        llm_raw_response = llm_decision.get("_raw_response", "") if llm_decision else ""
        llm_parsed_decision = {k: v for k, v in (llm_decision or {}).items() if not k.startswith("_")}

        # Safely extract justification - handle both None and dict cases
        justification = ""
        if llm_decision:
            if isinstance(llm_decision, dict):
                justification = llm_decision.get("justification", "")
            else:
                logger.warning(f"llm_decision is not a dict: {type(llm_decision)}")

        # Record trade with enhanced LLM context
        trade = {
            "id": len(self.trades) + 1,
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "side": "sell",
            "direction": "long",
            "price": price,
            "quantity": sell_quantity,
            "amount_usdt": amount_usdt,
            "leverage": position.get("leverage", 1.0),
            "margin_returned": margin_returned,
            "trading_fee": trading_fee,
            "profit": profit,
            "profit_pct": (profit / (position["avg_price"] * sell_quantity)) * 100,
            "confidence": confidence,
            "mode": config.TRADING_MODE,
            "llm_prompt": llm_prompt,
            "llm_raw_response": llm_raw_response,
            "llm_parsed_decision": llm_parsed_decision,
            "llm_justification": justification,
            "llm_reasoning": justification,
            "llm_risk_assessment": (
                llm_decision.get("risk_assessment", "medium")
                if llm_decision and isinstance(llm_decision, dict)
                else "medium"
            ),
            "llm_position_size_usdt": (
                llm_decision.get("position_size_usdt", 0.0) if llm_decision and isinstance(llm_decision, dict) else 0.0
            ),
            "exit_plan": llm_decision.get("exit_plan", {}) if llm_decision and isinstance(llm_decision, dict) else {},
        }

        # Update balance and positions (add margin returned + profit - fees)
        balance_before = self.balance
        balance_update = margin_returned + profit - trading_fee
        self.balance += balance_update
        balance_after = self.balance

        logger.debug(
            f"BALANCE_UPDATE symbol={symbol} balance_before={balance_before:.2f} "
            f"balance_after={balance_after:.2f} margin_returned={margin_returned:.2f} "
            f"profit={profit:.2f} fee={trading_fee:.2f} net_addition={balance_update:.2f}"
        )

        position["quantity"] -= sell_quantity
        position["value"] -= position_avg_price * sell_quantity
        position["margin_used"] -= margin_returned

        remaining_quantity = position["quantity"]
        logger.debug(
            f"POSITION_UPDATE symbol={symbol} quantity_before={position_quantity:.6f} "
            f"quantity_sold={sell_quantity:.6f} quantity_remaining={remaining_quantity:.6f}"
        )

        if position["quantity"] <= 0:
            logger.info(
                f"POSITION_CLOSED symbol={symbol} operation=full_close "
                f"remaining_positions={len(self.positions) - 1}"
            )
            del self.positions[symbol]
        else:
            logger.info(
                f"POSITION_PARTIAL_CLOSE symbol={symbol} operation=partial_close "
                f"remaining_quantity={position['quantity']:.6f} "
                f"remaining_margin={position['margin_used']:.2f}"
            )
            self.positions[symbol] = position

        logger.debug(f"TRADE_PERSISTENCE_START symbol={symbol} trade_id={trade['id']}")
        self.trades.append(trade)
        self._save_trades()
        logger.debug(
            f"TRADE_PERSISTENCE_COMPLETE symbol={symbol} trade_id={trade['id']} "
            f"total_trades={len(self.trades)} storage=local_file"
        )

        self._save_portfolio_state()
        logger.debug(
            f"PORTFOLIO_STATE_SAVED symbol={symbol} balance={self.balance:.2f} " f"positions={len(self.positions)}"
        )

        # Save to Supabase if available (synchronous call - CRITICAL FIX)
        if self.supabase_client:
            try:
                success = self.supabase_client.add_trade(trade)
                if success:
                    logger.info(
                        f"TRADE_PERSISTENCE_COMPLETE symbol={symbol} trade_id={trade['id']} "
                        f"storage=supabase status=success"
                    )
                else:
                    logger.error(
                        f"TRADE_PERSISTENCE_FAILED symbol={symbol} trade_id={trade['id']} "
                        f"storage=supabase status=false_received reason=unknown"
                    )
            except Exception as e:
                logger.error(
                    f"TRADE_PERSISTENCE_FAILED symbol={symbol} trade_id={trade['id']} "
                    f"storage=supabase exception_type={type(e).__name__} error={str(e)}",
                    exc_info=True,
                )
        else:
            logger.debug(
                f"TRADE_PERSISTENCE_SKIPPED symbol={symbol} trade_id={trade['id']} "
                f"storage=supabase reason=client_not_available"
            )

        logger.info(
            f"TRADE_EXECUTION_COMPLETE action=sell symbol={symbol} trade_id={trade['id']} "
            f"quantity={sell_quantity:.6f} price={price:.2f} amount_usdt={amount_usdt:.2f} "
            f"profit={profit:.2f} profit_pct={profit_pct:.2f} fee={trading_fee:.2f} "
            f"margin_returned={margin_returned:.2f} balance_remaining={self.balance:.2f} "
            f"total_positions={len(self.positions)}"
        )

        # Log order fill event
        if self.event_logger:
            try:
                self.event_logger.log_order_fill(
                    order_intent={"symbol": symbol, "side": "sell", "quantity": sell_quantity, "price": price},
                    fill={
                        "trade_id": trade["id"],
                        "price": price,
                        "quantity": sell_quantity,
                        "amount_usdt": amount_usdt,
                        "fee": trading_fee,
                        "profit": profit,
                    },
                    pnl_attrib={"profit": profit, "fee_impact": trading_fee},
                    venue=config.EXCHANGE,
                )
            except Exception as e:
                logger.debug(f"Error logging order fill: {e}")

        return trade

    @validate_trading_inputs
    @circuit_breaker(CircuitBreakerConfig(failure_threshold=5, recovery_timeout=30))
    @retry(RetryConfig(max_attempts=3, base_delay=0.5, max_delay=5.0))
    def execute_short(
        self,
        symbol: str,
        price: float,
        amount_usdt: float,
        confidence: float,
        llm_decision: Dict = None,
        leverage: float = 1.0,
    ) -> Optional[Dict]:
        """
        Execute a short order (paper trading) with leverage support.

        Args:
            symbol: Trading pair symbol
            price: Execution price
            amount_usdt: Amount in USDT to short (notional value)
            confidence: LLM confidence score
            llm_decision: Full LLM decision dict for additional context
            leverage: Leverage multiplier (1.0-10.0)

        Returns:
            Trade dictionary if successful, None otherwise
        """
        logger.info(
            f"TRADE_EXECUTION_START action=short symbol={symbol} price={price:.2f} amount_usdt={amount_usdt:.2f} "
            f"confidence={confidence:.2f} leverage={leverage:.1f}"
        )
        logger.info(
            f"TRADE_EXECUTION_CONTEXT symbol={symbol} balance={self.balance:.2f} "
            f"active_positions={len(self.positions)} existing_position={symbol in self.positions}"
        )
        if symbol in self.positions:
            pos = self.positions[symbol]
            logger.info(
                f"EXISTING_POSITION symbol={symbol} quantity={pos.get('quantity', 0):.6f} "
                f"avg_price={pos.get('avg_price', 0):.2f} margin_used={pos.get('margin_used', 0):.2f} "
                f"side={pos.get('side', 'unknown')}"
            )

        # CRITICAL: Risk validation BEFORE trade execution
        if self.risk_client:
            try:
                current_nav = self.get_portfolio_value(price)
                quantity = amount_usdt / price
                position_value = amount_usdt  # Notional value for new position

                # If position exists, add to existing position value
                if symbol in self.positions:
                    existing_pos = self.positions[symbol]
                    position_value = existing_pos.get("notional_value", 0) + amount_usdt

                validation_result = self.risk_client.validate_order(
                    strategy_id="default",
                    symbol=symbol,
                    side="short",
                    quantity=quantity,
                    price=price,
                    leverage=leverage,
                    current_nav=current_nav,
                    position_value=position_value,
                )

                if not validation_result.approved:
                    logger.error(
                        f"TRADE_REJECTED reason=risk_validation_failed symbol={symbol} "
                        f"status={validation_result.status} reason={validation_result.reason}"
                    )
                    return None

                logger.info(f"RISK_VALIDATION_PASSED symbol={symbol} status={validation_result.status}")
            except Exception as e:
                logger.error(f"Error during risk validation: {e}", exc_info=True)
                # If risk service is required and validation fails, reject trade
                if config.RISK_SERVICE_REQUIRED:
                    logger.critical(f"Risk validation failed and RISK_SERVICE_REQUIRED=true - REJECTING trade")
                    return None
                # Otherwise, log warning but continue (for paper trading)
                logger.warning(f"Risk validation error but continuing (RISK_SERVICE_REQUIRED=false)")

        # Kelly Criterion position sizing (if enabled) - for short orders
        original_amount_usdt = amount_usdt
        if self.position_sizer and (getattr(config, 'ENABLE_KELLY_SIZING', False) or (llm_decision and llm_decision.get("use_kelly_sizing", False))):
            try:
                portfolio = {
                    "balance": self.balance,
                    "total_value": self.get_portfolio_value(price),
                }
                # Get recent trades for Kelly calculation
                recent_trades = self.trades[-getattr(config, 'KELLY_LOOKBACK_TRADES', 30):] if len(self.trades) > 0 else []
                
                kelly_size = self.position_sizer.calculate_optimal_position_size(
                    portfolio=portfolio,
                    recent_trades=recent_trades,
                    max_position_size=config.MAX_POSITION_SIZE,
                    existing_positions=self.positions
                )
                
                if kelly_size > 0:
                    # Override amount_usdt with Kelly-calculated size
                    amount_usdt = kelly_size
                    logger.info(
                        f"KELLY_SIZING_APPLIED symbol={symbol} "
                        f"llm_suggested={original_amount_usdt:.2f} kelly_calculated={kelly_size:.2f} "
                        f"override={amount_usdt:.2f}"
                    )
                else:
                    logger.debug(f"Kelly sizing returned 0, using LLM suggested size: {original_amount_usdt:.2f}")
            except Exception as e:
                logger.warning(f"Error calculating Kelly position size: {e}, using LLM suggested size")
                amount_usdt = original_amount_usdt

        # Validate leverage
        original_leverage = leverage
        leverage = max(1.0, min(leverage, config.MAX_LEVERAGE))
        if leverage != original_leverage:
            logger.warning(
                f"LEVERAGE_ADJUSTED symbol={symbol} original={original_leverage:.1f} "
                f"adjusted={leverage:.1f} max_leverage={config.MAX_LEVERAGE}"
            )

        # Calculate required margin (amount_usdt / leverage)
        required_margin = amount_usdt / leverage
        logger.debug(
            f"MARGIN_CALCULATION symbol={symbol} amount_usdt={amount_usdt:.2f} leverage={leverage:.1f} "
            f"required_margin={required_margin:.2f}"
        )

        # Check if we have enough balance for margin
        if required_margin > self.balance:
            logger.error(
                f"TRADE_REJECTED reason=insufficient_balance symbol={symbol} "
                f"available_balance={self.balance:.2f} required_margin={required_margin:.2f} "
                f"shortfall={required_margin - self.balance:.2f}"
            )
            return None

        # Check position limits (Alpha Arena constraint)
        if len(self.positions) >= config.MAX_ACTIVE_POSITIONS:
            logger.error(
                f"TRADE_REJECTED reason=max_positions_reached symbol={symbol} "
                f"current_positions={len(self.positions)} max_allowed={config.MAX_ACTIVE_POSITIONS} "
                f"position_symbols={list(self.positions.keys())}"
            )
            return None

        # Apply position size limit based on margin
        max_margin = self.balance * config.MAX_POSITION_SIZE
        logger.debug(
            f"POSITION_SIZE_LIMIT symbol={symbol} max_margin_allowed={max_margin:.2f} "
            f"max_position_size_pct={config.MAX_POSITION_SIZE * 100:.1f}"
        )
        original_required_margin = required_margin
        required_margin = min(required_margin, max_margin)
        if required_margin != original_required_margin:
            logger.warning(
                f"MARGIN_CAPPED symbol={symbol} original={original_required_margin:.2f} "
                f"capped={required_margin:.2f} reason=position_size_limit"
            )
        amount_usdt = required_margin * leverage
        logger.debug(
            f"POSITION_SIZE_FINAL symbol={symbol} amount_usdt={amount_usdt:.2f} "
            f"margin={required_margin:.2f} leverage={leverage:.1f}"
        )

        quantity = amount_usdt / price
        logger.debug(
            f"QUANTITY_CALCULATED symbol={symbol} quantity={quantity:.6f} "
            f"amount_usdt={amount_usdt:.2f} price={price:.2f}"
        )

        # Calculate trading fees
        trading_fee = amount_usdt * (config.TRADING_FEE_PERCENT / 100)
        total_cost = required_margin + trading_fee
        logger.debug(
            f"FEE_CALCULATION symbol={symbol} trading_fee={trading_fee:.2f} "
            f"fee_percent={config.TRADING_FEE_PERCENT} total_cost={total_cost:.2f}"
        )

        # Extract LLM context for storage
        llm_prompt = llm_decision.get("_prompt", "") if llm_decision else ""
        llm_raw_response = llm_decision.get("_raw_response", "") if llm_decision else ""
        llm_parsed_decision = {k: v for k, v in (llm_decision or {}).items() if not k.startswith("_")}

        # Record trade with enhanced LLM context
        trade = {
            "id": len(self.trades) + 1,
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "side": "short",
            "direction": "short",
            "price": price,
            "quantity": quantity,
            "amount_usdt": amount_usdt,
            "leverage": leverage,
            "margin_used": required_margin,
            "trading_fee": trading_fee,
            "confidence": confidence,
            "mode": config.TRADING_MODE,
            "llm_prompt": llm_prompt,
            "llm_raw_response": llm_raw_response,
            "llm_parsed_decision": llm_parsed_decision,
            "llm_justification": llm_decision.get("justification", "") if llm_decision else "",
            "llm_reasoning": llm_decision.get("justification", "") if llm_decision else "",
            "llm_risk_assessment": llm_decision.get("risk_assessment", "medium") if llm_decision else "medium",
            "llm_position_size_usdt": llm_decision.get("position_size_usdt", 0.0) if llm_decision else 0.0,
            "exit_plan": llm_decision.get("exit_plan", {}) if llm_decision else {},
        }

        # Update balance and positions (deduct margin + fees)
        balance_before = self.balance
        self.balance -= required_margin + trading_fee
        balance_after = self.balance
        logger.debug(
            f"BALANCE_UPDATE symbol={symbol} balance_before={balance_before:.2f} "
            f"balance_after={balance_after:.2f} deduction={required_margin + trading_fee:.2f}"
        )

        if symbol in self.positions:
            # Average in if position exists
            pos = self.positions[symbol]
            old_quantity = pos["quantity"]
            old_avg_price = pos["avg_price"]
            old_margin = pos.get("margin_used", 0)

            total_cost = (pos["quantity"] * pos["avg_price"]) + amount_usdt
            total_quantity = pos["quantity"] + quantity
            total_margin = pos.get("margin_used", 0) + required_margin
            new_avg_price = total_cost / total_quantity

            logger.info(
                f"POSITION_AVERAGING symbol={symbol} operation=add_to_existing direction=short "
                f"old_quantity={old_quantity:.6f} old_avg_price={old_avg_price:.2f} "
                f"old_margin={old_margin:.2f} add_quantity={quantity:.6f} add_price={price:.2f} "
                f"new_quantity={total_quantity:.6f} new_avg_price={new_avg_price:.2f} "
                f"new_margin={total_margin:.2f}"
            )

            # Update trailing stop tracking when averaging positions
            existing_highest = pos.get("highest_price", old_avg_price)
            existing_lowest = pos.get("lowest_price", old_avg_price)

            # For shorts, preserve existing highest/lowest if better than current price
            # For shorts, we want lowest price (best entry) and highest price (worst entry)
            new_highest = max(existing_highest, price)
            new_lowest = min(existing_lowest, price)

            self.positions[symbol] = {
                "side": "short",
                "quantity": total_quantity,
                "avg_price": new_avg_price,
                "value": amount_usdt,
                "leverage": leverage,
                "margin_used": total_margin,
                "notional_value": total_quantity * price,
                "highest_price": new_highest,  # Preserve trailing stop tracking
                "lowest_price": new_lowest,  # Preserve trailing stop tracking
                # Preserve existing stop-loss, take-profit, and exit plan if they exist
                "stop_loss": pos.get("stop_loss", 0),
                "take_profit": pos.get("take_profit", 0),
                "exit_plan": pos.get("exit_plan", {}),
                "partial_profit_taken": pos.get("partial_profit_taken", False),
            }
        else:
            logger.info(
                f"POSITION_CREATED symbol={symbol} operation=new_position direction=short "
                f"quantity={quantity:.6f} entry_price={price:.2f} margin_used={required_margin:.2f} "
                f"notional_value={quantity * price:.2f}"
            )

            # Store stop-loss and take-profit from exit plan for shorts
            exit_plan = llm_decision.get("exit_plan", {}) if llm_decision else {}
            stop_loss = exit_plan.get("stop_loss", 0)
            take_profit = exit_plan.get("profit_target", 0)

            self.positions[symbol] = {
                "side": "short",
                "quantity": quantity,
                "avg_price": price,
                "value": amount_usdt,
                "leverage": leverage,
                "margin_used": required_margin,
                "notional_value": quantity * price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "exit_plan": exit_plan,
                "highest_price": price,  # For trailing stop-loss (shorts)
                "lowest_price": price,  # For trailing stop-loss
            }

        logger.debug(f"TRADE_PERSISTENCE_START symbol={symbol} trade_id={trade['id']}")
        self.trades.append(trade)
        self._save_trades()
        logger.debug(
            f"TRADE_PERSISTENCE_COMPLETE symbol={symbol} trade_id={trade['id']} "
            f"total_trades={len(self.trades)} storage=local_file"
        )

        self._save_portfolio_state()
        logger.debug(
            f"PORTFOLIO_STATE_SAVED symbol={symbol} balance={self.balance:.2f} " f"positions={len(self.positions)}"
        )

        # Save to Supabase if available (synchronous call - CRITICAL FIX)
        if self.supabase_client:
            try:
                success = self.supabase_client.add_trade(trade)
                if success:
                    logger.info(
                        f"TRADE_PERSISTENCE_COMPLETE symbol={symbol} trade_id={trade['id']} "
                        f"storage=supabase status=success"
                    )
                else:
                    logger.error(
                        f"TRADE_PERSISTENCE_FAILED symbol={symbol} trade_id={trade['id']} "
                        f"storage=supabase status=false_received reason=unknown"
                    )
            except Exception as e:
                logger.error(
                    f"TRADE_PERSISTENCE_FAILED symbol={symbol} trade_id={trade['id']} "
                    f"storage=supabase exception_type={type(e).__name__} error={str(e)}",
                    exc_info=True,
                )
        else:
            logger.debug(
                f"TRADE_PERSISTENCE_SKIPPED symbol={symbol} trade_id={trade['id']} "
                f"storage=supabase reason=client_not_available"
            )

        logger.info(
            f"TRADE_EXECUTION_COMPLETE action=short symbol={symbol} trade_id={trade['id']} "
            f"quantity={quantity:.6f} price={price:.2f} amount_usdt={amount_usdt:.2f} "
            f"leverage={leverage:.1f} margin_used={required_margin:.2f} fee={trading_fee:.2f} "
            f"balance_remaining={self.balance:.2f} total_positions={len(self.positions)}"
        )
        return trade

    def get_portfolio_summary(self, current_price: float) -> Dict:
        """
        Get a summary of the current portfolio state.

        Args:
            current_price: Current market price

        Returns:
            Dictionary with portfolio statistics
        """
        total_value = self.get_portfolio_value(current_price)
        initial_balance = config.INITIAL_BALANCE
        total_return = total_value - initial_balance
        total_return_pct = (total_return / initial_balance) * 100

        # Calculate advanced metrics
        advanced_metrics = self._calculate_advanced_metrics()

        return {
            "balance": self.balance,
            "positions_value": total_value - self.balance,
            "total_value": total_value,
            "initial_balance": initial_balance,
            "total_return": total_return,
            "total_return_pct": total_return_pct,
            "open_positions": len(self.positions),
            "total_trades": len(self.trades),
            **advanced_metrics,
        }

    def _calculate_advanced_metrics(self) -> Dict[str, Any]:
        """
        Calculate advanced trading metrics including Sharpe ratio and behavioral patterns.

        For Alpha Arena analysis.
        """
        if not self.trades:
            return {
                "win_rate": 0.0,
                "avg_profit_per_trade": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
                "volatility": 0.0,
                "profit_factor": 0.0,
                "avg_trade_duration_hours": 0.0,
                "max_consecutive_wins": 0,
                "max_consecutive_losses": 0,
                "excess_return": 0.0,
                "risk_adjusted_return": 0.0,
                # Alpha Arena behavioral metrics
                "bullish_tilt": 0.0,
                "avg_holding_period_hours": 0.0,
                "trade_frequency_per_day": 0.0,
                "avg_position_size_usdt": 0.0,
                "avg_confidence": 0.0,
                "exit_plan_tightness": 0.0,
                "active_positions_count": 0,
                "total_trading_fees": 0.0,
                "fee_impact_pct": 0.0,
            }

        # Basic trade analysis
        sell_trades = [t for t in self.trades if t.get("side") == "sell"]
        profits = [t.get("profit", 0) for t in sell_trades]

        # Initialize profit-based metrics (will be calculated if we have profits)
        win_rate = 0.0
        avg_profit = 0.0
        max_drawdown = 0.0
        sharpe_ratio = 0.0
        volatility = 0.0
        profit_factor = 0.0
        avg_trade_duration = 0.0
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        excess_return = 0.0
        risk_adjusted_return = 0.0

        # Calculate profit-based metrics only if we have closed trades
        if profits:
            # Win rate
            winning_trades = [p for p in profits if p > 0]
            win_rate = (len(winning_trades) / len(profits) * 100) if profits else 0

            # Average profit per trade
            avg_profit = sum(profits) / len(profits)

            # Max drawdown
            max_drawdown = self._calculate_max_drawdown(profits)

            # Enhanced Sharpe ratio calculation (Alpha Arena style)
            if len(profits) > 1:
                mean_return = sum(profits) / len(profits)
                variance = sum((p - mean_return) ** 2 for p in profits) / (len(profits) - 1)
                volatility = variance**0.5

                # Risk-free rate assumed to be 0 for crypto trading
                risk_free_rate = 0.0
                excess_return = mean_return - risk_free_rate
                sharpe_ratio = excess_return / volatility if volatility > 0 else 0

                # Risk-adjusted return (excess return per unit of risk)
                risk_adjusted_return = excess_return / max(volatility, 0.001)  # Avoid division by zero
            else:
                volatility = 0.0
                sharpe_ratio = 0.0
                excess_return = 0.0
                risk_adjusted_return = 0.0

            # Profit factor
            gross_profit = sum(p for p in profits if p > 0)
            gross_loss = abs(sum(p for p in profits if p < 0))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf") if gross_profit > 0 else 0

            # Trade duration analysis
            trade_durations = []
            for trade in self.trades:
                if "timestamp" in trade:
                    try:
                        trade_time = datetime.fromisoformat(trade["timestamp"].replace("Z", "+00:00"))
                        # Find corresponding buy trade for duration calculation
                        if trade.get("side") == "sell":
                            buy_trades = [
                                t
                                for t in self.trades
                                if t.get("side") == "buy"
                                and t.get("symbol") == trade.get("symbol")
                                and t.get("timestamp") < trade.get("timestamp")
                            ]
                            if buy_trades:
                                buy_time = datetime.fromisoformat(buy_trades[-1]["timestamp"].replace("Z", "+00:00"))
                                duration = (trade_time - buy_time).total_seconds() / 3600  # hours
                                trade_durations.append(duration)
                    except (ValueError, TypeError):
                        continue

            avg_trade_duration = sum(trade_durations) / len(trade_durations) if trade_durations else 0

            # Consecutive wins/losses
            max_consecutive_wins = self._calculate_max_consecutive(profits, lambda x: x > 0)
            max_consecutive_losses = self._calculate_max_consecutive(profits, lambda x: x < 0)

        # Alpha Arena behavioral pattern analysis
        behavioral_metrics = self._calculate_behavioral_metrics()

        return {
            "win_rate": win_rate,
            "avg_profit_per_trade": avg_profit,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "volatility": volatility,
            "profit_factor": profit_factor,
            "avg_trade_duration_hours": avg_trade_duration,
            "max_consecutive_wins": max_consecutive_wins,
            "max_consecutive_losses": max_consecutive_losses,
            "excess_return": excess_return,
            "risk_adjusted_return": risk_adjusted_return,
            **behavioral_metrics,
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

    def _calculate_max_consecutive(self, profits: List[float], condition) -> int:
        """Calculate maximum consecutive wins or losses."""
        if not profits:
            return 0

        max_consecutive = 0
        current_consecutive = 0

        for profit in profits:
            if condition(profit):
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        return max_consecutive

    def _calculate_behavioral_metrics(self) -> Dict[str, Any]:
        """Calculate Alpha Arena behavioral pattern metrics."""
        if not self.trades:
            return {
                "bullish_tilt": 0.0,
                "avg_holding_period_hours": 0.0,
                "trade_frequency_per_day": 0.0,
                "avg_position_size_usdt": 0.0,
                "avg_confidence": 0.0,
                "exit_plan_tightness": 0.0,
                "active_positions_count": len(self.positions),
                "total_trading_fees": 0.0,
                "fee_impact_pct": 0.0,
            }

        # Calculate bullish vs bearish tilt
        long_trades = [t for t in self.trades if t.get("side") == "buy" and t.get("direction") == "long"]
        short_trades = [t for t in self.trades if t.get("side") == "buy" and t.get("direction") == "short"]
        total_directional_trades = len(long_trades) + len(short_trades)
        bullish_tilt = len(long_trades) / total_directional_trades if total_directional_trades > 0 else 0.5

        # Calculate average holding period
        holding_periods = []
        for trade in self.trades:
            if "timestamp" in trade and trade.get("side") == "sell":
                try:
                    sell_time = datetime.fromisoformat(trade["timestamp"].replace("Z", "+00:00"))
                    # Find corresponding buy trade
                    buy_trades = [
                        t
                        for t in self.trades
                        if t.get("side") == "buy"
                        and t.get("symbol") == trade.get("symbol")
                        and t.get("timestamp") < trade.get("timestamp")
                    ]
                    if buy_trades:
                        buy_time = datetime.fromisoformat(buy_trades[-1]["timestamp"].replace("Z", "+00:00"))
                        duration = (sell_time - buy_time).total_seconds() / 3600  # hours
                        holding_periods.append(duration)
                except (ValueError, TypeError):
                    continue

        avg_holding_period = sum(holding_periods) / len(holding_periods) if holding_periods else 0.0

        # Calculate trade frequency per day (using time since first trade, not time between first and last)
        if self.trades:
            first_trade = min(self.trades, key=lambda x: x.get("timestamp", ""))
            try:
                start_time = datetime.fromisoformat(first_trade["timestamp"].replace("Z", "+00:00"))
                current_time = datetime.now(start_time.tzinfo) if start_time.tzinfo else datetime.now()
                days_elapsed = (current_time - start_time).total_seconds() / (24 * 3600)
                trade_frequency = len(self.trades) / max(days_elapsed, 0.001)  # Avoid division by zero
            except (ValueError, TypeError):
                trade_frequency = 0.0
        else:
            trade_frequency = 0.0

        # Calculate average position size and confidence
        position_sizes = [t.get("amount_usdt", 0) for t in self.trades if t.get("side") == "buy"]
        confidences = [t.get("confidence", 0) for t in self.trades]

        avg_position_size = sum(position_sizes) / len(position_sizes) if position_sizes else 0.0
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # Calculate exit plan tightness (average stop loss and profit target distances)
        exit_plan_distances = []
        for trade in self.trades:
            if "exit_plan" in trade and trade.get("side") == "buy":
                exit_plan = trade["exit_plan"]
                entry_price = trade.get("price", 0)
                if entry_price > 0:
                    profit_target = exit_plan.get("profit_target", 0)
                    stop_loss = exit_plan.get("stop_loss", 0)

                    if profit_target > 0:
                        profit_pct = abs(profit_target - entry_price) / entry_price * 100
                        exit_plan_distances.append(profit_pct)
                    if stop_loss > 0:
                        stop_pct = abs(stop_loss - entry_price) / entry_price * 100
                        exit_plan_distances.append(stop_pct)

        exit_plan_tightness = sum(exit_plan_distances) / len(exit_plan_distances) if exit_plan_distances else 0.0

        # Calculate total trading fees and impact
        total_fees = sum(t.get("trading_fee", 0) for t in self.trades)
        total_pnl = sum(t.get("profit", 0) for t in self.trades if t.get("side") == "sell")
        fee_impact = (total_fees / abs(total_pnl) * 100) if total_pnl != 0 else 0.0

        return {
            "bullish_tilt": bullish_tilt,
            "avg_holding_period_hours": avg_holding_period,
            "trade_frequency_per_day": trade_frequency,
            "avg_position_size_usdt": avg_position_size,
            "avg_confidence": avg_confidence,
            "exit_plan_tightness": exit_plan_tightness,
            "active_positions_count": len(self.positions),
            "total_trading_fees": total_fees,
            "fee_impact_pct": fee_impact,
        }

    def _close_position(
        self, symbol: str, price: float, quantity: float = None, reason: str = "manual"
    ) -> Optional[Dict]:
        """
        Close a position (handles both long and short positions) with retry logic.

        Args:
            symbol: Trading pair symbol
            price: Execution price
            quantity: Quantity to close (None to close entire position)
            reason: Reason for closing (for logging)

        Returns:
            Trade dictionary if successful, None otherwise
        """
        if symbol not in self.positions:
            logger.error(f"POSITION_CLOSE_FAILED symbol={symbol} reason=position_not_found")
            return None

        position = self.positions[symbol]
        side = position.get("side", "long")

        # Retry logic for position close
        max_retries = 3
        base_delay = 0.5

        for attempt in range(max_retries):
            try:
                # For long positions, use execute_sell
                if side == "long":
                    trade = self.execute_sell(symbol, price, quantity=quantity, confidence=1.0)
                else:
                    # For short positions, use execute_sell (it handles both sides)
                    trade = self.execute_sell(symbol, price, quantity=quantity, confidence=1.0)

                if trade:
                    return trade
                else:
                    # execute_sell returned None - might be a validation issue
                    if attempt < max_retries - 1:
                        delay = base_delay * (2**attempt)  # Exponential backoff
                        logger.warning(
                            f"Position close attempt {attempt + 1} failed for {symbol}, retrying in {delay:.2f}s"
                        )
                        time.sleep(delay)
                    else:
                        logger.error(f"Failed to close position {symbol} after {max_retries} attempts")
                        return None

            except Exception as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2**attempt)  # Exponential backoff
                    logger.warning(
                        f"Position close attempt {attempt + 1} failed for {symbol}: {e}, retrying in {delay:.2f}s"
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"Failed to close position {symbol} after {max_retries} attempts: {e}", exc_info=True)
                    return None

        return None

    def monitor_positions(self, current_price: float) -> Dict[str, Any]:
        """
        Monitor all open positions and check for stop-loss, take-profit, and other exit conditions.

        This method is called each trading cycle to automatically close positions when:
        - Stop-loss is hit
        - Take-profit is hit
        - Trailing stop-loss is triggered
        - Partial profit targets are reached

        Args:
            current_price: Current market price

        Returns:
            Dictionary with monitoring results:
            - positions_checked: Number of positions checked
            - positions_closed: Number of positions closed
            - stop_loss_triggers: Number of stop-loss triggers
            - take_profit_triggers: Number of take-profit triggers
            - trailing_stop_triggers: Number of trailing stop triggers
            - partial_profit_triggers: Number of partial profit triggers
        """
        if not config.ENABLE_POSITION_MONITORING:
            return {
                "positions_checked": 0,
                "positions_closed": 0,
                "stop_loss_triggers": 0,
                "take_profit_triggers": 0,
                "trailing_stop_triggers": 0,
                "partial_profit_triggers": 0,
            }

        results = {
            "positions_checked": len(self.positions),
            "positions_closed": 0,
            "stop_loss_triggers": 0,
            "take_profit_triggers": 0,
            "trailing_stop_triggers": 0,
            "partial_profit_triggers": 0,
        }

        if not self.positions:
            return results

        # Check portfolio-level profit target first
        portfolio_value = self.get_portfolio_value(current_price)
        initial_balance = config.INITIAL_BALANCE
        portfolio_profit_pct = ((portfolio_value - initial_balance) / initial_balance) * 100

        if portfolio_profit_pct >= config.PORTFOLIO_PROFIT_TARGET_PCT:
            logger.info(
                f"PORTFOLIO_PROFIT_TARGET_HIT portfolio_profit_pct={portfolio_profit_pct:.2f}% "
                f"target={config.PORTFOLIO_PROFIT_TARGET_PCT:.2f}% closing_all_positions"
            )
            # Close all positions
            symbols_to_close = list(self.positions.keys())
            for symbol in symbols_to_close:
                trade = self._close_position(symbol, current_price, quantity=None, reason="portfolio_profit_target")
                if trade:
                    results["positions_closed"] += 1
                    results["take_profit_triggers"] += 1
            return results

        # Check each position individually
        positions_to_update = {}
        for symbol, position in list(self.positions.items()):
            entry_price = position.get("avg_price", 0)
            if entry_price <= 0:
                continue

            side = position.get("side", "long")
            quantity = position.get("quantity", 0)
            if quantity <= 0:
                continue

            # Calculate current PnL
            if side == "long":
                pnl_pct = ((current_price - entry_price) / entry_price) * 100
            else:  # short
                pnl_pct = ((entry_price - current_price) / entry_price) * 100

            # Get stop-loss and take-profit from position or use defaults
            stop_loss_price = position.get("stop_loss", 0)
            take_profit_price = position.get("take_profit", 0)

            # If not set in position, calculate from config defaults
            if stop_loss_price <= 0:
                if side == "long":
                    stop_loss_price = entry_price * (1 - config.STOP_LOSS_PERCENT / 100)
                else:  # short
                    stop_loss_price = entry_price * (1 + config.STOP_LOSS_PERCENT / 100)

            if take_profit_price <= 0:
                if side == "long":
                    take_profit_price = entry_price * (1 + config.TAKE_PROFIT_PERCENT / 100)
                else:  # short
                    take_profit_price = entry_price * (1 - config.TAKE_PROFIT_PERCENT / 100)

            # Update trailing stop-loss if enabled and profit threshold met
            if config.ENABLE_TRAILING_STOP_LOSS and pnl_pct >= config.TRAILING_STOP_ACTIVATION_PCT:
                highest_price = position.get("highest_price", entry_price)
                lowest_price = position.get("lowest_price", entry_price)

                # Update highest/lowest price seen
                if side == "long":
                    if current_price > highest_price:
                        highest_price = current_price
                        position["highest_price"] = highest_price
                    # Trailing stop: highest_price * (1 - trailing_distance)
                    trailing_stop_price = highest_price * (1 - config.TRAILING_STOP_DISTANCE_PCT / 100)
                    if trailing_stop_price > stop_loss_price:
                        stop_loss_price = trailing_stop_price
                        position["stop_loss"] = stop_loss_price
                        logger.debug(
                            f"TRAILING_STOP_UPDATED symbol={symbol} side={side} "
                            f"highest_price={highest_price:.2f} trailing_stop={trailing_stop_price:.2f} "
                            f"pnl_pct={pnl_pct:.2f}%"
                        )
                else:  # short
                    if current_price < lowest_price:
                        lowest_price = current_price
                        position["lowest_price"] = lowest_price
                    # Trailing stop for short: lowest_price * (1 + trailing_distance)
                    # For shorts, stop-loss is above entry, so trailing stop should be above lowest_price
                    trailing_stop_price = lowest_price * (1 + config.TRAILING_STOP_DISTANCE_PCT / 100)
                    # For shorts, stop_loss_price should be >= trailing_stop_price (stop-loss is above entry for shorts)
                    # But we want trailing stop to be tighter (lower) than initial stop-loss
                    initial_stop_loss = entry_price * (1 + config.STOP_LOSS_PERCENT / 100)
                    if trailing_stop_price < initial_stop_loss:
                        stop_loss_price = trailing_stop_price
                        position["stop_loss"] = stop_loss_price
                        logger.debug(
                            f"TRAILING_STOP_UPDATED symbol={symbol} side={side} "
                            f"lowest_price={lowest_price:.2f} trailing_stop={trailing_stop_price:.2f} "
                            f"pnl_pct={pnl_pct:.2f}%"
                        )
            elif config.ENABLE_TRAILING_STOP_LOSS and pnl_pct < config.TRAILING_STOP_ACTIVATION_PCT:
                # Still update highest/lowest price tracking even if trailing stop not active yet
                if side == "long":
                    if current_price > position.get("highest_price", entry_price):
                        position["highest_price"] = current_price
                else:  # short
                    if current_price < position.get("lowest_price", entry_price):
                        position["lowest_price"] = current_price

            # Check stop-loss trigger
            stop_loss_triggered = False
            if side == "long":
                stop_loss_triggered = current_price <= stop_loss_price
            else:  # short
                stop_loss_triggered = current_price >= stop_loss_price

            # Check take-profit trigger
            take_profit_triggered = False
            if side == "long":
                take_profit_triggered = current_price >= take_profit_price
            else:  # short
                take_profit_triggered = current_price <= take_profit_price

            # Check partial profit-taking
            partial_profit_triggered = False
            if config.ENABLE_PARTIAL_PROFIT_TAKING and not position.get("partial_profit_taken", False):
                partial_profit_target_pct = config.PARTIAL_PROFIT_TARGET_PCT
                if side == "long":
                    partial_profit_price = entry_price * (1 + partial_profit_target_pct / 100)
                    partial_profit_triggered = current_price >= partial_profit_price
                else:  # short
                    partial_profit_price = entry_price * (1 - partial_profit_target_pct / 100)
                    partial_profit_triggered = current_price <= partial_profit_price

            # Execute exits based on priority: stop-loss > take-profit > partial profit
            if stop_loss_triggered:
                # Handle price gaps: use stop-loss price if price gapped through it
                if side == "long":
                    # For longs, use the lower of current price or stop-loss price
                    execution_price = min(current_price, stop_loss_price)
                else:  # short
                    # For shorts, use the higher of current price or stop-loss price
                    execution_price = max(current_price, stop_loss_price)

                logger.warning(
                    f"STOP_LOSS_TRIGGERED symbol={symbol} side={side} "
                    f"entry_price={entry_price:.2f} current_price={current_price:.2f} "
                    f"stop_loss_price={stop_loss_price:.2f} execution_price={execution_price:.2f} "
                    f"pnl_pct={pnl_pct:.2f}%"
                )
                trade = self._close_position(symbol, execution_price, quantity=None, reason="stop_loss")
                if trade:
                    results["positions_closed"] += 1
                    results["stop_loss_triggers"] += 1
                    # Log event if available
                    if self.event_logger:
                        try:
                            self.event_logger.log_event(
                                event_type="stop_loss_trigger",
                                data={
                                    "symbol": symbol,
                                    "side": side,
                                    "entry_price": entry_price,
                                    "exit_price": current_price,
                                    "pnl_pct": pnl_pct,
                                    "trade_id": trade.get("id"),
                                },
                            )
                        except Exception as e:
                            logger.debug(f"Error logging stop-loss event: {e}")
            elif take_profit_triggered:
                # Calculate profit locked
                if side == "long":
                    profit_locked = (current_price - entry_price) * quantity
                else:  # short
                    profit_locked = (entry_price - current_price) * quantity
                
                logger.info(
                    f"TAKE_PROFIT_TRIGGERED symbol={symbol} side={side} "
                    f"entry_price={entry_price:.2f} current_price={current_price:.2f} "
                    f"take_profit_price={take_profit_price:.2f} pnl_pct={pnl_pct:.2f}% "
                    f"profit_locked=${profit_locked:.2f}"
                )
                trade = self._close_position(symbol, current_price, quantity=None, reason="take_profit")
                if trade:
                    results["positions_closed"] += 1
                    results["take_profit_triggers"] += 1
                    # Log event if available
                    if self.event_logger:
                        try:
                            self.event_logger.log_event(
                                event_type="take_profit_trigger",
                                data={
                                    "symbol": symbol,
                                    "side": side,
                                    "entry_price": entry_price,
                                    "exit_price": current_price,
                                    "pnl_pct": pnl_pct,
                                    "trade_id": trade.get("id"),
                                },
                            )
                        except Exception as e:
                            logger.debug(f"Error logging take-profit event: {e}")
            elif partial_profit_triggered:
                # Close partial position (e.g., 50%)
                partial_quantity = quantity * (config.PARTIAL_PROFIT_PERCENT / 100)
                logger.info(
                    f"PARTIAL_PROFIT_TRIGGERED symbol={symbol} side={side} "
                    f"entry_price={entry_price:.2f} current_price={current_price:.2f} "
                    f"pnl_pct={pnl_pct:.2f}% closing_{config.PARTIAL_PROFIT_PERCENT:.0f}%"
                )
                trade = self._close_position(symbol, current_price, quantity=partial_quantity, reason="partial_profit")
                if trade:
                    results["partial_profit_triggers"] += 1
                    # Mark that partial profit has been taken
                    if symbol in self.positions:
                        self.positions[symbol]["partial_profit_taken"] = True
                    logger.info(
                        f"PARTIAL_PROFIT_EXECUTED symbol={symbol} quantity_closed={partial_quantity:.6f} "
                        f"remaining={self.positions.get(symbol, {}).get('quantity', 0):.6f}"
                    )
            else:
                # Update position tracking for trailing stop
                if config.ENABLE_TRAILING_STOP_LOSS:
                    if side == "long":
                        if current_price > position.get("highest_price", entry_price):
                            position["highest_price"] = current_price
                    else:  # short
                        if current_price < position.get("lowest_price", entry_price):
                            position["lowest_price"] = current_price
                    positions_to_update[symbol] = position

        # Update positions with trailing stop data
        for symbol, position in positions_to_update.items():
            if symbol in self.positions:
                self.positions[symbol].update(position)

        # Save portfolio state if any positions were closed
        if results["positions_closed"] > 0:
            self._save_portfolio_state(current_price)
            logger.debug(f"Portfolio state saved after closing {results['positions_closed']} positions")

        return results
