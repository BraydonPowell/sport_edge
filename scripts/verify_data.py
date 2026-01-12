"""
Verify loaded data with sanity check queries.
Shows summary statistics and sample records.

Usage:
    python scripts/verify_data.py
"""

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_schema import get_session, Game, Odds
from edge.odds_math import compute_edge_from_american


def main():
    """Run verification queries."""
    print("=" * 60)
    print("Verifying Database Contents")
    print("=" * 60)

    session = get_session()

    # Count records
    games_count = session.query(Game).count()
    odds_count = session.query(Odds).count()

    print(f"\n✓ Database Statistics:")
    print(f"  - Total games: {games_count}")
    print(f"  - Total odds records: {odds_count}")

    # Sample games
    print(f"\n✓ Sample Games:")
    print("-" * 60)
    sample_games = session.query(Game).limit(5).all()
    for game in sample_games:
        print(
            f"  {game.date.strftime('%Y-%m-%d')} | "
            f"{game.away_team} @ {game.home_team} | "
            f"Score: {game.away_score}-{game.home_score} | "
            f"Winner: {game.winner}"
        )

    # Sample odds
    print(f"\n✓ Sample Odds:")
    print("-" * 60)
    sample_odds = session.query(Odds).limit(5).all()
    for odds in sample_odds:
        print(
            f"  {odds.game_id} | {odds.book} | "
            f"Home: {odds.home_ml:+.0f} | Away: {odds.away_ml:+.0f} | "
            f"Source: {odds.source}"
        )

    # Test edge calculation on first odds record
    if sample_odds:
        print(f"\n✓ Sample Edge Calculation:")
        print("-" * 60)
        first_odds = sample_odds[0]
        p_model = 0.55  # Example model probability

        edge_info = compute_edge_from_american(
            p_model, first_odds.home_ml, first_odds.away_ml, "home"
        )

        print(f"  Game: {first_odds.game_id}")
        print(f"  Odds: {first_odds.home_ml:+.0f} / {first_odds.away_ml:+.0f}")
        print(f"  Model probability (home): {p_model:.2%}")
        print(f"  Market probability (home): {edge_info['p_market_fair']:.2%}")
        print(f"  Edge: {edge_info['edge_pct']:+.2f}%")
        print(f"  Expected Value: {edge_info['ev']:+.4f} units")

    # Date range
    if games_count > 0:
        earliest = session.query(Game).order_by(Game.date.asc()).first()
        latest = session.query(Game).order_by(Game.date.desc()).first()
        print(f"\n✓ Date Range:")
        print(f"  - Earliest game: {earliest.date.strftime('%Y-%m-%d')}")
        print(f"  - Latest game: {latest.date.strftime('%Y-%m-%d')}")

    # Games with odds
    games_with_odds = (
        session.query(Game)
        .join(Odds)
        .distinct()
        .count()
    )
    print(f"\n✓ Coverage:")
    print(f"  - Games with odds: {games_with_odds}/{games_count} ({games_with_odds/games_count*100:.1f}%)")

    session.close()

    print("\n" + "=" * 60)
    print("Verification complete!")
    print("=" * 60)
    print("\nDatabase is ready for feature engineering and modeling.")


if __name__ == "__main__":
    main()
