-- SQL script to reset portfolio in Supabase database
-- Run this in Supabase SQL Editor to fully reset the portfolio to 10000

-- WARNING: This will delete ALL trading data!
-- This includes: trades, portfolio snapshots, positions, behavioral metrics,
-- observability metrics, and service health checks.
-- Make sure you have backups if needed.
--
-- Note: If you want to keep monitoring history, comment out steps 5 and 6
-- (the DELETE statements for observability_metrics and service_health).

-- Step 1: Delete all trades
DELETE FROM trades;

-- Step 2: Delete all portfolio snapshots
DELETE FROM portfolio_snapshots;

-- Step 3: Delete all positions (both active and closed)
DELETE FROM positions;

-- Step 4: Delete all behavioral metrics
DELETE FROM behavioral_metrics;

-- Step 5: Delete all observability metrics (if table exists)
-- Note: This will only work if observability tables have been created via schema migration
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'observability_metrics') THEN
        DELETE FROM observability_metrics;
        RAISE NOTICE 'Deleted observability_metrics';
    ELSE
        RAISE NOTICE 'Table observability_metrics does not exist (skipping)';
    END IF;
END $$;

-- Step 6: Delete all service health checks (if table exists)
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'service_health') THEN
        DELETE FROM service_health;
        RAISE NOTICE 'Deleted service_health';
    ELSE
        RAISE NOTICE 'Table service_health does not exist (skipping)';
    END IF;
END $$;

-- Step 7: Update initial_balance in bot_config to 10000
UPDATE bot_config 
SET value = '10000.0', 
    updated_at = NOW()
WHERE key = 'initial_balance';

-- If the config doesn't exist, insert it
INSERT INTO bot_config (key, value, description, updated_at)
VALUES ('initial_balance', '10000.0', 'Initial balance in USDT', NOW())
ON CONFLICT (key) DO UPDATE 
SET value = '10000.0', 
    updated_at = NOW();

-- Step 8: Create a fresh portfolio snapshot with initial balance
INSERT INTO portfolio_snapshots (
    timestamp,
    balance,
    positions_value,
    total_value,
    initial_balance,
    total_return,
    total_return_pct,
    total_trades,
    active_positions,
    total_fees
)
VALUES (
    NOW(),
    10000.0,
    0.0,
    10000.0,
    10000.0,
    0.0,
    0.0,
    0,
    0,
    0.0
);

-- Verify the reset
SELECT 
    'Trades' as table_name, 
    COUNT(*) as count 
FROM trades
UNION ALL
SELECT 
    'Portfolio Snapshots', 
    COUNT(*) 
FROM portfolio_snapshots
UNION ALL
SELECT 
    'Positions', 
    COUNT(*) 
FROM positions
UNION ALL
SELECT 
    'Behavioral Metrics', 
    COUNT(*) 
FROM behavioral_metrics
UNION ALL
SELECT 
    'Initial Balance Config', 
    COUNT(*) 
FROM bot_config 
WHERE key = 'initial_balance' AND value = '10000.0';

-- Verify observability tables (if they exist)
DO $$
BEGIN
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'observability_metrics') THEN
        RAISE NOTICE 'Observability Metrics: %', (SELECT COUNT(*) FROM observability_metrics);
    ELSE
        RAISE NOTICE 'Observability Metrics: Table does not exist';
    END IF;
    
    IF EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'service_health') THEN
        RAISE NOTICE 'Service Health Checks: %', (SELECT COUNT(*) FROM service_health);
    ELSE
        RAISE NOTICE 'Service Health Checks: Table does not exist';
    END IF;
END $$;

