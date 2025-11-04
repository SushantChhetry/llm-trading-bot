# Resetting Portfolio to Initial Balance

This guide explains how to reset your trading bot's portfolio to start fresh from an initial balance (default: $10,000).

## Overview

Resetting the portfolio will:
- Clear all trade history
- Reset portfolio balance to initial value (default: 10000)
- Close all open positions
- Reset all portfolio metrics
- Start tracking from scratch

⚠️ **WARNING**: This action **cannot be undone**. All trading history will be permanently deleted.

## Quick Reset (Recommended)

### Option 1: Using the Reset Script

The easiest way to reset is using the provided Python script:

```bash
# Reset both local files and Supabase database
python scripts/reset_portfolio.py

# Reset only local files (if not using Supabase)
python scripts/reset_portfolio.py --local-only

# Reset only Supabase database (for production)
python scripts/reset_portfolio.py --supabase-only

# Use custom initial balance
python scripts/reset_portfolio.py --initial-balance 5000
```

### Option 2: Manual Reset via Supabase SQL

If you're using Supabase (production), you can run SQL commands directly:

1. Open Supabase Dashboard → SQL Editor
2. Run the SQL script from `scripts/reset_portfolio_supabase.sql`
3. Or run these commands manually:

```sql
-- Delete all trading data
DELETE FROM trades;
DELETE FROM portfolio_snapshots;
DELETE FROM positions;
DELETE FROM behavioral_metrics;

-- Update initial balance
UPDATE bot_config 
SET value = '10000.0', updated_at = NOW()
WHERE key = 'initial_balance';

-- Create fresh portfolio snapshot
INSERT INTO portfolio_snapshots (
    timestamp, balance, positions_value, total_value,
    initial_balance, total_return, total_return_pct,
    total_trades, active_positions, total_fees
)
VALUES (
    NOW(), 10000.0, 0.0, 10000.0,
    10000.0, 0.0, 0.0, 0, 0, 0.0
);
```

## Production Deployment Reset (Railway)

If your bot is deployed on Railway:

### Step 1: Set Environment Variable

1. Go to Railway Dashboard → Your Trading Bot Service
2. Settings → Variables
3. Set `INITIAL_BALANCE=10000.0` (or your desired value)
4. Save changes

### Step 2: Reset Database

**If using Supabase:**
1. Open Supabase Dashboard → SQL Editor
2. Run the SQL commands from `scripts/reset_portfolio_supabase.sql`
3. Verify: All tables should be empty except for the fresh portfolio snapshot

**If using local files (Docker):**
The reset script will handle this, or you can manually delete files in the container.

### Step 3: Restart the Bot

1. In Railway Dashboard → Your Trading Bot Service
2. Click "Restart" or redeploy
3. The bot will start with a fresh balance of 10000

## Local Development Reset

If running locally:

```bash
# 1. Delete local data files
rm data/trades.json
rm data/portfolio.json

# 2. Set environment variable
export INITIAL_BALANCE=10000.0

# 3. Restart the bot
python -m src.main
```

Or use the reset script:

```bash
python scripts/reset_portfolio.py --local-only
```

## Verification

After resetting, verify the portfolio is correct:

1. **Check Dashboard**: Portfolio should show:
   - Balance: $10,000.00
   - Total Value: $10,000.00
   - Total Return: $0.00 (0.00%)
   - Total Trades: 0

2. **Check Database** (Supabase):
   ```sql
   SELECT COUNT(*) FROM trades;  -- Should be 0
   SELECT COUNT(*) FROM portfolio_snapshots;  -- Should be 1
   SELECT balance, initial_balance FROM portfolio_snapshots ORDER BY timestamp DESC LIMIT 1;
   -- Should show balance=10000, initial_balance=10000
   ```

3. **Check Bot Logs**: Look for:
   ```
   Trading engine initialized with balance: 10000.0
   ```

## Troubleshooting

### Portfolio still shows old balance after reset

1. **Check environment variable**: Ensure `INITIAL_BALANCE=10000.0` is set correctly
2. **Verify database reset**: Check that tables were actually cleared
3. **Clear cache**: If using a dashboard, refresh the page or clear browser cache
4. **Restart services**: Make sure both bot and API server are restarted

### Reset script fails with Supabase errors

1. **Check credentials**: Verify `SUPABASE_URL` and `SUPABASE_KEY` are set correctly
2. **Check RLS policies**: You may need to use `SUPABASE_SERVICE_KEY` instead of `SUPABASE_KEY`
3. **Manual SQL reset**: Use the SQL script directly in Supabase SQL Editor

### Bot initializes with wrong balance

1. **Check config priority**: Environment variables override config files
2. **Check config.yaml**: Ensure `initial_balance: 10000.0` in `config.yaml`
3. **Check command line**: If running with `--balance`, it overrides everything

## Best Practices

1. **Backup before reset**: Export trades and portfolio data if you want to keep history
2. **Test in development**: Always test reset in dev environment first
3. **Document the reset**: Note why you reset and what the new baseline is
4. **Monitor after reset**: Check bot behavior for first few cycles after reset

## Exporting Data Before Reset

If you want to keep a backup of your trading history:

```bash
# Export trades to CSV (if using Supabase)
# Use Supabase dashboard → Table Editor → Export

# Or use Python script
python -c "
import json
from pathlib import Path
from datetime import datetime

trades_file = Path('data/trades.json')
if trades_file.exists():
    backup_file = f'data/trades_backup_{datetime.now().strftime(\"%Y%m%d_%H%M%S\")}.json'
    trades_file.rename(backup_file)
    print(f'Backed up to {backup_file}')
"
```

## Related Files

- `scripts/reset_portfolio.py` - Main reset script
- `scripts/reset_portfolio_supabase.sql` - SQL commands for Supabase
- `config/config.py` - Configuration file (INITIAL_BALANCE default)
- `src/trading_engine.py` - Trading engine that uses INITIAL_BALANCE

