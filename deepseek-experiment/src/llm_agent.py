"""
LLM Agent - Multi-Step Reasoning for Trading Decisions

Implements an agentic approach where LLM makes multiple reasoning steps before
final trading decision, improving decision quality and profit potential.

Uses hybrid LLM approach: cheaper model for analysis, better model for final decision.
"""

import json
import logging
import hashlib
import time
from typing import Dict, Optional, Any, List
from datetime import datetime

from config import config
from .llm_client import LLMClient
from .logger import LogDomain, get_logger

logger = get_logger(__name__, domain=LogDomain.LLM)

# Decision schema for validation
DECISION_SCHEMA = {
    "action": {"type": "string", "enum": ["buy", "sell", "hold"]},
    "direction": {"type": "string", "enum": ["long", "short", "none"]},
    "confidence": {"type": "float", "minimum": 0.4, "maximum": 0.95},
    "position_size_usdt": {"type": "float", "minimum": 0, "maximum": 5000},
    "stop_loss_pct": {"type": "float", "minimum": 0.01, "maximum": 0.10},
    "take_profit_pct": {"type": "float", "minimum": 0.02, "maximum": 0.50},
    "leverage": {"type": "float", "minimum": 1.0, "maximum": 10.0},
    "justification": {"type": "string"},
    "risk_assessment": {"type": "string", "enum": ["low", "medium", "high"]},
}


class LLMAgent:
    """
    Multi-step LLM agent for trading decisions.
    
    Workflow:
    1. Market Analysis Agent: Analyze market conditions, trends, regime
    2. Strategy Evaluation Agent: Evaluate different trading strategies
    3. Risk Assessment Agent: Assess risk for each strategy
    4. Decision Agent: Make final trading decision
    """

    def __init__(
        self,
        fast_llm_client: LLMClient = None,
        best_llm_client: LLMClient = None,
        max_retries: int = None,
        timeout_seconds: int = None,
        use_hybrid: bool = True,
    ):
        """
        Initialize the LLM agent.
        
        Args:
            fast_llm_client: Fast/cheap LLM for analysis steps
            best_llm_client: Better/more expensive LLM for final decision
            max_retries: Maximum retries per agent step
            timeout_seconds: Timeout per agent step
            use_hybrid: If True, use hybrid approach (fast for analysis, best for decision)
        """
        self.fast_llm_client = fast_llm_client or LLMClient()
        self.best_llm_client = best_llm_client or LLMClient()
        self.max_retries = max_retries or getattr(config, "AGENT_MAX_RETRIES", 2)
        self.timeout_seconds = timeout_seconds or getattr(config, "AGENT_TIMEOUT_SECONDS", 60)
        self.use_hybrid = use_hybrid

        # Cache for previous good decisions (fallback)
        self.cached_decision: Optional[Dict] = None
        self.decision_cache: Dict[str, Dict] = {}  # Cache key -> decision with timestamp
        self.MAX_CACHE_SIZE = 1000
        self.CACHE_TTL_SECONDS = 3600  # 1 hour

        logger.info(
            f"LLMAgent initialized: hybrid={use_hybrid}, "
            f"max_retries={self.max_retries}, timeout={self.timeout_seconds}s"
        )

    def execute_agent_workflow(self, market_data: Dict, portfolio: Dict, use_cache: bool = True) -> Dict:
        """
        CORRECTED: Execute the full agent workflow with robust error recovery.
        
        Includes:
        - Cache checking (use recent decisions if available)
        - Retry logic per step
        - Fallback to cached decision
        - Fallback to single LLM call
        - Fallback to hold decision
        
        Args:
            market_data: Market data dictionary
            portfolio: Portfolio state dictionary
            use_cache: If True, check cache first
        
        Returns:
            Final trading decision dictionary
        """
        # Check cache first (with proper cache key to avoid collisions)
        cache_data = json.dumps({
            "timestamp": market_data.get('timestamp', 'unknown'),
            "price": market_data.get('price', 0),
            "balance": portfolio.get('balance', 0),
            "positions": portfolio.get('open_positions', 0)
        }, sort_keys=True)
        cache_key = hashlib.md5(cache_data.encode()).hexdigest()[:16]
        
        # Cleanup expired cache entries
        self._cleanup_cache()
        
        if use_cache and cache_key in self.decision_cache:
            cached_decision = self.decision_cache[cache_key]
            cache_age = (datetime.now() - cached_decision["timestamp"]).total_seconds()
            if cache_age < 60:  # Use cache if < 60 seconds old
                logger.info("Using cached decision from agent workflow")
                return cached_decision["decision"]
        
        try:
            # Step 1: Market Analysis
            market_analysis = self._call_agent_with_retry(
                "market_analysis",
                self._format_market_analysis_prompt(market_data, portfolio),
                market_data,
                max_retries=2
            )

            if not market_analysis:
                logger.warning("Market analysis failed, using cached decision or fallback")
                return self._get_fallback_decision(portfolio)

            # Step 2: Strategy Evaluation
            strategy_options = self._call_agent_with_retry(
                "strategy_evaluation",
                self._format_strategy_evaluation_prompt(market_analysis, portfolio),
                market_data,
                max_retries=2
            )

            if not strategy_options:
                logger.warning("Strategy evaluation failed, using cached decision or fallback")
                return self._get_fallback_decision(portfolio)

            # Step 3: Risk Assessment
            risk_assessment = self._call_agent_with_retry(
                "risk_assessment",
                self._format_risk_assessment_prompt(strategy_options, portfolio),
                market_data,
                max_retries=2
            )

            if not risk_assessment:
                logger.warning("Risk assessment failed, using cached decision or fallback")
                return self._get_fallback_decision(portfolio)

            # Step 4: Final Decision (use best model)
            final_decision = self._call_agent_with_retry(
                "decision",
                self._format_decision_prompt(market_analysis, strategy_options, risk_assessment, portfolio),
                market_data,
                use_best_model=True,
                max_retries=2
            )

            if not final_decision:
                logger.warning("Final decision failed, using cached decision or fallback")
                return self._get_fallback_decision(portfolio)

            # Validate and cache decision
            validated_decision = self._validate_decision(final_decision)
            if validated_decision:
                # Cache successful decision
                self.cached_decision = validated_decision
                self.decision_cache[cache_key] = {
                    "timestamp": datetime.now(),
                    "decision": validated_decision
                }
                return validated_decision
            else:
                logger.warning("Decision validation failed, using cached decision or fallback")
                return self._get_fallback_decision(portfolio, cache_key)

        except Exception as e:
            logger.error(f"Error in agent workflow: {e}", exc_info=True)
            
            # Fallback 1: Use cached decision if available
            if cache_key in self.decision_cache:
                logger.warning("Using older cached decision as fallback")
                return self.decision_cache[cache_key]["decision"]
            
            # Fallback 2: Use previous good decision
            if self.cached_decision:
                logger.warning("Using previous good decision as fallback")
                return self.cached_decision
            
            # Fallback 3: Use deterministic single LLM call
            logger.warning("Falling back to single LLM call")
            try:
                simple_decision = self.best_llm_client.get_trading_decision(
                    market_data, portfolio, use_agentic_mode=False
                )
                return simple_decision
            except Exception as e2:
                logger.critical(f"All decision methods failed: {e2}")
                # Fallback 4: Return hold decision (safest option)
                return self._get_fallback_decision(portfolio, cache_key)

    def _call_agent_with_retry(
        self, agent_name: str, prompt: str, context: Dict, use_best_model: bool = False, max_retries: int = None
    ) -> Optional[Dict]:
        """
        CORRECTED: Call an agent step with robust retry logic.
        
        Args:
            agent_name: Name of the agent step
            prompt: Prompt text
            context: Additional context
            use_best_model: If True, use best_llm_client instead of fast_llm_client
            max_retries: Override max retries for this call
        
        Returns:
            Agent response dictionary or None if failed
        """
        client = self.best_llm_client if (use_best_model or not self.use_hybrid) else self.fast_llm_client
        retries = max_retries or self.max_retries

        for attempt in range(retries):
            try:
                logger.debug(f"Agent step: {agent_name}, attempt {attempt + 1}/{retries}")

                # Exponential backoff for retries
                if attempt > 0:
                    backoff_delay = min(2 ** attempt, 10)  # Max 10 seconds
                    time.sleep(backoff_delay)
                    logger.debug(f"Retrying after {backoff_delay}s backoff")

                # Use LLMClient's internal method to make API call
                # Format prompt with system message
                full_prompt = f"You are a {agent_name.replace('_', ' ').title()} Agent. Provide only valid JSON responses.\n\n{prompt}"
                
                # Make API request using LLMClient's internal method (with timeout)
                api_response = client._make_api_request(full_prompt)
                
                # Extract response text
                if api_response and "choices" in api_response:
                    response_text = api_response["choices"][0]["message"]["content"]
                    
                    # Parse JSON response
                    try:
                        decision = client._validate_llm_response(response_text)
                        if decision:
                            logger.debug(f"Agent step {agent_name} succeeded")
                            return decision
                    except Exception as e:
                        logger.warning(f"Failed to parse response from {agent_name}: {e}")
                        continue

            except Exception as e:
                logger.warning(f"Agent step {agent_name} attempt {attempt + 1} failed: {e}")
                if attempt == retries - 1:
                    logger.error(f"Agent step {agent_name} failed after {retries} attempts")

        return None
    
    def _call_agent(
        self, agent_name: str, prompt: str, context: Dict, use_best_model: bool = False
    ) -> Optional[Dict]:
        """Wrapper for backward compatibility."""
        return self._call_agent_with_retry(agent_name, prompt, context, use_best_model)

    def _format_market_analysis_prompt(self, market_data: Dict, portfolio: Dict) -> str:
        """Format prompt for Market Analysis Agent."""
        return f"""You are a Market Analysis Agent. Analyze the current market conditions.

Market Data:
{json.dumps(market_data, indent=2)}

Portfolio State:
{json.dumps(portfolio, indent=2)}

Provide a JSON response with:
- market_regime: "bullish", "bearish", "sideways", "choppy"
- trend_strength: 0.0-1.0
- volatility_level: "low", "medium", "high"
- key_signals: List of key technical signals
- momentum: "strong_up", "weak_up", "neutral", "weak_down", "strong_down"

Respond in JSON format only."""

    def _format_strategy_evaluation_prompt(self, market_analysis: Dict, portfolio: Dict) -> str:
        """Format prompt for Strategy Evaluation Agent."""
        open_positions = portfolio.get("open_positions", 0)
        has_positions = open_positions > 0
        
        return f"""You are a Strategy Evaluation Agent. Evaluate trading strategies based on market analysis.

Market Analysis:
{json.dumps(market_analysis, indent=2)}

Portfolio State:
{json.dumps(portfolio, indent=2)}

CRITICAL: You currently have {open_positions} open position(s). Consider exit strategies FIRST before new entries.

Evaluate these strategies:
1. Long position (new entry)
2. Short position (new entry)
3. Hold (maintain current positions)
4. SELL/EXIT (close existing positions) - CRITICAL if confidence drops or conditions deteriorate

For each strategy, provide:
- expected_outcome: "profit", "loss", "neutral"
- expected_return_pct: Estimated return percentage
- probability_of_success: 0.0-1.0
- pros: List of advantages
- cons: List of disadvantages

EXIT STRATEGY PRIORITY:
- If you have open positions and confidence < 0.5, STRONGLY consider selling
- If market conditions deteriorate significantly, prioritize exit over entry
- Take profits when momentum weakens, even if position is profitable
- Cut losses early - don't hold losing positions hoping for recovery

Respond in JSON format with a "strategies" array."""

    def _format_risk_assessment_prompt(self, strategy_options: Dict, portfolio: Dict) -> str:
        """Format prompt for Risk Assessment Agent."""
        return f"""You are a Risk Assessment Agent. Assess risk for each trading strategy.

Strategy Options:
{json.dumps(strategy_options, indent=2)}

Portfolio State:
{json.dumps(portfolio, indent=2)}

For each strategy, provide:
- risk_score: 0.0-1.0 (higher = riskier)
- recommended_position_size_usdt: Optimal position size
- recommended_stop_loss_pct: Stop loss percentage
- recommended_take_profit_pct: Take profit percentage
- max_leverage: Maximum safe leverage
- risk_factors: List of risk factors

Respond in JSON format with a "risk_assessments" array."""

    def _format_decision_prompt(
        self, market_analysis: Dict, strategy_options: Dict, risk_assessment: Dict, portfolio: Dict
    ) -> str:
        """Format prompt for Decision Agent."""
        open_positions = portfolio.get("open_positions", 0)
        has_positions = open_positions > 0
        
        return f"""You are a Decision Agent. Make the final trading decision based on all analysis.

Market Analysis:
{json.dumps(market_analysis, indent=2)}

Strategy Options:
{json.dumps(strategy_options, indent=2)}

Risk Assessment:
{json.dumps(risk_assessment, indent=2)}

Portfolio State:
{json.dumps(portfolio, indent=2)}

CRITICAL EXIT RULES:
- If you have open positions ({open_positions}) and confidence drops below 0.5, STRONGLY consider selling
- If market regime changes unfavorably, prioritize exit over entry
- Take profits when momentum weakens - don't be greedy
- Cut losses early - if position is losing >1% and confidence is low, sell immediately
- If confidence < 0.4 and you have a position, action should be "sell", not "hold"

PROFIT MAXIMIZATION STRATEGY:
- Maximize position size when confidence is high (>0.7) and conditions are favorable
- Use larger position sizes for high-conviction trades
- Take partial profits at +2% if momentum weakens
- Full exit at +5% or when confidence drops significantly

Make a final trading decision. Provide a JSON response with:
- action: "buy", "sell", or "hold" (prefer "sell" over "hold" if confidence < 0.5 and position exists)
- direction: "long", "short", or "none"
- confidence: 0.4-0.95
- position_size_usdt: Position size in USDT (0-5000) - use larger sizes for high confidence
- stop_loss_pct: Stop loss percentage (0.01-0.10)
- take_profit_pct: Take profit percentage (0.02-0.50)
- leverage: Leverage multiplier (1.0-10.0)
- justification: Reasoning for the decision (emphasize exit logic if selling)
- risk_assessment: "low", "medium", or "high"
- exit_plan: Object with profit_target and stop_loss

Respond in JSON format only."""

    def _validate_decision(self, decision: Dict) -> Optional[Dict]:
        """
        Validate decision against schema.
        
        Returns:
            Validated decision or None if invalid
        """
        try:
            # Validate action
            if decision.get("action") not in DECISION_SCHEMA["action"]["enum"]:
                logger.warning(f"Invalid action: {decision.get('action')}")
                return None

            # Validate direction
            if decision.get("direction") not in DECISION_SCHEMA["direction"]["enum"]:
                logger.warning(f"Invalid direction: {decision.get('direction')}")
                return None

            # Validate confidence
            confidence = decision.get("confidence", 0.0)
            if not (
                DECISION_SCHEMA["confidence"]["minimum"]
                <= confidence
                <= DECISION_SCHEMA["confidence"]["maximum"]
            ):
                logger.warning(f"Confidence out of range: {confidence}")
                decision["confidence"] = max(
                    DECISION_SCHEMA["confidence"]["minimum"],
                    min(confidence, DECISION_SCHEMA["confidence"]["maximum"]),
                )

            # Validate position size
            position_size = decision.get("position_size_usdt", 0.0)
            if position_size > DECISION_SCHEMA["position_size_usdt"]["maximum"]:
                logger.warning(f"Position size too large: {position_size}, capping to maximum")
                decision["position_size_usdt"] = DECISION_SCHEMA["position_size_usdt"]["maximum"]

            # Validate stop loss
            stop_loss = decision.get("stop_loss_pct", 0.02)
            if not (
                DECISION_SCHEMA["stop_loss_pct"]["minimum"]
                <= stop_loss
                <= DECISION_SCHEMA["stop_loss_pct"]["maximum"]
            ):
                logger.warning(f"Stop loss out of range: {stop_loss}")
                decision["stop_loss_pct"] = max(
                    DECISION_SCHEMA["stop_loss_pct"]["minimum"],
                    min(stop_loss, DECISION_SCHEMA["stop_loss_pct"]["maximum"]),
                )

            # Validate take profit
            take_profit = decision.get("take_profit_pct", 0.05)
            if not (
                DECISION_SCHEMA["take_profit_pct"]["minimum"]
                <= take_profit
                <= DECISION_SCHEMA["take_profit_pct"]["maximum"]
            ):
                logger.warning(f"Take profit out of range: {take_profit}")
                decision["take_profit_pct"] = max(
                    DECISION_SCHEMA["take_profit_pct"]["minimum"],
                    min(take_profit, DECISION_SCHEMA["take_profit_pct"]["maximum"]),
                )

            # Validate leverage
            leverage = decision.get("leverage", 1.0)
            if not (
                DECISION_SCHEMA["leverage"]["minimum"]
                <= leverage
                <= DECISION_SCHEMA["leverage"]["maximum"]
            ):
                logger.warning(f"Leverage out of range: {leverage}")
                decision["leverage"] = max(
                    DECISION_SCHEMA["leverage"]["minimum"],
                    min(leverage, DECISION_SCHEMA["leverage"]["maximum"]),
                )

            # Validate risk assessment
            risk_assessment = decision.get("risk_assessment", "medium")
            if risk_assessment not in DECISION_SCHEMA["risk_assessment"]["enum"]:
                logger.warning(f"Invalid risk assessment: {risk_assessment}, defaulting to medium")
                decision["risk_assessment"] = "medium"

            return decision

        except Exception as e:
            logger.error(f"Error validating decision: {e}")
            return None

    def _cleanup_cache(self):
        """Remove expired and old cache entries to prevent memory leak."""
        now = datetime.now()
        expired_keys = [
            k for k, v in self.decision_cache.items()
            if (now - v["timestamp"]).total_seconds() > self.CACHE_TTL_SECONDS
        ]
        for k in expired_keys:
            del self.decision_cache[k]
        
        # Limit cache size
        if len(self.decision_cache) > self.MAX_CACHE_SIZE:
            # Remove oldest entries
            sorted_items = sorted(
                self.decision_cache.items(),
                key=lambda x: x[1]["timestamp"]
            )
            for k, _ in sorted_items[:len(self.decision_cache) - self.MAX_CACHE_SIZE]:
                del self.decision_cache[k]
    
    def _get_fallback_decision(self, portfolio: Dict, cache_key: str = None) -> Dict:
        """
        Get fallback decision (cached or default).
        
        Returns:
            Fallback decision dictionary
        """
        # Try cache first
        if cache_key and cache_key in self.decision_cache:
            logger.info("Using cached decision as fallback")
            return self.decision_cache[cache_key]["decision"]
        
        if self.cached_decision:
            logger.info("Using previous good decision as fallback")
            return self.cached_decision

        # Default conservative decision
        logger.info("Using default conservative decision as fallback")
        return {
            "action": "hold",
            "direction": "none",
            "confidence": 0.4,
            "position_size_usdt": 0.0,
            "stop_loss_pct": 0.02,
            "take_profit_pct": 0.05,
            "leverage": 1.0,
            "justification": "System error - holding position",
            "risk_assessment": "medium",
            "exit_plan": {"profit_target": 0, "stop_loss": 0},
        }

