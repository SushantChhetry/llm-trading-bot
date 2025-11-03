#!/usr/bin/env python3
"""
Script to create initial Alembic migration from existing schema.

Run this after setting up Alembic to create the initial migration
that matches your current database schema.
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Create initial Alembic migration."""
    project_root = Path(__file__).parent.parent

    # Check if alembic is installed
    try:
        import alembic
    except ImportError:
        print("❌ Alembic not installed. Install with: pip install alembic")
        sys.exit(1)

    # Create initial revision
    print("📝 Creating initial Alembic migration...")

    result = subprocess.run(
        ["alembic", "revision", "--autogenerate", "-m", "Initial schema migration"],
        cwd=project_root,
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        print("✅ Initial migration created successfully")
        print(result.stdout)
    else:
        print("❌ Failed to create migration:")
        print(result.stderr)
        sys.exit(1)

    print("\n📋 Next steps:")
    print("1. Review the generated migration file in alembic/versions/")
    print("2. Test migration: alembic upgrade head --sql")
    print("3. Apply migration: alembic upgrade head")

if __name__ == "__main__":
    main()
