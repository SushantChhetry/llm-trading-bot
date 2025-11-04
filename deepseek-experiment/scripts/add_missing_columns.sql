-- Add missing columns to Supabase tables
-- Run this in your Supabase SQL Editor

-- Add llm_provider and llm_model to trades table
ALTER TABLE trades
ADD COLUMN IF NOT EXISTS llm_provider VARCHAR(50),
ADD COLUMN IF NOT EXISTS llm_model VARCHAR(100);

-- Add llm_position_size_usdt to trades table
ALTER TABLE trades
ADD COLUMN IF NOT EXISTS llm_position_size_usdt DECIMAL(20, 8) DEFAULT 0.0;

-- Ensure profit and profit_pct columns exist (they should, but adding IF NOT EXISTS for safety)
ALTER TABLE trades
ADD COLUMN IF NOT EXISTS profit DECIMAL(20, 8),
ADD COLUMN IF NOT EXISTS profit_pct DECIMAL(10, 4);

-- Add entry_price alias to positions table (or just use avg_price in code)
-- Actually, let's add entry_price as an alias column that references avg_price
-- Or we can just update the code to use avg_price. For now, let's add entry_price as a separate column
ALTER TABLE positions
ADD COLUMN IF NOT EXISTS entry_price DECIMAL(20, 8);

-- Copy avg_price to entry_price for existing records
UPDATE positions
SET entry_price = avg_price
WHERE entry_price IS NULL AND avg_price IS NOT NULL;

-- The behavioral_metrics table should already have active_positions_count
-- But let's make sure it exists
ALTER TABLE behavioral_metrics
ADD COLUMN IF NOT EXISTS active_positions_count INTEGER;

-- Handle avg_position_size column name mismatch
-- Step 1: If avg_position_size exists but avg_position_size_usdt doesn't, rename it
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'behavioral_metrics'
        AND column_name = 'avg_position_size'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'behavioral_metrics'
        AND column_name = 'avg_position_size_usdt'
    ) THEN
        -- First, drop NOT NULL constraint if it exists
        ALTER TABLE behavioral_metrics
        ALTER COLUMN avg_position_size DROP NOT NULL;

        -- Rename the column
        ALTER TABLE behavioral_metrics
        RENAME COLUMN avg_position_size TO avg_position_size_usdt;

        -- Add NOT NULL constraint back with default
        ALTER TABLE behavioral_metrics
        ALTER COLUMN avg_position_size_usdt SET DEFAULT 0.0,
        ALTER COLUMN avg_position_size_usdt SET NOT NULL;

        -- Update any NULL values
        UPDATE behavioral_metrics
        SET avg_position_size_usdt = 0.0
        WHERE avg_position_size_usdt IS NULL;
    END IF;
END $$;

-- Step 2: If avg_position_size_usdt doesn't exist at all, add it
ALTER TABLE behavioral_metrics
ADD COLUMN IF NOT EXISTS avg_position_size_usdt DECIMAL(20, 8) NOT NULL DEFAULT 0.0;

-- Step 3: Handle fee_impact column name mismatch
-- If fee_impact_percent exists but fee_impact_pct doesn't, rename it
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'behavioral_metrics'
        AND column_name = 'fee_impact_percent'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'behavioral_metrics'
        AND column_name = 'fee_impact_pct'
    ) THEN
        -- Rename the column from fee_impact_percent to fee_impact_pct
        -- This preserves the NOT NULL constraint and data
        ALTER TABLE behavioral_metrics
        RENAME COLUMN fee_impact_percent TO fee_impact_pct;
    END IF;
END $$;

-- Ensure fee_impact_pct exists (add if it doesn't exist after potential rename)
-- First add as nullable, then update NULLs, then set NOT NULL
ALTER TABLE behavioral_metrics
ADD COLUMN IF NOT EXISTS fee_impact_pct DECIMAL(5, 2) DEFAULT 0.0;

-- Update any NULL values to 0.0
UPDATE behavioral_metrics
SET fee_impact_pct = 0.0
WHERE fee_impact_pct IS NULL;

-- Now set NOT NULL constraint
ALTER TABLE behavioral_metrics
ALTER COLUMN fee_impact_pct SET NOT NULL,
ALTER COLUMN fee_impact_pct SET DEFAULT 0.0;

-- If fee_impact_percent still exists (shouldn't happen after rename, but just in case), drop it
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'behavioral_metrics'
        AND column_name = 'fee_impact_percent'
    ) AND EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'behavioral_metrics'
        AND column_name = 'fee_impact_pct'
    ) THEN
        -- Copy data from old column to new column if needed
        UPDATE behavioral_metrics
        SET fee_impact_pct = fee_impact_percent
        WHERE fee_impact_pct IS NULL AND fee_impact_percent IS NOT NULL;

        -- Drop the old column
        ALTER TABLE behavioral_metrics
        DROP COLUMN fee_impact_percent;
    END IF;
END $$;

-- Step 4: If avg_position_size still exists (and avg_position_size_usdt also exists), drop the old one
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'behavioral_metrics'
        AND column_name = 'avg_position_size'
    ) AND EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'behavioral_metrics'
        AND column_name = 'avg_position_size_usdt'
    ) THEN
        ALTER TABLE behavioral_metrics
        DROP COLUMN avg_position_size;
    END IF;
END $$;

-- Add avg_profit_per_trade to portfolio_snapshots table
ALTER TABLE portfolio_snapshots
ADD COLUMN IF NOT EXISTS avg_profit_per_trade DECIMAL(20, 8) DEFAULT 0.0;

-- Verify the columns were added
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'trades'
AND column_name IN ('llm_provider', 'llm_model', 'llm_position_size_usdt', 'profit', 'profit_pct')
ORDER BY column_name;

SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'portfolio_snapshots'
AND column_name = 'avg_profit_per_trade'
ORDER BY column_name;

SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'positions'
AND column_name = 'entry_price'
ORDER BY column_name;

SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'behavioral_metrics'
AND column_name IN ('active_positions_count', 'avg_position_size_usdt', 'fee_impact_pct')
ORDER BY column_name;
