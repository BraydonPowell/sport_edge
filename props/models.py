"""
Data models for player props analysis.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class PropType(Enum):
    """Types of player props."""
    # NBA
    POINTS = "points"
    REBOUNDS = "rebounds"
    ASSISTS = "assists"
    THREES = "threes"
    STEALS = "steals"
    BLOCKS = "blocks"
    PTS_REB_AST = "pts_reb_ast"
    PTS_REB = "pts_reb"
    PTS_AST = "pts_ast"
    REB_AST = "reb_ast"

    # NFL
    PASSING_YARDS = "passing_yards"
    PASSING_TDS = "passing_tds"
    RUSHING_YARDS = "rushing_yards"
    RUSHING_TDS = "rushing_tds"
    RECEIVING_YARDS = "receiving_yards"
    RECEPTIONS = "receptions"
    RECEIVING_TDS = "receiving_tds"

    # NHL
    GOALS = "goals"
    NHL_ASSISTS = "nhl_assists"
    NHL_POINTS = "nhl_points"
    SHOTS = "shots"
    SAVES = "saves"


@dataclass
class GameLog:
    """Single game performance for a player."""
    game_id: str
    date: datetime
    opponent: str
    is_home: bool
    minutes: float = 0.0
    stats: Dict[str, float] = field(default_factory=dict)

    def get_stat(self, stat_type: str) -> float:
        """Get a stat value, defaulting to 0."""
        return self.stats.get(stat_type, 0.0)


@dataclass
class PlayerStats:
    """Aggregated player statistics for analysis."""
    player_id: str
    player_name: str
    team: str
    league: str
    position: str
    game_logs: List[GameLog] = field(default_factory=list)

    @property
    def games_played(self) -> int:
        return len(self.game_logs)

    def get_stat_average(self, stat_type: str, last_n: Optional[int] = None) -> float:
        """Calculate average for a stat over last N games."""
        logs = self.game_logs[-last_n:] if last_n else self.game_logs
        if not logs:
            return 0.0
        values = [log.get_stat(stat_type) for log in logs]
        return sum(values) / len(values)

    def get_stat_median(self, stat_type: str, last_n: Optional[int] = None) -> float:
        """Calculate median for a stat over last N games."""
        logs = self.game_logs[-last_n:] if last_n else self.game_logs
        if not logs:
            return 0.0
        values = sorted([log.get_stat(stat_type) for log in logs])
        n = len(values)
        if n % 2 == 0:
            return (values[n//2 - 1] + values[n//2]) / 2
        return values[n//2]

    def get_hit_rate(self, stat_type: str, line: float, last_n: Optional[int] = None) -> float:
        """Calculate percentage of games where player hit over the line."""
        logs = self.game_logs[-last_n:] if last_n else self.game_logs
        if not logs:
            return 0.0
        hits = sum(1 for log in logs if log.get_stat(stat_type) > line)
        return hits / len(logs)

    def get_stat_std(self, stat_type: str, last_n: Optional[int] = None) -> float:
        """Calculate standard deviation for a stat."""
        logs = self.game_logs[-last_n:] if last_n else self.game_logs
        if len(logs) < 2:
            return 0.0
        values = [log.get_stat(stat_type) for log in logs]
        avg = sum(values) / len(values)
        variance = sum((v - avg) ** 2 for v in values) / len(values)
        return variance ** 0.5

    def get_vs_opponent(self, stat_type: str, opponent: str) -> List[float]:
        """Get stat values from games against a specific opponent."""
        return [
            log.get_stat(stat_type)
            for log in self.game_logs
            if log.opponent == opponent
        ]


@dataclass
class PropBet:
    """A player prop betting line."""
    player_id: str
    player_name: str
    team: str
    opponent: str
    game_date: datetime
    prop_type: PropType
    line: float
    over_odds: int  # American odds
    under_odds: int  # American odds
    book: str = "consensus"
    event_id: Optional[str] = None

    @property
    def prop_name(self) -> str:
        return f"{self.player_name} {self.prop_type.value} O/U {self.line}"


@dataclass
class PropEdge:
    """Analysis result for a prop bet."""
    prop: PropBet
    player_stats: PlayerStats

    # Model predictions
    projected_value: float
    hit_rate_season: float
    hit_rate_last10: float
    hit_rate_last5: float

    # Edge calculations
    model_prob_over: float
    market_prob_over: float
    edge_pct: float
    ev_over: float
    ev_under: float
    decimal_over: float = 0.0
    decimal_under: float = 0.0
    stake_frac_over: float = 0.0
    stake_frac_under: float = 0.0
    stake_dollars_over: float = 0.0
    stake_dollars_under: float = 0.0

    # Recommendation
    recommended_side: Optional[str] = None  # "over", "under", or None
    confidence: str = "low"  # "low", "medium", "high"

    # Context
    sample_size: int = 0
    vs_opponent_avg: Optional[float] = None
    home_avg: Optional[float] = None
    away_avg: Optional[float] = None
    trend: str = "neutral"  # "up", "down", "neutral"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "player_id": self.prop.player_id,
            "player_name": self.prop.player_name,
            "team": self.prop.team,
            "opponent": self.prop.opponent,
            "game_date": self.prop.game_date.isoformat() if self.prop.game_date else None,
            "prop_type": self.prop.prop_type.value,
            "line": self.prop.line,
            "over_odds": self.prop.over_odds,
            "under_odds": self.prop.under_odds,
            "book": self.prop.book,
            "projected_value": round(self.projected_value, 1),
            "hit_rate_season": round(self.hit_rate_season * 100, 1),
            "hit_rate_last10": round(self.hit_rate_last10 * 100, 1),
            "hit_rate_last5": round(self.hit_rate_last5 * 100, 1),
            "model_prob_over": round(self.model_prob_over * 100, 1),
            "market_prob_over": round(self.market_prob_over * 100, 1),
            "edge_pct": round(self.edge_pct, 1),
            "ev_over": round(self.ev_over, 3),
            "ev_under": round(self.ev_under, 3),
            "decimal_over": round(self.decimal_over, 3),
            "decimal_under": round(self.decimal_under, 3),
            "stake_frac_over": round(self.stake_frac_over, 4),
            "stake_frac_under": round(self.stake_frac_under, 4),
            "stake_dollars_over": round(self.stake_dollars_over, 2),
            "stake_dollars_under": round(self.stake_dollars_under, 2),
            "recommended_side": self.recommended_side,
            "confidence": self.confidence,
            "sample_size": self.sample_size,
            "vs_opponent_avg": round(self.vs_opponent_avg, 1) if self.vs_opponent_avg else None,
            "trend": self.trend,
        }
