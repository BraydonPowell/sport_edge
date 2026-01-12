"""
Predict today's games across NBA, NHL, and NFL using current Elo ratings.
Shows which bets have positive EV.

Usage:
    python scripts/predict_all_leagues.py
"""

import sys
import os
from datetime import datetime
import yaml

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from features.build import build_features_from_db, EloRatingSystem
from edge.odds_math import compute_edge_from_american


# League-specific Elo parameters
LEAGUE_PARAMS = {
    'NBA': {'initial_elo': 1500, 'k_factor': 20, 'home_advantage': 100},
    'NHL': {'initial_elo': 1500, 'k_factor': 20, 'home_advantage': 50},
    'NFL': {'initial_elo': 1500, 'k_factor': 30, 'home_advantage': 80}
}


def load_config():
    """Load config with league-specific parameters."""
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            if 'model' in config and 'elo' in config['model']:
                return config['model']['elo']
    return LEAGUE_PARAMS


def get_current_elos(league):
    """Get current Elo ratings for a league from all games in database."""
    print(f"Loading {league} Elo ratings from database...")

    # Get league-specific parameters
    params = LEAGUE_PARAMS[league]

    features_df = build_features_from_db(
        league=league,
        initial_elo=params['initial_elo'],
        k_factor=params['k_factor'],
        home_advantage=params['home_advantage']
    )

    # Rebuild Elo system to get final ratings
    elo = EloRatingSystem(
        initial_elo=params['initial_elo'],
        k_factor=params['k_factor'],
        home_advantage=params['home_advantage']
    )

    for _, game in features_df.iterrows():
        if game['home_score'] and game['away_score']:
            elo.update_ratings(
                game['home_team'],
                game['away_team'],
                int(game['home_score']),
                int(game['away_score'])
            )

    return elo, params


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


def process_league(league):
    """Process all games for a single league."""
    print(f"\n{'=' * 60}")
    print(f"{league} GAMES")
    print(f"{'=' * 60}")

    # Get current Elos
    try:
        elo, params = get_current_elos(league)
    except Exception as e:
        print(f"❌ No historical data for {league}. Skipping.")
        print(f"   Error: {e}")
        return []

    print(f"✓ Loaded {len(elo.ratings)} team ratings")

    if len(elo.ratings) > 0:
        print(f"\nTop 5 {league} teams by Elo:")
        sorted_teams = sorted(elo.ratings.items(), key=lambda x: x[1], reverse=True)[:5]
        for team, rating in sorted_teams:
            print(f"  {team}: {rating:.0f}")

    print(f"\n{'=' * 60}")
    print(f"ENTER {league} GAMES")
    print(f"{'=' * 60}")
    print(f"\nFormat: Home Team, Away Team, Home ML, Away ML")
    print(f"Example: Boston Celtics, New York Knicks, -150, +130")
    print(f"Type 'done' when finished\n")

    games = []
    while True:
        try:
            inp = input(f"{league} Game: ").strip()
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
                'league': league,
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
            break

    if not games:
        print(f"\nNo {league} games entered.")
        return []

    # Analyze games
    print(f"\n{'=' * 60}")
    print(f"{league} PREDICTIONS & EDGES")
    print(f"{'=' * 60}")

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
                'league': league,
                'game': f"{game['home_team']} vs {game['away_team']}",
                'bet': game['home_team'],
                'odds': game['home_ml'],
                'edge': result['home_edge']['edge_pct'],
                'ev': home_ev
            })
            print(f"✅ BET: {game['home_team']} at {game['home_ml']:+.0f}")

        if away_ev > 0.01:
            recommendations.append({
                'league': league,
                'game': f"{game['home_team']} vs {game['away_team']}",
                'bet': game['away_team'],
                'odds': game['away_ml'],
                'edge': result['away_edge']['edge_pct'],
                'ev': away_ev
            })
            print(f"✅ BET: {game['away_team']} at {game['away_ml']:+.0f}")

    return recommendations


def main():
    print("=" * 60)
    print("MULTI-LEAGUE PREDICTION & EDGE DETECTION")
    print("=" * 60)
    print("\nSupported leagues: NBA, NHL, NFL")
    print("Enter games for each league, or type 'skip' to skip a league")

    all_recommendations = []

    for league in ['NBA', 'NHL', 'NFL']:
        recs = process_league(league)
        all_recommendations.extend(recs)

    # Summary
    print("\n" + "=" * 60)
    print("ALL BETTING RECOMMENDATIONS")
    print("=" * 60)

    if all_recommendations:
        print(f"\n{len(all_recommendations)} bets with positive EV:\n")

        # Group by league
        for league in ['NBA', 'NHL', 'NFL']:
            league_recs = [r for r in all_recommendations if r['league'] == league]
            if league_recs:
                print(f"\n{league}:")
                for rec in league_recs:
                    print(f"  ✅ {rec['bet']} at {rec['odds']:+.0f}")
                    print(f"     Edge: {rec['edge']:+.1f}% | EV: {rec['ev']:+.3f}")
                    print(f"     Game: {rec['game']}\n")
    else:
        print("\n❌ No positive EV bets found across all leagues.")
        print("   (Threshold: 1% EV)")

    print("=" * 60)


if __name__ == "__main__":
    main()
