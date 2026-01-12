"""
Fetch injury data for NBA, NHL, and NFL from ESPN's public API.

This is a free, unofficial API that doesn't require authentication.
Data includes: player name, position, status (out/doubtful/questionable), injury description.

Usage:
    python scripts/fetch_injuries.py
"""

import sys
import os
import requests
from datetime import datetime
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ESPN API endpoints (unofficial, free)
ESPN_INJURY_URLS = {
    'NBA': 'https://site.web.api.espn.com/apis/site/v2/sports/basketball/nba/teams',
    'NHL': 'https://site.web.api.espn.com/apis/site/v2/sports/hockey/nhl/teams',
    'NFL': 'https://site.web.api.espn.com/apis/site/v2/sports/football/nfl/teams'
}


def fetch_team_injuries(league, team_id):
    """Fetch injuries for a specific team."""
    try:
        # ESPN team injuries endpoint
        url = f"https://site.web.api.espn.com/apis/site/v2/sports/{league.lower()}/{league.lower()}/teams/{team_id}"

        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return []

        data = response.json()

        # Navigate to injuries section
        injuries = []
        if 'team' in data and 'injuries' in data['team']:
            for injury in data['team']['injuries']:
                injuries.append({
                    'player': injury.get('athlete', {}).get('displayName', 'Unknown'),
                    'position': injury.get('athlete', {}).get('position', {}).get('abbreviation', ''),
                    'status': injury.get('status', 'Unknown'),
                    'description': injury.get('details', {}).get('detail', 'No details'),
                    'date': injury.get('date', datetime.now().isoformat())
                })

        return injuries

    except Exception as e:
        print(f"Error fetching injuries for team {team_id}: {e}")
        return []


def fetch_all_teams_for_league(league):
    """Get all team IDs for a league."""
    try:
        url = ESPN_INJURY_URLS[league]
        response = requests.get(url, timeout=10)

        if response.status_code != 200:
            return []

        data = response.json()
        teams = []

        if 'sports' in data and len(data['sports']) > 0:
            leagues = data['sports'][0].get('leagues', [])
            if leagues:
                for team in leagues[0].get('teams', []):
                    team_info = team.get('team', {})
                    teams.append({
                        'id': team_info.get('id'),
                        'name': team_info.get('displayName'),
                        'abbreviation': team_info.get('abbreviation')
                    })

        return teams

    except Exception as e:
        print(f"Error fetching teams for {league}: {e}")
        return []


def fetch_league_injuries(league):
    """Fetch all injuries for a league."""
    print(f"\n{'=' * 60}")
    print(f"Fetching {league} Injuries from ESPN API")
    print(f"{'=' * 60}")

    teams = fetch_all_teams_for_league(league)

    if not teams:
        print(f"❌ Could not fetch teams for {league}")
        return {}

    print(f"✓ Found {len(teams)} teams")

    all_injuries = {}
    teams_with_injuries = 0

    for team in teams:
        injuries = fetch_team_injuries(league, team['id'])

        if injuries:
            all_injuries[team['name']] = {
                'abbreviation': team['abbreviation'],
                'injuries': injuries
            }
            teams_with_injuries += 1

    print(f"✓ Found injuries for {teams_with_injuries} teams")

    return all_injuries


def display_injuries(league_injuries, league):
    """Display injuries in a readable format."""
    print(f"\n{'=' * 60}")
    print(f"{league} INJURY REPORT")
    print(f"{'=' * 60}")

    if not league_injuries:
        print("✓ No injuries reported")
        return

    for team_name, team_data in league_injuries.items():
        injuries = team_data['injuries']

        if injuries:
            print(f"\n{team_name} ({team_data['abbreviation']}):")
            print("-" * 60)

            for injury in injuries:
                status_emoji = {
                    'Out': '🔴',
                    'Doubtful': '🟠',
                    'Questionable': '🟡',
                    'Day-To-Day': '🟢'
                }.get(injury['status'], '⚪')

                print(f"  {status_emoji} {injury['player']} ({injury['position']})")
                print(f"     Status: {injury['status']}")
                print(f"     Injury: {injury['description']}")
                print()


def calculate_impact_score(injuries):
    """
    Calculate a simple impact score based on injuries.

    Returns:
        float: Negative impact score (0 = no impact, -100+ = severe)
    """
    if not injuries:
        return 0.0

    impact = 0.0

    for injury in injuries:
        status = injury['status']
        position = injury['position']

        # Status impact
        if status == 'Out':
            base_impact = -30
        elif status == 'Doubtful':
            base_impact = -20
        elif status == 'Questionable':
            base_impact = -10
        else:
            base_impact = -5

        # Position multiplier (simplified - would need sport-specific logic)
        # For now, assume QB/PG/starting positions are more valuable
        if position in ['QB', 'PG', 'C', 'G']:  # Key positions
            multiplier = 2.0
        elif position in ['RB', 'WR', 'SG', 'SF']:
            multiplier = 1.5
        else:
            multiplier = 1.0

        impact += base_impact * multiplier

    return impact


def main():
    print("=" * 60)
    print("INJURY REPORT - ESPN API")
    print("=" * 60)
    print(f"\nFetching latest injury data for NBA, NHL, NFL...")
    print("This may take a minute...\n")

    all_league_injuries = {}

    for league in ['NBA', 'NHL', 'NFL']:
        injuries = fetch_league_injuries(league)
        all_league_injuries[league] = injuries
        display_injuries(injuries, league)

    # Save to JSON file
    output_file = 'data/current_injuries.json'
    os.makedirs('data', exist_ok=True)

    output_data = {
        'last_updated': datetime.now().isoformat(),
        'injuries': all_league_injuries
    }

    with open(output_file, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"✓ Injury data saved to {output_file}")
    print(f"{'=' * 60}")

    # Summary
    total_injuries = sum(
        len(team_data['injuries'])
        for league_injuries in all_league_injuries.values()
        for team_data in league_injuries.values()
    )

    print(f"\nTotal injuries tracked: {total_injuries}")
    print(f"Last updated: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}")


if __name__ == "__main__":
    main()
