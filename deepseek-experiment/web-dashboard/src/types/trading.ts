export interface Trade {
  id: number;
  timestamp: string;
  symbol: string;
  side: 'buy' | 'sell';
  price: number;
  quantity: number;
  amount_usdt: number;
  confidence: number;
  mode: 'paper' | 'live';
  llm_reasoning: string;
  llm_risk_assessment: 'low' | 'medium' | 'high';
  llm_position_size: number;
  profit?: number;
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
