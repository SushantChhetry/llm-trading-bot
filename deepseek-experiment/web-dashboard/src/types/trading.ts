export interface Trade {
  id: number;
  timestamp: string;
  symbol: string;
  side: 'buy' | 'sell' | 'short';
  direction?: 'long' | 'short' | 'none';
  price: number;
  quantity: number;
  amount_usdt: number;
  confidence: number;
  mode: 'paper' | 'live';
  leverage?: number;
  trading_fee?: number;
  margin_used?: number;
  llm_prompt?: string;
  llm_raw_response?: string;
  llm_parsed_decision?: Record<string, unknown>;
  llm_reasoning?: string;
  llm_justification?: string;
  llm_risk_assessment?: 'low' | 'medium' | 'high';
  llm_position_size?: number;
  llm_position_size_usdt?: number;
  exit_plan?: {
    profit_target?: number;
    stop_loss?: number;
    invalidation_conditions?: string[];
  };
  profit?: number;
  profit_pct?: number;
}

export interface Portfolio {
  balance: number;
  total_value: number;
  positions_value: number;
  total_return: number;
  total_return_pct: number;
  open_positions: number;
  total_trades: number;
  initial_balance: number;
}

export interface MarketData {
  symbol: string;
  price: number;
  volume: number;
  change_24h: number;
}

export interface LLMDecision {
  action: 'buy' | 'sell' | 'hold';
  confidence: number;
  reasoning: string;
  position_size: number;
  risk_assessment: 'low' | 'medium' | 'high';
}

export interface PnLDataPoint {
  timestamp: string;
  total_value: number;
  total_return: number;
  total_return_pct: number;
  trade_count: number;
}

export interface BotStatus {
  is_running: boolean;
  last_update: string;
  trading_mode: 'paper' | 'live';
  llm_provider: string;
  exchange: string;
  run_interval_seconds: number;
}
