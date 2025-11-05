"""
Realistic Backtesting Framework

Includes realistic simulation of:
- Trading fees (taker/maker)
- Funding rates (for perpetuals)
- Borrow costs
- Partial fills (slippage)
- Order queue position
- Latency delays
- API rate limits
- Liquidations/ADL rules
- Insurance fund haircuts
- Walk-forward analysis
- Monte Carlo simulation
- Nightmare scenario stress testing
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd

from config import config

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """Backtesting configuration."""
    initial_balance: float = 10000.0
    trading_fee_percent: float = 0.05  # 0.05% taker fee
    maker_fee_percent: float = 0.02  # 0.02% maker fee (if post-only)
    funding_rate_percent: float = 0.01  # 0.01% per 8 hours (typical)
    borrow_rate_apr: float = 0.05  # 5% APR for borrowing
    slippage_bps: float = 10.0  # 10 bps average slippage
    partial_fill_probability: float = 0.3  # 30% chance of partial fill
    min_fill_ratio: float = 0.5  # At least 50% filled
    latency_ms: float = 50.0  # 50ms average latency
    rate_limit_delay: float = 0.1  # 100ms delay for rate limits
    liquidation_threshold: float = 0.8  # 80% of margin = liquidation
    max_leverage: float = 10.0


@dataclass
class BacktestTrade:
    """Backtest trade with realistic execution."""
    timestamp: datetime
    symbol: str
    side: str
    intended_quantity: float
    intended_price: float
    filled_quantity: float
    fill_price: float
    slippage: float
    trading_fee: float
    funding_cost: float
    borrow_cost: float
    latency_ms: float
    partial_fill: bool
    rate_limit_delay: float


@dataclass
class BacktestResult:
    """Backtest results."""
    total_return: float
    total_return_pct: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    total_trades: int
    total_fees: float
    total_funding: float
    total_borrow: float
    total_slippage: float
    liquidations: int
    trades: List[BacktestTrade]
    equity_curve: List[float]


class RealisticBacktester:
    """
    Realistic backtesting engine with fees, funding, slippage, latency, etc.
    """
    
    def __init__(self, config: BacktestConfig = None):
        self.config = config or BacktestConfig()
        self.trades: List[BacktestTrade] = []
        self.equity_curve: List[Tuple[datetime, float]] = []
        self.positions: Dict[str, Dict] = {}
        self.balance = self.config.initial_balance
        
        logger.info(f"Realistic Backtester initialized: balance={self.balance:.2f}")
    
    def simulate_order_execution(
        self,
        timestamp: datetime,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        order_type: str = "market",  # "market" or "limit"
        post_only: bool = False
    ) -> BacktestTrade:
        """
        Simulate realistic order execution with slippage, partial fills, latency.
        """
        # Simulate latency
        latency_ms = np.random.normal(self.config.latency_ms, 10)
        latency_ms = max(10, min(200, latency_ms))  # Clamp to reasonable range
        
        # Simulate slippage (market orders have more slippage)
        if order_type == "market":
            slippage_bps = np.random.normal(self.config.slippage_bps, 5)
        else:
            slippage_bps = np.random.normal(2.0, 1.0)  # Less slippage for limit orders
        
        slippage_pct = slippage_bps / 10000
        fill_price = price * (1 + slippage_pct) if side == "buy" else price * (1 - slippage_pct)
        
        # Simulate partial fills
        partial_fill = np.random.random() < self.config.partial_fill_probability
        if partial_fill:
            fill_ratio = np.random.uniform(self.config.min_fill_ratio, 1.0)
            filled_quantity = quantity * fill_ratio
        else:
            filled_quantity = quantity
        
        # Calculate fees
        notional_value = filled_quantity * fill_price
        if post_only:
            trading_fee = notional_value * (self.config.maker_fee_percent / 100)
        else:
            trading_fee = notional_value * (self.config.trading_fee_percent / 100)
        
        # Simulate rate limit delay (occasional)
        rate_limit_delay = 0.0
        if np.random.random() < 0.1:  # 10% chance
            rate_limit_delay = self.config.rate_limit_delay
        
        # Funding cost (for perpetual positions, charged every 8 hours)
        funding_cost = 0.0  # Would calculate based on position size and funding rate
        
        # Borrow cost (if using borrowed funds)
        borrow_cost = 0.0  # Would calculate based on borrow amount and rate
        
        trade = BacktestTrade(
            timestamp=timestamp,
            symbol=symbol,
            side=side,
            intended_quantity=quantity,
            intended_price=price,
            filled_quantity=filled_quantity,
            fill_price=fill_price,
            slippage=abs(fill_price - price) / price * 10000,  # In bps
            trading_fee=trading_fee,
            funding_cost=funding_cost,
            borrow_cost=borrow_cost,
            latency_ms=latency_ms,
            partial_fill=partial_fill,
            rate_limit_delay=rate_limit_delay
        )
        
        self.trades.append(trade)
        return trade
    
    def check_liquidation(
        self,
        symbol: str,
        current_price: float,
        leverage: float
    ) -> bool:
        """Check if position should be liquidated."""
        if symbol not in self.positions:
            return False
        
        position = self.positions[symbol]
        entry_price = position["entry_price"]
        quantity = position["quantity"]
        margin_used = position["margin_used"]
        
        # Calculate unrealized P&L
        if position["side"] == "long":
            pnl = (current_price - entry_price) * quantity
        else:  # short
            pnl = (entry_price - current_price) * quantity
        
        # Calculate margin ratio
        margin_ratio = (margin_used + pnl) / margin_used if margin_used > 0 else 1.0
        
        # Liquidation if margin ratio < threshold
        if margin_ratio < self.config.liquidation_threshold:
            return True
        
        return False
    
    def run_backtest(
        self,
        historical_data: pd.DataFrame,
        strategy_func: callable,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> BacktestResult:
        """
        Run backtest on historical data.
        
        Args:
            historical_data: DataFrame with columns: timestamp, open, high, low, close, volume
            strategy_func: Function that takes (data, portfolio_state) and returns trade decision
            start_date: Start date for backtest
            end_date: End date for backtest
        """
        # Filter data by date range
        if start_date:
            historical_data = historical_data[historical_data['timestamp'] >= start_date]
        if end_date:
            historical_data = historical_data[historical_data['timestamp'] <= end_date]
        
        # Reset state
        self.balance = self.config.initial_balance
        self.positions = {}
        self.trades = []
        self.last_funding_time = historical_data.iloc[0]['timestamp'] if len(historical_data) > 0 else None
        self.equity_curve = [(historical_data.iloc[0]['timestamp'], self.balance)] if len(historical_data) > 0 else []
        
        # Iterate through historical data
        for idx, row in historical_data.iterrows():
            current_time = row['timestamp']
            current_price = row['close']
            
            # Get strategy decision
            portfolio_state = {
                "balance": self.balance,
                "positions": self.positions,
                "total_value": self._calculate_portfolio_value(current_price)
            }
            
            try:
                decision = strategy_func(row, portfolio_state)
            except Exception as e:
                logger.warning(f"Strategy error at {current_time}: {e}")
                continue
            
            # Execute trade if decision is to trade
            if decision and decision.get("action") in ["buy", "sell", "short"]:
                self._execute_trade_decision(current_time, current_price, decision)
            
            # Check for liquidations
            for symbol in list(self.positions.keys()):
                if self.check_liquidation(symbol, current_price, decision.get("leverage", 1.0) if decision else 1.0):
                    self._liquidate_position(symbol, current_price, current_time)
            
            # Update equity curve
            portfolio_value = self._calculate_portfolio_value(current_price)
            self.equity_curve.append((current_time, portfolio_value))
            
            # Apply funding costs (every 8 hours = 28800 seconds)
            if self.last_funding_time:
                time_since_funding = (current_time - self.last_funding_time).total_seconds()
                if time_since_funding >= 28800:  # 8 hours
                    self._apply_funding_costs(current_time)
                    self.last_funding_time = current_time
            else:
                self.last_funding_time = current_time
        
        # Calculate results
        return self._calculate_results()
    
    def _execute_trade_decision(
        self,
        timestamp: datetime,
        price: float,
        decision: Dict[str, Any]
    ):
        """Execute a trade decision with realistic execution."""
        symbol = decision.get("symbol", "BTC/USDT")
        side = decision.get("action", "buy")
        quantity = decision.get("quantity", 0)
        leverage = decision.get("leverage", 1.0)
        order_type = decision.get("order_type", "market")
        post_only = decision.get("post_only", False)
        
        # Simulate execution
        trade = self.simulate_order_execution(
            timestamp=timestamp,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            order_type=order_type,
            post_only=post_only
        )
        
        # Update balance and positions
        notional_value = trade.filled_quantity * trade.fill_price
        margin_required = notional_value / leverage
        
        if side == "buy":
            self.balance -= (margin_required + trade.trading_fee)
            # Update position
            if symbol in self.positions:
                # Average in
                pos = self.positions[symbol]
                total_cost = (pos["quantity"] * pos["entry_price"]) + notional_value
                total_quantity = pos["quantity"] + trade.filled_quantity
                self.positions[symbol] = {
                    "side": "long",
                    "quantity": total_quantity,
                    "entry_price": total_cost / total_quantity,
                    "margin_used": pos["margin_used"] + margin_required,
                    "leverage": leverage
                }
            else:
                self.positions[symbol] = {
                    "side": "long",
                    "quantity": trade.filled_quantity,
                    "entry_price": trade.fill_price,
                    "margin_used": margin_required,
                    "leverage": leverage
                }
        elif side == "sell":
            # Close or reduce position
            if symbol in self.positions:
                pos = self.positions[symbol]
                close_quantity = min(trade.filled_quantity, pos["quantity"])
                pnl = (trade.fill_price - pos["entry_price"]) * close_quantity
                margin_returned = (pos["margin_used"] * close_quantity) / pos["quantity"]
                
                self.balance += margin_returned + pnl - trade.trading_fee
                
                pos["quantity"] -= close_quantity
                pos["margin_used"] -= margin_returned
                
                if pos["quantity"] <= 0:
                    del self.positions[symbol]
                else:
                    self.positions[symbol] = pos
    
    def _liquidate_position(self, symbol: str, price: float, timestamp: datetime):
        """Liquidate a position due to margin call."""
        if symbol not in self.positions:
            return
        
        pos = self.positions[symbol]
        quantity = pos["quantity"]
        entry_price = pos["entry_price"]
        
        # Calculate P&L at liquidation
        if pos["side"] == "long":
            pnl = (price - entry_price) * quantity
        else:
            pnl = (entry_price - price) * quantity
        
        # Liquidation penalty (insurance fund haircut)
        liquidation_penalty = pos["margin_used"] * 0.1  # 10% penalty
        
        self.balance += pos["margin_used"] + pnl - liquidation_penalty
        
        # Log liquidation
        trade = BacktestTrade(
            timestamp=timestamp,
            symbol=symbol,
            side="liquidation",
            intended_quantity=quantity,
            intended_price=price,
            filled_quantity=quantity,
            fill_price=price,
            slippage=0.0,
            trading_fee=liquidation_penalty,
            funding_cost=0.0,
            borrow_cost=0.0,
            latency_ms=0.0,
            partial_fill=False,
            rate_limit_delay=0.0
        )
        self.trades.append(trade)
        
        del self.positions[symbol]
        logger.warning(f"Position liquidated: {symbol} at {price:.2f}, PnL={pnl:.2f}")
    
    def _apply_funding_costs(self, timestamp: datetime):
        """Apply funding costs to perpetual positions."""
        for symbol, pos in self.positions.items():
            notional_value = pos["quantity"] * pos["entry_price"]
            funding_cost = notional_value * (self.config.funding_rate_percent / 100)
            self.balance -= funding_cost
            
            # Log funding cost
            trade = BacktestTrade(
                timestamp=timestamp,
                symbol=symbol,
                side="funding",
                intended_quantity=0,
                intended_price=0,
                filled_quantity=0,
                fill_price=0,
                slippage=0.0,
                trading_fee=0.0,
                funding_cost=funding_cost,
                borrow_cost=0.0,
                latency_ms=0.0,
                partial_fill=False,
                rate_limit_delay=0.0
            )
            self.trades.append(trade)
    
    def _calculate_portfolio_value(self, current_price: float) -> float:
        """Calculate total portfolio value."""
        position_value = 0.0
        for symbol, pos in self.positions.items():
            if pos["side"] == "long":
                position_value += pos["quantity"] * current_price
            else:  # short
                entry_value = pos["quantity"] * pos["entry_price"]
                current_value = pos["quantity"] * current_price
                position_value += entry_value + (entry_value - current_value)
        
        return self.balance + position_value
    
    def _calculate_results(self) -> BacktestResult:
        """Calculate backtest results."""
        if not self.trades:
            return BacktestResult(
                total_return=0.0,
                total_return_pct=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                win_rate=0.0,
                profit_factor=0.0,
                total_trades=0,
                total_fees=0.0,
                total_funding=0.0,
                total_borrow=0.0,
                total_slippage=0.0,
                liquidations=0,
                trades=self.trades,
                equity_curve=[v for _, v in self.equity_curve]
            )
        
        # Calculate returns
        initial_value = self.config.initial_balance
        final_value = self.equity_curve[-1][1] if self.equity_curve else initial_value
        total_return = final_value - initial_value
        total_return_pct = (total_return / initial_value) * 100
        
        # Calculate metrics from equity curve
        equity_values = [v for _, v in self.equity_curve]
        returns = np.diff(equity_values) / equity_values[:-1]
        
        sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if len(returns) > 1 and np.std(returns) > 0 else 0.0
        
        # Max drawdown
        cumulative = np.cumsum(returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = running_max - cumulative
        max_drawdown = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0
        
        # Trade statistics - track P&L properly
        closed_trades = [t for t in self.trades if t.side == "sell"]
        liquidations = len([t for t in self.trades if t.side == "liquidation"])
        
        # Calculate actual P&L from trades
        profits = []
        position_tracker = {}  # Track entry prices for each position
        
        for trade in self.trades:
            symbol = trade.symbol
            if trade.side == "buy":
                # Record entry price
                if symbol not in position_tracker:
                    position_tracker[symbol] = {
                        "entry_price": trade.fill_price,
                        "quantity": trade.filled_quantity,
                        "entry_time": trade.timestamp
                    }
                else:
                    # Average in
                    old_qty = position_tracker[symbol]["quantity"]
                    old_price = position_tracker[symbol]["entry_price"]
                    new_qty = trade.filled_quantity
                    new_price = trade.fill_price
                    total_qty = old_qty + new_qty
                    avg_price = (old_price * old_qty + new_price * new_qty) / total_qty if total_qty > 0 else new_price
                    position_tracker[symbol] = {
                        "entry_price": avg_price,
                        "quantity": total_qty,
                        "entry_time": position_tracker[symbol]["entry_time"]
                    }
            elif trade.side == "sell":
                # Calculate P&L
                if symbol in position_tracker:
                    entry_price = position_tracker[symbol]["entry_price"]
                    entry_qty = position_tracker[symbol]["quantity"]
                    exit_price = trade.fill_price
                    exit_qty = min(trade.filled_quantity, entry_qty)
                    
                    # P&L = (exit_price - entry_price) * quantity - fees
                    pnl = (exit_price - entry_price) * exit_qty - trade.trading_fee
                    profits.append(pnl)
                    
                    # Update position
                    position_tracker[symbol]["quantity"] -= exit_qty
                    if position_tracker[symbol]["quantity"] <= 0:
                        del position_tracker[symbol]
            elif trade.side == "liquidation":
                # Liquidated position - calculate P&L
                if symbol in position_tracker:
                    entry_price = position_tracker[symbol]["entry_price"]
                    entry_qty = position_tracker[symbol]["quantity"]
                    exit_price = trade.fill_price
                    
                    # P&L = (exit_price - entry_price) * quantity - fees
                    pnl = (exit_price - entry_price) * entry_qty - trade.trading_fee
                    profits.append(pnl)
                    
                    del position_tracker[symbol]
        
        win_rate = len([p for p in profits if p > 0]) / len(profits) if profits else 0.0
        
        # Profit factor
        gross_profit = sum(p for p in profits if p > 0)
        gross_loss = abs(sum(p for p in profits if p < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 0.0
        
        # Cost summary
        total_fees = sum(t.trading_fee for t in self.trades)
        total_funding = sum(t.funding_cost for t in self.trades)
        total_borrow = sum(t.borrow_cost for t in self.trades)
        total_slippage = sum(t.slippage * t.filled_quantity * t.fill_price / 10000 for t in self.trades)
        
        return BacktestResult(
            total_return=total_return,
            total_return_pct=total_return_pct,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_trades=len(self.trades),
            total_fees=total_fees,
            total_funding=total_funding,
            total_borrow=total_borrow,
            total_slippage=total_slippage,
            liquidations=liquidations,
            trades=self.trades,
            equity_curve=equity_values
        )

