"""
Data fetcher for player stats and props.
Fetches from ESPN for stats and The Odds API for live props.
"""

import requests
import json
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from props.models import PlayerStats, PropBet, PropType, GameLog

try:
    from nba_api.stats.static import players as nba_players
    from nba_api.stats.endpoints import playergamelog as nba_playergamelog
    NBA_API_AVAILABLE = True
except Exception:
    NBA_API_AVAILABLE = False

# Load .env file if it exists
def _load_env():
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())

_load_env()

# The Odds API configuration
ODDS_API_KEY = os.environ.get('ODDS_API_KEY')
ODDS_API_BASE = 'https://api.the-odds-api.com/v4'

# Sport keys for The Odds API
SPORT_KEYS = {
    'NBA': 'basketball_nba',
    'NHL': 'icehockey_nhl',
    'NFL': 'americanfootball_nfl'
}

# Map The Odds API prop market names to our PropType (league-specific)
PROP_MARKET_MAP_NBA = {
    'player_points': PropType.POINTS,
    'player_rebounds': PropType.REBOUNDS,
    'player_assists': PropType.ASSISTS,
    'player_threes': PropType.THREES,
    'player_points_rebounds_assists': PropType.PTS_REB_AST,
    'player_points_rebounds': PropType.PTS_REB,
    'player_points_assists': PropType.PTS_AST,
    'player_rebounds_assists': PropType.REB_AST,
    'player_steals': PropType.STEALS,
    'player_blocks': PropType.BLOCKS,
}

PROP_MARKET_MAP_NFL = {
    'player_pass_yds': PropType.PASSING_YARDS,
    'player_pass_tds': PropType.PASSING_TDS,
    'player_rush_yds': PropType.RUSHING_YARDS,
    'player_rush_tds': PropType.RUSHING_TDS,
    'player_reception_yds': PropType.RECEIVING_YARDS,
    'player_receptions': PropType.RECEPTIONS,
    'player_reception_tds': PropType.RECEIVING_TDS,
}

PROP_MARKET_MAP_NHL = {
    'player_goals': PropType.GOALS,
    'player_assists': PropType.NHL_ASSISTS,
    'player_points': PropType.NHL_POINTS,
    'player_shots_on_goal': PropType.SHOTS,
    'player_saves': PropType.SAVES,
}

PROP_MARKET_MAPS = {
    'NBA': PROP_MARKET_MAP_NBA,
    'NFL': PROP_MARKET_MAP_NFL,
    'NHL': PROP_MARKET_MAP_NHL,
}


class StatsFetcher:
    """
    Fetches player statistics from ESPN API.
    Supports NBA, NFL, and NHL.
    """

    ESPN_API_BASE = "https://site.api.espn.com/apis/site/v2/sports"

    LEAGUE_CONFIG = {
        "NBA": {
            "sport": "basketball",
            "league": "nba",
            "stat_mapping": {
                "points": "points",
                "rebounds": "rebounds",
                "assists": "assists",
                "steals": "steals",
                "blocks": "blocks",
                "threes": "threePointFieldGoalsMade",
                "minutes": "minutes",
            },
            "combo_stats": {
                "pts_reb_ast": ["points", "rebounds", "assists"],
                "pts_reb": ["points", "rebounds"],
                "pts_ast": ["points", "assists"],
                "reb_ast": ["rebounds", "assists"],
            }
        },
        "NFL": {
            "sport": "football",
            "league": "nfl",
            "stat_mapping": {
                "passing_yards": "passingYards",
                "passing_tds": "passingTouchdowns",
                "rushing_yards": "rushingYards",
                "rushing_tds": "rushingTouchdowns",
                "receiving_yards": "receivingYards",
                "receptions": "receptions",
                "receiving_tds": "receivingTouchdowns",
            },
        },
        "NHL": {
            "sport": "hockey",
            "league": "nhl",
            "stat_mapping": {
                "goals": "goals",
                "assists": "assists",
                "points": "points",
                "shots": "shots",
                "saves": "saves",
            },
        },
    }

    def __init__(self, cache_dir: str = "data/props_cache"):
        """Initialize fetcher with optional cache directory."""
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self._player_id_cache: Dict[tuple, Optional[str]] = {}
        self._nba_player_id_map: Optional[Dict[str, str]] = None

    def get_player_gamelog(
        self,
        player_id: str,
        league: str,
        season: Optional[int] = None,
    ) -> Optional[PlayerStats]:
        """
        Fetch player game log for the season.

        Args:
            player_id: ESPN player ID
            league: NBA, NFL, or NHL
            season: Season year

        Returns:
            PlayerStats object with game logs
        """
        if league not in self.LEAGUE_CONFIG:
            raise ValueError(f"Unsupported league: {league}")

        season = season or get_current_season(league)
        config = self.LEAGUE_CONFIG[league]
        sport = config["sport"]
        league_code = config["league"]

        # Try cache first
        cache_file = os.path.join(self.cache_dir, f"{league}_{player_id}_{season}.json")
        if os.path.exists(cache_file):
            cache_age = datetime.now().timestamp() - os.path.getmtime(cache_file)
            if cache_age < 3600:  # 1 hour cache
                with open(cache_file, 'r') as f:
                    cached = json.load(f)
                    return self._parse_cached_stats(cached, league)

        player_stats = self._fetch_player_gamelog_with_season(
            player_id,
            league,
            season,
            cache_file,
        )
        if player_stats and player_stats.games_played == 0 and season and season > 2000:
            fallback_cache = os.path.join(self.cache_dir, f"{league}_{player_id}_{season - 1}.json")
            player_stats = self._fetch_player_gamelog_with_season(
                player_id,
                league,
                season - 1,
                fallback_cache,
            )

        return player_stats

    def _fetch_player_gamelog_with_season(
        self,
        player_id: str,
        league: str,
        season: int,
        cache_file: str,
    ) -> Optional[PlayerStats]:
        config = self.LEAGUE_CONFIG[league]
        sport = config["sport"]
        league_code = config["league"]
        url = f"{self.ESPN_API_BASE}/{sport}/{league_code}/players/{player_id}/gamelog"
        params = {"season": season}

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            player_stats = self._parse_player_gamelog(data, player_id, league)

            if player_stats:
                with open(cache_file, 'w') as f:
                    json.dump(player_stats.__dict__, f, default=str)

            return player_stats

        except Exception as e:
            print(f"Error fetching player {player_id} season {season}: {e}")
            return None

    def get_player_stats_by_name(
        self,
        player_name: str,
        league: str,
        season: Optional[int] = None,
        team_abbrs: Optional[List[str]] = None,
    ) -> Optional[PlayerStats]:
        """Resolve player name to ESPN ID, then fetch gamelog stats."""
        if league == "NBA" and NBA_API_AVAILABLE:
            season = season or get_current_season(league)
            season_key = get_nba_api_season(season)
            stats = self._get_nba_player_gamelog(player_name, season_key)
            if stats:
                return stats

        player_id = self.find_player_id_by_name(
            player_name,
            league,
            season=season,
            team_abbrs=team_abbrs,
        )
        if not player_id:
            return None
        return self.get_player_gamelog(player_id, league, season=season)

    def find_player_id_by_name(
        self,
        player_name: str,
        league: str,
        season: Optional[int] = None,
        team_abbrs: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Search ESPN APIs to resolve a player name to an ESPN ID."""
        cache_key = (league, _normalize_player_name(player_name))
        if cache_key in self._player_id_cache:
            return self._player_id_cache[cache_key]

        if league not in self.LEAGUE_CONFIG:
            return None

        season = season or get_current_season(league)

        if team_abbrs:
            roster_lookup = self._build_roster_lookup(league, season, team_abbrs)
            roster_match = roster_lookup.get(_normalize_player_name(player_name))
            if roster_match:
                self._player_id_cache[cache_key] = roster_match
                return roster_match

        config = self.LEAGUE_CONFIG[league]
        sport = config["sport"]
        league_code = config["league"]

        endpoints = [
            (f"{self.ESPN_API_BASE}/{sport}/{league_code}/athletes", {"search": player_name}),
            (f"{self.ESPN_API_BASE}/{sport}/{league_code}/players", {"search": player_name}),
            ("https://site.web.api.espn.com/apis/common/v3/search", {"query": player_name, "limit": 20}),
        ]

        best_match = None
        best_score = 0
        best_id = None

        for url, params in endpoints:
            try:
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
            except Exception:
                continue

            for candidate in _extract_candidates(data):
                candidate_id = _extract_espn_id(candidate.get("id"))
                candidate_name = candidate.get("name")
                score = _match_name_score(player_name, candidate_name)
                if candidate_id and score > best_score:
                    best_score = score
                    best_match = candidate_name
                    best_id = candidate_id

            if best_id and best_score >= 3:
                break

        if best_id:
            self._player_id_cache[cache_key] = best_id
        else:
            self._player_id_cache[cache_key] = None
            if best_match:
                print(f"Name search miss for {player_name}, closest match: {best_match}")

        return best_id

    def _build_roster_lookup(
        self,
        league: str,
        season: int,
        team_abbrs: List[str],
    ) -> Dict[str, str]:
        lookup: Dict[str, str] = {}
        team_id_map = self._get_team_id_map(league, season)

        for abbr in team_abbrs:
            team_id = team_id_map.get(abbr.upper())
            if not team_id:
                continue
            for athlete in self._get_team_roster(league, team_id):
                name = athlete.get("displayName") or athlete.get("fullName")
                athlete_id = athlete.get("id")
                if not name or not athlete_id:
                    continue
                lookup[_normalize_player_name(name)] = str(athlete_id)

        return lookup

    def _get_team_id_map(self, league: str, season: int) -> Dict[str, str]:
        cache_file = os.path.join(self.cache_dir, f"teams_{league}_{season}.json")
        if os.path.exists(cache_file):
            cache_age = datetime.now().timestamp() - os.path.getmtime(cache_file)
            if cache_age < 86400:
                with open(cache_file, "r") as f:
                    return json.load(f)

        if league not in self.LEAGUE_CONFIG:
            return {}

        config = self.LEAGUE_CONFIG[league]
        sport = config["sport"]
        league_code = config["league"]
        teams_url = f"https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league_code}/seasons/{season}/teams"

        try:
            response = requests.get(teams_url, params={"limit": 200}, timeout=10)
            response.raise_for_status()
            data = response.json()
        except Exception:
            return {}

        team_map: Dict[str, str] = {}
        for item in data.get("items", []):
            team_ref = item.get("$ref")
            if not team_ref:
                continue
            try:
                team_resp = requests.get(team_ref, timeout=10)
                team_resp.raise_for_status()
                team = team_resp.json()
            except Exception:
                continue
            abbr = team.get("abbreviation")
            team_id = team.get("id")
            if abbr and team_id:
                team_map[str(abbr).upper()] = str(team_id)

        if team_map:
            with open(cache_file, "w") as f:
                json.dump(team_map, f)

        return team_map

    def _get_team_roster(self, league: str, team_id: str) -> List[Dict[str, Any]]:
        cache_file = os.path.join(self.cache_dir, f"roster_{league}_{team_id}.json")
        if os.path.exists(cache_file):
            cache_age = datetime.now().timestamp() - os.path.getmtime(cache_file)
            if cache_age < 43200:
                with open(cache_file, "r") as f:
                    return json.load(f)

        if league not in self.LEAGUE_CONFIG:
            return []

        config = self.LEAGUE_CONFIG[league]
        sport = config["sport"]
        league_code = config["league"]
        roster_url = f"https://site.web.api.espn.com/apis/site/v2/sports/{sport}/{league_code}/teams/{team_id}/roster"

        try:
            response = requests.get(roster_url, timeout=10)
            response.raise_for_status()
            data = response.json()
        except Exception:
            return []

        athletes = data.get("athletes", [])
        if athletes:
            with open(cache_file, "w") as f:
                json.dump(athletes, f)

        return athletes

    def _get_nba_player_gamelog(self, player_name: str, season: str) -> Optional[PlayerStats]:
        player_id = self._get_nba_player_id(player_name)
        if not player_id:
            return None

        cache_file = os.path.join(self.cache_dir, f"nba_{player_id}_{season}.json")
        if os.path.exists(cache_file):
            cache_age = datetime.now().timestamp() - os.path.getmtime(cache_file)
            if cache_age < 3600:
                with open(cache_file, "r") as f:
                    cached = json.load(f)
                return self._parse_cached_stats(cached, "NBA")

        try:
            gamelog = nba_playergamelog.PlayerGameLog(player_id=player_id, season=season)
            df = gamelog.get_data_frames()[0]
        except Exception as e:
            print(f"Error fetching NBA gamelog for {player_name}: {e}")
            return None

        if df.empty:
            return None

        game_logs: List[GameLog] = []
        team = ""

        for _, row in df.iterrows():
            matchup = str(row.get("MATCHUP", "")).upper()
            team_abbr = str(row.get("TEAM_ABBREVIATION", "")).upper()
            team = team or team_abbr

            is_home = "VS" in matchup
            opponent = ""
            if "VS" in matchup:
                opponent = matchup.split("VS")[-1].strip()
            elif "@" in matchup:
                opponent = matchup.split("@")[-1].strip()

            game_id = str(row.get("GAME_ID", ""))
            date_raw = str(row.get("GAME_DATE", ""))
            try:
                game_date = datetime.strptime(date_raw, "%b %d, %Y")
            except Exception:
                game_date = datetime.now()

            stats = {
                "points": float(row.get("PTS", 0) or 0),
                "rebounds": float(row.get("REB", 0) or 0),
                "assists": float(row.get("AST", 0) or 0),
                "threes": float(row.get("FG3M", 0) or 0),
                "steals": float(row.get("STL", 0) or 0),
                "blocks": float(row.get("BLK", 0) or 0),
                "minutes": float(row.get("MIN", 0) or 0),
            }
            stats["pts_reb_ast"] = stats["points"] + stats["rebounds"] + stats["assists"]
            stats["pts_reb"] = stats["points"] + stats["rebounds"]
            stats["pts_ast"] = stats["points"] + stats["assists"]
            stats["reb_ast"] = stats["rebounds"] + stats["assists"]

            game_logs.append(GameLog(
                game_id=game_id,
                date=game_date,
                opponent=opponent,
                is_home=is_home,
                minutes=stats.get("minutes", 0),
                stats=stats,
            ))

        game_logs.sort(key=lambda x: x.date)

        player_stats = PlayerStats(
            player_id=player_id,
            player_name=_format_player_name(player_name),
            team=team,
            league="NBA",
            position="",
            game_logs=game_logs,
        )

        with open(cache_file, "w") as f:
            json.dump(_serialize_player_stats(player_stats), f)

        return player_stats

    def _get_nba_player_id(self, player_name: str) -> Optional[str]:
        if not NBA_API_AVAILABLE:
            return None
        if self._nba_player_id_map is None:
            self._nba_player_id_map = {}
            for player in nba_players.get_players():
                name = _normalize_player_name(player.get("full_name", ""))
                player_id = player.get("id")
                if name and player_id:
                    self._nba_player_id_map[name] = str(player_id)

        return self._nba_player_id_map.get(_normalize_player_name(player_name))

    def get_team_roster(self, team_id: str, league: str) -> List[Dict[str, str]]:
        """
        Get team roster with player IDs.

        Args:
            team_id: ESPN team ID
            league: NBA, NFL, or NHL

        Returns:
            List of player dicts with id, name, position
        """
        config = self.LEAGUE_CONFIG[league]
        sport = config["sport"]
        league_code = config["league"]

        url = f"{self.ESPN_API_BASE}/{sport}/{league_code}/teams/{team_id}/roster"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            players = []
            for athlete in data.get("athletes", []):
                for item in athlete.get("items", []):
                    players.append({
                        "id": item.get("id"),
                        "name": item.get("fullName"),
                        "position": item.get("position", {}).get("abbreviation", ""),
                    })

            return players

        except Exception as e:
            print(f"Error fetching roster: {e}")
            return []

    def get_todays_props(self, league: str) -> List[PropBet]:
        """
        Get today's prop lines from The Odds API.

        Args:
            league: NBA, NFL, or NHL

        Returns:
            List of PropBet objects
        """
        return fetch_live_props(league)

    def _parse_player_gamelog(
        self,
        data: Dict[str, Any],
        player_id: str,
        league: str,
    ) -> Optional[PlayerStats]:
        """Parse ESPN gamelog response into PlayerStats."""
        try:
            # Extract player info
            player_info = data.get("player", {})
            player_name = player_info.get("displayName", "Unknown")
            team = player_info.get("team", {}).get("abbreviation", "UNK")
            position = player_info.get("position", {}).get("abbreviation", "")

            # Parse game logs
            game_logs = []
            events = data.get("events", [])

            config = self.LEAGUE_CONFIG[league]
            stat_mapping = config["stat_mapping"]

            for event in events:
                event_id = event.get("eventId", "")
                event_date = event.get("gameDate", "")
                opponent = event.get("opponent", {}).get("abbreviation", "")
                is_home = event.get("homeAway", "") == "home"

                # Parse stats
                stats = {}
                raw_stats = event.get("stats", {})

                for our_key, espn_key in stat_mapping.items():
                    stats[our_key] = float(raw_stats.get(espn_key, 0))

                # Calculate combo stats for NBA
                if league == "NBA" and "combo_stats" in config:
                    for combo_key, components in config["combo_stats"].items():
                        stats[combo_key] = sum(stats.get(c, 0) for c in components)

                try:
                    game_date = datetime.fromisoformat(event_date.replace('Z', '+00:00'))
                except:
                    game_date = datetime.now()

                game_logs.append(GameLog(
                    game_id=event_id,
                    date=game_date,
                    opponent=opponent,
                    is_home=is_home,
                    minutes=stats.get("minutes", 0),
                    stats=stats,
                ))

            # Sort by date
            game_logs.sort(key=lambda x: x.date)

            return PlayerStats(
                player_id=player_id,
                player_name=player_name,
                team=team,
                league=league,
                position=position,
                game_logs=game_logs,
            )

        except Exception as e:
            print(f"Error parsing gamelog: {e}")
            return None

    def _parse_cached_stats(self, cached: Dict, league: str) -> PlayerStats:
        """Parse cached stats back into PlayerStats."""
        game_logs = []
        for log_data in cached.get("game_logs", []):
            game_logs.append(GameLog(
                game_id=log_data.get("game_id", ""),
                date=datetime.fromisoformat(log_data["date"]) if isinstance(log_data.get("date"), str) else log_data.get("date", datetime.now()),
                opponent=log_data.get("opponent", ""),
                is_home=log_data.get("is_home", False),
                minutes=log_data.get("minutes", 0),
                stats=log_data.get("stats", {}),
            ))

        return PlayerStats(
            player_id=cached.get("player_id", ""),
            player_name=cached.get("player_name", ""),
            team=cached.get("team", ""),
            league=cached.get("league", league),
            position=cached.get("position", ""),
            game_logs=game_logs,
        )


def fetch_live_props(
    league: str,
    hours_ahead: int = 24,
    max_events: Optional[int] = None,
    max_props: Optional[int] = None,
) -> List[PropBet]:
    """
    Fetch live player props from The Odds API.

    Args:
        league: NBA, NFL, or NHL

    Returns:
        List of PropBet objects for today's games
    """
    if not ODDS_API_KEY:
        print("Warning: ODDS_API_KEY not set, returning empty props")
        return []

    sport_key = SPORT_KEYS.get(league)
    if not sport_key:
        print(f"Unknown league: {league}")
        return []

    # First get today's events
    events_url = f"{ODDS_API_BASE}/sports/{sport_key}/events"
    params = {
        'apiKey': ODDS_API_KEY,
        'dateFormat': 'iso',
    }

    try:
        response = requests.get(events_url, params=params, timeout=10)
        if response.status_code != 200:
            try:
                payload = response.json()
            except Exception:
                payload = {}
            error_code = payload.get("error_code")
            if error_code:
                raise RuntimeError(f"Odds API error ({error_code}): {payload.get('message', 'Unknown')}")
            response.raise_for_status()
        events = response.json()
    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        print(f"Error fetching events: {e}")
        return []

    # Filter to games starting within next 24 hours
    now = datetime.now().astimezone()
    todays_events = []
    for event in events:
        try:
            commence_time = datetime.fromisoformat(event['commence_time'].replace('Z', '+00:00'))
            hours_until = (commence_time - now).total_seconds() / 3600
            if 0 <= hours_until <= hours_ahead:
                todays_events.append(event)
        except Exception:
            continue

    if not todays_events:
        print(f"No {league} games found in next 24 hours")
        return []

    # Determine which prop markets to fetch based on league
    if league == 'NBA':
        markets = 'player_points,player_rebounds,player_assists,player_threes,player_points_rebounds_assists'
    elif league == 'NFL':
        markets = 'player_pass_yds,player_rush_yds,player_reception_yds,player_receptions'
    else:  # NHL
        markets = 'player_goals,player_shots_on_goal,player_points'

    props = []

    todays_events.sort(key=lambda e: e.get('commence_time', ''))
    if max_events:
        todays_events = todays_events[:max_events]

    # Fetch props for each event
    for event in todays_events:
        event_id = event['id']
        home_team = event.get('home_team', '')
        away_team = event.get('away_team', '')
        commence_time = datetime.fromisoformat(event['commence_time'].replace('Z', '+00:00'))

        # Get team abbreviations
        home_abbr = _get_team_abbr(home_team, league)
        away_abbr = _get_team_abbr(away_team, league)

        # Fetch props for this event
        props_url = f"{ODDS_API_BASE}/sports/{sport_key}/events/{event_id}/odds"
        props_params = {
            'apiKey': ODDS_API_KEY,
            'regions': 'us',
            'markets': markets,
            'oddsFormat': 'american',
        }

        try:
            props_response = requests.get(props_url, params=props_params, timeout=15)
            if props_response.status_code != 200:
                try:
                    payload = props_response.json()
                except Exception:
                    payload = {}
                error_code = payload.get("error_code")
                if error_code:
                    raise RuntimeError(f"Odds API error ({error_code}): {payload.get('message', 'Unknown')}")
                props_response.raise_for_status()
            props_data = props_response.json()
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            print(f"Error fetching props for {event_id}: {e}")
            continue

        # Parse bookmaker odds - only use FanDuel, Bet365, DraftKings
        bookmakers = props_data.get('bookmakers', [])
        if not bookmakers:
            continue

        # Filter to only FanDuel, Bet365, DraftKings
        allowed_books = {'fanduel', 'bet365', 'draftkings'}
        filtered_books = [
            b for b in bookmakers
            if b.get('key') in allowed_books or b.get('title', '').lower().replace(' ', '') in allowed_books
        ]
        if not filtered_books:
            continue
        bookmakers = filtered_books

        prop_market_map = PROP_MARKET_MAPS.get(league, {})

        for bookmaker in bookmakers:
            book_name = bookmaker.get('title') or bookmaker.get('key', 'consensus')
            for market in bookmaker.get('markets', []):
                market_key = market.get('key', '')
                prop_type = prop_market_map.get(market_key)

                if not prop_type:
                    continue

                # Group outcomes by player (each player has over/under)
                player_outcomes = {}
                for outcome in market.get('outcomes', []):
                    player_name = outcome.get('description', '')
                    if not player_name:
                        continue

                    if player_name not in player_outcomes:
                        player_outcomes[player_name] = {'over': None, 'under': None, 'line': None}

                    name = outcome.get('name', '').lower()
                    price = outcome.get('price', 0)
                    point = outcome.get('point', 0)

                    if 'over' in name and player_outcomes[player_name]['over'] is None:
                        player_outcomes[player_name]['over'] = price
                        player_outcomes[player_name]['line'] = point
                    elif 'under' in name and player_outcomes[player_name]['under'] is None:
                        player_outcomes[player_name]['under'] = price
                        if player_outcomes[player_name]['line'] is None:
                            player_outcomes[player_name]['line'] = point

                # Create PropBet for each player with both over/under odds
                for player_name, odds in player_outcomes.items():
                    if odds['over'] is None or odds['under'] is None or odds['line'] is None:
                        continue

                    props.append(PropBet(
                        player_id=f"{player_name.replace(' ', '_').lower()}_{event_id}",
                        player_name=player_name,
                        team=home_abbr,  # Home team
                        opponent=away_abbr,  # Away team
                        game_date=commence_time,
                        prop_type=prop_type,
                        line=odds['line'],
                        over_odds=odds['over'],
                        under_odds=odds['under'],
                        book=book_name,
                        event_id=event_id,
                    ))

    # Apply max_props limit - distribute evenly across games
    if max_props and len(props) > max_props:
        # Group props by event_id
        props_by_event: Dict[str, List[PropBet]] = {}
        for prop in props:
            eid = prop.event_id or 'unknown'
            if eid not in props_by_event:
                props_by_event[eid] = []
            props_by_event[eid].append(prop)

        # Take proportional amount from each game
        num_events = len(props_by_event)
        props_per_event = max_props // num_events if num_events > 0 else max_props

        limited_props = []
        for eid, event_props in props_by_event.items():
            limited_props.extend(event_props[:props_per_event])

        props = limited_props[:max_props]

    print(f"Fetched {len(props)} live props for {league}")
    return props


def build_player_stats_map_for_props(
    props: List[PropBet],
    league: str,
    season: Optional[int] = None,
    fetcher: Optional[StatsFetcher] = None,
    max_players: Optional[int] = None,
) -> Dict[str, PlayerStats]:
    """Fetch PlayerStats for unique players in props."""
    if not props:
        return {}

    fetcher = fetcher or StatsFetcher()
    season = season or get_current_season(league)

    stats_map: Dict[str, PlayerStats] = {}
    seen_names = set()
    team_abbrs = set()

    for prop in props:
        if prop.team:
            team_abbrs.add(prop.team.upper())
        if prop.opponent:
            team_abbrs.add(prop.opponent.upper())

    for prop in props:
        name = (prop.player_name or "").strip()
        if not name:
            continue
        key = _normalize_player_name(name)
        if key in seen_names:
            continue
        seen_names.add(key)

        stats = fetcher.get_player_stats_by_name(
            name,
            league,
            season=season,
            team_abbrs=list(team_abbrs) if team_abbrs else None,
        )
        if stats and stats.games_played > 0:
            stats_map[stats.player_id] = stats
            if max_players and len(stats_map) >= max_players:
                break

    return stats_map


def get_current_season(league: str) -> int:
    """Infer current season year for ESPN endpoints."""
    now = datetime.now()
    if league == "NFL":
        return now.year - 1 if now.month <= 2 else now.year
    if league in {"NBA", "NHL"}:
        return now.year + 1 if now.month >= 9 else now.year
    return now.year


def get_nba_api_season(season_end_year: int) -> str:
    """Convert season end year to nba_api season string (e.g., 2026 -> 2025-26)."""
    start_year = season_end_year - 1
    end_suffix = str(season_end_year)[-2:]
    return f"{start_year}-{end_suffix}"


def _serialize_player_stats(player_stats: PlayerStats) -> Dict[str, Any]:
    return {
        "player_id": player_stats.player_id,
        "player_name": player_stats.player_name,
        "team": player_stats.team,
        "league": player_stats.league,
        "position": player_stats.position,
        "game_logs": [
            {
                "game_id": log.game_id,
                "date": log.date.isoformat(),
                "opponent": log.opponent,
                "is_home": log.is_home,
                "minutes": log.minutes,
                "stats": log.stats,
            }
            for log in player_stats.game_logs
        ],
    }


def _format_player_name(name: str) -> str:
    return " ".join(part for part in name.strip().split())


def _normalize_player_name(name: str) -> str:
    name = name.lower().replace(".", "").replace("'", "")
    name = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", name)
    name = re.sub(r"[^a-z0-9 ]+", " ", name)
    return re.sub(r"\s+", " ", name).strip()


def _match_name_score(target: str, candidate: Optional[str]) -> int:
    if not target or not candidate:
        return 0
    t_norm = _normalize_player_name(target)
    c_norm = _normalize_player_name(candidate)
    if not t_norm or not c_norm:
        return 0
    if t_norm == c_norm:
        return 3
    if t_norm in c_norm or c_norm in t_norm:
        return 2
    t_parts = t_norm.split()
    c_parts = c_norm.split()
    if t_parts and c_parts and t_parts[0] == c_parts[0] and t_parts[-1] == c_parts[-1]:
        return 1
    return 0


def _extract_espn_id(raw_id: Any) -> Optional[str]:
    if raw_id is None:
        return None
    if isinstance(raw_id, int):
        return str(raw_id)
    raw = str(raw_id).strip()
    if raw.isdigit():
        return raw
    match = re.search(r"(\d{3,})", raw)
    if match:
        return match.group(1)
    return None


def _extract_candidates(data: Dict[str, Any]) -> List[Dict[str, Optional[str]]]:
    candidates: List[Dict[str, Optional[str]]] = []

    athletes = data.get("athletes")
    if isinstance(athletes, list):
        for athlete in athletes:
            candidates.append({
                "id": athlete.get("id"),
                "name": athlete.get("displayName") or athlete.get("fullName"),
            })

    items = data.get("items")
    if isinstance(items, list):
        for item in items:
            item_type = item.get("type", "")
            uid = item.get("uid", "")
            if item_type == "athlete" or "athlete" in uid:
                candidates.append({
                    "id": item.get("id") or uid,
                    "name": item.get("displayName") or item.get("name") or item.get("title"),
                })

    results = data.get("searchResults")
    if isinstance(results, list):
        for result in results:
            if result.get("type") == "athlete":
                candidates.append({
                    "id": result.get("id") or result.get("uid"),
                    "name": result.get("displayName") or result.get("name"),
                })

    results = data.get("results")
    if isinstance(results, list):
        for result in results:
            if result.get("type") == "athlete":
                candidates.append({
                    "id": result.get("id") or result.get("uid"),
                    "name": result.get("displayName") or result.get("name"),
                })

    return candidates


def _get_team_abbr(team_name: str, league: str) -> str:
    """Convert full team name to abbreviation."""
    # Common team name to abbreviation mappings
    NBA_TEAMS = {
        'Atlanta Hawks': 'ATL', 'Boston Celtics': 'BOS', 'Brooklyn Nets': 'BKN',
        'Charlotte Hornets': 'CHA', 'Chicago Bulls': 'CHI', 'Cleveland Cavaliers': 'CLE',
        'Dallas Mavericks': 'DAL', 'Denver Nuggets': 'DEN', 'Detroit Pistons': 'DET',
        'Golden State Warriors': 'GSW', 'Houston Rockets': 'HOU', 'Indiana Pacers': 'IND',
        'Los Angeles Clippers': 'LAC', 'Los Angeles Lakers': 'LAL', 'Memphis Grizzlies': 'MEM',
        'Miami Heat': 'MIA', 'Milwaukee Bucks': 'MIL', 'Minnesota Timberwolves': 'MIN',
        'New Orleans Pelicans': 'NOP', 'New York Knicks': 'NYK', 'Oklahoma City Thunder': 'OKC',
        'Orlando Magic': 'ORL', 'Philadelphia 76ers': 'PHI', 'Phoenix Suns': 'PHX',
        'Portland Trail Blazers': 'POR', 'Sacramento Kings': 'SAC', 'San Antonio Spurs': 'SAS',
        'Toronto Raptors': 'TOR', 'Utah Jazz': 'UTA', 'Washington Wizards': 'WAS',
    }
    NFL_TEAMS = {
        'Arizona Cardinals': 'ARI', 'Atlanta Falcons': 'ATL', 'Baltimore Ravens': 'BAL',
        'Buffalo Bills': 'BUF', 'Carolina Panthers': 'CAR', 'Chicago Bears': 'CHI',
        'Cincinnati Bengals': 'CIN', 'Cleveland Browns': 'CLE', 'Dallas Cowboys': 'DAL',
        'Denver Broncos': 'DEN', 'Detroit Lions': 'DET', 'Green Bay Packers': 'GB',
        'Houston Texans': 'HOU', 'Indianapolis Colts': 'IND', 'Jacksonville Jaguars': 'JAX',
        'Kansas City Chiefs': 'KC', 'Las Vegas Raiders': 'LV', 'Los Angeles Chargers': 'LAC',
        'Los Angeles Rams': 'LAR', 'Miami Dolphins': 'MIA', 'Minnesota Vikings': 'MIN',
        'New England Patriots': 'NE', 'New Orleans Saints': 'NO', 'New York Giants': 'NYG',
        'New York Jets': 'NYJ', 'Philadelphia Eagles': 'PHI', 'Pittsburgh Steelers': 'PIT',
        'San Francisco 49ers': 'SF', 'Seattle Seahawks': 'SEA', 'Tampa Bay Buccaneers': 'TB',
        'Tennessee Titans': 'TEN', 'Washington Commanders': 'WAS',
    }
    NHL_TEAMS = {
        'Anaheim Ducks': 'ANA', 'Arizona Coyotes': 'ARI', 'Boston Bruins': 'BOS',
        'Buffalo Sabres': 'BUF', 'Calgary Flames': 'CGY', 'Carolina Hurricanes': 'CAR',
        'Chicago Blackhawks': 'CHI', 'Colorado Avalanche': 'COL', 'Columbus Blue Jackets': 'CBJ',
        'Dallas Stars': 'DAL', 'Detroit Red Wings': 'DET', 'Edmonton Oilers': 'EDM',
        'Florida Panthers': 'FLA', 'Los Angeles Kings': 'LAK', 'Minnesota Wild': 'MIN',
        'Montreal Canadiens': 'MTL', 'Nashville Predators': 'NSH', 'New Jersey Devils': 'NJD',
        'New York Islanders': 'NYI', 'New York Rangers': 'NYR', 'Ottawa Senators': 'OTT',
        'Philadelphia Flyers': 'PHI', 'Pittsburgh Penguins': 'PIT', 'San Jose Sharks': 'SJS',
        'Seattle Kraken': 'SEA', 'St. Louis Blues': 'STL', 'Tampa Bay Lightning': 'TBL',
        'Toronto Maple Leafs': 'TOR', 'Vancouver Canucks': 'VAN', 'Vegas Golden Knights': 'VGK',
        'Washington Capitals': 'WSH', 'Winnipeg Jets': 'WPG',
    }

    teams = {'NBA': NBA_TEAMS, 'NFL': NFL_TEAMS, 'NHL': NHL_TEAMS}.get(league, {})
    return teams.get(team_name, team_name[:3].upper())


def create_sample_player_stats(league: str) -> Dict[str, PlayerStats]:
    """
    Create sample player stats for testing/demo.
    In production, this would fetch from ESPN API.
    """
    import random

    sample_players = {
        "NBA": [
            ("1", "LeBron James", "LAL", "SF"),
            ("2", "Stephen Curry", "GSW", "PG"),
            ("3", "Giannis Antetokounmpo", "MIL", "PF"),
            ("4", "Luka Doncic", "LAL", "PG"),
            ("5", "Nikola Jokic", "DEN", "C"),
            ("6", "Joel Embiid", "PHI", "C"),
            ("7", "Kevin Durant", "PHX", "SF"),
            ("8", "Jayson Tatum", "BOS", "SF"),
            ("9", "Anthony Edwards", "MIN", "SG"),
            ("10", "Shai Gilgeous-Alexander", "OKC", "PG"),
        ],
        "NFL": [
            ("1", "Patrick Mahomes", "KC", "QB"),
            ("2", "Josh Allen", "BUF", "QB"),
            ("3", "Derrick Henry", "BAL", "RB"),
            ("4", "Tyreek Hill", "MIA", "WR"),
            ("5", "CeeDee Lamb", "DAL", "WR"),
        ],
        "NHL": [
            ("1", "Connor McDavid", "EDM", "C"),
            ("2", "Nathan MacKinnon", "COL", "C"),
            ("3", "Auston Matthews", "TOR", "C"),
            ("4", "Leon Draisaitl", "EDM", "C"),
            ("5", "Cale Makar", "COL", "D"),
        ],
    }

    players = {}
    for player_id, name, team, pos in sample_players.get(league, []):
        logs = []
        base_stats = _get_base_stats(league, pos)

        for i in range(30):  # 30 games
            game_date = datetime.now() - timedelta(days=60 - i*2)
            stats = {}

            for stat_name, (base, variance) in base_stats.items():
                # Add some randomness
                value = base + random.gauss(0, variance)
                stats[stat_name] = max(0, round(value, 1))

            # Calculate combo stats for NBA
            if league == "NBA":
                stats["pts_reb_ast"] = stats.get("points", 0) + stats.get("rebounds", 0) + stats.get("assists", 0)
                stats["pts_reb"] = stats.get("points", 0) + stats.get("rebounds", 0)
                stats["pts_ast"] = stats.get("points", 0) + stats.get("assists", 0)
                stats["reb_ast"] = stats.get("rebounds", 0) + stats.get("assists", 0)

            logs.append(GameLog(
                game_id=f"{league}_{player_id}_{i}",
                date=game_date,
                opponent=random.choice(["OPP1", "OPP2", "OPP3", "OPP4"]),
                is_home=i % 2 == 0,
                minutes=32 + random.gauss(0, 5),
                stats=stats,
            ))

        players[player_id] = PlayerStats(
            player_id=player_id,
            player_name=name,
            team=team,
            league=league,
            position=pos,
            game_logs=logs,
        )

    return players


def _get_base_stats(league: str, position: str) -> Dict[str, tuple]:
    """Get base stats (mean, std) for a position."""
    if league == "NBA":
        if position in ["PG", "SG"]:
            return {
                "points": (22, 6),
                "rebounds": (4, 2),
                "assists": (6, 2.5),
                "threes": (3, 1.5),
                "steals": (1.2, 0.8),
                "blocks": (0.3, 0.3),
            }
        elif position in ["SF", "PF"]:
            return {
                "points": (24, 7),
                "rebounds": (7, 3),
                "assists": (4, 2),
                "threes": (2, 1.2),
                "steals": (0.8, 0.6),
                "blocks": (0.8, 0.6),
            }
        else:  # C
            return {
                "points": (22, 6),
                "rebounds": (11, 3),
                "assists": (4, 2),
                "threes": (0.5, 0.5),
                "steals": (0.6, 0.5),
                "blocks": (1.5, 1),
            }
    elif league == "NFL":
        if position == "QB":
            return {
                "passing_yards": (280, 60),
                "passing_tds": (2.2, 1.2),
                "rushing_yards": (25, 20),
            }
        elif position == "RB":
            return {
                "rushing_yards": (75, 35),
                "rushing_tds": (0.5, 0.6),
                "receiving_yards": (25, 20),
                "receptions": (3, 2),
            }
        else:  # WR
            return {
                "receiving_yards": (70, 40),
                "receptions": (5, 2.5),
                "receiving_tds": (0.4, 0.5),
            }
    else:  # NHL
        if position in ["C", "LW", "RW"]:
            return {
                "goals": (0.4, 0.6),
                "assists": (0.6, 0.7),
                "points": (1.0, 1.0),
                "shots": (3, 2),
            }
        elif position == "D":
            return {
                "goals": (0.15, 0.35),
                "assists": (0.35, 0.5),
                "points": (0.5, 0.7),
                "shots": (2, 1.5),
            }
        else:  # G
            return {
                "saves": (28, 8),
            }

    return {}


def create_sample_props(
    player_stats: Dict[str, PlayerStats],
    league: str,
) -> List[PropBet]:
    """Create sample props for players."""
    import random

    props = []
    prop_types = {
        "NBA": [
            (PropType.POINTS, "points"),
            (PropType.REBOUNDS, "rebounds"),
            (PropType.ASSISTS, "assists"),
            (PropType.THREES, "threes"),
            (PropType.PTS_REB_AST, "pts_reb_ast"),
        ],
        "NFL": [
            (PropType.PASSING_YARDS, "passing_yards"),
            (PropType.RUSHING_YARDS, "rushing_yards"),
            (PropType.RECEIVING_YARDS, "receiving_yards"),
            (PropType.RECEPTIONS, "receptions"),
        ],
        "NHL": [
            (PropType.GOALS, "goals"),
            (PropType.NHL_ASSISTS, "assists"),
            (PropType.SHOTS, "shots"),
        ],
    }

    opponents = {
        "NBA": ["BOS", "MIA", "PHI", "NYK", "CHI", "LAC", "DEN", "DAL"],
        "NFL": ["KC", "BUF", "SF", "DAL", "PHI", "BAL", "DET", "MIA"],
        "NHL": ["TOR", "BOS", "NYR", "CAR", "COL", "VGK", "DAL", "EDM"],
    }

    for player_id, player in player_stats.items():
        for prop_type, stat_key in prop_types.get(league, []):
            # Check if player has this stat
            if player.games_played < 5:
                continue

            avg = player.get_stat_average(stat_key)
            if avg <= 0:
                continue

            # Create a line near the average
            line = round(avg * 2) / 2  # Round to nearest 0.5
            if line <= 0.5:
                line = 0.5

            # Generate odds with slight vig
            over_odds = random.choice([-115, -110, -120, -105])
            under_odds = random.choice([-105, -110, -115, -120])

            props.append(PropBet(
                player_id=player_id,
                player_name=player.player_name,
                team=player.team,
                opponent=random.choice(opponents.get(league, ["OPP"])),
                game_date=datetime.now() + timedelta(hours=random.randint(2, 12)),
                prop_type=prop_type,
                line=line,
                over_odds=over_odds,
                under_odds=under_odds,
            ))

    return props


if __name__ == "__main__":
    # Test sample data generation
    print("Generating sample NBA player stats...")
    nba_players = create_sample_player_stats("NBA")

    for pid, player in list(nba_players.items())[:3]:
        print(f"\n{player.player_name} ({player.team})")
        print(f"  Games: {player.games_played}")
        print(f"  PPG: {player.get_stat_average('points'):.1f}")
        print(f"  RPG: {player.get_stat_average('rebounds'):.1f}")
        print(f"  APG: {player.get_stat_average('assists'):.1f}")

    print("\n\nGenerating sample props...")
    props = create_sample_props(nba_players, "NBA")
    print(f"Created {len(props)} props")

    for prop in props[:5]:
        print(f"  {prop.prop_name} (O {prop.over_odds} / U {prop.under_odds})")
