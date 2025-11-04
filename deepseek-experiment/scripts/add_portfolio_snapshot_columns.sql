-- Quick fix: Add missing columns to portfolio_snapshots table
-- Run this in your Supabase SQL Editor to fix the PGRST204 error

-- Add avg_trade_duration_hours column
ALTER TABLE portfolio_snapshots
ADD COLUMN IF NOT EXISTS avg_trade_duration_hours DECIMAL(8, 2);

-- Add max_consecutive_wins column
ALTER TABLE portfolio_snapshots
ADD COLUMN IF NOT EXISTS max_consecutive_wins INTEGER;

-- Add max_consecutive_losses column
ALTER TABLE portfolio_snapshots
ADD COLUMN IF NOT EXISTS max_consecutive_losses INTEGER;

-- Verify columns were added
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'portfolio_snapshots'
AND column_name IN ('avg_trade_duration_hours', 'max_consecutive_wins', 'max_consecutive_losses')
ORDER BY column_name;

