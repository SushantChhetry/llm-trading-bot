# Database Setup Guide

Complete guide for setting up your database connection for the Alpha Arena Trading Bot.

## 🎯 Quick Reference

**For those who know what they're doing:**

```bash
# Get connection string from Supabase Dashboard
# Settings → Database → Connection string → Direct connection (port 5432)
# Add to .env:
DATABASE_URL=postgresql://postgres.xxx:[YOUR-PASSWORD]@db.xxx.supabase.co:5432/postgres

# Verify:
python scripts/test_alembic_connection.py
```

---

## Understanding SUPABASE_URL vs DATABASE_URL

**These are two different connection methods to Supabase:**

### `SUPABASE_URL` - REST API Access
- **What it is**: Supabase REST API endpoint
- **Format**: `https://xxx.supabase.co`
- **Used for**:
  - Supabase Python client (`create_client()`)
  - REST API operations (get_trades, add_trade, etc.)
  - Application code

**Example:**
```python
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
trades = supabase.table("trades").select("*").execute()
```

### `DATABASE_URL` - Direct PostgreSQL Connection
- **What it is**: Direct PostgreSQL connection string
- **Format**: `postgresql://postgres.xxx:password@db.xxx.supabase.co:5432/postgres`
- **Used for**:
  - Alembic migrations
  - Direct SQL queries
  - Database tools (psql, pgAdmin, etc.)

**Example:**
```python
engine = create_engine(DATABASE_URL)
conn = engine.connect()
conn.execute(text("SELECT * FROM trades"))
```

### Visual Relationship

```
Your Supabase Database
    ├── REST API (SUPABASE_URL)
    │   └── Used by: supabase Python client
    │   └── Port: 443 (HTTPS)
    │
    └── Direct PostgreSQL (DATABASE_URL)
        └── Used by: Alembic, psql, SQL tools
        └── Port: 5432 (PostgreSQL)
```

### When to Use Which

| Use Case | Use | Why |
|----------|-----|-----|
| Your app code | `SUPABASE_URL` | REST API is simpler, managed, secure |
| Alembic migrations | `DATABASE_URL` | Needs direct SQL access |
| Database tools | `DATABASE_URL` | Direct PostgreSQL connection |

**Recommendation**: Keep both - they serve different purposes.

---

## Step-by-Step Setup Guide

### Step 1: Get Connection String from Supabase

1. **Go to Supabase Dashboard**
   - Visit: https://supabase.com/dashboard
   - Select your project

2. **Navigate to Database Settings**
   - Click **Project Settings** (gear icon in sidebar)
   - Click **Database** in left menu

3. **Get Connection String**
   - Scroll to **"Connection string"** section
   - **IMPORTANT**: Select **"Direct connection"** (NOT "Connection pooling")
   - The URI should show port **5432** (NOT 6543)
   - Click the **copy icon** next to the URI

4. **The Connection String Format**
   ```
   postgresql://postgres.abcdefghijklmnop:[YOUR-PASSWORD]@db.abcdefghijklmnop.supabase.co:5432/postgres
   ```

### Step 2: Replace Password

Replace `[YOUR-PASSWORD]` with your actual database password.

**Don't know your password?**
- Go to: **Project Settings → Database → Database Settings**
- Reset your database password if needed

**After replacing:**
```
postgresql://postgres.abcdefghijklmnop:MySecurePassword123@db.abcdefghijklmnop.supabase.co:5432/postgres
```

### Step 3: Configure Your Environment

#### Option 1: Local Development (.env file) - Recommended

Create or edit `.env` file in the `deepseek-experiment/` directory:

```bash
cd deepseek-experiment
nano .env  # or use any text editor
```

Add your connection strings:

```bash
# Supabase REST API (for application code)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key

# Direct PostgreSQL (for Alembic migrations)
DATABASE_URL=postgresql://postgres.xxx:your_password@db.xxx.supabase.co:5432/postgres
```

#### Option 2: Export in Terminal (Temporary - Testing Only)

```bash
export DATABASE_URL="postgresql://postgres.xxx:your_password@db.xxx.supabase.co:5432/postgres"
```

⚠️ **Warning**: This only works for your current terminal session. Use `.env` file for persistent configuration.

#### Option 3: Railway (Production)

1. Go to Railway dashboard
2. Select your service (Trading Bot or API Server)
3. Go to **Variables** tab
4. Click **+ New Variable**
5. Add:
   - **Key**: `DATABASE_URL`
   - **Value**: `postgresql://postgres.xxx:password@db.xxx.supabase.co:5432/postgres`

### Step 4: Verify Configuration

```bash
# Check if .env is loaded
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('DATABASE_URL:', os.getenv('DATABASE_URL', 'NOT SET')[:50] + '...' if os.getenv('DATABASE_URL') else 'NOT SET')"

# Or test Alembic connection
python scripts/test_alembic_connection.py
```

You should see:
```
✅ Connection successful!
```

---

## Configuration Options

### Option 1: Set Both Explicitly (Recommended)

```bash
# .env file
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your_anon_key

# For Alembic migrations
DATABASE_URL=postgresql://postgres.xxx:password@db.xxx.supabase.co:5432/postgres
```

### Option 2: Auto-Build DATABASE_URL (If Supported)

Some configurations may auto-build `DATABASE_URL` from `SUPABASE_URL` and `SUPABASE_DB_PASSWORD`:

```bash
# .env file
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your_anon_key
SUPABASE_DB_PASSWORD=your_database_password
```

---

## Where Each Variable is Used

### SUPABASE_URL Used In:
- `src/supabase_client.py` - Supabase service
- `web-dashboard/api_server_supabase.py` - API server
- `src/startup_validator.py` - Validation

### DATABASE_URL Used In:
- `alembic/env.py` - Database migrations
- `scripts/test_alembic_connection.py` - Connection testing

---

## Troubleshooting

### "DATABASE_URL not found"
**Symptoms**: Application can't find DATABASE_URL variable

**Solutions**:
- Check `.env` file exists in `deepseek-experiment/` directory
- Verify the variable name is exactly `DATABASE_URL` (case-sensitive)
- Make sure you're running from the correct directory
- Ensure `python-dotenv` is installed: `pip install python-dotenv`

### "Connection refused"
**Symptoms**: Can't connect to database

**Solutions**:
- Verify you're using "Direct connection" (port 5432, NOT 6543)
- Check your IP isn't blocked in Supabase Network Restrictions
- Verify password is correct (try resetting in Supabase Dashboard)
- Ensure Supabase project is active

### "Module 'dotenv' not found"
**Symptoms**: Python can't import dotenv

**Solutions**:
```bash
pip install python-dotenv
```

### Wrong Port Number
**Symptoms**: Connection works but migration fails

**Solutions**:
- Use **"Direct connection"** (port 5432) for Alembic
- ❌ Don't use **"Connection pooling"** (port 6543)
- Verify in connection string: `:5432/postgres`

### Password Issues
**Symptoms**: Authentication fails

**Solutions**:
- Make sure you replaced `[YOUR-PASSWORD]` placeholder
- Check for special characters that might need URL encoding
- Reset password in Supabase Dashboard if unsure

---

## Security Best Practices

- ✅ `.env` files are typically git-ignored (check `.gitignore`)
- ✅ Never commit `DATABASE_URL` to version control
- ✅ Use different passwords for development/production
- ✅ Railway automatically encrypts environment variables
- ✅ Use strong, unique passwords
- ✅ Rotate passwords regularly
- ✅ Limit database access to necessary IPs in Supabase

---

## Quick Setup Commands

### One-Line Setup (Once you have connection string)

```bash
cd deepseek-experiment
echo 'DATABASE_URL=postgresql://postgres.xxx:password@db.xxx.supabase.co:5432/postgres' >> .env
```

(Replace with your actual connection string)

### Verify Connection

```bash
# Quick test
python scripts/test_alembic_connection.py

# Or check manually
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('✅ Set' if os.getenv('DATABASE_URL') else '❌ Not set')"
```

---

## Next Steps

Once your database is configured:

1. **Initialize Schema**: Run migrations (see [Migration Guide](migrations.md))
2. **Test Connection**: Verify both `SUPABASE_URL` and `DATABASE_URL` work
3. **Start Application**: Launch your trading bot
4. **Monitor**: Check logs for database connection status

---

## Related Documentation

- **[Database Migrations](migrations.md)** - Using Alembic for schema changes
- **[Configuration Reference](../reference/configuration.md)** - All configuration options
- **[Troubleshooting Guide](../../troubleshooting/common-issues.md)** - More troubleshooting help

---

## Summary

**Quick Checklist:**
- [ ] Get connection string from Supabase (Direct connection, port 5432)
- [ ] Replace `[YOUR-PASSWORD]` placeholder
- [ ] Add to `.env` file or Railway variables
- [ ] Verify with test script
- [ ] Ready to use!

**Remember:**
- Use `SUPABASE_URL` for application code
- Use `DATABASE_URL` for migrations and direct SQL
- Both point to the same database, just different access methods
- Always use "Direct connection" (5432) for Alembic
