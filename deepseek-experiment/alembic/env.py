from logging.config import fileConfig
import os
import sys
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import your models (if using ORM) - adjust path as needed
# from src.database_manager import Base
# target_metadata = Base.metadata

# For now, we're using raw SQL migrations, so no metadata needed
target_metadata = None

# Get database URL from environment
def get_database_url():
    """
    Get database URL from environment variables.

    Priority:
    1. DATABASE_URL (explicit PostgreSQL connection string) - highest priority
    2. Build from SUPABASE_URL + SUPABASE_DB_PASSWORD (if available)

    For Supabase:
    - SUPABASE_URL: REST API endpoint (e.g., https://xxx.supabase.co)
    - DATABASE_URL: Direct PostgreSQL connection (e.g., postgresql://postgres.xxx:pass@db.xxx.supabase.co:5432/postgres)

    To get DATABASE_URL:
    Supabase Dashboard → Project Settings → Database → Connection string → "Direct connection"
    """
    # Priority 1: Explicit DATABASE_URL
    db_url = os.getenv("DATABASE_URL")
    if db_url and db_url.startswith("postgresql://"):
        return db_url

    # Priority 2: Build from SUPABASE_URL if DATABASE_URL not set
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_db_password = os.getenv("SUPABASE_DB_PASSWORD", "")

    if supabase_url and supabase_db_password:
        try:
            # Extract project reference from SUPABASE_URL
            # https://xxx.supabase.co -> xxx
            project_ref = supabase_url.replace("https://", "").replace(".supabase.co", "").strip()
            if project_ref:
                # Build direct PostgreSQL connection string
                db_url = f"postgresql://postgres.{project_ref}:{supabase_db_password}@db.{project_ref}.supabase.co:5432/postgres"
                return db_url
        except Exception:
            pass

    # Fallback: Return None to trigger clear error message
    return None


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the database URL
database_url = get_database_url()
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)
else:
    # Provide helpful error message
    import sys
    print("=" * 60, file=sys.stderr)
    print("❌ DATABASE_URL not configured", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    print("\nSet DATABASE_URL to your PostgreSQL connection string:", file=sys.stderr)
    print("  export DATABASE_URL='postgresql://postgres.xxx:pass@db.xxx.supabase.co:5432/postgres'", file=sys.stderr)
    print("\nOr set SUPABASE_URL + SUPABASE_DB_PASSWORD to auto-build it.", file=sys.stderr)
    print("=" * 60, file=sys.stderr)
    sys.exit(1)

# Set target metadata if using ORM
# config.set_main_option("target_metadata", target_metadata)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
