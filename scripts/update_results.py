"""
Fetch final scores from ESPN and update the database.

Usage:
    python scripts/update_results.py
"""

import sys
import os
from datetime import datetime, timedelta
import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_schema import get_session, Game


LEAGUE_ENDPOINTS = {
    "NBA": ("basketball", "nba"),
    "NHL": ("hockey", "nhl"),
    "NFL": ("football", "nfl"),
}


def fetch_scoreboard(sport, league, date_str):
    url = f"https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard"
    params = {"dates": date_str}
    resp = requests.get(url, params=params, timeout=15)
    if resp.status_code != 200:
        return []
    data = resp.json()
    return data.get("events", [])


def get_competitors(event):
    competitions = event.get("competitions", [])
    if not competitions:
        return None, None, None
    comp = competitions[0]
    status = comp.get("status", {}).get("type", {})
    competitors = comp.get("competitors", [])
    home = None
    away = None
    for c in competitors:
        if c.get("homeAway") == "home":
            home = c
        elif c.get("homeAway") == "away":
            away = c
    return home, away, status


def winner_from_scores(home_score, away_score):
    if home_score > away_score:
        return "home"
    if away_score > home_score:
        return "away"
    return "draw"


def find_game(session, league, home_team, away_team, event_dt):
    start = datetime.combine(event_dt.date(), datetime.min.time())
    end = datetime.combine(event_dt.date(), datetime.max.time())
    return (
        session.query(Game)
        .filter(Game.league == league)
        .filter(Game.home_team == home_team)
        .filter(Game.away_team == away_team)
        .filter(Game.date >= start)
        .filter(Game.date <= end)
        .first()
    )


def update_results_for_league(session, league, sport_key, league_key, dates):
    updated = 0
    created = 0
    for date_str in dates:
        events = fetch_scoreboard(sport_key, league_key, date_str)
        for event in events:
            home, away, status = get_competitors(event)
            if not home or not away:
                continue
            if not status.get("completed"):
                continue
            event_dt = datetime.fromisoformat(event["date"].replace("Z", "+00:00"))
            home_team = home.get("team", {}).get("displayName", "Unknown")
            away_team = away.get("team", {}).get("displayName", "Unknown")
            home_score = int(float(home.get("score", 0)))
            away_score = int(float(away.get("score", 0)))
            winner = winner_from_scores(home_score, away_score)

            game = find_game(session, league, home_team, away_team, event_dt)
            if game:
                game.home_score = home_score
                game.away_score = away_score
                game.winner = winner
                updated += 1
            else:
                game_id = f"{league}_{event.get('id', event_dt.strftime('%Y%m%d'))}"
                game = Game(
                    game_id=game_id,
                    date=event_dt,
                    league=league,
                    home_team=home_team,
                    away_team=away_team,
                    home_score=home_score,
                    away_score=away_score,
                    winner=winner,
                )
                session.add(game)
                created += 1
    return updated, created


def main():
    session = get_session()
    today = datetime.utcnow().date()
    dates = [
        (today - timedelta(days=1)).strftime("%Y%m%d"),
        today.strftime("%Y%m%d"),
    ]

    print("=" * 60)
    print("Updating Final Scores from ESPN")
    print("=" * 60)

    total_updated = 0
    total_created = 0

    for league, (sport_key, league_key) in LEAGUE_ENDPOINTS.items():
        updated, created = update_results_for_league(
            session, league, sport_key, league_key, dates
        )
        total_updated += updated
        total_created += created
        print(f"{league}: updated {updated}, created {created}")

    session.commit()
    session.close()

    print("-" * 60)
    print(f"Total updated: {total_updated}")
    print(f"Total created: {total_created}")
    print("=" * 60)


if __name__ == "__main__":
    main()
