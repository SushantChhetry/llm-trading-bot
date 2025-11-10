"""
LLM client module for DeepSeek API integration.

Handles communication with DeepSeek LLM for trading decision generation.
Includes a mock mode for testing without API calls and structured prompt templates.
"""

import json
import logging
import re
from typing import Dict, Optional

import requests

from config import config

from .resilience import (
    CircuitBreakerConfig,
    RetryConfig,
    circuit_breaker,
    fallback,
    retry,
)
from .security import (
    SecurityManager,
    rate_limit,
    validate_trading_inputs,
)

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
        self, provider: str = None, api_key: str = None, api_url: str = None, model: str = None, mock_mode: bool = None
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
            self.mock_mode = self.provider == "mock" or not self.api_key
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

    def _get_regime_guidance_text(
        self, regime: str, volatility_regime: str, trend_strength: float, market_structure: str
    ) -> str:
        """Generate regime-based trading guidance text."""
        if regime in ["trending_bullish", "trending_bearish"]:
            regime_status = "✅ TRENDING MARKET DETECTED"
            strategy_focus = "- Focus on MOMENTUM strategies"
            if trend_strength > 0.7:
                leverage_guidance = "- Consider higher leverage (up to 3x)"
            else:
                leverage_guidance = "- Use moderate leverage (≤2.5x)"
        elif regime in ["mean_reverting", "choppy"]:
            regime_status = "⚠️ MEAN-REVERTING/CHOPPY MARKET"
            strategy_focus = "- Focus on MEAN REVERSION strategies"
            leverage_guidance = "- Use lower leverage (≤2x)"
        else:
            regime_status = "❓ REGIME UNCLEAR"
            strategy_focus = "- Use conservative position sizing"
            leverage_guidance = "- Use moderate leverage (≤2.5x)"

        volatility_text = f"- Volatility is {volatility_regime.upper()}" if volatility_regime else ""

        size_adjustment = ""
        if volatility_regime in ["high", "extreme"]:
            size_adjustment = "- Reduce position sizes by 30-40%"

        structure_text = ""
        if market_structure != "unknown":
            structure_text = f"- Market structure shows {market_structure.replace('_', ' ').upper()}"

        lines = [f"{regime_status}: {regime.upper()}", strategy_focus, leverage_guidance]

        if volatility_text:
            lines.append(volatility_text)
        if size_adjustment:
            lines.append(size_adjustment)
        if structure_text:
            lines.append(structure_text)

        return "\n".join(lines)

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
            price = float(market_data.get("price", 0))
        except (ValueError, TypeError):
            price = 0.0

        try:
            volume = float(market_data.get("volume", 0))
        except (ValueError, TypeError):
            volume = 0.0

        try:
            change_24h = float(market_data.get("change_24h", 0))
        except (ValueError, TypeError):
            change_24h = 0.0

        try:
            balance = float(portfolio_state.get("balance", 0))
        except (ValueError, TypeError):
            balance = 0.0

        try:
            total_value = float(portfolio_state.get("total_value", 0))
        except (ValueError, TypeError):
            total_value = 0.0

        try:
            return_pct = float(portfolio_state.get("total_return_pct", 0))
        except (ValueError, TypeError):
            return_pct = 0.0

        # Extract Sharpe ratio and risk metrics for Alpha Arena style feedback
        sharpe_ratio = portfolio_state.get("sharpe_ratio", 0.0) if portfolio_state else 0.0
        volatility = portfolio_state.get("volatility", 0.0) if portfolio_state else 0.0
        max_drawdown = portfolio_state.get("max_drawdown", 0.0) if portfolio_state else 0.0
        risk_adjusted_return = portfolio_state.get("risk_adjusted_return", 0.0) if portfolio_state else 0.0

        # Extract technical indicators
        indicators = market_data.get("indicators", {}) if market_data else {}
        ema_20 = indicators.get("ema_20", price)
        ema_50 = indicators.get("ema_50", price)
        macd = indicators.get("macd", 0.0)
        macd_signal = indicators.get("macd_signal", 0.0)
        macd_histogram = indicators.get("macd_histogram", 0.0)
        rsi_7 = indicators.get("rsi_7", 50.0)
        rsi_14 = indicators.get("rsi_14", 50.0)
        atr = indicators.get("atr", 0.0)

        # Extract regime information (if available)
        regime = indicators.get("regime", "unknown")
        volatility_regime = indicators.get("volatility_regime", "medium")
        regime_confidence = indicators.get("regime_confidence", 0.0)
        adx = indicators.get("adx", 0.0)
        trend_strength = indicators.get("trend_strength", 0.0)
        momentum = indicators.get("momentum", 0.0)
        market_structure = indicators.get("market_structure", "unknown")

        prompt = f"""
You are a quantitative cryptocurrency trader in the Alpha Arena competition.
Your goal is to maximize PnL through systematic analysis of numerical data only.
You have $10,000 to trade perpetual futures with leverage.

IMPORTANT: Read all data carefully.
Market data is presented in chronological order (oldest to newest).
Account state shows current values.

MARKET DATA (Quantitative Only - Chronological Order):
- Symbol: {market_data.get('symbol', 'N/A') if market_data else 'N/A'}
- Current Price: ${price:.2f} (LATEST PRICE)
- 24h Volume: {volume:,.0f}
- 24h Change: {change_24h:.2f}% (from 24 hours ago to now)

TECHNICAL INDICATORS (Time-Series Analysis - 5m candles):
- EMA 20: ${ema_20:.2f} (20-period Exponential Moving Average)
- EMA 50: ${ema_50:.2f} (50-period Exponential Moving Average)
- MACD: {macd:.4f} (MACD line)
- MACD Signal: {macd_signal:.4f} (Signal line)
- MACD Histogram: {macd_histogram:.4f} (MACD - Signal, positive = bullish momentum)
- RSI 7: {rsi_7:.2f} (7-period Relative Strength Index, >70 = overbought, <30 = oversold)
- RSI 14: {rsi_14:.2f} (14-period Relative Strength Index, >70 = overbought, <30 = oversold)
- ATR: ${atr:.2f} (14-period Average True Range - volatility measure)

MARKET REGIME DETECTION (Adaptive Strategy Selection):
- Current Regime: {regime} (trending_bullish/trending_bearish/mean_reverting/choppy)
- Volatility Regime: {volatility_regime} (low/medium/high/extreme)
- Regime Confidence: {regime_confidence:.2f} (0.0-1.0, higher = more confident in regime)
- ADX: {adx:.2f} (Average Directional Index, >25 = strong trend)
- Trend Strength: {trend_strength:.2f} (0.0-1.0, higher = stronger trend)
- Price Momentum: {momentum:.2f}% (recent price change)
- Market Structure: {market_structure} (higher_highs/lower_lows/choppy)

REGIME-BASED TRADING GUIDANCE:
{self._get_regime_guidance_text(regime, volatility_regime, trend_strength, market_structure)}

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

REQUIRED RESPONSE FORMAT (Valid JSON only - no markdown, no code blocks):

You MUST respond with ONLY valid JSON.
Do NOT wrap it in markdown code blocks (no ```json or ```).
Do NOT add any explanatory text before or after the JSON.
All keys MUST be in double quotes.

Format:
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

CRITICAL: Respond with ONLY the raw JSON object above.
Start with {{ and end with }}.
All property names must be in double quotes (e.g., "action" not action).
No markdown formatting, no code blocks, no extra text.
"""
        return prompt.strip()

    def _extract_json_from_text(self, text: str) -> Optional[str]:
        """
        Extract JSON object from text, handling markdown code blocks and nested braces.

        Args:
            text: Text that may contain JSON

        Returns:
            Extracted JSON string, or None if not found
        """
        # Clean up the text
        cleaned = text.strip()

        # Remove markdown code blocks if present
        # Match ```json ... ``` or ``` ... ```
        code_block_pattern = r"```(?:json)?\s*\n?(.*?)\n?```"
        code_block_match = re.search(code_block_pattern, cleaned, re.DOTALL)
        if code_block_match:
            cleaned = code_block_match.group(1).strip()

        # Find the first { and then find the matching }
        start_idx = cleaned.find("{")
        if start_idx == -1:
            return None

        # Count braces to find the matching closing brace
        brace_count = 0
        in_string = False
        escape_next = False

        for i in range(start_idx, len(cleaned)):
            char = cleaned[i]

            if escape_next:
                escape_next = False
                continue

            if char == "\\":
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if not in_string:
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        # Found the matching closing brace
                        json_str = cleaned[start_idx : i + 1]
                        return json_str

        return None

    def _fix_json_keys(self, json_str: str) -> str:
        """
        Fix unquoted keys in JSON (JavaScript-style to JSON).

        Args:
            json_str: JSON string with potential unquoted keys

        Returns:
            JSON string with quoted keys
        """

        # Use regex to find and quote unquoted keys
        # Pattern matches: ({ or ,) whitespace? identifier whitespace? :
        # This handles the common case of unquoted keys
        def quote_key(match):
            prefix = match.group(1)  # { or ,
            whitespace1 = match.group(2) or ""  # optional whitespace
            key = match.group(3)  # the key name (identifier)
            whitespace2 = match.group(4) or ""  # optional whitespace before :
            return f'{prefix}{whitespace1}"{key}"{whitespace2}:'

        # Match unquoted keys that appear after { or ,
        # Pattern breakdown:
        # ([{,]) - matches { or ,
        # (\s*) - optional whitespace
        # ([a-zA-Z_][a-zA-Z0-9_]*) - identifier (word starting with letter/underscore)
        # (\s*) - optional whitespace before colon
        # : - colon
        json_str = re.sub(r"([{,])(\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*):", quote_key, json_str)
        return json_str

    def _fix_json_string_values(self, json_str: str) -> str:
        """
        Fix unquoted string values in JSON.

        Args:
            json_str: JSON string with potential unquoted string values

        Returns:
            JSON string with quoted string values
        """
        # Use a regex-based approach to find and quote unquoted string values
        # Pattern: : whitespace? value whitespace? (, or } or \n)
        # We'll match values that are likely strings (not numbers, booleans, null, objects, arrays)

        def quote_string_value(match):
            colon_ws = match.group(1)  # colon and optional whitespace
            value = match.group(2)  # the value (may contain spaces/newlines)
            ws_comma = match.group(3)  # whitespace and comma/brace/newline

            value = value.strip()

            # Don't quote if it's already quoted, numeric, boolean, null, or starts with { or [
            if self._is_numeric_or_constant(value) or value.startswith(("{", "[")):
                return f"{colon_ws}{value}{ws_comma}"

            # Quote the string value
            # Escape any quotes in the value
            escaped_value = value.replace("\\", "\\\\").replace('"', '\\"')
            return f'{colon_ws}"{escaped_value}"{ws_comma}'

        # Pattern explanation:
        # (:\s*) - colon followed by optional whitespace
        # ([^,}\n\[\{]+?) - non-greedy match of value (anything except comma, closing brace, newline, [ or {)
        # (\s*[,}\n]) - whitespace followed by comma, closing brace, or newline
        #
        # This will match simple unquoted values but skip over nested objects/arrays
        # For multi-line values, we need a more sophisticated approach

        # First pass: handle simple single-line values
        # Match: : whitespace? unquoted-value whitespace? (comma|brace|newline)
        pattern = r"(:\s*)([^,}\n\[\{]+?)(\s*[,}\n])"

        # But we need to be careful - this might match parts of nested structures
        # So we'll use a more careful state-based replacement

        result = []
        i = 0
        in_string = False
        escape_next = False
        brace_depth = 0

        while i < len(json_str):
            char = json_str[i]

            if escape_next:
                result.append(char)
                escape_next = False
                i += 1
                continue

            if char == "\\":
                result.append(char)
                escape_next = True
                i += 1
                continue

            if char == '"':
                in_string = not in_string
                result.append(char)
                i += 1
                continue

            if in_string:
                result.append(char)
                i += 1
                continue

            if char == "{":
                brace_depth += 1
                result.append(char)
                i += 1
                continue
            elif char == "}":
                brace_depth -= 1
                result.append(char)
                i += 1
                continue

            # Look for : followed by an unquoted value
            if char == ":" and brace_depth > 0:
                result.append(char)
                i += 1

                # Skip whitespace
                while i < len(json_str) and json_str[i] in " \t":
                    result.append(json_str[i])
                    i += 1

                if i >= len(json_str):
                    break

                # Check if value is already quoted
                if json_str[i] == '"':
                    # Already quoted - just copy until closing quote
                    result.append('"')
                    i += 1
                    escape_next_quote = False
                    while i < len(json_str):
                        ch = json_str[i]
                        if escape_next_quote:
                            escape_next_quote = False
                            result.append(ch)
                            i += 1
                            continue
                        if ch == "\\":
                            escape_next_quote = True
                            result.append(ch)
                            i += 1
                            continue
                        result.append(ch)
                        if ch == '"':
                            i += 1
                            break
                        i += 1
                    continue

                # Check if it's a nested object/array
                if json_str[i] in "{[":
                    # Skip nested structure
                    start = i
                    i = self._skip_nested(json_str, i)
                    result.append(json_str[start:i])
                    continue

                # Extract the value - need to be smarter about where it ends
                # Values end at: comma before next key, closing brace, or newline before next key
                value_start = i
                value_end = i

                # Look ahead to find the end of the value
                # For simple values (numbers, booleans, null), they end at comma, brace, or newline
                # For string-like values, they may contain commas, so we need to look for the pattern:
                # value, whitespace? newline? whitespace? key:
                # or value} (end of object)

                # First, check if it's a nested structure
                if json_str[i] in "{[":
                    start = i
                    i = self._skip_nested(json_str, i)
                    result.append(json_str[start:i])
                    continue

                # For other values, scan forward looking for the end
                # Stop at: comma followed by key-like pattern, closing brace, or newline followed by key
                while value_end < len(json_str):
                    ch = json_str[value_end]

                    # If we hit a closing brace, that's definitely the end
                    if ch == "}":
                        break

                    # If we hit a comma, check if it's followed by a key (indicating next key-value pair)
                    if ch == ",":
                        # Look ahead past whitespace to see if there's a key
                        lookahead = value_end + 1
                        while lookahead < len(json_str) and json_str[lookahead] in " \t\n\r":
                            lookahead += 1
                        if lookahead < len(json_str):
                            next_char = json_str[lookahead]
                            # Keys may be quoted (") or unquoted (letter/underscore)
                            # If next char is a quote, letter/underscore (start of key), or closing brace, this comma ends the value
                            if next_char == '"' or next_char.isalpha() or next_char == "_" or next_char == "}":
                                # value_end points to comma, value is everything before it
                                break

                    # If we hit a newline, check if next non-whitespace looks like a key
                    if ch == "\n":
                        # Look ahead past whitespace to see if there's a key
                        lookahead = value_end + 1
                        while lookahead < len(json_str) and json_str[lookahead] in " \t":
                            lookahead += 1
                        if lookahead < len(json_str):
                            next_char = json_str[lookahead]
                            # Keys may be quoted (") or unquoted (letter/underscore)
                            # If next char is a quote, letter/underscore (start of key), or closing brace, newline ends the value
                            if next_char == '"' or next_char.isalpha() or next_char == "_" or next_char == "}":
                                break

                    # If we hit a nested structure, handle it separately
                    if ch in "{[":
                        # Include the nested structure as part of the value
                        value_end = self._skip_nested(json_str, value_end)
                        break

                    value_end += 1

                # value_end now points to the character that ends the value (comma, brace, newline, or end of nested)
                # The value itself is everything from value_start to value_end (not including the ending character)

                value = json_str[value_start:value_end].rstrip()

                # Check if there's a comma after the value (separator before next key-value pair)
                has_comma = value_end < len(json_str) and json_str[value_end] == ","

                # Check if this needs quoting
                if value and not self._is_numeric_or_constant(value) and not value.startswith(("{", "[")):
                    # Quote it and escape special characters
                    escaped_value = (
                        value.replace("\\", "\\\\")  # Escape backslashes first
                        .replace('"', '\\"')  # Escape quotes
                        .replace("\n", "\\n")  # Escape newlines
                        .replace("\r", "\\r")  # Escape carriage returns
                        .replace("\t", "\\t")  # Escape tabs
                    )
                    result.append('"')
                    result.append(escaped_value)
                    result.append('"')
                else:
                    # Keep as-is (number, boolean, null, or nested structure)
                    result.append(value)

                # Add comma if it was there (separator between key-value pairs)
                if has_comma:
                    result.append(",")
                    value_end += 1

                i = value_end
                continue

            result.append(char)
            i += 1

        return "".join(result)

    def _skip_nested(self, json_str: str, start_pos: int) -> int:
        """Skip nested object or array, returning position after it."""
        pos = start_pos
        char = json_str[pos]

        if char == "{":
            depth = 1
            pos += 1
            in_string = False
            escape_next = False

            while pos < len(json_str) and depth > 0:
                ch = json_str[pos]
                if escape_next:
                    escape_next = False
                    pos += 1
                    continue
                if ch == "\\":
                    escape_next = True
                    pos += 1
                    continue
                if ch == '"':
                    in_string = not in_string
                    pos += 1
                    continue
                if not in_string:
                    if ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                pos += 1
            return pos
        elif char == "[":
            depth = 1
            pos += 1
            in_string = False
            escape_next = False

            while pos < len(json_str) and depth > 0:
                ch = json_str[pos]
                if escape_next:
                    escape_next = False
                    pos += 1
                    continue
                if ch == "\\":
                    escape_next = True
                    pos += 1
                    continue
                if ch == '"':
                    in_string = not in_string
                    pos += 1
                    continue
                if not in_string:
                    if ch == "[":
                        depth += 1
                    elif ch == "]":
                        depth -= 1
                pos += 1
            return pos

        return pos

    def _is_numeric_or_constant(self, value: str) -> bool:
        """Check if value is a number, boolean, or null (shouldn't be quoted)."""
        value = value.strip()
        if not value:
            return True  # Empty is safe

        # Check for boolean/null
        if value.lower() in ("true", "false", "null"):
            return True

        # Check for number (including negative, decimal, scientific notation)
        try:
            float(value)
            return True
        except ValueError:
            pass

        # Check if it's already quoted
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            return True

        return False

    def _validate_llm_response(self, response_text: str) -> Optional[Dict]:
        """
        Validate and parse LLM response JSON.

        Handles:
        - Markdown code blocks (```json ... ```)
        - Multiline JSON
        - Unquoted keys (JavaScript-style JSON)
        - Unquoted string values (e.g., action: hold instead of "action": "hold")

        Args:
            response_text: Raw response text from LLM

        Returns:
            Parsed and validated response dict, or None if invalid
        """
        logger.debug(f"JSON_PARSE_START response_length={len(response_text)}")

        # First, try parsing directly
        try:
            response = json.loads(response_text.strip())
            logger.debug(f"JSON_PARSE_SUCCESS method=direct")
            return self._validate_response_structure(response)
        except json.JSONDecodeError as e:
            logger.debug(f"JSON_PARSE_FAILED method=direct error={str(e)}")

        # Extract JSON from text
        json_str = self._extract_json_from_text(response_text)

        if json_str:
            logger.debug(f"JSON_EXTRACTION_SUCCESS extracted_length={len(json_str)}")
            # Try to fix unquoted keys first
            json_str = self._fix_json_keys(json_str)
            # Then fix unquoted string values
            json_str = self._fix_json_string_values(json_str)
            logger.debug(f"JSON_FIXES_APPLIED")

            try:
                response = json.loads(json_str)
                logger.debug(f"JSON_PARSE_SUCCESS method=extracted_and_fixed")
                return self._validate_response_structure(response)
            except json.JSONDecodeError as e:
                logger.error(
                    f"JSON_PARSE_FAILED method=extracted_and_fixed "
                    f"error_type={type(e).__name__} error={str(e)} "
                    f"extracted_preview={json_str[:200]}"
                )

        logger.error(
            f"JSON_PARSE_FAILED reason=no_valid_json_found "
            f"response_length={len(response_text)} response_preview={response_text[:200]}"
        )
        return None

    def _validate_response_structure(self, response: Dict) -> Optional[Dict]:
        """
        Validate and normalize the response structure.

        Args:
            response: Parsed JSON response

        Returns:
            Validated and normalized response dict, or None if invalid
        """
        logger.debug(f"RESPONSE_STRUCTURE_VALIDATION_START response_keys={list(response.keys())}")

        # Use security manager for validation
        if not self.security_manager.validate_trading_decision(response):
            logger.error(
                f"SECURITY_VALIDATION_FAILED response={response} "
                f"possible_causes=invalid_action_or_confidence_or_leverage_or_position_size"
            )
            return None
        logger.debug(f"SECURITY_VALIDATION_SUCCESS")

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
            "invalidation_conditions": exit_plan.get("invalidation_conditions", []),
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
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a cryptocurrency trading assistant. "
                        "Always respond with valid JSON in the exact format requested."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 500,
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=30)

            # Handle specific HTTP errors
            if response.status_code == 402:
                error_msg = (
                    "💳 DeepSeek API payment required (402). "
                    "Your DeepSeek account needs payment to use the API. "
                    "Options: 1) Add payment to DeepSeek account, 2) Switch to LLM_PROVIDER=mock for testing"
                )
                logger.error(error_msg)
                raise ValueError(error_msg)

            if response.status_code == 401:
                error_msg = (
                    "🔑 DeepSeek API authentication failed (401). "
                    "Check your LLM_API_KEY is correct and has proper permissions."
                )
                logger.error(error_msg)
                raise ValueError(error_msg)

            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"DeepSeek API HTTP error: {e}")
            raise
        except ValueError:
            # Re-raise our custom error messages
            raise
        except Exception:
            logger.error("DeepSeek API request failed")
            raise

    def _make_openai_request(self, prompt: str) -> Dict:
        """Make API request to OpenAI."""
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a cryptocurrency trading assistant. "
                        "Always respond with valid JSON in the exact format requested."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 500,
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
            "anthropic-version": "2023-06-01",
        }

        payload = {
            "model": self.model,
            "max_tokens": 500,
            "temperature": 0.7,
            "system": (
                "You are a cryptocurrency trading assistant. "
                "Always respond with valid JSON in the exact format requested."
            ),
            "messages": [{"role": "user", "content": prompt}],
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
        price = market_data.get("price", 50000)
        change_24h = market_data.get("change_24h", 0)
        balance = portfolio_state.get("balance", 10000)
        open_positions = portfolio_state.get("open_positions", 0)

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
                "profit_target": (
                    round(price * 0.02, 2) if action == "buy" else round(price * 0.02, 2) if action == "sell" else 0.0
                ),
                "stop_loss": round(price * 0.01, 2) if action in ["buy", "sell"] else 0.0,
                "invalidation_conditions": (
                    ["market_volatility_spike", "unexpected_news"] if action in ["buy", "sell"] else []
                ),
            },
            "position_size_usdt": round(position_size_usdt, 2),
            "risk_assessment": random.choice(["low", "medium", "high"]),
        }

        return {"choices": [{"message": {"content": json.dumps(mock_decision)}}]}

    @validate_trading_inputs
    @fallback(
        lambda: {"action": "hold", "direction": "none", "confidence": 0.0, "justification": "Fallback due to error"}
    )
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
                "total_trades": 0,
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
                    error_str = str(api_error)
                    # Check for payment-related errors
                    if "402" in error_str or "Payment Required" in error_str or "payment required" in error_str.lower():
                        error_msg = (
                            "💳 DeepSeek API payment required. "
                            "The bot will continue in mock mode until payment is added. "
                            "To fix: 1) Add payment to your DeepSeek account at "
                            "https://platform.deepseek.com, "
                            "or 2) Set LLM_PROVIDER=mock in Railway environment variables "
                            "for testing."
                        )
                        logger.error(error_msg)
                    elif "401" in error_str or "authentication failed" in error_str.lower():
                        error_msg = (
                            "🔑 DeepSeek API authentication failed. "
                            "The bot will continue in mock mode. "
                            "To fix: Verify your LLM_API_KEY is correct in Railway "
                            "environment variables."
                        )
                        logger.error(error_msg)
                    else:
                        logger.error(f"API call failed: {api_error}")
                    logger.warning("🔄 Falling back to mock mode for this cycle")
                    response = self._get_mock_response(market_data, portfolio_state)

            # Extract content from response based on provider
            raw_response_content = self._extract_response_content(response)
            logger.debug(f"Raw LLM response: {raw_response_content}")

            # Validate and parse response
            logger.debug(f"LLM_RESPONSE_VALIDATION_START response_length={len(raw_response_content)}")
            decision = self._validate_llm_response(raw_response_content)

            if decision is None:
                logger.error(
                    f"LLM_RESPONSE_VALIDATION_FAILED reason=invalid_response "
                    f"response_length={len(raw_response_content)} "
                    f"response_preview={raw_response_content[:200]} "
                    f"fallback_action=hold"
                )
                fallback_decision = {
                    "action": "hold",
                    "direction": "none",
                    "quantity": 0.0,
                    "leverage": 1.0,
                    "confidence": 0.0,
                    "justification": "Invalid LLM response format",
                    "exit_plan": {"profit_target": 0.0, "stop_loss": 0.0, "invalidation_conditions": []},
                    "position_size_usdt": 0.0,
                    "risk_assessment": "high",
                    "_prompt": prompt,
                    "_raw_response": raw_response_content,
                }
                return fallback_decision

            logger.info(
                f"LLM_DECISION_VALIDATED action={decision['action']} "
                f"direction={decision.get('direction', 'none')} "
                f"confidence={decision['confidence']:.2f} "
                f"position_size_usdt={decision.get('position_size_usdt', 0.0):.2f} "
                f"leverage={decision.get('leverage', 1.0):.1f} "
                f"risk_assessment={decision.get('risk_assessment', 'medium')}"
            )
            exit_plan = decision.get("exit_plan", {})
            if exit_plan:
                logger.debug(
                    f"LLM_EXIT_PLAN profit_target={exit_plan.get('profit_target', 0.0):.2f} "
                    f"stop_loss={exit_plan.get('stop_loss', 0.0):.2f}"
                )

            # Attach prompt and raw response for storage
            decision["_prompt"] = prompt
            decision["_raw_response"] = raw_response_content

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
                "exit_plan": {"profit_target": 0.0, "stop_loss": 0.0, "invalidation_conditions": []},
                "position_size_usdt": 0.0,
                "risk_assessment": "high",
                "_prompt": prompt if "prompt" in locals() else "",
                "_raw_response": "",
            }
