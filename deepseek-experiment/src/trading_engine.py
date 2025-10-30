"""
Trading engine for paper trading simulation.

Records paper trades, tracks portfolio balance, and can be upgraded to live trading
by modifying the execution methods (see config.TRADING_MODE).
"""

import asyncio
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from config import config
from .database_manager import get_database_manager
from .security import SecurityManager, validate_trading_inputs
from .resilience import circuit_breaker, retry, CircuitBreakerConfig, RetryConfig
from .logger import get_logger

logger = get_logger(__name__)


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
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Supabase client: {e}")
        
        # Load existing trades if file exists
        self._load_trades()
        
        logger.info(f"Trading engine initialized with balance: {self.balance}")
    
    def _load_trades(self):
        """Load trade history from file."""
        if self.trades_file.exists():
            try:
                with open(self.trades_file, 'r') as f:
                    self.trades = json.load(f)
                logger.info(f"Loaded {len(self.trades)} historical trades")
            except Exception as e:
                logger.error(f"Error loading trades: {e}")
                self.trades = []
    
    def _save_trades(self):
        """Save trade history to file."""
        try:
            with open(self.trades_file, 'w') as f:
                json.dump(self.trades, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving trades: {e}")
    
    def _save_portfolio_state(self):
        """Save current portfolio state to file."""
        portfolio_file = config.DATA_DIR / "portfolio.json"
        state = {
            "balance": self.balance,
            "positions": self.positions,
            "timestamp": datetime.now().isoformat()
        }
        try:
            with open(portfolio_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving portfolio state: {e}")
        
        # Save to Supabase if available
        if self.supabase_client:
            try:
                asyncio.create_task(self.supabase_client.update_portfolio(state))
            except Exception as e:
                logger.warning(f"Failed to save portfolio to Supabase: {e}")
    
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
            if position['side'] == 'long':
                # Long position: profit/loss from price appreciation
                position_value += position['quantity'] * current_price
            elif position['side'] == 'short':
                # Short position: profit/loss from price decline
                # Short profit = (entry_price - current_price) * quantity
                entry_value = position['quantity'] * position['avg_price']
                current_value = position['quantity'] * current_price
                short_pnl = entry_value - current_value  # Profit when price goes down
                position_value += entry_value + short_pnl  # Original value + PnL
            else:
                # Fallback for other position types
                position_value += position.get('value', 0)
        
        return self.balance + position_value
    
    @validate_trading_inputs
    @circuit_breaker(CircuitBreakerConfig(failure_threshold=5, recovery_timeout=30))
    @retry(RetryConfig(max_attempts=3, base_delay=0.5, max_delay=5.0))
    def execute_buy(self, symbol: str, price: float, amount_usdt: float, confidence: float, llm_decision: Dict = None, leverage: float = 1.0) -> Optional[Dict]:
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
        # Validate leverage
        leverage = max(1.0, min(leverage, config.MAX_LEVERAGE))  # Clamp between 1.0 and MAX_LEVERAGE
        
        # Calculate required margin (amount_usdt / leverage)
        required_margin = amount_usdt / leverage
        
        # Check if we have enough balance for margin
        if required_margin > self.balance:
            logger.warning(f"Insufficient balance for margin. Available: {self.balance}, Required margin: {required_margin}")
            return None
        
        # Check position limits (Alpha Arena constraint)
        if len(self.positions) >= config.MAX_ACTIVE_POSITIONS:
            logger.warning(f"Maximum active positions reached ({config.MAX_ACTIVE_POSITIONS}). Cannot open new position.")
            return None
        
        # Apply position size limit based on margin
        max_margin = self.balance * config.MAX_POSITION_SIZE
        required_margin = min(required_margin, max_margin)
        amount_usdt = required_margin * leverage
        
        quantity = amount_usdt / price
        
        # Calculate trading fees
        trading_fee = amount_usdt * (config.TRADING_FEE_PERCENT / 100)
        
        # Record trade with enhanced LLM context
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
            "llm_justification": llm_decision.get("justification", "") if llm_decision else "",
            "llm_risk_assessment": llm_decision.get("risk_assessment", "medium") if llm_decision else "medium",
            "llm_position_size_usdt": llm_decision.get("position_size_usdt", 0.0) if llm_decision else 0.0,
            "exit_plan": llm_decision.get("exit_plan", {}) if llm_decision else {}
        }
        
        # Update balance and positions (deduct margin + fees)
        self.balance -= (required_margin + trading_fee)
        if symbol in self.positions:
            # Average in if position exists
            pos = self.positions[symbol]
            total_cost = (pos['quantity'] * pos['avg_price']) + amount_usdt
            total_quantity = pos['quantity'] + quantity
            total_margin = pos.get('margin_used', 0) + required_margin
            self.positions[symbol] = {
                'side': 'long',
                'quantity': total_quantity,
                'avg_price': total_cost / total_quantity,
                'value': amount_usdt,
                'leverage': leverage,
                'margin_used': total_margin,
                'notional_value': total_quantity * price
            }
        else:
            self.positions[symbol] = {
                'side': 'long',
                'quantity': quantity,
                'avg_price': price,
                'value': amount_usdt,
                'leverage': leverage,
                'margin_used': required_margin,
                'notional_value': quantity * price
            }
        
        self.trades.append(trade)
        self._save_trades()
        self._save_portfolio_state()
        
        # Save to Supabase if available
        if self.supabase_client:
            try:
                asyncio.create_task(self.supabase_client.add_trade(trade))
            except Exception as e:
                logger.warning(f"Failed to save trade to Supabase: {e}")
        
        logger.info(f"BUY executed: {quantity:.6f} {symbol} @ ${price:.2f} (${amount_usdt:.2f})")
        return trade
    
    @validate_trading_inputs
    @circuit_breaker(CircuitBreakerConfig(failure_threshold=5, recovery_timeout=30))
    @retry(RetryConfig(max_attempts=3, base_delay=0.5, max_delay=5.0))
    def execute_sell(self, symbol: str, price: float, quantity: float = None, confidence: float = 0.0, llm_decision: Dict = None, leverage: float = 1.0) -> Optional[Dict]:
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
        # Check if we have a position
        if symbol not in self.positions or self.positions[symbol]['quantity'] <= 0:
            logger.warning(f"No position to sell for {symbol}")
            return None
        
        position = self.positions[symbol]
        sell_quantity = quantity if quantity else position['quantity']
        
        if sell_quantity > position['quantity']:
            sell_quantity = position['quantity']
        
        amount_usdt = sell_quantity * price
        profit = (price - position['avg_price']) * sell_quantity
        
        # Calculate trading fees
        trading_fee = amount_usdt * (config.TRADING_FEE_PERCENT / 100)
        
        # Calculate margin to return (proportional to quantity sold)
        margin_returned = (position.get('margin_used', 0) * sell_quantity) / position['quantity']
        
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
            "leverage": position.get('leverage', 1.0),
            "margin_returned": margin_returned,
            "trading_fee": trading_fee,
            "profit": profit,
            "profit_pct": (profit / (position['avg_price'] * sell_quantity)) * 100,
            "confidence": confidence,
            "mode": config.TRADING_MODE,
            "llm_justification": llm_decision.get("justification", "") if llm_decision else "",
            "llm_risk_assessment": llm_decision.get("risk_assessment", "medium") if llm_decision else "medium",
            "llm_position_size_usdt": llm_decision.get("position_size_usdt", 0.0) if llm_decision else 0.0,
            "exit_plan": llm_decision.get("exit_plan", {}) if llm_decision else {}
        }
        
        # Update balance and positions (add margin returned + profit - fees)
        self.balance += (margin_returned + profit - trading_fee)
        position['quantity'] -= sell_quantity
        position['value'] -= position['avg_price'] * sell_quantity
        position['margin_used'] -= margin_returned
        
        if position['quantity'] <= 0:
            del self.positions[symbol]
        else:
            self.positions[symbol] = position
        
        self.trades.append(trade)
        self._save_trades()
        self._save_portfolio_state()
        
        # Save to Supabase if available
        if self.supabase_client:
            try:
                asyncio.create_task(self.supabase_client.add_trade(trade))
            except Exception as e:
                logger.warning(f"Failed to save trade to Supabase: {e}")
        
        logger.info(f"SELL executed: {sell_quantity:.6f} {symbol} @ ${price:.2f} (profit: ${profit:.2f})")
        return trade
    
    @validate_trading_inputs
    @circuit_breaker(CircuitBreakerConfig(failure_threshold=5, recovery_timeout=30))
    @retry(RetryConfig(max_attempts=3, base_delay=0.5, max_delay=5.0))
    def execute_short(self, symbol: str, price: float, amount_usdt: float, confidence: float, llm_decision: Dict = None, leverage: float = 1.0) -> Optional[Dict]:
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
        # Validate leverage
        leverage = max(1.0, min(leverage, config.MAX_LEVERAGE))
        
        # Calculate required margin (amount_usdt / leverage)
        required_margin = amount_usdt / leverage
        
        # Check if we have enough balance for margin
        if required_margin > self.balance:
            logger.warning(f"Insufficient balance for short margin. Available: {self.balance}, Required margin: {required_margin}")
            return None
        
        # Check position limits (Alpha Arena constraint)
        if len(self.positions) >= config.MAX_ACTIVE_POSITIONS:
            logger.warning(f"Maximum active positions reached ({config.MAX_ACTIVE_POSITIONS}). Cannot open new position.")
            return None
        
        # Apply position size limit based on margin
        max_margin = self.balance * config.MAX_POSITION_SIZE
        required_margin = min(required_margin, max_margin)
        amount_usdt = required_margin * leverage
        
        quantity = amount_usdt / price
        
        # Calculate trading fees
        trading_fee = amount_usdt * (config.TRADING_FEE_PERCENT / 100)
        
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
            "llm_justification": llm_decision.get("justification", "") if llm_decision else "",
            "llm_risk_assessment": llm_decision.get("risk_assessment", "medium") if llm_decision else "medium",
            "llm_position_size_usdt": llm_decision.get("position_size_usdt", 0.0) if llm_decision else 0.0,
            "exit_plan": llm_decision.get("exit_plan", {}) if llm_decision else {}
        }
        
        # Update balance and positions (deduct margin + fees)
        self.balance -= (required_margin + trading_fee)
        if symbol in self.positions:
            # Average in if position exists
            pos = self.positions[symbol]
            total_cost = (pos['quantity'] * pos['avg_price']) + amount_usdt
            total_quantity = pos['quantity'] + quantity
            total_margin = pos.get('margin_used', 0) + required_margin
            self.positions[symbol] = {
                'side': 'short',
                'quantity': total_quantity,
                'avg_price': total_cost / total_quantity,
                'value': amount_usdt,
                'leverage': leverage,
                'margin_used': total_margin,
                'notional_value': total_quantity * price
            }
        else:
            self.positions[symbol] = {
                'side': 'short',
                'quantity': quantity,
                'avg_price': price,
                'value': amount_usdt,
                'leverage': leverage,
                'margin_used': required_margin,
                'notional_value': quantity * price
            }
        
        self.trades.append(trade)
        self._save_trades()
        self._save_portfolio_state()
        
        # Save to Supabase if available
        if self.supabase_client:
            try:
                asyncio.create_task(self.supabase_client.add_trade(trade))
            except Exception as e:
                logger.warning(f"Failed to save trade to Supabase: {e}")
        
        logger.info(f"SHORT executed: {quantity:.6f} {symbol} @ ${price:.2f} (${amount_usdt:.2f})")
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
            **advanced_metrics
        }
    
    def _calculate_advanced_metrics(self) -> Dict[str, Any]:
        """Calculate advanced trading metrics including Sharpe ratio and behavioral patterns for Alpha Arena analysis."""
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
                "fee_impact_pct": 0.0
            }
        
        # Basic trade analysis
        sell_trades = [t for t in self.trades if t.get("side") == "sell"]
        profits = [t.get("profit", 0) for t in sell_trades]
        
        if not profits:
            return {
                "win_rate": 0.0,
                "avg_profit_per_trade": 0.0,
                "max_drawdown": 0.0,
                "sharpe_ratio": 0.0,
                "volatility": 0.0,
                "profit_factor": 0.0,
                "avg_trade_duration_hours": 0.0,
                "max_consecutive_wins": 0,
                "max_consecutive_losses": 0
            }
        
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
            volatility = variance ** 0.5
            
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
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 0
        
        # Trade duration analysis
        trade_durations = []
        for trade in self.trades:
            if "timestamp" in trade:
                try:
                    trade_time = datetime.fromisoformat(trade["timestamp"].replace('Z', '+00:00'))
                    # Find corresponding buy trade for duration calculation
                    if trade.get("side") == "sell":
                        buy_trades = [t for t in self.trades 
                                    if t.get("side") == "buy" 
                                    and t.get("symbol") == trade.get("symbol")
                                    and t.get("timestamp") < trade.get("timestamp")]
                        if buy_trades:
                            buy_time = datetime.fromisoformat(buy_trades[-1]["timestamp"].replace('Z', '+00:00'))
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
            **behavioral_metrics
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
                "fee_impact_pct": 0.0
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
                    sell_time = datetime.fromisoformat(trade["timestamp"].replace('Z', '+00:00'))
                    # Find corresponding buy trade
                    buy_trades = [t for t in self.trades 
                                if t.get("side") == "buy" 
                                and t.get("symbol") == trade.get("symbol")
                                and t.get("timestamp") < trade.get("timestamp")]
                    if buy_trades:
                        buy_time = datetime.fromisoformat(buy_trades[-1]["timestamp"].replace('Z', '+00:00'))
                        duration = (sell_time - buy_time).total_seconds() / 3600  # hours
                        holding_periods.append(duration)
                except (ValueError, TypeError):
                    continue
        
        avg_holding_period = sum(holding_periods) / len(holding_periods) if holding_periods else 0.0
        
        # Calculate trade frequency per day
        if self.trades:
            first_trade = min(self.trades, key=lambda x: x.get("timestamp", ""))
            last_trade = max(self.trades, key=lambda x: x.get("timestamp", ""))
            try:
                start_time = datetime.fromisoformat(first_trade["timestamp"].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(last_trade["timestamp"].replace('Z', '+00:00'))
                days_elapsed = (end_time - start_time).total_seconds() / (24 * 3600)
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
            "fee_impact_pct": fee_impact
        }

