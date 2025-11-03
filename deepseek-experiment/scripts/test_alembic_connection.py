#!/usr/bin/env python3
"""
Test Alembic connection to PostgreSQL database.

Verifies that Alembic can connect to your database (Supabase or other PostgreSQL).
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_alembic_connection():
    """Test if Alembic can connect to the database."""
    print("🔍 Testing Alembic Database Connection")
    print("=" * 60)

    # Try to get DATABASE_URL (check alembic's get_database_url function)
    database_url = os.getenv("DATABASE_URL")

    # If not set, try to build from SUPABASE_URL
    if not database_url or not database_url.startswith("postgresql://"):
        supabase_url = os.getenv("SUPABASE_URL", "")
        supabase_db_password = os.getenv("SUPABASE_DB_PASSWORD", "")

        if supabase_url and supabase_db_password:
            try:
                project_ref = supabase_url.replace("https://", "").replace(".supabase.co", "").strip()
                if project_ref:
                    database_url = f"postgresql://postgres.{project_ref}:{supabase_db_password}@db.{project_ref}.supabase.co:5432/postgres"
                    print(f"ℹ️  Built DATABASE_URL from SUPABASE_URL")
            except Exception:
                pass

    if not database_url or not database_url.startswith("postgresql://"):
        print("❌ DATABASE_URL not configured")
        print("\n📝 You have two options:")
        print("\n   Option 1: Set DATABASE_URL directly (recommended)")
        print("   1. Go to Supabase Dashboard → Project Settings → Database")
        print("   2. Under 'Connection string', select 'Direct connection'")
        print("   3. Copy the URI (port 5432, not 6543)")
        print('   4. Set: export DATABASE_URL="postgresql://postgres.[ref]:[password]@db.xxx.supabase.co:5432/postgres"')
        print("\n   Option 2: Auto-build from SUPABASE_URL")
        print("   If you have SUPABASE_URL set, also set SUPABASE_DB_PASSWORD:")
        print('   export SUPABASE_DB_PASSWORD="your_database_password"')
        print("   Alembic will automatically build DATABASE_URL from SUPABASE_URL")
        print("\n   Note: SUPABASE_URL is for REST API, DATABASE_URL is for direct SQL access")
        return False

    print(f"✅ DATABASE_URL found")
    print(f"   Connection: {database_url.split('@')[1] if '@' in database_url else 'hidden'}")
    print()

    # Test SQLAlchemy connection
    try:
        from sqlalchemy import create_engine, text

        print("🔄 Testing SQLAlchemy connection...")
        engine = create_engine(database_url, echo=False)

        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"✅ Connected to PostgreSQL successfully!")
            print(f"   Version: {version[:50]}...")

            # Test query on information_schema
            result = conn.execute(text("SELECT current_database();"))
            db_name = result.fetchone()[0]
            print(f"   Database: {db_name}")

            # Check if alembic_version table exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'alembic_version'
                );
            """))
            has_alembic_version = result.fetchone()[0]

            if has_alembic_version:
                result = conn.execute(text("SELECT version_num FROM alembic_version ORDER BY version_num DESC LIMIT 1;"))
                current_version = result.fetchone()
                if current_version:
                    print(f"   Current Alembic version: {current_version[0]}")
                else:
                    print(f"   Alembic initialized (no migrations applied)")
            else:
                print(f"   Alembic not initialized (no alembic_version table)")

        print()
        print("✅ Connection test PASSED")
        print()
        print("📋 Next steps:")
        print("   • Check migration status: alembic current")
        print("   • View migration history: alembic history")
        print("   • Create migration: alembic revision -m 'description'")

        return True

    except ImportError:
        print("❌ SQLAlchemy not installed")
        print("   Install with: pip install sqlalchemy")
        return False
    except Exception as e:
        print(f"❌ Connection FAILED: {e}")
        print()
        print("🔍 Troubleshooting:")
        print("   1. Verify DATABASE_URL is correct")
        print("   2. Check if database is accessible from your IP")
        print("   3. Verify credentials (username/password)")
        print("   4. For Supabase: Use 'Direct connection' (port 5432)")
        print("   5. Check firewall/network restrictions")
        return False


def test_alembic_config():
    """Test if Alembic configuration is valid."""
    print("🔍 Testing Alembic Configuration")
    print("=" * 60)

    try:
        import alembic
        try:
            version = alembic.__version__
        except AttributeError:
            # Try alternative way to get version
            try:
                import pkg_resources
                version = pkg_resources.get_distribution("alembic").version
            except Exception:
                version = "installed (version unknown)"
        print(f"✅ Alembic installed: version {version}")
    except ImportError:
        print("❌ Alembic not installed")
        print("   Install with: pip install alembic")
        return False

    # Check alembic.ini exists
    alembic_ini = project_root / "alembic.ini"
    if alembic_ini.exists():
        print(f"✅ alembic.ini found")
    else:
        print(f"❌ alembic.ini not found at {alembic_ini}")
        return False

    # Check alembic directory
    alembic_dir = project_root / "alembic"
    if alembic_dir.exists():
        print(f"✅ alembic/ directory found")
    else:
        print(f"❌ alembic/ directory not found")
        return False

    # Check env.py
    env_py = alembic_dir / "env.py"
    if env_py.exists():
        print(f"✅ alembic/env.py found")
    else:
        print(f"❌ alembic/env.py not found")
        return False

    print()
    return True


if __name__ == "__main__":
    print()

    # Test Alembic config first
    config_ok = test_alembic_config()
    print()

    if not config_ok:
        sys.exit(1)

    # Test database connection
    connection_ok = test_alembic_connection()

    print()
    if connection_ok:
        print("🎉 All tests passed! Alembic is ready to use.")
        sys.exit(0)
    else:
        print("❌ Connection test failed. Fix the issues above.")
        sys.exit(1)
