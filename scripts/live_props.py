"""
Fetch live NBA props and compute value recommendations.
"""

import json
import os
import sys
import io
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from props.fetcher import fetch_live_props, StatsFetcher, build_player_stats_map_for_props, get_current_season
from props.analyzer import PropsAnalyzer


def _load_env(project_root: str) -> None:
    env_path = os.path.join(project_root, ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())


def _fetch_today_event_count() -> int:
    api_key = os.environ.get("ODDS_API_KEY")
    if not api_key:
        return 0

    url = "https://api.the-odds-api.com/v4/sports/basketball_nba/events"
    try:
        response = requests.get(url, params={"apiKey": api_key, "dateFormat": "iso"}, timeout=10)
        response.raise_for_status()
        events = response.json()
    except Exception:
        return 0

    eastern = ZoneInfo("America/New_York")
    now = datetime.now(tz=eastern)
    count = 0
    for event in events:
        try:
            commence = datetime.fromisoformat(event.get("commence_time", "").replace("Z", "+00:00")).astimezone(eastern)
        except Exception:
            continue
        if commence.date() == now.date():
            count += 1
    return count


def main() -> None:
    _load_env(PROJECT_ROOT)

    league = os.environ.get("PROPS_LEAGUE", "NBA")
    if league != "NBA":
        print(json.dumps({"props": []}))
        return

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()

    events_limit = 10
    try:
        live_props = fetch_live_props(league, hours_ahead=72, max_events=events_limit, max_props=2000)
        eastern = ZoneInfo("America/New_York")
        today_et = datetime.now(tz=eastern).date()
        live_props = [
            prop for prop in live_props
            if prop.game_date and prop.game_date.astimezone(eastern).date() == today_et
        ]

        fetcher = StatsFetcher()
        season = get_current_season(league)
        player_stats = build_player_stats_map_for_props(live_props, league, season, fetcher, max_players=120)

        name_map = {stats.player_name.lower(): stats for stats in player_stats.values()}
        for prop in live_props:
            stats = name_map.get(prop.player_name.lower())
            if stats:
                prop.player_id = stats.player_id
                if stats.team and prop.team and stats.team != prop.team and stats.team == prop.opponent:
                    prop.team, prop.opponent = prop.opponent, prop.team

        analyzer = PropsAnalyzer(
            min_games=5,
            edge_threshold=1.0,
            ev_threshold=0.0,
            shrink_weight=float(os.environ.get("PROB_SHRINK_W", "0.7")),
            kelly_mult=float(os.environ.get("KELLY_MULT", "0.25")),
            max_stake=float(os.environ.get("MAX_STAKE", "0.02")),
            bankroll=float(os.environ.get("BANKROLL", "1000")),
        )
        edges = analyzer.analyze_props(live_props, player_stats) if live_props else []

        eligible = [
            edge for edge in edges
            if edge.sample_size >= analyzer.min_games
            and edge.recommended_side is not None
        ]
        eligible.sort(
            key=lambda e: max(e.ev_over * e.stake_frac_over, e.ev_under * e.stake_frac_under),
            reverse=True,
        )
        event_ids = {prop.event_id for prop in live_props if prop.event_id}
        events_today = _fetch_today_event_count()
        results = {
            "props": [edge.to_dict() for edge in eligible[:20]],
            "meta": {
                "events_with_props": len(event_ids),
                "events_today": events_today,
                "props_count": len(live_props),
            },
        }
    except Exception as e:
        results = {
            "props": [],
            "error": str(e),
            "meta": {
                "events_with_props": 0,
                "events_today": 0,
                "props_count": 0,
            },
        }

    sys.stdout = old_stdout
    print(json.dumps(results))


if __name__ == "__main__":
    main()
