"""
Ingestion module for loading historical game results.
Supports CSV input; API integration can be added later.
"""

import pandas as pd
from datetime import datetime
from typing import Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_schema import get_session, Game


def load_games_from_csv(csv_path: str, league: str = "NBA") -> pd.DataFrame:
    """
    Load games from CSV file.

    Expected CSV columns:
    - game_id: unique identifier
    - date: game date (YYYY-MM-DD or datetime)
    - home_team: home team name
    - away_team: away team name
    - home_score: final home score
    - away_score: final away score

    Returns:
        DataFrame with standardized game data
    """
    print(f"Loading games from {csv_path}...")
    df = pd.read_csv(csv_path)

    required_cols = ["game_id", "date", "home_team", "away_team", "home_score", "away_score"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")

    df["date"] = pd.to_datetime(df["date"])
    df["league"] = league

    # Determine winner
    def get_winner(row):
        if pd.isna(row["home_score"]) or pd.isna(row["away_score"]):
            return None
        if row["home_score"] > row["away_score"]:
            return "home"
        elif row["away_score"] > row["home_score"]:
            return "away"
        else:
            return "draw"

    df["winner"] = df.apply(get_winner, axis=1)

    print(f"Loaded {len(df)} games from {df['date'].min()} to {df['date'].max()}")
    return df


def ingest_games_to_db(
    csv_path: str,
    league: str = "NBA",
    session=None,
    replace: bool = False
) -> int:
    """
    Load games from CSV and insert into database.

    Args:
        csv_path: path to CSV file
        league: league identifier
        session: database session (creates new if None)
        replace: if True, delete existing games before inserting

    Returns:
        Number of games inserted
    """
    df = load_games_from_csv(csv_path, league)

    close_session = False
    if session is None:
        session = get_session()
        close_session = True

    try:
        if replace:
            print("Deleting existing games...")
            session.query(Game).filter(Game.league == league).delete()
            session.commit()

        inserted = 0
        for _, row in df.iterrows():
            game = Game(
                game_id=row["game_id"],
                date=row["date"],
                league=row["league"],
                home_team=row["home_team"],
                away_team=row["away_team"],
                home_score=int(row["home_score"]) if pd.notna(row["home_score"]) else None,
                away_score=int(row["away_score"]) if pd.notna(row["away_score"]) else None,
                winner=row["winner"],
            )
            session.merge(game)  # Use merge to handle duplicates
            inserted += 1

        session.commit()
        print(f"Inserted {inserted} games into database")
        return inserted

    finally:
        if close_session:
            session.close()


if __name__ == "__main__":
    # Example usage
    import argparse

    parser = argparse.ArgumentParser(description="Ingest game data from CSV")
    parser.add_argument("csv_path", help="Path to games CSV file")
    parser.add_argument("--league", default="NBA", help="League identifier")
    parser.add_argument("--replace", action="store_true", help="Replace existing data")

    args = parser.parse_args()

    count = ingest_games_to_db(args.csv_path, args.league, replace=args.replace)
    print(f"Ingestion complete: {count} games")
