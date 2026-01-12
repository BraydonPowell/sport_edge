"""
Ingestion module for loading historical odds snapshots.
Supports CSV input; API integration can be added later.
"""

import pandas as pd
from datetime import datetime
from typing import Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_schema import get_session, Odds


def load_odds_from_csv(csv_path: str) -> pd.DataFrame:
    """
    Load odds from CSV file.

    Expected CSV columns:
    - game_id: unique game identifier (must match games table)
    - book: sportsbook name
    - timestamp: when odds were captured (YYYY-MM-DD HH:MM:SS or datetime)
    - home_ml: home moneyline in American odds format (e.g., -110, +150)
    - away_ml: away moneyline in American odds format
    - source: source type (e.g., "closing", "opening", "api_snapshot")

    Returns:
        DataFrame with standardized odds data
    """
    print(f"Loading odds from {csv_path}...")
    df = pd.read_csv(csv_path)

    required_cols = ["game_id", "book", "timestamp", "home_ml", "away_ml"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")

    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Add default source if not provided
    if "source" not in df.columns:
        df["source"] = "closing"

    print(f"Loaded {len(df)} odds records from {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"Books: {df['book'].unique()}")
    return df


def ingest_odds_to_db(
    csv_path: str,
    session=None,
    replace: bool = False
) -> int:
    """
    Load odds from CSV and insert into database.

    Args:
        csv_path: path to CSV file
        session: database session (creates new if None)
        replace: if True, delete existing odds before inserting

    Returns:
        Number of odds records inserted
    """
    df = load_odds_from_csv(csv_path)

    close_session = False
    if session is None:
        session = get_session()
        close_session = True

    try:
        if replace:
            print("Deleting existing odds...")
            session.query(Odds).delete()
            session.commit()

        inserted = 0
        for _, row in df.iterrows():
            odds = Odds(
                game_id=row["game_id"],
                book=row["book"],
                timestamp=row["timestamp"],
                home_ml=float(row["home_ml"]) if pd.notna(row["home_ml"]) else None,
                away_ml=float(row["away_ml"]) if pd.notna(row["away_ml"]) else None,
                source=row["source"],
            )
            session.add(odds)
            inserted += 1

        session.commit()
        print(f"Inserted {inserted} odds records into database")
        return inserted

    finally:
        if close_session:
            session.close()


def get_closing_odds(game_id: str, session=None) -> Optional[dict]:
    """
    Retrieve closing odds for a specific game.

    Args:
        game_id: game identifier
        session: database session (creates new if None)

    Returns:
        Dictionary with closing odds or None if not found
    """
    close_session = False
    if session is None:
        session = get_session()
        close_session = True

    try:
        odds = (
            session.query(Odds)
            .filter(Odds.game_id == game_id, Odds.source == "closing")
            .order_by(Odds.timestamp.desc())
            .first()
        )

        if odds:
            return {
                "game_id": odds.game_id,
                "book": odds.book,
                "timestamp": odds.timestamp,
                "home_ml": odds.home_ml,
                "away_ml": odds.away_ml,
            }
        return None

    finally:
        if close_session:
            session.close()


if __name__ == "__main__":
    # Example usage
    import argparse

    parser = argparse.ArgumentParser(description="Ingest odds data from CSV")
    parser.add_argument("csv_path", help="Path to odds CSV file")
    parser.add_argument("--replace", action="store_true", help="Replace existing data")

    args = parser.parse_args()

    count = ingest_odds_to_db(args.csv_path, replace=args.replace)
    print(f"Ingestion complete: {count} odds records")
