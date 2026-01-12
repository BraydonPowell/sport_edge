"""
Initialize database schema.
Creates all tables defined in db_schema.py.

Usage:
    python scripts/init_db.py
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_schema import init_db, get_engine, Game, Odds, TeamRating, Prediction, BacktestRun


def main():
    """Initialize database and verify tables."""
    print("=" * 60)
    print("Initializing Sports Edge Database")
    print("=" * 60)

    # Ensure data directory exists
    data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    os.makedirs(data_dir, exist_ok=True)

    # Initialize database
    engine = init_db()
    print(f"\n✓ Database created at: {engine.url}")

    # Verify tables
    print("\n✓ Tables created:")
    from sqlalchemy import inspect
    inspector = inspect(engine)
    for table_name in inspector.get_table_names():
        columns = inspector.get_columns(table_name)
        print(f"  - {table_name} ({len(columns)} columns)")

    print("\n" + "=" * 60)
    print("Database initialization complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Run: python scripts/load_sample_data.py")
    print("  2. Verify: python scripts/verify_data.py")


if __name__ == "__main__":
    main()
