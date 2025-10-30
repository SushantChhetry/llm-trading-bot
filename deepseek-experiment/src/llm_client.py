"""
LLM client module for DeepSeek API integration.

Handles communication with DeepSeek LLM for trading decision generation.
Includes a mock mode for testing without API calls and structured prompt templates.
"""

import logging
import json
import re
from typing import Dict, Optional, List
import requests

from config import config
from .security import SecurityManager, secure_api_key_required, validate_trading_inputs, rate_limit
from .resilience import circuit_breaker, retry, fallback, CircuitBreakerConfig, RetryConfig

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Client for interacting with DeepSeek LLM API.
    
    Provides methods to prompt the LLM for trading decisions and can operate
    in mock mode for testing without API calls. Uses structured prompt templates
    and validates JSON responses for reliable trading decisions.
    
    Attributes:
        api_key: DeepSeek API key
        api_url: DeepSeek API endpoint URL
        model: Model name to use
        mock_mode: Whether to use mock responses instead of real API calls
    """
    
    def __init__(
        self,
        provider: str = None,
        api_key: str = None,
        api_url: str = None,
        model: str = None,
        mock_mode: bool = None
    ):
        """
        Initialize the LLM client.
        
        Args:
            provider: LLM provider ("mock", "deepseek", "openai", "anthropic"). Defaults to config.
            api_key: API key. Defaults to config.
            api_url: API endpoint URL. Defaults to config.
            model: Model name. Defaults to config.
            mock_mode: If True, returns mock responses without API calls. Auto-detected if None.
        """
        self.provider = provider or config.LLM_PROVIDER
        self.api_key = api_key or config.LLM_API_KEY
        self.api_url = api_url or config.LLM_API_URL
        self.model = model or config.LLM_MODEL
        
        # Initialize security manager
        self.security_manager = SecurityManager()
        
        # Auto-detect mock mode if not specified
        if mock_mode is None:
            self.mock_mode = (self.provider == "mock" or not self.api_key)
        else:
            self.mock_mode = mock_mode
        
        # Validate API key if not in mock mode
        if not self.mock_mode:
            if not self.api_key:
                logger.warning(f"No API key provided for {self.provider}. Will use mock responses.")
                self.mock_mode = True
            elif not self.security_manager.validate_api_key(self.api_key, self.provider):
                logger.error(f"Invalid API key format for {self.provider}. Will use mock responses.")
                self.mock_mode = True
        
        logger.info(f"LLM Client initialized: {self.provider.upper()} {'(MOCK)' if self.mock_mode else '(LIVE)'}")
    
    def _format_trading_prompt(self, market_data: Dict, portfolio_state: Dict) -> str:
        """
        Format a structured prompt for trading decisions.
        
        Args:
            market_data: Current market information (price, volume, etc.)
            portfolio_state: Current portfolio state (balance, positions, etc.)
            
        Returns:
            Formatted prompt string for the LLM
        """
        # Safely extract and format values with error handling
        try:
            price = float(market_data.get('price', 0))
        except (ValueError, TypeError):
            price = 0.0
            
        try:
            volume = float(market_data.get('volume', 0))
        except (ValueError, TypeError):
            volume = 0.0
            
        try:
            change_24h = float(market_data.get('change_24h', 0))
        except (ValueError, TypeError):
            change_24h = 0.0
            
        try:
            balance = float(portfolio_state.get('balance', 0))
        except (ValueError, TypeError):
            balance = 0.0
            
        try:
            total_value = float(portfolio_state.get('total_value', 0))
        except (ValueError, TypeError):
            total_value = 0.0
            
        try:
            return_pct = float(portfolio_state.get('total_return_pct', 0))
        except (ValueError, TypeError):
            return_pct = 0.0

        # Extract Sharpe ratio and risk metrics for Alpha Arena style feedback
        sharpe_ratio = portfolio_state.get('sharpe_ratio', 0.0) if portfolio_state else 0.0
        volatility = portfolio_state.get('volatility', 0.0) if portfolio_state else 0.0
        max_drawdown = portfolio_state.get('max_drawdown', 0.0) if portfolio_state else 0.0
        risk_adjusted_return = portfolio_state.get('risk_adjusted_return', 0.0) if portfolio_state else 0.0

        prompt = f"""
You are a quantitative cryptocurrency trader in the Alpha Arena competition. Your goal is to maximize PnL through systematic analysis of numerical data only. You have $10,000 to trade perpetual futures with leverage.

IMPORTANT: Read all data carefully. Market data is presented in chronological order (oldest to newest). Account state shows current values.

MARKET DATA (Quantitative Only - Chronological Order):
- Symbol: {market_data.get('symbol', 'N/A') if market_data else 'N/A'}
- Current Price: ${price:.2f} (LATEST PRICE)
- 24h Volume: {volume:,.0f}
- 24h Change: {change_24h:.2f}% (from 24 hours ago to now)

ACCOUNT STATE (Current Values):
- Available Cash: ${balance:.2f} (FREE COLLATERAL - money available for new positions)
- Total Portfolio Value: ${total_value:.2f} (total account value including positions)
- Open Positions: {portfolio_state.get('open_positions', 0) if portfolio_state else 0}
- Total Return: {return_pct:.2f}%
- Total Trades: {portfolio_state.get('total_trades', 0) if portfolio_state else 0}

RISK PERFORMANCE METRICS (Alpha Arena Feedback):
- Sharpe Ratio: {sharpe_ratio:.3f} (excess return per unit of risk)
- Volatility: {volatility:.3f}
- Max Drawdown: ${max_drawdown:.2f}
- Risk-Adjusted Return: {risk_adjusted_return:.3f}

BEHAVIORAL PATTERNS (Your Trading Style):
- Bullish Tilt: {portfolio_state.get('bullish_tilt', 0.5):.2f} (1.0 = always long, 0.0 = always short)
- Avg Holding Period: {portfolio_state.get('avg_holding_period_hours', 0):.1f} hours
- Trade Frequency: {portfolio_state.get('trade_frequency_per_day', 0):.1f} trades/day
- Avg Position Size: ${portfolio_state.get('avg_position_size_usdt', 0):.0f}
- Avg Confidence: {portfolio_state.get('avg_confidence', 0):.2f}
- Exit Plan Tightness: {portfolio_state.get('exit_plan_tightness', 0):.1f}% average distance
- Active Positions: {portfolio_state.get('active_positions_count', 0)}
- Total Fees Paid: ${portfolio_state.get('total_trading_fees', 0):.2f}
- Fee Impact: {portfolio_state.get('fee_impact_pct', 0):.1f}% of PnL

TRADING PARAMETERS:
- Maximum Leverage: 10x (use responsibly)
- Trading Fees: 0.05% per trade (taker)
- Position Sizing: Calculate based on available cash, leverage, and risk tolerance
- Minimum Confidence: 0.6 for trade execution

ALPHA ARENA OBJECTIVES:
- PRIMARY GOAL: Maximize PnL (profit and loss)
- Use Sharpe ratio feedback to normalize for risky behavior
- Focus purely on quantitative data analysis
- No access to news or market narratives - infer from time-series data only
- Systematic trading based on numerical patterns

FEE AWARENESS (CRITICAL):
- Trading fees are 0.05% per trade (taker) - they add up quickly!
- Avoid over-trading: small, frequent trades get eaten by fees
- Focus on fewer, higher-conviction positions with larger size
- Only trade when confidence > 0.6 and clear signal exists
- Consider fee impact: if fee impact > 20% of PnL, reduce trade frequency

RISK MANAGEMENT:
- Never risk more than 2% of portfolio per trade
- Use stop losses and take profits
- Consider Sharpe ratio when making decisions (higher is better)
- Maintain discipline and avoid emotional decisions
- Optimize for risk-adjusted returns, not just raw profits
- Be consistent with your exit plans - don't contradict yourself

REQUIRED RESPONSE FORMAT (JSON only):
{{
    "action": "buy|sell|hold",
    "direction": "long|short|none",
    "quantity": 0.0,
    "leverage": 1.0-10.0,
    "confidence": 0.0-1.0,
    "justification": "Brief explanation of your decision",
    "exit_plan": {{
        "profit_target": 0.0,
        "stop_loss": 0.0,
        "invalidation_conditions": ["condition1", "condition2"]
    }},
    "position_size_usdt": 0.0,
    "risk_assessment": "low|medium|high"
}}

Provide your trading decision in the exact JSON format above. Include specific exit conditions and risk parameters.
"""
        return prompt.strip()
    
    @validate_trading_inputs
    def _validate_llm_response(self, response_text: str) -> Optional[Dict]:
        """
        Validate and parse LLM response JSON.
        
        Args:
            response_text: Raw response text from LLM
            
        Returns:
            Parsed and validated response dict, or None if invalid
        """
        try:
            # Try to parse as JSON directly
            response = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from text using regex
            json_match = re.search(r'\{[^{}]*"action"[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    response = json.loads(json_match.group())
                except json.JSONDecodeError:
                    logger.error(f"Could not parse JSON from response: {response_text[:200]}...")
                    return None
            else:
                logger.error(f"No JSON found in response: {response_text[:200]}...")
                return None
        
        # Use security manager for validation
        if not self.security_manager.validate_trading_decision(response):
            logger.error("Trading decision failed security validation")
            return None
        
        # Validate exit plan structure
        exit_plan = response.get("exit_plan", {})
        if not isinstance(exit_plan, dict):
            exit_plan = {}
        
        # Set defaults for optional fields
        response["direction"] = response.get("direction", "none").lower()
        response["quantity"] = float(response.get("quantity", 0.0))
        response["position_size_usdt"] = float(response.get("position_size_usdt", 0.0))
        response["risk_assessment"] = response.get("risk_assessment", "medium")
        response["exit_plan"] = {
            "profit_target": float(exit_plan.get("profit_target", 0.0)),
            "stop_loss": float(exit_plan.get("stop_loss", 0.0)),
            "invalidation_conditions": exit_plan.get("invalidation_conditions", [])
        }
        
        # Normalize action to lowercase
        response["action"] = response["action"].lower()
        
        return response
    
    @circuit_breaker(CircuitBreakerConfig(failure_threshold=3, recovery_timeout=30))
    @retry(RetryConfig(max_attempts=3, base_delay=1.0, max_delay=10.0))
    @rate_limit(60)  # 60 requests per minute
    def _make_api_request(self, prompt: str) -> Dict:
        """
        Make actual API request to the configured LLM provider.
        
        Supports DeepSeek, OpenAI, and Anthropic APIs with proper error handling
        and automatic fallback to mock mode on API failures.
        
        Args:
            prompt: The prompt text to send
            
        Returns:
            Response dictionary from API
            
        Raises:
            Exception: If API request fails
        """
        if self.provider == "deepseek":
            return self._make_deepseek_request(prompt)
        elif self.provider == "openai":
            return self._make_openai_request(prompt)
        elif self.provider == "anthropic":
            return self._make_anthropic_request(prompt)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
    
    def _make_deepseek_request(self, prompt: str) -> Dict:
        """Make API request to DeepSeek."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a cryptocurrency trading assistant. Always respond with valid JSON in the exact format requested."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"DeepSeek API request failed: {e}")
            raise
    
    def _make_openai_request(self, prompt: str) -> Dict:
        """Make API request to OpenAI."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a cryptocurrency trading assistant. Always respond with valid JSON in the exact format requested."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"OpenAI API request failed: {e}")
            raise
    
    def _make_anthropic_request(self, prompt: str) -> Dict:
        """Make API request to Anthropic Claude."""
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": self.model,
            "max_tokens": 500,
            "temperature": 0.7,
            "system": "You are a cryptocurrency trading assistant. Always respond with valid JSON in the exact format requested.",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Anthropic API request failed: {e}")
            raise
    
    def _extract_response_content(self, response: Dict) -> str:
        """
        Extract content from API response based on provider format.
        
        Args:
            response: Raw API response dictionary
            
        Returns:
            Extracted text content
        """
        if self.provider in ["deepseek", "openai"]:
            return response["choices"][0]["message"]["content"]
        elif self.provider == "anthropic":
            return response["content"][0]["text"]
        else:
            raise ValueError(f"Unknown provider for response parsing: {self.provider}")
    
    def _get_mock_response(self, market_data: Dict, portfolio_state: Dict) -> Dict:
        """
        Generate a mock LLM response for testing.
        
        Args:
            market_data: Current market data for context
            portfolio_state: Current portfolio state for context
            
        Returns:
            Mock API response structure
        """
        import random
        
        # Simulate more realistic decision making based on market data
        price = market_data.get('price', 50000)
        change_24h = market_data.get('change_24h', 0)
        balance = portfolio_state.get('balance', 10000)
        open_positions = portfolio_state.get('open_positions', 0)
        
        # Enhanced mock logic for Alpha Arena style trading
        if change_24h > 2.0 and balance > 1000:
            action = "buy"
            direction = "long"
            confidence = random.uniform(0.7, 0.9)
            reasoning = f"Mock: Strong positive momentum (+{change_24h:.1f}%) suggests long opportunity"
        elif change_24h < -2.0 and balance > 1000:
            action = "buy"
            direction = "short"
            confidence = random.uniform(0.7, 0.9)
            reasoning = f"Mock: Strong negative momentum ({change_24h:.1f}%) suggests short opportunity"
        elif change_24h < -1.0 and open_positions > 0:
            action = "sell"
            direction = "none"
            confidence = random.uniform(0.7, 0.9)
            reasoning = f"Mock: Negative momentum ({change_24h:.1f}%) suggests closing positions to limit losses"
        else:
            action = "hold"
            direction = "none"
            confidence = random.uniform(0.5, 0.7)
            reasoning = f"Mock: Market conditions unclear ({change_24h:.1f}%), holding position"
        
        # Calculate position size based on available balance and confidence
        position_size_usdt = min(balance * 0.1 * confidence, balance * 0.2)  # Max 20% of balance
        leverage = random.uniform(1.0, 3.0)  # Conservative leverage for mock
        quantity = position_size_usdt * leverage / price if price > 0 else 0
        
        mock_decision = {
            "action": action,
            "direction": direction,
            "quantity": round(quantity, 6),
            "leverage": round(leverage, 1),
            "confidence": round(confidence, 2),
            "justification": reasoning,
            "exit_plan": {
                "profit_target": round(price * 0.02, 2) if action == "buy" else round(price * 0.02, 2) if action == "sell" else 0.0,
                "stop_loss": round(price * 0.01, 2) if action in ["buy", "sell"] else 0.0,
                "invalidation_conditions": ["market_volatility_spike", "unexpected_news"] if action in ["buy", "sell"] else []
            },
            "position_size_usdt": round(position_size_usdt, 2),
            "risk_assessment": random.choice(["low", "medium", "high"])
        }
        
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(mock_decision)
                    }
                }
            ]
        }
    
    @validate_trading_inputs
    @fallback(lambda: {"action": "hold", "direction": "none", "confidence": 0.0, "justification": "Fallback due to error"})
    def get_trading_decision(self, market_data: Dict, portfolio_state: Dict = None) -> Dict:
        """
        Get a trading decision from the LLM based on market data and portfolio state.
        
        Args:
            market_data: Dictionary containing market information (price, volume, etc.)
            portfolio_state: Dictionary containing portfolio state (balance, positions, etc.)
            
        Returns:
            Dictionary with validated trading decision including action, confidence, reasoning, etc.
        """
        # Set default portfolio state if not provided
        if portfolio_state is None:
            portfolio_state = {
                "balance": 10000.0,
                "total_value": 10000.0,
                "open_positions": 0,
                "total_return_pct": 0.0,
                "total_trades": 0
            }
        
        # Format structured prompt
        prompt = self._format_trading_prompt(market_data, portfolio_state)
        
        try:
            if self.mock_mode:
                logger.info(f"Using mock LLM response ({self.provider})")
                response = self._get_mock_response(market_data, portfolio_state)
            else:
                logger.info(f"Calling {self.provider.upper()} API")
                try:
                    response = self._make_api_request(prompt)
                except Exception as api_error:
                    logger.error(f"API call failed: {api_error}")
                    logger.warning("Falling back to mock mode for this cycle")
                    response = self._get_mock_response(market_data, portfolio_state)
            
            # Extract content from response based on provider
            content = self._extract_response_content(response)
            logger.debug(f"Raw LLM response: {content}")
            
            # Validate and parse response
            decision = self._validate_llm_response(content)
            
            if decision is None:
                logger.error("Invalid LLM response, falling back to hold")
                return {
                    "action": "hold",
                    "direction": "none",
                    "quantity": 0.0,
                    "leverage": 1.0,
                    "confidence": 0.0,
                    "justification": "Invalid LLM response format",
                    "exit_plan": {
                        "profit_target": 0.0,
                        "stop_loss": 0.0,
                        "invalidation_conditions": []
                    },
                    "position_size_usdt": 0.0,
                    "risk_assessment": "high"
                }
            
            logger.info(f"LLM decision: {decision['action'].upper()} "
                       f"(confidence: {decision['confidence']:.2f}, "
                       f"risk: {decision['risk_assessment']})")
            logger.info(f"LLM justification: {decision['justification']}")
            
            return decision
            
        except Exception as e:
            logger.error(f"Error getting trading decision: {e}")
            # Fallback to hold on error
            return {
                "action": "hold",
                "direction": "none",
                "quantity": 0.0,
                "leverage": 1.0,
                "confidence": 0.0,
                "justification": f"Error occurred: {str(e)}",
                "exit_plan": {
                    "profit_target": 0.0,
                    "stop_loss": 0.0,
                    "invalidation_conditions": []
                },
                "position_size_usdt": 0.0,
                "risk_assessment": "high"
            }

