# Slow Queries Troubleshooting Guide

## Understanding Supabase Dashboard Queries

If you see slow queries in your Supabase dashboard, most of them are likely from **Supabase's dashboard UI itself**, not your application code. Here's what to know:

### Common Dashboard Queries

1. **`SELECT name FROM pg_timezone_names`** (0.14s, 59 calls)
   - **Source**: Supabase dashboard UI (populates timezone dropdowns)
   - **Impact**: Minimal - these are UI queries, not application queries
   - **Optimization**: Not necessary to optimize (internal dashboard use)

2. **Table/View Definition Queries** (0.53s - 0.72s)
   - **Source**: Supabase dashboard schema viewer
   - **Impact**: Minimal - only runs when viewing schema in dashboard
   - **Optimization**: Not necessary to optimize (internal dashboard use)

3. **Function Definition Queries** (0.13s)
   - **Source**: Supabase dashboard function viewer
   - **Impact**: Minimal - only runs when viewing functions in dashboard
   - **Optimization**: Not necessary to optimize (internal dashboard use)

4. **Extension Queries** (0.06s)
   - **Source**: Supabase dashboard extension viewer
   - **Impact**: Minimal - only runs when viewing extensions in dashboard
   - **Optimization**: Not necessary to optimize (internal dashboard use)

## Application Query Optimization

While dashboard queries are normal, here are ways to optimize **your application's queries**:

### 1. Connection Pool Optimization

We've configured the database connection with:
- **Explicit timezone setting**: Prevents PostgreSQL from querying `pg_timezone_names` on each connection
- **Connection pool recycling**: Prevents stale connections
- **Application name**: Helps identify queries in monitoring

See `src/database_manager.py` for the configuration.

### 2. Index Optimization

Ensure your tables have proper indexes:

```sql
-- Already created in supabase_schema.sql
CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);
CREATE INDEX IF NOT EXISTS idx_portfolio_timestamp ON portfolio_snapshots(timestamp);
CREATE INDEX IF NOT EXISTS idx_behavioral_timestamp ON behavioral_metrics(timestamp);
```

### 3. Query Optimization Best Practices

- **Use LIMIT clauses** for large result sets
- **Filter early** with WHERE clauses
- **Select only needed columns** instead of `SELECT *`
- **Use connection pooling** (already configured)
- **Avoid N+1 queries** - use batch operations

### 4. Monitoring Application Queries

To see **your application's queries** (not dashboard queries):

1. **Enable query logging**:
   ```python
   # In database_manager.py, set echo=True temporarily
   self.engine = create_async_engine(
       self.database_url, echo=True, ...
   )
   ```

2. **Use Supabase Query Performance**:
   - Go to Supabase Dashboard → Database → Query Performance
   - Filter by your application name: `trading_bot`
   - This shows only your app's queries, not dashboard queries

3. **Use PostgreSQL Logging**:
   - Enable `log_statement = 'all'` in Supabase settings (development only)

### 5. Reducing Timezone Queries

If you're seeing many `pg_timezone_names` queries from your app:

1. **Set timezone in connection** (already done):
   ```python
   connect_args = {
       "server_settings": {"timezone": "UTC"}
   }
   ```

2. **Use timezone-aware datetime consistently**:
   - Our code uses `datetime.utcnow()` which matches UTC timezone setting
   - Avoid mixing timezone-aware and naive datetimes

3. **Configure database timezone**:
   - Supabase databases default to UTC, which matches our code

## When to Worry About Slow Queries

✅ **Don't worry about**:
- Dashboard UI queries (schema viewers, timezone dropdowns, etc.)
- Queries with < 0.5s execution time
- Queries that run < 10 times per day

⚠️ **Investigate if you see**:
- Queries taking > 1 second repeatedly
- Queries running > 100 times per hour from your application
- Missing indexes causing table scans
- Lock contention on frequently updated tables

## Quick Checklist

- [x] Connection pool configured with timezone
- [x] Indexes created on timestamp columns
- [x] Application name set for query identification
- [ ] Review actual application queries (not dashboard queries)
- [ ] Monitor query performance over time

## Further Reading

- [Supabase Query Performance Guide](https://supabase.com/docs/guides/platform/performance)
- [PostgreSQL Query Optimization](https://www.postgresql.org/docs/current/performance-tips.html)
- [SQLAlchemy Connection Pooling](https://docs.sqlalchemy.org/en/20/core/pooling.html)
