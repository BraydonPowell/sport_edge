"""
Prediction script with injury adjustments.

Loads injury data and adjusts team Elo ratings before making predictions.

Usage:
    export ODDS_API_KEY=your_key_here
    python scripts/predict_with_injuries.py
"""

import sys
import os
import json
import csv
from pathlib import Path
from datetime import datetime
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from features.build import build_features_from_db, EloRatingSystem
from edge.odds_math import compute_edge_from_american


API_KEY = os.environ.get('ODDS_API_KEY')

SPORT_KEYS = {
    'NBA': 'basketball_nba',
    'NHL': 'icehockey_nhl',
    'NFL': 'americanfootball_nfl'
}

LEAGUE_PARAMS = {
    'NBA': {'initial_elo': 1500, 'k_factor': 20, 'home_advantage': 100},
    'NHL': {'initial_elo': 1500, 'k_factor': 20, 'home_advantage': 50},
    'NFL': {'initial_elo': 1500, 'k_factor': 30, 'home_advantage': 80}
}


def load_injury_adjustments():
    """Load injury data from file."""
    try:
        with open('data/current_injuries.json', 'r') as f:
            data = json.load(f)
            return data.get('injuries', {})
    except FileNotFoundError:
        print("⚠️  No injury data found. Run fetch_live_injuries.py first.")
        return {}


def get_team_injuries(injuries, league, team_name):
    """Return a list of injury records for a given team."""
    return injuries.get(league, {}).get(team_name, [])


def format_injury_list(injury_list, max_players=6):
    """Format injuries for compact display."""
    if not injury_list:
        return ""
    items = []
    for injury in injury_list[:max_players]:
        player = injury.get("player", "Unknown")
        status = injury.get("status", "Unknown")
        items.append(f"{player} ({status})")
    suffix = "…" if len(injury_list) > max_players else ""
    return ", ".join(items) + suffix


def get_injury_adjustment(team_name, league):
    """Get Elo adjustment for injuries."""
    injuries = load_injury_adjustments()
    league_injuries = injuries.get(league, {})
    team_injuries = league_injuries.get(team_name, [])

    if not team_injuries:
        return 0

    return sum(injury.get('impact', 0) for injury in team_injuries)


def log_recommendations(recommendations, filename="data/live_bets.csv"):
    """Append recommended bets to a CSV for ROI tracking."""
    if not recommendations:
        return

    Path("data").mkdir(exist_ok=True)
    file_exists = Path(filename).exists()

    fieldnames = [
        "logged_at",
        "league",
        "home_team",
        "away_team",
        "bet_team",
        "odds",
        "edge_pct",
        "ev",
        "bookmaker",
        "commence_time",
        "p_home",
        "p_away",
        "p_market_home",
        "p_market_away",
    ]

    with open(filename, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for rec in recommendations:
            writer.writerow({
                "logged_at": datetime.utcnow().isoformat(),
                "league": rec["league"],
                "home_team": rec["home_team"],
                "away_team": rec["away_team"],
                "bet_team": rec["bet"],
                "odds": f"{rec['odds']:.0f}",
                "edge_pct": f"{rec['edge']:.2f}",
                "ev": f"{rec['ev']:.4f}",
                "bookmaker": rec.get("bookmaker", ""),
                "commence_time": rec["time"].isoformat(),
                "p_home": f"{rec.get('p_home', 0):.6f}",
                "p_away": f"{rec.get('p_away', 0):.6f}",
                "p_market_home": f"{rec.get('p_market_home', 0):.6f}",
                "p_market_away": f"{rec.get('p_market_away', 0):.6f}",
            })


def get_current_elos_with_injuries(league):
    """Get current Elo ratings adjusted for injuries."""
    params = LEAGUE_PARAMS[league]

    try:
        features_df = build_features_from_db(
            league=league,
            initial_elo=params['initial_elo'],
            k_factor=params['k_factor'],
            home_advantage=params['home_advantage']
        )

        if len(features_df) == 0:
            print(f"⚠️  No historical data for {league}. Using default ratings.")
            return EloRatingSystem(
                initial_elo=params['initial_elo'],
                k_factor=params['k_factor'],
                home_advantage=params['home_advantage']
            ), {}

        # Rebuild Elo system
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

        # Apply injury adjustments
        injury_adjustments = {}
        for team in elo.ratings.keys():
            adjustment = get_injury_adjustment(team, league)
            if adjustment != 0:
                injury_adjustments[team] = adjustment
                elo.ratings[team] += adjustment  # Negative adjustment for injuries

        return elo, injury_adjustments

    except Exception as e:
        print(f"⚠️  Error loading {league} data: {e}")
        return EloRatingSystem(
            initial_elo=params['initial_elo'],
            k_factor=params['k_factor'],
            home_advantage=params['home_advantage']
        ), {}


def fetch_games_for_league(league):
    """Fetch today's games."""
    if not API_KEY:
        return []

    sport_key = SPORT_KEYS.get(league)
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    params = {
        'apiKey': API_KEY,
        'regions': 'us',
        'markets': 'h2h',
        'oddsFormat': 'american'
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        games = []
        for event in data:
            commence_time = datetime.fromisoformat(event['commence_time'].replace('Z', '+00:00'))
            now = datetime.now(commence_time.tzinfo)
            hours_until_game = (commence_time - now).total_seconds() / 3600

            if hours_until_game < 0 or hours_until_game > 24:
                continue

            home_team = event['home_team']
            away_team = event['away_team']

            if not event.get('bookmakers'):
                continue

            bookmaker = event['bookmakers'][0]
            h2h_market = next((m for m in bookmaker['markets'] if m['key'] == 'h2h'), None)

            if not h2h_market or len(h2h_market['outcomes']) < 2:
                continue

            home_odds = None
            away_odds = None

            for outcome in h2h_market['outcomes']:
                if outcome['name'] == home_team:
                    home_odds = outcome['price']
                elif outcome['name'] == away_team:
                    away_odds = outcome['price']

            if home_odds is None or away_odds is None:
                continue

            games.append({
                'league': league,
                'home_team': home_team,
                'away_team': away_team,
                'home_ml': home_odds,
                'away_ml': away_odds,
                'commence_time': commence_time,
                'bookmaker': bookmaker['key']
            })

        return games

    except Exception as e:
        print(f"❌ API request failed: {e}")
        return []


def predict_game(elo, home_team, away_team, home_ml, away_ml):
    """Predict a game."""
    p_home, p_away = elo.predict_game(home_team, away_team)
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
    print("🏥 INJURY-ADJUSTED PREDICTIONS")
    print("=" * 60)
    print(f"\nCurrent Time: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}")

    if not API_KEY:
        print("\n❌ ERROR: ODDS_API_KEY environment variable not set")
        return

    # Load injuries
    injuries = load_injury_adjustments()
    if injuries:
        print(f"\n✓ Loaded injury data")
    else:
        print(f"\n⚠️  No injury data loaded - predictions will use base Elo only")

    all_recommendations = []

    for league in ['NBA', 'NHL', 'NFL']:
        print(f"\n{'=' * 60}")
        print(f"{league} GAMES (Injury-Adjusted)")
        print(f"{'=' * 60}")

        games = fetch_games_for_league(league)

        if not games:
            print(f"No {league} games in next 24 hours")
            continue

        print(f"✓ Found {len(games)} game(s)")

        # Get Elo ratings with injury adjustments
        elo, injury_adjustments = get_current_elos_with_injuries(league)
        print(f"✓ Loaded {len(elo.ratings)} team ratings")

        if injury_adjustments:
            print(f"\n⚠️  Injury Adjustments Applied:")
            for team, adj in injury_adjustments.items():
                print(f"  {team}: {adj:+.0f} Elo")

        # Show top teams
        if len(elo.ratings) > 0:
            print(f"\nTop 5 {league} teams (injury-adjusted):")
            sorted_teams = sorted(elo.ratings.items(), key=lambda x: x[1], reverse=True)[:5]
            for team, rating in sorted_teams:
                adj = injury_adjustments.get(team, 0)
                adj_str = f" ({adj:+.0f})" if adj != 0 else ""
                print(f"  {team}: {rating:.0f}{adj_str}")

        # Analyze games
        print(f"\n{'=' * 60}")
        print(f"{league} PREDICTIONS & EDGES")
        print(f"{'=' * 60}")

        league_recommendations = []

        for game in games:
            print(f"\n{game['home_team']} vs {game['away_team']}")
            print(f"Time: {game['commence_time'].strftime('%I:%M %p')}")
            print(f"Odds: {game['home_ml']:+.0f} / {game['away_ml']:+.0f} ({game['bookmaker']})")

            # Show injury adjustments for this game
            home_adj = injury_adjustments.get(game['home_team'], 0)
            away_adj = injury_adjustments.get(game['away_team'], 0)
            if home_adj != 0 or away_adj != 0:
                print(
                    f"🏥 Injuries: {game['home_team']} ({home_adj:+.0f}) | "
                    f"{game['away_team']} ({away_adj:+.0f})"
                )

            print("-" * 60)

            result = predict_game(
                elo,
                game['home_team'],
                game['away_team'],
                game['home_ml'],
                game['away_ml']
            )

            print(f"Model: {game['home_team']} {result['p_home']:.1%} | {game['away_team']} {result['p_away']:.1%}")
            print(f"Market: {result['home_edge']['p_market_fair']:.1%} | {result['away_edge']['p_market_fair']:.1%}")

            home_ev = result['home_edge']['ev']
            away_ev = result['away_edge']['ev']

            print(f"\nHome edge: {result['home_edge']['edge_pct']:+.1f}% (EV: {home_ev:+.3f})")
            print(f"Away edge: {result['away_edge']['edge_pct']:+.1f}% (EV: {away_ev:+.3f})")

            if home_ev > 0.01:
                league_recommendations.append({
                    'league': league,
                    'game': f"{game['home_team']} vs {game['away_team']}",
                    'home_team': game['home_team'],
                    'away_team': game['away_team'],
                    'bet': game['home_team'],
                    'odds': game['home_ml'],
                    'edge': result['home_edge']['edge_pct'],
                    'ev': home_ev,
                    'time': game['commence_time'],
                    'bookmaker': game['bookmaker'],
                    'p_home': result['p_home'],
                    'p_away': result['p_away'],
                    'p_market_home': result['home_edge']['p_market_fair'],
                    'p_market_away': result['away_edge']['p_market_fair'],
                })
                print(f"✅ BET: {game['home_team']} at {game['home_ml']:+.0f}")

            if away_ev > 0.01:
                league_recommendations.append({
                    'league': league,
                    'game': f"{game['home_team']} vs {game['away_team']}",
                    'home_team': game['home_team'],
                    'away_team': game['away_team'],
                    'bet': game['away_team'],
                    'odds': game['away_ml'],
                    'edge': result['away_edge']['edge_pct'],
                    'ev': away_ev,
                    'time': game['commence_time'],
                    'bookmaker': game['bookmaker'],
                    'p_home': result['p_home'],
                    'p_away': result['p_away'],
                    'p_market_home': result['home_edge']['p_market_fair'],
                    'p_market_away': result['away_edge']['p_market_fair'],
                })
                print(f"✅ BET: {game['away_team']} at {game['away_ml']:+.0f}")

        all_recommendations.extend(league_recommendations)

    # Top 5 bets by edge
    if all_recommendations:
        print("\n" + "=" * 60)
        print("🔥 TOP 5 BEST BETS (Highest Edge)")
        print("=" * 60)

        top_bets = sorted(all_recommendations, key=lambda x: x['edge'], reverse=True)[:5]

        for i, bet in enumerate(top_bets, 1):
            print(f"\n#{i}. {bet['bet']} at {bet['odds']:+.0f} ({bet['league']})")
            print(f"    💰 Expected Value: {bet['ev']:+.3f} ({bet['edge']:+.1f}% edge)")
            print(f"    🕐 Game Time: {bet['time'].strftime('%I:%M %p')}")
            print(f"    🏆 Matchup: {bet['game']}")
            home_injuries = format_injury_list(
                get_team_injuries(injuries, bet['league'], bet['home_team'])
            )
            away_injuries = format_injury_list(
                get_team_injuries(injuries, bet['league'], bet['away_team'])
            )
            if home_injuries or away_injuries:
                home_str = f"{bet['home_team']}: {home_injuries}" if home_injuries else f"{bet['home_team']}: none"
                away_str = f"{bet['away_team']}: {away_injuries}" if away_injuries else f"{bet['away_team']}: none"
                print(f"    🏥 Injuries: {home_str} | {away_str}")

        log_recommendations(top_bets)
        print("\n✓ Logged bets to data/live_bets.csv")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
