"""
Main entry point for the DeepSeek trading bot.

Schedules bot workflow to run at regular intervals (default: every 5 minutes),
handles logging, and coordinates data fetching, LLM decisions, and trade execution.
"""

import logging
import time
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import config
from src.data_fetcher import DataFetcher
from src.llm_client import LLMClient
from src.trading_engine import TradingEngine

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


class TradingBot:
    """
    Main trading bot that coordinates all components.
    
    Orchestrates the workflow: fetch data -> get LLM decision -> execute trade.
    Runs on a schedule defined by config.RUN_INTERVAL_SECONDS.
    """
    
    def __init__(self):
        """Initialize all bot components."""
        logger.info("=" * 60)
        logger.info("Initializing DeepSeek Trading Bot")
        logger.info("=" * 60)
        
        # Check if we're in mock mode (no API key)
        use_mock_llm = not config.DEEPSEEK_API_KEY
        
        self.data_fetcher = DataFetcher()
        self.llm_client = LLMClient(mock_mode=use_mock_llm)
        self.trading_engine = TradingEngine()
        
        logger.info(f"Trading mode: {config.TRADING_MODE}")
        logger.info(f"Exchange: {config.EXCHANGE} ({'testnet' if config.USE_TESTNET else 'live'})")
        logger.info(f"Symbol: {config.SYMBOL}")
        logger.info(f"Run interval: {config.RUN_INTERVAL_SECONDS} seconds")
        logger.info(f"LLM mode: {'MOCK' if use_mock_llm else 'LIVE'}")
    
    def run_cycle(self):
        """
        Execute one complete trading cycle.
        
        Fetches market data, gets LLM decision, and executes trades if needed.
        """
        try:
            logger.info("-" * 60)
            logger.info(f"Starting trading cycle at {datetime.now()}")
            
            # 1. Fetch market data
            logger.info("Fetching market data...")
            ticker = self.data_fetcher.get_ticker()
            current_price = float(ticker["last"])
            
            market_data = {
                "symbol": config.SYMBOL,
                "price": current_price,
                "volume": ticker.get("quoteVolume", 0),
                "change_24h": ticker.get("percentage", 0)
            }
            
            logger.info(f"Current price: ${current_price:.2f}")
            
            # 2. Get portfolio summary
            portfolio = self.trading_engine.get_portfolio_summary(current_price)
            logger.info(f"Portfolio value: ${portfolio['total_value']:.2f} "
                       f"(Return: {portfolio['total_return_pct']:.2f}%)")
            
            # 3. Get LLM decision with portfolio context
            logger.info("Consulting LLM for trading decision...")
            decision = self.llm_client.get_trading_decision(market_data, portfolio)
            
            action = decision.get("action", "hold").lower()
            confidence = decision.get("confidence", 0.0)
            reasoning = decision.get("reasoning", "No reasoning provided")
            position_size = decision.get("position_size", 0.1)
            risk_assessment = decision.get("risk_assessment", "medium")
            
            logger.info("=" * 50)
            logger.info("LLM TRADING DECISION")
            logger.info("=" * 50)
            logger.info(f"Action: {action.upper()}")
            logger.info(f"Confidence: {confidence:.2f}")
            logger.info(f"Position Size: {position_size:.2f}")
            logger.info(f"Risk Assessment: {risk_assessment.upper()}")
            logger.info(f"Reasoning: {reasoning}")
            logger.info("=" * 50)
            
            # 4. Execute trade based on decision
            trade_executed = False
            if action == "buy" and confidence > 0.6:
                # Calculate trade amount based on confidence and LLM position size
                available_balance = portfolio["balance"]
                if available_balance > 0:
                    # Use LLM position size and confidence for trade amount
                    base_amount = available_balance * config.MAX_POSITION_SIZE
                    trade_amount = base_amount * position_size * confidence
                    
                    logger.info(f"Executing BUY: ${trade_amount:.2f} (position_size: {position_size:.2f})")
                    trade = self.trading_engine.execute_buy(
                        config.SYMBOL,
                        current_price,
                        trade_amount,
                        confidence,
                        decision
                    )
                    if trade:
                        trade_executed = True
                        logger.info(f"✅ BUY trade executed successfully (ID: {trade['id']})")
                    else:
                        logger.warning("❌ BUY trade failed (insufficient balance or other error)")
                        
            elif action == "sell" and confidence > 0.6:
                # Sell all or partial position
                if config.SYMBOL in self.trading_engine.positions:
                    logger.info(f"Executing SELL: {position_size:.2f} of position")
                    trade = self.trading_engine.execute_sell(
                        config.SYMBOL,
                        current_price,
                        confidence=confidence,
                        llm_decision=decision
                    )
                    if trade:
                        trade_executed = True
                        logger.info(f"✅ SELL trade executed successfully (ID: {trade['id']}, "
                                   f"Profit: ${trade.get('profit', 0):.2f})")
                    else:
                        logger.warning("❌ SELL trade failed (no position or other error)")
                else:
                    logger.info("No position to sell")
            else:
                logger.info("Decision is to HOLD or confidence too low. No action taken.")
            
            if not trade_executed:
                logger.info("No trade executed this cycle")
            
            logger.info("Trading cycle completed successfully")
            
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}", exc_info=True)
            # Continue running despite errors
    
    def run(self):
        """
        Run the bot continuously on a schedule.
        
        Executes trading cycles at intervals defined by config.RUN_INTERVAL_SECONDS.
        Can be stopped with Ctrl+C.
        """
        logger.info("Starting bot scheduler...")
        logger.info(f"Bot will run every {config.RUN_INTERVAL_SECONDS} seconds")
        logger.info("Press Ctrl+C to stop")
        
        try:
            while True:
                self.run_cycle()
                logger.info(f"Waiting {config.RUN_INTERVAL_SECONDS} seconds until next cycle...")
                time.sleep(config.RUN_INTERVAL_SECONDS)
                
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            
            # Print final portfolio summary
            try:
                ticker = self.data_fetcher.get_ticker()
                current_price = float(ticker["last"])
                portfolio = self.trading_engine.get_portfolio_summary(current_price)
                
                logger.info("=" * 60)
                logger.info("FINAL PORTFOLIO SUMMARY")
                logger.info("=" * 60)
                logger.info(f"Initial Balance: ${portfolio['initial_balance']:.2f}")
                logger.info(f"Current Balance: ${portfolio['balance']:.2f}")
                logger.info(f"Positions Value: ${portfolio['positions_value']:.2f}")
                logger.info(f"Total Value: ${portfolio['total_value']:.2f}")
                logger.info(f"Total Return: ${portfolio['total_return']:.2f} ({portfolio['total_return_pct']:.2f}%)")
                logger.info(f"Total Trades: {portfolio['total_trades']}")
                logger.info("=" * 60)
                
            except Exception as e:
                logger.error(f"Error generating final summary: {e}")
            
            sys.exit(0)


def main():
    """Main entry point."""
    bot = TradingBot()
    bot.run()


if __name__ == "__main__":
    main()

