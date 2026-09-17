#!/usr/bin/env python3
"""Reset the database to a clean state.

Usage:
  python .dev/reset_db.py          # Reset main database
  python .dev/reset_db.py --tests  # Also reset test database
"""

import sys
from pathlib import Path

repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from app.config import get_settings
from app.database import engine, SessionLocal
from app.models import Base
from app.seed import seed_all


def reset_database(db_path: Path) -> None:
    """Delete and recreate a SQLite database file."""
    if db_path.exists():
        db_path.unlink()
        print(f"✅ Deleted old database at {db_path}")


def reset_main_db() -> None:
    """Reset the main application database."""
    settings = get_settings()
    
    # Parse SQLite path
    db_url = settings.database_url
    if db_url.startswith("sqlite:////"):
        db_path = Path(db_url[10:])  # Absolute path
    elif db_url.startswith("sqlite:///"):
        db_path = repo_root / db_url[10:]  # Relative path
    else:
        db_path = repo_root / "booktracker.db"
    
    print(f"🗑️  Resetting database at {db_path}...")
    reset_database(db_path)
    
    print("📊 Creating fresh tables...")
    Base.metadata.create_all(bind=engine)
    
    print("🌱 Seeding initial data...")
    db = SessionLocal()
    try:
        seed_all(db)
        print("✨ Database initialized with owner account and preset tags")
    finally:
        db.close()
    
    print()
    print("✅ Database reset complete!")
    print(f"   Username: {settings.owner_username}")
    print(f"   Password: {settings.owner_password}")
    print()


def reset_test_db() -> None:
    """Reset the test database."""
    db_path = repo_root / "test_booktracker.db"
    print(f"🗑️  Resetting test database...")
    reset_database(db_path)
    print("✅ Test database reset complete!")


if __name__ == "__main__":
    try:
        reset_main_db()
        if "--tests" in sys.argv or "-t" in sys.argv:
            print()
            reset_test_db()
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
