-- Migration: Add LLM prompt/response storage and enhance portfolio metrics
-- Run this in your Supabase SQL editor after the base schema

-- Add LLM storage fields to trades table
ALTER TABLE trades
ADD COLUMN IF NOT EXISTS llm_prompt TEXT,
ADD COLUMN IF NOT EXISTS llm_raw_response TEXT,
ADD COLUMN IF NOT EXISTS llm_parsed_decision JSONB,
ADD COLUMN IF NOT EXISTS direction VARCHAR(10) CHECK (direction IN ('long', 'short', 'none')),
ADD COLUMN IF NOT EXISTS trading_fee DECIMAL(20, 8) DEFAULT 0,
ADD COLUMN IF NOT EXISTS margin_used DECIMAL(20, 8) DEFAULT 0,
ADD COLUMN IF NOT EXISTS exit_plan JSONB;

-- Standardize field name: support both llm_reasoning (old) and llm_justification (new)
ALTER TABLE trades
ADD COLUMN IF NOT EXISTS llm_justification TEXT;

-- Update portfolio_snapshots to include all advanced metrics
ALTER TABLE portfolio_snapshots
ADD COLUMN IF NOT EXISTS positions_value DECIMAL(20, 8) DEFAULT 0,
ADD COLUMN IF NOT EXISTS initial_balance DECIMAL(20, 8) DEFAULT 10000,
ADD COLUMN IF NOT EXISTS total_return DECIMAL(20, 8) DEFAULT 0,
ADD COLUMN IF NOT EXISTS total_return_pct DECIMAL(10, 4) DEFAULT 0,
ADD COLUMN IF NOT EXISTS total_trades INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS sharpe_ratio DECIMAL(8, 4),
ADD COLUMN IF NOT EXISTS volatility DECIMAL(10, 4),
ADD COLUMN IF NOT EXISTS max_drawdown DECIMAL(20, 8),
ADD COLUMN IF NOT EXISTS win_rate DECIMAL(5, 2),
ADD COLUMN IF NOT EXISTS profit_factor DECIMAL(8, 4),
ADD COLUMN IF NOT EXISTS risk_adjusted_return DECIMAL(10, 4),
ADD COLUMN IF NOT EXISTS excess_return DECIMAL(10, 4);

-- Enhance behavioral_metrics to include all calculated fields
ALTER TABLE behavioral_metrics
ADD COLUMN IF NOT EXISTS volatility DECIMAL(10, 4),
ADD COLUMN IF NOT EXISTS win_rate DECIMAL(5, 2),
ADD COLUMN IF NOT EXISTS profit_factor DECIMAL(8, 4),
ADD COLUMN IF NOT EXISTS risk_adjusted_return DECIMAL(10, 4),
ADD COLUMN IF NOT EXISTS excess_return DECIMAL(10, 4),
ADD COLUMN IF NOT EXISTS total_trading_fees DECIMAL(20, 8) DEFAULT 0;

-- Create index on LLM fields for querying
CREATE INDEX IF NOT EXISTS idx_trades_confidence ON trades(confidence);
CREATE INDEX IF NOT EXISTS idx_trades_llm_fields ON trades USING gin(llm_parsed_decision);

-- Add comment for documentation
COMMENT ON COLUMN trades.llm_prompt IS 'Full prompt sent to LLM for this trade decision';
COMMENT ON COLUMN trades.llm_raw_response IS 'Raw JSON response from LLM before parsing';
COMMENT ON COLUMN trades.llm_parsed_decision IS 'Parsed and validated LLM decision as JSONB';
COMMENT ON COLUMN trades.llm_justification IS 'AI reasoning/justification for the trade';
COMMENT ON COLUMN portfolio_snapshots.sharpe_ratio IS 'Risk-adjusted return metric';
COMMENT ON COLUMN portfolio_snapshots.volatility IS 'Standard deviation of returns';
