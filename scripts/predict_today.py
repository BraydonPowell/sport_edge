"""
Predict today's NBA games using current Elo ratings.
Shows which bets have positive EV.

Usage:
    python scripts/predict_today.py
"""

import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from features.build import build_features_from_db, EloRatingSystem
from edge.odds_math import compute_edge_from_american


def get_current_elos():
    """Get current Elo ratings from all games in database."""
    print("Loading current Elo ratings from database...")
    features_df = build_features_from_db()

    # Rebuild Elo system to get final ratings
    elo = EloRatingSystem()

    for _, game in features_df.iterrows():
        if game['home_score'] and game['away_score']:
            elo.update_ratings(
                game['home_team'],
                game['away_team'],
                int(game['home_score']),
                int(game['away_score'])
            )

    return elo


def predict_game(elo, home_team, away_team, home_ml, away_ml):
    """Predict a single game and show edge."""
    # Get predictions
    p_home, p_away = elo.predict_game(home_team, away_team)

    # Calculate edges
    home_edge = compute_edge_from_american(p_home, home_ml, away_ml, 'home')
    away_edge = compute_edge_from_american(p_away, home_ml, away_ml, 'away')

    return {
        'p_home': p_home,
        'p_away': p_away,
        'home_edge': home_edge,
        'away_edge': away_edge
    }


def main():
    print("=" * 60)
    print("TODAY'S GAMES - Prediction & Edge Detection")
    print("=" * 60)

    # Get current Elos
    elo = get_current_elos()

    print(f"\n✓ Loaded {len(elo.ratings)} team ratings")
    print(f"\nTop 5 teams by Elo:")
    sorted_teams = sorted(elo.ratings.items(), key=lambda x: x[1], reverse=True)[:5]
    for team, rating in sorted_teams:
        print(f"  {team}: {rating:.0f}")

    print("\n" + "=" * 60)
    print("ENTER TODAY'S GAMES")
    print("=" * 60)
    print("\nFormat: Home Team, Away Team, Home ML, Away ML")
    print("Example: Boston Celtics, New York Knicks, -150, +130")
    print("Type 'done' when finished\n")

    games = []
    while True:
        try:
            inp = input("Game: ").strip()
            if inp.lower() == 'done':
                break

            if not inp:
                continue

            parts = [p.strip() for p in inp.split(',')]
            if len(parts) != 4:
                print("  ❌ Need 4 values: home team, away team, home ML, away ML")
                continue

            home_team, away_team = parts[0], parts[1]
            home_ml = float(parts[2])
            away_ml = float(parts[3])

            games.append({
                'home_team': home_team,
                'away_team': away_team,
                'home_ml': home_ml,
                'away_ml': away_ml
            })
            print(f"  ✓ Added: {home_team} vs {away_team}")

        except ValueError:
            print("  ❌ Invalid odds format. Use numbers like -150 or +130")
        except KeyboardInterrupt:
            print("\n\nStopped.")
            return

    if not games:
        print("\nNo games entered. Exiting.")
        return

    # Analyze games
    print("\n" + "=" * 60)
    print("PREDICTIONS & EDGES")
    print("=" * 60)

    recommendations = []

    for game in games:
        print(f"\n{game['home_team']} vs {game['away_team']}")
        print("-" * 60)

        result = predict_game(
            elo,
            game['home_team'],
            game['away_team'],
            game['home_ml'],
            game['away_ml']
        )

        # Show predictions
        print(f"Model: {game['home_team']} {result['p_home']:.1%} | {game['away_team']} {result['p_away']:.1%}")
        print(f"Market: {result['home_edge']['p_market_fair']:.1%} | {result['away_edge']['p_market_fair']:.1%}")

        # Show edges
        home_ev = result['home_edge']['ev']
        away_ev = result['away_edge']['ev']

        print(f"\nHome edge: {result['home_edge']['edge_pct']:+.1f}% (EV: {home_ev:+.3f})")
        print(f"Away edge: {result['away_edge']['edge_pct']:+.1f}% (EV: {away_ev:+.3f})")

        # Recommendations
        if home_ev > 0.01:  # 1% threshold
            recommendations.append({
                'game': f"{game['home_team']} vs {game['away_team']}",
                'bet': game['home_team'],
                'odds': game['home_ml'],
                'edge': result['home_edge']['edge_pct'],
                'ev': home_ev
            })
            print(f"✅ BET: {game['home_team']} at {game['home_ml']:+.0f}")

        if away_ev > 0.01:
            recommendations.append({
                'game': f"{game['home_team']} vs {game['away_team']}",
                'bet': game['away_team'],
                'odds': game['away_ml'],
                'edge': result['away_edge']['edge_pct'],
                'ev': away_ev
            })
            print(f"✅ BET: {game['away_team']} at {game['away_ml']:+.0f}")

    # Summary
    print("\n" + "=" * 60)
    print("BETTING RECOMMENDATIONS")
    print("=" * 60)

    if recommendations:
        print(f"\n{len(recommendations)} bets with positive EV:\n")
        for rec in recommendations:
            print(f"✅ {rec['bet']} at {rec['odds']:+.0f}")
            print(f"   Edge: {rec['edge']:+.1f}% | EV: {rec['ev']:+.3f}")
            print(f"   Game: {rec['game']}\n")
    else:
        print("\n❌ No positive EV bets found.")
        print("   (Threshold: 1% EV)")

    print("=" * 60)


if __name__ == "__main__":
    main()
