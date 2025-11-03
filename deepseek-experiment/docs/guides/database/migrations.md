# Database Migration Guide

Complete guide for managing database schema changes using Alembic.

## Using Alembic for Database Migrations

Alembic is configured for managing database schema changes. This replaces manual SQL scripts.

---

## Initial Setup

1. **Install Alembic** (if not already installed):
   ```bash
   pip install alembic
   ```

2. **Set DATABASE_URL** in environment:
   ```bash
   export DATABASE_URL="postgresql://user:password@host:port/database"
   ```

   Or for Supabase, get connection string from Supabase dashboard.

   **See**: [Database Setup Guide](setup.md) for getting your connection string.

3. **Create initial migration** (one-time setup):
   ```bash
   python scripts/create_initial_migration.py
   ```

   Or manually:
   ```bash
   alembic revision --autogenerate -m "Initial schema migration"
   ```

---

## Creating Migrations

### Auto-generate from Models (if using ORM):
```bash
alembic revision --autogenerate -m "Description of changes"
```

### Manual migration:
```bash
alembic revision -m "Description of changes"
```

Then edit the generated file in `alembic/versions/` with your SQL.

---

## Applying Migrations

### Preview (dry-run):
```bash
alembic upgrade head --sql
```

This shows what SQL will be executed without actually running it.

### Apply migration:
```bash
alembic upgrade head
```

### Apply specific revision:
```bash
alembic upgrade <revision_id>
```

---

## Rolling Back

### Rollback one revision:
```bash
alembic downgrade -1
```

### Rollback to specific revision:
```bash
alembic downgrade <revision_id>
```

### Rollback all:
```bash
alembic downgrade base
```

---

## Checking Status

```bash
# Current revision
alembic current

# Migration history
alembic history

# Show pending migrations
alembic heads
```

---

## Production Deployment

1. **Before deployment**: Review migration in `alembic/versions/`
2. **Test locally**: `alembic upgrade head --sql` to preview
3. **Backup database**: Always backup before migrations
4. **Apply migration**: `alembic upgrade head`
5. **Verify**: Check application health after migration

---

## Migration Best Practices

- ✅ Always test migrations on staging first
- ✅ Keep migrations small and focused
- ✅ Never edit existing migrations (create new ones)
- ✅ Include both upgrade and downgrade logic
- ✅ Test rollback procedures
- ✅ Document breaking changes

---

## Converting Existing SQL to Alembic

If you have existing SQL migration scripts:

1. Create new Alembic revision:
   ```bash
   alembic revision -m "Migration description"
   ```

2. Copy SQL into `upgrade()` function:
   ```python
   def upgrade():
       op.execute("""
       -- Your SQL here
       """)
   ```

3. Add rollback in `downgrade()` function:
   ```python
   def downgrade():
       op.execute("""
       -- Reverse SQL here
       """)
   ```

---

## Example: Adding LLM Fields Migration

```python
def upgrade():
    op.add_column('trades', sa.Column('llm_prompt', sa.Text(), nullable=True))
    op.add_column('trades', sa.Column('llm_raw_response', sa.Text(), nullable=True))
    op.add_column('trades', sa.Column('llm_parsed_decision', sa.JSON(), nullable=True))

def downgrade():
    op.drop_column('trades', 'llm_parsed_decision')
    op.drop_column('trades', 'llm_raw_response')
    op.drop_column('trades', 'llm_prompt')
```

---

## Troubleshooting

### "DATABASE_URL not found"
- Check `.env` file exists
- Verify variable name is exactly `DATABASE_URL` (case-sensitive)
- See [Database Setup Guide](setup.md)

### "Can't connect to database"
- Verify connection string is correct
- Check database is running
- Verify network access/permissions
- See [Database Setup Guide](setup.md) for troubleshooting

### "Table already exists"
- Check if migration was already applied: `alembic current`
- Review migration history: `alembic history`
- May need to mark as applied: `alembic stamp head`

---

## Related Documentation

- **[Database Setup Guide](setup.md)** - Initial database configuration
- **[Configuration Reference](../../reference/configuration.md)** - Environment variables
- **[Troubleshooting Guide](../../troubleshooting/common-issues.md)** - Common issues

---

**Last Updated**: See git history for updates.
