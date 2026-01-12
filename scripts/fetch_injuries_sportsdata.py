"""
Fetch injury data using SportsDataIO API (free tier available).

Alternative: Manual injury tracking or scraping from public sources.

For MVP, this script provides:
1. Template for injury data structure
2. Manual input option
3. Framework for future API integration

Get API key from: https://sportsdata.io/ (free tier: 1000 requests/month)

Usage:
    export SPORTSDATA_API_KEY=your_key_here
    python scripts/fetch_injuries_sportsdata.py
"""

import sys
import os
import json
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# For now, use manual injury tracking
# This can be automated with paid APIs or web scraping

MANUAL_INJURIES = {
    'NBA': {
        # Example format - update manually or via API
        # Format: Team Name -> list of injuries
        'Boston Celtics': [
            {'player': 'Kristaps Porzingis', 'status': 'Out', 'description': 'Ankle injury', 'impact': -20}
        ],
        'Los Angeles Lakers': [
            {'player': 'Anthony Davis', 'status': 'Questionable', 'description': 'Hip soreness', 'impact': -15}
        ]
    },
    'NHL': {
        # Add NHL injuries here
    },
    'NFL': {
        # Add NFL injuries here
    }
}


def save_injury_data(injuries, filename='data/current_injuries.json'):
    """Save injury data to JSON file."""
    os.makedirs('data', exist_ok=True)

    output = {
        'last_updated': datetime.now().isoformat(),
        'source': 'manual',  # Change to 'api' when using real API
        'injuries': injuries
    }

    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"✓ Saved injury data to {filename}")


def load_injury_data(filename='data/current_injuries.json'):
    """Load injury data from JSON file."""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def display_injuries():
    """Display current injury data."""
    print("=" * 60)
    print("CURRENT INJURY REPORT")
    print("=" * 60)

    for league in ['NBA', 'NHL', 'NFL']:
        injuries = MANUAL_INJURIES.get(league, {})

        if not injuries:
            continue

        print(f"\n{league}:")
        print("-" * 60)

        for team, team_injuries in injuries.items():
            if team_injuries:
                print(f"\n  {team}:")
                for injury in team_injuries:
                    status_emoji = {
                        'Out': '🔴',
                        'Doubtful': '🟠',
                        'Questionable': '🟡'
                    }.get(injury['status'], '⚪')

                    print(f"    {status_emoji} {injury['player']}")
                    print(f"       Status: {injury['status']}")
                    print(f"       Injury: {injury['description']}")
                    print(f"       Impact: {injury['impact']} Elo points")


def get_team_injury_adjustment(team_name, league='NBA'):
    """
    Get Elo adjustment for a team based on injuries.

    Args:
        team_name: Team name
        league: League (NBA/NHL/NFL)

    Returns:
        int: Negative Elo adjustment (0 = no injuries, -50+ = major injuries)
    """
    league_injuries = MANUAL_INJURIES.get(league, {})
    team_injuries = league_injuries.get(team_name, [])

    if not team_injuries:
        return 0

    # Sum up impact scores
    total_impact = sum(injury.get('impact', 0) for injury in team_injuries)

    return total_impact


def main():
    print("\n" + "=" * 60)
    print("INJURY TRACKING SYSTEM")
    print("=" * 60)

    print("\n📋 Current Mode: Manual Entry")
    print("   To use API: Get key from https://sportsdata.io/")
    print("   Or implement web scraping from injury reports")

    display_injuries()

    # Save to file
    save_injury_data(MANUAL_INJURIES)

    print("\n" + "=" * 60)
    print("HOW TO UPDATE INJURIES:")
    print("=" * 60)
    print("1. Edit MANUAL_INJURIES dictionary in this file")
    print("2. Run: python scripts/fetch_injuries_sportsdata.py")
    print("3. Injury adjustments will be applied to predictions")
    print("\nImpact scores:")
    print("  - Superstar out: -30 to -50 Elo")
    print("  - Starter out: -15 to -25 Elo")
    print("  - Role player out: -5 to -10 Elo")
    print("  - Questionable: -5 to -15 Elo")

    print("\n" + "=" * 60)

    # Example usage
    print("\nExample adjustment:")
    lakers_adjustment = get_team_injury_adjustment('Los Angeles Lakers', 'NBA')
    print(f"  Lakers Elo adjustment: {lakers_adjustment}")


if __name__ == "__main__":
    main()
