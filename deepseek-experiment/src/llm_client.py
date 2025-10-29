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
        api_key: str = None,
        api_url: str = None,
        model: str = None,
        mock_mode: bool = False
    ):
        """
        Initialize the LLM client.
        
        Args:
            api_key: DeepSeek API key. Defaults to config.
            api_url: API endpoint URL. Defaults to config.
            model: Model name. Defaults to config.
            mock_mode: If True, returns mock responses without API calls
        """
        self.api_key = api_key or config.DEEPSEEK_API_KEY
        self.api_url = api_url or config.DEEPSEEK_API_URL
        self.model = model or config.DEEPSEEK_MODEL
        self.mock_mode = mock_mode
        
        if not self.mock_mode and not self.api_key:
            logger.warning("No API key provided and mock_mode=False. Will use mock responses.")
            self.mock_mode = True
    
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

        prompt = f"""
You are an expert cryptocurrency trading assistant. Analyze the following market data and portfolio state to make a trading decision.

MARKET DATA:
- Symbol: {market_data.get('symbol', 'N/A') if market_data else 'N/A'}
- Current Price: ${price:.2f}
- 24h Volume: {volume:,.0f}
- 24h Change: {change_24h:.2f}%

PORTFOLIO STATE:
- Available Balance: ${balance:.2f}
- Total Portfolio Value: ${total_value:.2f}
- Open Positions: {portfolio_state.get('open_positions', 0) if portfolio_state else 0}
- Total Return: {return_pct:.2f}%
- Total Trades: {portfolio_state.get('total_trades', 0) if portfolio_state else 0}

TRADING RULES:
- Only trade if confidence > 0.6
- Consider risk management and position sizing
- Look for clear market signals and trends
- Avoid overtrading and emotional decisions

REQUIRED RESPONSE FORMAT (JSON only):
{{
    "action": "buy|sell|hold",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of your decision",
    "position_size": 0.0-1.0,
    "risk_assessment": "low|medium|high"
}}

Provide your trading decision in the exact JSON format above. Be concise but clear in your reasoning.
"""
        return prompt.strip()
    
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
        
        # Validate required fields
        required_fields = ["action", "confidence", "reasoning"]
        for field in required_fields:
            if field not in response:
                logger.error(f"Missing required field '{field}' in response")
                return None
        
        # Validate action
        valid_actions = ["buy", "sell", "hold"]
        if response["action"].lower() not in valid_actions:
            logger.error(f"Invalid action '{response['action']}'. Must be one of: {valid_actions}")
            return None
        
        # Validate confidence
        try:
            confidence = float(response["confidence"])
            if not 0.0 <= confidence <= 1.0:
                logger.error(f"Confidence {confidence} must be between 0.0 and 1.0")
                return None
            response["confidence"] = confidence
        except (ValueError, TypeError):
            logger.error(f"Invalid confidence value: {response['confidence']}")
            return None
        
        # Set defaults for optional fields
        response["position_size"] = response.get("position_size", 0.1)
        response["risk_assessment"] = response.get("risk_assessment", "medium")
        
        # Normalize action to lowercase
        response["action"] = response["action"].lower()
        
        return response
    
    def _make_api_request(self, prompt: str) -> Dict:
        """
        Make actual API request to DeepSeek.
        
        TODO: Implement DeepSeek API call
        This is a placeholder for the actual DeepSeek API integration.
        Replace with real API call when credentials are available.
        
        Args:
            prompt: The prompt text to send
            
        Returns:
            Response dictionary from API
            
        Raises:
            Exception: If API request fails
        """
        # TODO: Implement DeepSeek API call
        # Replace this placeholder with actual API call
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
            # TODO: Replace with actual DeepSeek API call
            # response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)
            # response.raise_for_status()
            # return response.json()
            
            # Placeholder - this should never be reached in mock mode
            raise NotImplementedError("DeepSeek API not implemented yet. Use mock_mode=True for testing.")
            
        except Exception as e:
            logger.error(f"API request failed: {e}")
            raise
    
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
        
        # Simple mock logic based on market conditions
        if change_24h > 2.0 and balance > 1000:
            action = "buy"
            confidence = random.uniform(0.7, 0.9)
            reasoning = f"Mock: Strong positive momentum (+{change_24h:.1f}%) suggests buying opportunity"
        elif change_24h < -2.0 and open_positions > 0:
            action = "sell"
            confidence = random.uniform(0.7, 0.9)
            reasoning = f"Mock: Negative momentum ({change_24h:.1f}%) suggests selling to limit losses"
        else:
            action = "hold"
            confidence = random.uniform(0.5, 0.7)
            reasoning = f"Mock: Market conditions unclear ({change_24h:.1f}%), holding position"
        
        mock_decision = {
            "action": action,
            "confidence": round(confidence, 2),
            "reasoning": reasoning,
            "position_size": round(random.uniform(0.05, 0.15), 2),
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
                logger.info("Using mock LLM response")
                response = self._get_mock_response(market_data, portfolio_state)
            else:
                logger.info("Calling DeepSeek API")
                response = self._make_api_request(prompt)
            
            # Extract content from response
            content = response["choices"][0]["message"]["content"]
            logger.debug(f"Raw LLM response: {content}")
            
            # Validate and parse response
            decision = self._validate_llm_response(content)
            
            if decision is None:
                logger.error("Invalid LLM response, falling back to hold")
                return {
                    "action": "hold",
                    "confidence": 0.0,
                    "reasoning": "Invalid LLM response format",
                    "position_size": 0.0,
                    "risk_assessment": "high"
                }
            
            logger.info(f"LLM decision: {decision['action'].upper()} "
                       f"(confidence: {decision['confidence']:.2f}, "
                       f"risk: {decision['risk_assessment']})")
            logger.info(f"LLM reasoning: {decision['reasoning']}")
            
            return decision
            
        except Exception as e:
            logger.error(f"Error getting trading decision: {e}")
            # Fallback to hold on error
            return {
                "action": "hold",
                "confidence": 0.0,
                "reasoning": f"Error occurred: {str(e)}",
                "position_size": 0.0,
                "risk_assessment": "high"
            }

