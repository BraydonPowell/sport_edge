"""
Fetch today's games and odds from The Odds API.

Requires API key: https://the-odds-api.com/
Free tier: 500 requests/month

Usage:
    export ODDS_API_KEY=your_key_here
    python scripts/fetch_todays_games.py
"""

import os
import sys
import requests
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from features.build import build_features_from_db, EloRatingSystem
from edge.odds_math import compute_edge_from_american


# API configuration
API_KEY = os.environ.get('ODDS_API_KEY')
BASE_URL = 'https://api.the-odds-api.com/v4'

# Sport keys for The Odds API
SPORT_KEYS = {
    'NBA': 'basketball_nba',
    'NHL': 'icehockey_nhl',
    'NFL': 'americanfootball_nfl'
}

# League-specific Elo parameters
LEAGUE_PARAMS = {
    'NBA': {'initial_elo': 1500, 'k_factor': 20, 'home_advantage': 100},
    'NHL': {'initial_elo': 1500, 'k_factor': 20, 'home_advantage': 50},
    'NFL': {'initial_elo': 1500, 'k_factor': 30, 'home_advantage': 80}
}


def fetch_games_for_league(league):
    """Fetch today's games for a specific league."""
    if not API_KEY:
        print("❌ ODDS_API_KEY environment variable not set")
        print("   Get a free API key at: https://the-odds-api.com/")
        return []

    sport_key = SPORT_KEYS.get(league)
    if not sport_key:
        print(f"❌ Unknown league: {league}")
        return []

    url = f"{BASE_URL}/sports/{sport_key}/odds"
    params = {
        'apiKey': API_KEY,
        'regions': 'us',
        'markets': 'h2h',  # head-to-head (moneyline)
        'oddsFormat': 'american',
        'dateFormat': 'iso'
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        games = []
        for event in data:
            # Check if game is within next 24 hours
            commence_time = datetime.fromisoformat(event['commence_time'].replace('Z', '+00:00'))
            now = datetime.now(commence_time.tzinfo)
            hours_until_game = (commence_time - now).total_seconds() / 3600

            # Skip games that already started or are more than 24 hours away
            if hours_until_game < 0 or hours_until_game > 24:
                continue

            # Get home/away teams and odds
            home_team = event['home_team']
            away_team = event['away_team']

            # Get odds from first bookmaker (usually DraftKings or FanDuel)
            if not event.get('bookmakers'):
                continue

            bookmaker = event['bookmakers'][0]
            h2h_market = next((m for m in bookmaker['markets'] if m['key'] == 'h2h'), None)

            if not h2h_market or len(h2h_market['outcomes']) < 2:
                continue

            # Find home and away odds
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

    except requests.exceptions.RequestException as e:
        print(f"❌ API request failed: {e}")
        return []
    except Exception as e:
        print(f"❌ Error parsing API response: {e}")
        return []


def get_current_elos(league):
    """Get current Elo ratings for a league from database."""
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

        return elo

    except Exception as e:
        print(f"⚠️  Error loading {league} data: {e}")
        return EloRatingSystem(
            initial_elo=params['initial_elo'],
            k_factor=params['k_factor'],
            home_advantage=params['home_advantage']
        )


def predict_game(elo, home_team, away_team, home_ml, away_ml):
    """Predict a single game and show edge."""
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
    print("UPCOMING GAMES (Next 24 Hours) - Live Data from The Odds API")
    print("=" * 60)
    print(f"\nCurrent Time: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}")

    if not API_KEY:
        print("\n❌ ERROR: ODDS_API_KEY environment variable not set")
        print("\nTo use this script:")
        print("1. Get a free API key at: https://the-odds-api.com/")
        print("2. Set the environment variable:")
        print("   export ODDS_API_KEY=your_key_here")
        print("3. Run this script again")
        return

    all_recommendations = []

    for league in ['NBA', 'NHL', 'NFL']:
        print(f"\n{'=' * 60}")
        print(f"{league} GAMES")
        print(f"{'=' * 60}")

        # Fetch today's games
        games = fetch_games_for_league(league)

        if not games:
            print(f"No {league} games today or API error")
            continue

        print(f"✓ Found {len(games)} game(s)")

        # Load Elo ratings
        elo = get_current_elos(league)
        print(f"✓ Loaded {len(elo.ratings)} team ratings")

        if len(elo.ratings) > 0:
            print(f"\nTop 5 {league} teams by Elo:")
            sorted_teams = sorted(elo.ratings.items(), key=lambda x: x[1], reverse=True)[:5]
            for team, rating in sorted_teams:
                print(f"  {team}: {rating:.0f}")

        # Analyze each game
        print(f"\n{'=' * 60}")
        print(f"{league} PREDICTIONS & EDGES")
        print(f"{'=' * 60}")

        league_recommendations = []

        for game in games:
            print(f"\n{game['home_team']} vs {game['away_team']}")
            print(f"Time: {game['commence_time'].strftime('%I:%M %p')}")
            print(f"Odds: {game['home_ml']:+.0f} / {game['away_ml']:+.0f} ({game['bookmaker']})")
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

            # Recommendations (1% threshold)
            if home_ev > 0.01:
                league_recommendations.append({
                    'league': league,
                    'game': f"{game['home_team']} vs {game['away_team']}",
                    'bet': game['home_team'],
                    'odds': game['home_ml'],
                    'edge': result['home_edge']['edge_pct'],
                    'ev': home_ev,
                    'time': game['commence_time']
                })
                print(f"✅ BET: {game['home_team']} at {game['home_ml']:+.0f}")

            if away_ev > 0.01:
                league_recommendations.append({
                    'league': league,
                    'game': f"{game['home_team']} vs {game['away_team']}",
                    'bet': game['away_team'],
                    'odds': game['away_ml'],
                    'edge': result['away_edge']['edge_pct'],
                    'ev': away_ev,
                    'time': game['commence_time']
                })
                print(f"✅ BET: {game['away_team']} at {game['away_ml']:+.0f}")

        all_recommendations.extend(league_recommendations)

    # Final summary
    print("\n" + "=" * 60)
    print("BETTING RECOMMENDATIONS SUMMARY")
    print("=" * 60)

    if all_recommendations:
        print(f"\n{len(all_recommendations)} bet(s) with positive EV:\n")

        for league in ['NBA', 'NHL', 'NFL']:
            league_recs = [r for r in all_recommendations if r['league'] == league]
            if league_recs:
                print(f"\n{league}:")
                for rec in league_recs:
                    print(f"  ✅ {rec['bet']} at {rec['odds']:+.0f}")
                    print(f"     Edge: {rec['edge']:+.1f}% | EV: {rec['ev']:+.3f}")
                    print(f"     Time: {rec['time'].strftime('%I:%M %p')}")
                    print(f"     Game: {rec['game']}\n")
    else:
        print("\n❌ No positive EV bets found.")
        print("   (Threshold: 1% EV)")

    # Show top 5 best bets by EV
    if all_recommendations:
        print("\n" + "=" * 60)
        print("🔥 TOP 5 BEST BETS (Highest Expected Value)")
        print("=" * 60)

        # Sort by EV descending and take top 5
        top_bets = sorted(all_recommendations, key=lambda x: x['ev'], reverse=True)[:5]

        for i, bet in enumerate(top_bets, 1):
            print(f"\n#{i}. {bet['bet']} at {bet['odds']:+.0f} ({bet['league']})")
            print(f"    💰 Expected Value: {bet['ev']:+.3f} ({bet['edge']:+.1f}% edge)")
            print(f"    🕐 Game Time: {bet['time'].strftime('%I:%M %p')}")
            print(f"    🏆 Matchup: {bet['game']}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
