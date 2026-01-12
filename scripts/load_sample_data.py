"""
Load sample data into database.
Ingests sample games and odds from CSV files.

Usage:
    python scripts/load_sample_data.py
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ingest.games import ingest_games_to_db
from ingest.odds import ingest_odds_to_db


def main():
    """Load sample data into database."""
    print("=" * 60)
    print("Loading Sample Data")
    print("=" * 60)

    # Determine paths
    base_dir = os.path.dirname(os.path.dirname(__file__))
    games_csv = os.path.join(base_dir, "data", "sample_games.csv")
    odds_csv = os.path.join(base_dir, "data", "sample_odds.csv")

    # Verify files exist
    if not os.path.exists(games_csv):
        print(f"ERROR: Sample games file not found: {games_csv}")
        return

    if not os.path.exists(odds_csv):
        print(f"ERROR: Sample odds file not found: {odds_csv}")
        return

    print(f"\n1. Loading games from: {games_csv}")
    print("-" * 60)
    games_count = ingest_games_to_db(games_csv, league="NBA", replace=True)

    print(f"\n2. Loading odds from: {odds_csv}")
    print("-" * 60)
    odds_count = ingest_odds_to_db(odds_csv, replace=True)

    print("\n" + "=" * 60)
    print("Data loading complete!")
    print("=" * 60)
    print(f"\nSummary:")
    print(f"  - Games loaded: {games_count}")
    print(f"  - Odds records loaded: {odds_count}")
    print("\nNext steps:")
    print("  - Run: python scripts/verify_data.py")


if __name__ == "__main__":
    main()
