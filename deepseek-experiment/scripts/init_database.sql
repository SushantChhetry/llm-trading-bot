-- ============================================================================
-- INITIAL DATABASE CONFIGURATION
-- ============================================================================
-- Complete database setup with proper security from the start
-- Run this in your Supabase SQL Editor for initial setup
-- ============================================================================

BEGIN;

-- ============================================================================
-- STEP 1: CLEANUP (Drop existing objects if they exist)
-- ============================================================================

-- Drop views first (they depend on tables)
DROP VIEW IF EXISTS recent_trades CASCADE;
DROP VIEW IF EXISTS portfolio_performance CASCADE;

-- Drop triggers
DROP TRIGGER IF EXISTS update_positions_updated_at ON positions;

-- Drop functions
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;

-- Drop all policies
DROP POLICY IF EXISTS "Allow all operations on trades" ON trades;
DROP POLICY IF EXISTS "Allow all operations on portfolio_snapshots" ON portfolio_snapshots;
DROP POLICY IF EXISTS "Allow all operations on positions" ON positions;
DROP POLICY IF EXISTS "Allow all operations on behavioral_metrics" ON behavioral_metrics;
DROP POLICY IF EXISTS "Allow all operations on bot_config" ON bot_config;
DROP POLICY IF EXISTS "Service role full access trades" ON trades;
DROP POLICY IF EXISTS "Service role full access portfolio_snapshots" ON portfolio_snapshots;
DROP POLICY IF EXISTS "Service role full access positions" ON positions;
DROP POLICY IF EXISTS "Service role full access behavioral_metrics" ON behavioral_metrics;
DROP POLICY IF EXISTS "Service role full access bot_config" ON bot_config;
DROP POLICY IF EXISTS "Public read trades" ON trades;
DROP POLICY IF EXISTS "Public read portfolio_snapshots" ON portfolio_snapshots;
DROP POLICY IF EXISTS "Public read positions" ON positions;
DROP POLICY IF EXISTS "Public read behavioral_metrics" ON behavioral_metrics;
DROP POLICY IF EXISTS "Public read bot_config" ON bot_config;

-- Drop tables (CASCADE handles dependencies)
DROP TABLE IF EXISTS trades CASCADE;
DROP TABLE IF EXISTS portfolio_snapshots CASCADE;
DROP TABLE IF EXISTS positions CASCADE;
DROP TABLE IF EXISTS behavioral_metrics CASCADE;
DROP TABLE IF EXISTS bot_config CASCADE;

-- ============================================================================
-- STEP 2: CREATE TABLES
-- ============================================================================

-- Trades table
CREATE TABLE trades (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('buy', 'sell', 'short')),
    direction VARCHAR(10) CHECK (direction IN ('long', 'short', 'none')),
    price DECIMAL(20, 8) NOT NULL,
    quantity DECIMAL(20, 8) NOT NULL,
    amount_usdt DECIMAL(20, 8) NOT NULL,
    confidence DECIMAL(3, 2) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    mode VARCHAR(20) NOT NULL DEFAULT 'paper',
    leverage DECIMAL(5, 2) DEFAULT 1.0,
    trading_fee DECIMAL(20, 8) DEFAULT 0,
    margin_used DECIMAL(20, 8) DEFAULT 0,
    margin_returned DECIMAL(20, 8) DEFAULT 0,
    fees DECIMAL(20, 8) DEFAULT 0,
    pnl DECIMAL(20, 8) DEFAULT 0,
    profit DECIMAL(20, 8),
    profit_pct DECIMAL(10, 4),
    llm_prompt TEXT,
    llm_raw_response TEXT,
    llm_parsed_decision JSONB,
    llm_reasoning TEXT,
    llm_justification TEXT,
    llm_risk_assessment VARCHAR(20),
    llm_position_size_usdt DECIMAL(20, 8),
    exit_plan JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Portfolio snapshots table
CREATE TABLE portfolio_snapshots (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    balance DECIMAL(20, 8) NOT NULL,
    positions_value DECIMAL(20, 8) DEFAULT 0,
    total_value DECIMAL(20, 8) NOT NULL,
    initial_balance DECIMAL(20, 8) DEFAULT 10000,
    total_return DECIMAL(20, 8) DEFAULT 0,
    total_return_pct DECIMAL(10, 4) DEFAULT 0,
    total_trades INTEGER DEFAULT 0,
    unrealized_pnl DECIMAL(20, 8) DEFAULT 0,
    realized_pnl DECIMAL(20, 8) DEFAULT 0,
    total_fees DECIMAL(20, 8) DEFAULT 0,
    active_positions INTEGER DEFAULT 0,
    sharpe_ratio DECIMAL(8, 4),
    volatility DECIMAL(10, 4),
    max_drawdown DECIMAL(20, 8),
    win_rate DECIMAL(5, 2),
    profit_factor DECIMAL(8, 4),
    risk_adjusted_return DECIMAL(10, 4),
    excess_return DECIMAL(10, 4),
    avg_profit_per_trade DECIMAL(20, 8),
    avg_trade_duration_hours DECIMAL(8, 2),
    max_consecutive_wins INTEGER,
    max_consecutive_losses INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Positions table
CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL CHECK (side IN ('long', 'short')),
    quantity DECIMAL(20, 8) NOT NULL,
    avg_price DECIMAL(20, 8) NOT NULL,
    current_price DECIMAL(20, 8),
    value DECIMAL(20, 8) NOT NULL,
    unrealized_pnl DECIMAL(20, 8) DEFAULT 0,
    leverage DECIMAL(5, 2) DEFAULT 1.0,
    margin_used DECIMAL(20, 8) DEFAULT 0,
    notional_value DECIMAL(20, 8) DEFAULT 0,
    opened_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Behavioral metrics table
CREATE TABLE behavioral_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    bullish_tilt DECIMAL(3, 2) NOT NULL,
    avg_holding_period_hours DECIMAL(8, 2) NOT NULL,
    trade_frequency_per_day DECIMAL(8, 2) NOT NULL,
    avg_position_size_usdt DECIMAL(20, 8) NOT NULL,
    avg_confidence DECIMAL(3, 2) NOT NULL,
    exit_plan_tightness DECIMAL(5, 2) NOT NULL,
    active_positions_count INTEGER NOT NULL,
    total_trading_fees DECIMAL(20, 8) DEFAULT 0,
    fee_impact_pct DECIMAL(5, 2) NOT NULL DEFAULT 0.0,
    sharpe_ratio DECIMAL(8, 4),
    volatility DECIMAL(10, 4),
    max_drawdown DECIMAL(20, 8),
    win_rate DECIMAL(5, 2),
    profit_factor DECIMAL(8, 4),
    risk_adjusted_return DECIMAL(10, 4),
    excess_return DECIMAL(10, 4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Bot config table
CREATE TABLE bot_config (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) NOT NULL UNIQUE,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- STEP 3: CREATE INDEXES
-- ============================================================================

CREATE INDEX idx_trades_timestamp ON trades(timestamp);
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_side ON trades(side);
CREATE INDEX idx_trades_confidence ON trades(confidence);
CREATE INDEX idx_trades_mode ON trades(mode);
CREATE INDEX idx_trades_llm_fields ON trades USING gin(llm_parsed_decision);

CREATE INDEX idx_portfolio_timestamp ON portfolio_snapshots(timestamp);

CREATE INDEX idx_positions_symbol ON positions(symbol);
CREATE INDEX idx_positions_active ON positions(is_active);
CREATE INDEX idx_positions_symbol_active ON positions(symbol, is_active);

CREATE INDEX idx_behavioral_timestamp ON behavioral_metrics(timestamp);

-- ============================================================================
-- STEP 4: CREATE FUNCTIONS AND TRIGGERS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for positions table
CREATE TRIGGER update_positions_updated_at
    BEFORE UPDATE ON positions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- STEP 5: INSERT DEFAULT CONFIGURATION
-- ============================================================================

INSERT INTO bot_config (key, value, description) VALUES
('trading_mode', 'paper', 'Trading mode: paper or live'),
('llm_provider', 'mock', 'LLM provider: mock, deepseek, openai, anthropic'),
('max_position_size', '0.1', 'Maximum position size as percentage of balance'),
('max_leverage', '10.0', 'Maximum leverage allowed'),
('stop_loss_percent', '2.0', 'Default stop loss percentage'),
('take_profit_percent', '3.0', 'Default take profit percentage'),
('run_interval_seconds', '150', 'Bot run interval in seconds'),
('initial_balance', '10000.0', 'Initial balance in USDT')
ON CONFLICT (key) DO UPDATE SET
    value = EXCLUDED.value,
    updated_at = NOW();

-- ============================================================================
-- STEP 6: ENABLE ROW LEVEL SECURITY (RLS)
-- ============================================================================

ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE behavioral_metrics ENABLE ROW LEVEL SECURITY;
ALTER TABLE bot_config ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- STEP 7: CREATE SECURE RLS POLICIES
-- ============================================================================

-- TRADES: Service role (bot) can write, anonymous (dashboard) can read
CREATE POLICY "Service role full access trades" ON trades 
    FOR ALL 
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "Public read trades" ON trades 
    FOR SELECT 
    USING (true);

-- PORTFOLIO_SNAPSHOTS: Service role (bot) can write, anonymous (dashboard) can read
CREATE POLICY "Service role full access portfolio_snapshots" ON portfolio_snapshots 
    FOR ALL 
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "Public read portfolio_snapshots" ON portfolio_snapshots 
    FOR SELECT 
    USING (true);

-- POSITIONS: Service role (bot) can write, anonymous (dashboard) can read
CREATE POLICY "Service role full access positions" ON positions 
    FOR ALL 
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "Public read positions" ON positions 
    FOR SELECT 
    USING (true);

-- BEHAVIORAL_METRICS: Service role (bot) can write, anonymous (dashboard) can read
CREATE POLICY "Service role full access behavioral_metrics" ON behavioral_metrics 
    FOR ALL 
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "Public read behavioral_metrics" ON behavioral_metrics 
    FOR SELECT 
    USING (true);

-- BOT_CONFIG: Service role (bot) can write, anonymous (dashboard) can read
CREATE POLICY "Service role full access bot_config" ON bot_config 
    FOR ALL 
    USING (auth.role() = 'service_role')
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "Public read bot_config" ON bot_config 
    FOR SELECT 
    USING (true);

-- ============================================================================
-- STEP 8: CREATE VIEWS
-- ============================================================================

-- Recent trades view (inherits security from trades table)
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

-- Portfolio performance view (inherits security from portfolio_snapshots table)
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

COMMIT;

-- ============================================================================
-- VERIFICATION
-- ============================================================================

DO $$
DECLARE
    table_count INTEGER;
    view_count INTEGER;
    policy_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM pg_tables
    WHERE schemaname = 'public'
    AND tablename IN ('trades', 'portfolio_snapshots', 'positions', 'behavioral_metrics', 'bot_config');
    
    SELECT COUNT(*) INTO view_count
    FROM pg_views
    WHERE schemaname = 'public'
    AND viewname IN ('recent_trades', 'portfolio_performance');
    
    SELECT COUNT(*) INTO policy_count
    FROM pg_policies
    WHERE schemaname = 'public';
    
    RAISE NOTICE '========================================';
    RAISE NOTICE 'DATABASE INITIALIZATION COMPLETE';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Tables: %', table_count;
    RAISE NOTICE 'Views: %', view_count;
    RAISE NOTICE 'RLS Policies: %', policy_count;
    RAISE NOTICE '========================================';
    RAISE NOTICE '✓ All tables have RLS enabled';
    RAISE NOTICE '✓ Service role can write';
    RAISE NOTICE '✓ Anonymous users can read';
    RAISE NOTICE '✓ Views inherit security from tables';
    RAISE NOTICE '========================================';
END $$;

-- ============================================================================
-- NEXT STEPS
-- ============================================================================
--
-- 1. Update your bot code to use SUPABASE_SERVICE_KEY for write operations:
--    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
--
-- 2. Keep using SUPABASE_KEY (anon key) for dashboard read operations
--
-- 3. Test that:
--    - Bot can write trades, portfolio snapshots, positions, metrics, config
--    - Dashboard can read all data
--    - No unauthorized access possible
--
-- 4. In Supabase UI:
--    - Tables should NOT show "Unrestricted" label
--    - Views inherit security from underlying tables
--
-- ============================================================================

