"""
Fetch LIVE injury data from ESPN's public API.

ESPN provides free injury endpoints for NBA, NHL, and NFL.

Usage:
    python scripts/fetch_live_injuries.py
"""

import sys
import os
import requests
from datetime import datetime
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def status_to_impact(status):
    """Map ESPN status text to an Elo impact value."""
    status_lower = status.lower()
    if "out" in status_lower or "suspended" in status_lower:
        return -25
    if "doubtful" in status_lower:
        return -15
    if "questionable" in status_lower:
        return -10
    if "day-to-day" in status_lower or "day to day" in status_lower:
        return -8
    if "probable" in status_lower:
        return -5
    return -5


def fetch_injuries_espn(sport, league):
    """Fetch live injuries from ESPN's public API."""
    print(f"\nFetching live {league} injuries from ESPN...")

    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/injuries"
        headers = {
            "User-Agent": "Mozilla/5.0"
        }
        response = requests.get(url, headers=headers, timeout=15)

        if response.status_code != 200:
            print(f"❌ API returned status {response.status_code}")
            return {}

        data = response.json()
        injuries_by_team = {}

        for team in data.get("injuries", []):
            team_name = team.get("displayName") or "Unknown Team"
            team_injuries = team.get("injuries", [])

            for injury in team_injuries:
                athlete = injury.get("athlete", {})
                player_name = athlete.get("displayName") or injury.get("displayName") or "Unknown Player"
                status = injury.get("status") or injury.get("type", {}).get("description") or "Unknown"
                description = injury.get("shortComment") or injury.get("longComment") or "No details"
                impact = status_to_impact(status)

                if team_name not in injuries_by_team:
                    injuries_by_team[team_name] = []

                injuries_by_team[team_name].append({
                    "player": player_name.strip(),
                    "status": status,
                    "description": description,
                    "impact": impact,
                })

        print(f"✓ Found injuries for {len(injuries_by_team)} teams")
        return injuries_by_team

    except Exception as e:
        print(f"❌ Error fetching {league} injuries: {e}")
        return {}


def save_injury_data(injuries, filename='data/current_injuries.json'):
    """Save injury data to JSON file."""
    os.makedirs('data', exist_ok=True)

    output = {
        'last_updated': datetime.now().isoformat(),
        'source': 'live_api',
        'injuries': injuries
    }

    with open(filename, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n✓ Saved to {filename}")


def display_injuries(league_injuries, league):
    """Display injuries in readable format."""
    print(f"\n{'=' * 60}")
    print(f"{league} INJURY REPORT - LIVE DATA")
    print(f"{'=' * 60}")

    if not league_injuries:
        print("✓ No injuries found or API unavailable")
        return

    total_injuries = 0

    for team_name, injuries in sorted(league_injuries.items()):
        if injuries:
            print(f"\n{team_name}:")
            print("-" * 60)

            for injury in injuries:
                status_emoji = {
                    'Out': '🔴',
                    'Doubtful': '🟠',
                    'Questionable': '🟡',
                    'Day-To-Day': '🟢'
                }.get(injury['status'], '⚪')

                # Try to determine status from description if not in status field
                desc = injury['description'].lower() if injury['description'] else ''
                if 'out' in desc and status_emoji == '⚪':
                    status_emoji = '🔴'
                elif 'doubtful' in desc and status_emoji == '⚪':
                    status_emoji = '🟠'
                elif 'questionable' in desc and status_emoji == '⚪':
                    status_emoji = '🟡'

                print(f"  {status_emoji} {injury['player']}")
                print(f"     Status: {injury['status']}")
                print(f"     Injury: {injury['description']}")
                print(f"     Impact: {injury['impact']} Elo")
                total_injuries += 1

    print(f"\nTotal injuries: {total_injuries}")


def main():
    print("=" * 60)
    print("LIVE INJURY TRACKER")
    print("=" * 60)
    print(f"\nCurrent Time: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}")

    all_injuries = {
        'NBA': {},
        'NHL': {},
        'NFL': {}
    }

    # Fetch NBA injuries
    print("\n" + "=" * 60)
    print("Fetching NBA Injuries...")
    print("=" * 60)

    nba_injuries = fetch_injuries_espn("basketball", "nba")
    all_injuries['NBA'] = nba_injuries
    display_injuries(nba_injuries, 'NBA')

    # Fetch NHL injuries
    print("\n" + "=" * 60)
    print("Fetching NHL Injuries...")
    print("=" * 60)

    nhl_injuries = fetch_injuries_espn("hockey", "nhl")
    all_injuries['NHL'] = nhl_injuries
    display_injuries(nhl_injuries, 'NHL')

    # Fetch NFL injuries
    print("\n" + "=" * 60)
    print("Fetching NFL Injuries...")
    print("=" * 60)

    nfl_injuries = fetch_injuries_espn("football", "nfl")
    all_injuries['NFL'] = nfl_injuries
    display_injuries(nfl_injuries, 'NFL')

    # Save data
    save_injury_data(all_injuries)

    print("\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    print("\n1. Review injury data: cat data/current_injuries.json")
    print("2. Run predictions with injuries:")
    print("   export ODDS_API_KEY=xxx")
    print("   python scripts/predict_with_injuries.py")
    print("\n3. Injuries are now live for NBA/NHL/NFL via ESPN.")


if __name__ == "__main__":
    main()
