-- Trading Bot Database Schema
-- This script initializes the PostgreSQL database for the trading bot

-- Create tables for trading data
CREATE TABLE IF NOT EXISTS trades (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('buy', 'sell')),
    price DECIMAL(20, 8) NOT NULL,
    quantity DECIMAL(20, 8) NOT NULL,
    amount_usdt DECIMAL(20, 8) NOT NULL,
    confidence DECIMAL(3, 2) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    mode VARCHAR(20) NOT NULL DEFAULT 'paper',
    llm_reasoning TEXT,
    llm_risk_assessment VARCHAR(20),
    llm_position_size DECIMAL(5, 4),
    leverage DECIMAL(5, 2) DEFAULT 1.0,
    fees DECIMAL(20, 8) DEFAULT 0,
    pnl DECIMAL(20, 8) DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create table for portfolio snapshots
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    balance DECIMAL(20, 8) NOT NULL,
    total_value DECIMAL(20, 8) NOT NULL,
    unrealized_pnl DECIMAL(20, 8) DEFAULT 0,
    realized_pnl DECIMAL(20, 8) DEFAULT 0,
    total_fees DECIMAL(20, 8) DEFAULT 0,
    active_positions INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create table for positions
CREATE TABLE IF NOT EXISTS positions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('long', 'short')),
    quantity DECIMAL(20, 8) NOT NULL,
    avg_price DECIMAL(20, 8) NOT NULL,
    current_price DECIMAL(20, 8),
    value DECIMAL(20, 8) NOT NULL,
    unrealized_pnl DECIMAL(20, 8) DEFAULT 0,
    leverage DECIMAL(5, 2) DEFAULT 1.0,
    opened_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create table for behavioral metrics
CREATE TABLE IF NOT EXISTS behavioral_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    bullish_tilt DECIMAL(3, 2) NOT NULL,
    avg_holding_period_hours DECIMAL(8, 2) NOT NULL,
    trade_frequency_per_day DECIMAL(8, 2) NOT NULL,
    avg_position_size DECIMAL(20, 8) NOT NULL,
    avg_confidence DECIMAL(3, 2) NOT NULL,
    exit_plan_tightness DECIMAL(5, 2) NOT NULL,
    active_positions INTEGER NOT NULL,
    fee_impact_percent DECIMAL(5, 2) NOT NULL,
    sharpe_ratio DECIMAL(8, 4),
    max_drawdown DECIMAL(8, 4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create table for bot configuration
CREATE TABLE IF NOT EXISTS bot_config (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) NOT NULL UNIQUE,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_side ON trades(side);
CREATE INDEX IF NOT EXISTS idx_portfolio_timestamp ON portfolio_snapshots(timestamp);
CREATE INDEX IF NOT EXISTS idx_positions_symbol ON positions(symbol);
CREATE INDEX IF NOT EXISTS idx_positions_active ON positions(is_active);
CREATE INDEX IF NOT EXISTS idx_behavioral_timestamp ON behavioral_metrics(timestamp);

-- Insert default configuration
INSERT INTO bot_config (key, value, description) VALUES
('trading_mode', 'paper', 'Trading mode: paper or live'),
('llm_provider', 'mock', 'LLM provider: mock, deepseek, openai, anthropic'),
('max_position_size', '0.1', 'Maximum position size as percentage of balance'),
('max_leverage', '10.0', 'Maximum leverage allowed'),
('stop_loss_percent', '2.0', 'Default stop loss percentage'),
('take_profit_percent', '3.0', 'Default take profit percentage'),
('run_interval_seconds', '300', 'Bot run interval in seconds'),
('initial_balance', '10000.0', 'Initial balance in USDT')
ON CONFLICT (key) DO NOTHING;

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for positions table
CREATE TRIGGER update_positions_updated_at 
    BEFORE UPDATE ON positions 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create a view for recent trading activity
CREATE OR REPLACE VIEW recent_trades AS
SELECT 
    t.*,
    p.balance as portfolio_balance,
    p.total_value as portfolio_value
FROM trades t
LEFT JOIN LATERAL (
    SELECT balance, total_value
    FROM portfolio_snapshots ps
    WHERE ps.timestamp <= t.timestamp
    ORDER BY ps.timestamp DESC
    LIMIT 1
) p ON true
ORDER BY t.timestamp DESC;

-- Create a view for portfolio performance
CREATE OR REPLACE VIEW portfolio_performance AS
SELECT 
    ps.timestamp,
    ps.balance,
    ps.total_value,
    ps.unrealized_pnl,
    ps.realized_pnl,
    ps.total_fees,
    ps.active_positions,
    LAG(ps.total_value) OVER (ORDER BY ps.timestamp) as prev_value,
    CASE 
        WHEN LAG(ps.total_value) OVER (ORDER BY ps.timestamp) IS NOT NULL 
        THEN ((ps.total_value - LAG(ps.total_value) OVER (ORDER BY ps.timestamp)) / LAG(ps.total_value) OVER (ORDER BY ps.timestamp)) * 100
        ELSE 0
    END as daily_return_percent
FROM portfolio_snapshots ps
ORDER BY ps.timestamp DESC;
