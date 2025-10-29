"""
Trading engine for paper trading simulation.

Records paper trades, tracks portfolio balance, and can be upgraded to live trading
by modifying the execution methods (see config.TRADING_MODE).
"""

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config import config

logger = logging.getLogger(__name__)


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
                position_value += position['quantity'] * current_price
            else:
                # For short positions, value is stored differently
                position_value += position['value']
        
        return self.balance + position_value
    
    def execute_buy(self, symbol: str, price: float, amount_usdt: float, confidence: float, llm_decision: Dict = None) -> Optional[Dict]:
        """
        Execute a buy order (paper trading).
        
        Args:
            symbol: Trading pair symbol
            price: Execution price
            amount_usdt: Amount in USDT to spend
            confidence: LLM confidence score
            llm_decision: Full LLM decision dict for additional context
            
        Returns:
            Trade dictionary if successful, None otherwise
        """
        # Check if we have enough balance
        if amount_usdt > self.balance:
            logger.warning(f"Insufficient balance. Available: {self.balance}, Required: {amount_usdt}")
            return None
        
        # Apply position size limit
        max_amount = self.balance * config.MAX_POSITION_SIZE
        amount_usdt = min(amount_usdt, max_amount)
        
        quantity = amount_usdt / price
        
        # Record trade with enhanced LLM context
        trade = {
            "id": len(self.trades) + 1,
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "side": "buy",
            "price": price,
            "quantity": quantity,
            "amount_usdt": amount_usdt,
            "confidence": confidence,
            "mode": config.TRADING_MODE,
            "llm_reasoning": llm_decision.get("reasoning", "") if llm_decision else "",
            "llm_risk_assessment": llm_decision.get("risk_assessment", "medium") if llm_decision else "medium",
            "llm_position_size": llm_decision.get("position_size", 0.1) if llm_decision else 0.1
        }
        
        # Update balance and positions
        self.balance -= amount_usdt
        if symbol in self.positions:
            # Average in if position exists
            pos = self.positions[symbol]
            total_cost = (pos['quantity'] * pos['avg_price']) + amount_usdt
            total_quantity = pos['quantity'] + quantity
            self.positions[symbol] = {
                'side': 'long',
                'quantity': total_quantity,
                'avg_price': total_cost / total_quantity,
                'value': total_cost
            }
        else:
            self.positions[symbol] = {
                'side': 'long',
                'quantity': quantity,
                'avg_price': price,
                'value': amount_usdt
            }
        
        self.trades.append(trade)
        self._save_trades()
        self._save_portfolio_state()
        
        logger.info(f"BUY executed: {quantity:.6f} {symbol} @ ${price:.2f} (${amount_usdt:.2f})")
        return trade
    
    def execute_sell(self, symbol: str, price: float, quantity: float = None, confidence: float = 0.0, llm_decision: Dict = None) -> Optional[Dict]:
        """
        Execute a sell order (paper trading).
        
        Args:
            symbol: Trading pair symbol
            price: Execution price
            quantity: Quantity to sell (None to sell entire position)
            confidence: LLM confidence score
            llm_decision: Full LLM decision dict for additional context
            
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
        
        # Record trade with enhanced LLM context
        trade = {
            "id": len(self.trades) + 1,
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "side": "sell",
            "price": price,
            "quantity": sell_quantity,
            "amount_usdt": amount_usdt,
            "profit": profit,
            "profit_pct": (profit / (position['avg_price'] * sell_quantity)) * 100,
            "confidence": confidence,
            "mode": config.TRADING_MODE,
            "llm_reasoning": llm_decision.get("reasoning", "") if llm_decision else "",
            "llm_risk_assessment": llm_decision.get("risk_assessment", "medium") if llm_decision else "medium",
            "llm_position_size": llm_decision.get("position_size", 0.1) if llm_decision else 0.1
        }
        
        # Update balance and positions
        self.balance += amount_usdt
        position['quantity'] -= sell_quantity
        position['value'] -= position['avg_price'] * sell_quantity
        
        if position['quantity'] <= 0:
            del self.positions[symbol]
        else:
            self.positions[symbol] = position
        
        self.trades.append(trade)
        self._save_trades()
        self._save_portfolio_state()
        
        logger.info(f"SELL executed: {sell_quantity:.6f} {symbol} @ ${price:.2f} (profit: ${profit:.2f})")
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
        
        return {
            "balance": self.balance,
            "positions_value": total_value - self.balance,
            "total_value": total_value,
            "initial_balance": initial_balance,
            "total_return": total_return,
            "total_return_pct": total_return_pct,
            "open_positions": len(self.positions),
            "total_trades": len(self.trades)
        }

