# SUPABASE_URL vs DATABASE_URL - Understanding the Difference

## Key Difference

**These are two different connection methods to Supabase:**

### `SUPABASE_URL` - REST API Access
- **What it is**: Supabase REST API endpoint
- **Format**: `https://xxx.supabase.co`
- **Used for**:
  - Supabase Python client (`create_client()`)
  - REST API operations (get_trades, add_trade, etc.)
  - What your code currently uses

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

## Why You Need Both

| Use Case | Use | Why |
|----------|-----|-----|
| Your app code | `SUPABASE_URL` | REST API is simpler, managed, secure |
| Alembic migrations | `DATABASE_URL` | Needs direct SQL access |
| Database tools | `DATABASE_URL` | Direct PostgreSQL connection |

## How They Relate

Both point to the same Supabase database, just different access methods:

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

## Configuration

### Option 1: Set Both Explicitly (Recommended)

```bash
# .env file
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your_anon_key

# For Alembic migrations
DATABASE_URL=postgresql://postgres.xxx:password@db.xxx.supabase.co:5432/postgres
```

### Option 2: Auto-Build DATABASE_URL (Convenient)

```bash
# .env file
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your_anon_key
SUPABASE_DB_PASSWORD=your_database_password  # Alembic will auto-build DATABASE_URL
```

## Where Each is Used

### SUPABASE_URL Used In:
- `src/supabase_client.py` - Supabase service
- `web-dashboard/api_server_supabase.py` - API server
- `src/startup_validator.py` - Validation

### DATABASE_URL Used In:
- `alembic/env.py` - Database migrations
- `scripts/test_alembic_connection.py` - Connection testing

## Recommendation

**Keep both as-is** - they serve different purposes:

✅ **SUPABASE_URL**: Keep for your application code (REST API)
✅ **DATABASE_URL**: Add separately for Alembic migrations

No need to rename anything - they're different connection methods for different use cases.

## Quick Setup

1. **Keep your existing SUPABASE_URL** (for app code)
2. **Add DATABASE_URL** (for Alembic):

```bash
# In Supabase Dashboard → Database → Connection string
# Copy "Direct connection" URI
# Add to .env:
DATABASE_URL=postgresql://postgres.xxx:[YOUR-PASSWORD]@db.xxx.supabase.co:5432/postgres
```

Replace `[YOUR-PASSWORD]` with your actual database password.
