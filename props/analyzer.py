"""
Player Props Edge Analyzer.
Uses season statistics to find value in prop bets.
"""

import sys
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import math

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from props.models import PlayerStats, PropBet, PropEdge, PropType, GameLog
from edge.odds_math import american_to_implied_prob, american_to_decimal, expected_value


class PropsAnalyzer:
    """
    Analyzes player props to find edges using historical performance.

    Uses multiple factors:
    1. Season averages and medians
    2. Recent form (last 5/10 games)
    3. Hit rate at the line
    4. Performance vs opponent
    5. Home/away splits
    6. Trend analysis
    """

    def __init__(
        self,
        min_games: int = 5,
        edge_threshold: float = 1.0,
        ev_threshold: float = 0.03,
        shrink_weight: float = 0.7,
        kelly_mult: float = 0.25,
        max_stake: float = 0.02,
        bankroll: float = 1000.0,
    ):
        """
        Initialize analyzer.

        Args:
            min_games: Minimum games required for analysis
            edge_threshold: Minimum edge % to recommend a bet
            ev_threshold: Minimum EV to recommend a bet
        """
        self.min_games = min_games
        self.edge_threshold = edge_threshold
        self.ev_threshold = ev_threshold
        self.shrink_weight = shrink_weight
        self.kelly_mult = kelly_mult
        self.max_stake = max_stake
        self.bankroll = bankroll

    def analyze_prop(
        self,
        prop: PropBet,
        player_stats: PlayerStats,
    ) -> PropEdge:
        """
        Analyze a single prop bet for edge.

        Args:
            prop: The prop bet to analyze
            player_stats: Player's historical stats

        Returns:
            PropEdge with analysis results
        """
        stat_type = self._prop_type_to_stat(prop.prop_type)

        # Calculate averages
        season_avg = player_stats.get_stat_average(stat_type)
        last10_avg = player_stats.get_stat_average(stat_type, last_n=10)
        last5_avg = player_stats.get_stat_average(stat_type, last_n=5)
        season_median = player_stats.get_stat_median(stat_type)

        # Calculate hit rates
        hit_rate_season = player_stats.get_hit_rate(stat_type, prop.line)
        hit_rate_last10 = player_stats.get_hit_rate(stat_type, prop.line, last_n=10)
        hit_rate_last5 = player_stats.get_hit_rate(stat_type, prop.line, last_n=5)

        # Get vs opponent stats
        vs_opp = player_stats.get_vs_opponent(stat_type, prop.opponent)
        vs_opponent_avg = sum(vs_opp) / len(vs_opp) if vs_opp else None

        # Calculate home/away splits
        home_logs = [l for l in player_stats.game_logs if l.is_home]
        away_logs = [l for l in player_stats.game_logs if not l.is_home]
        home_avg = sum(l.get_stat(stat_type) for l in home_logs) / len(home_logs) if home_logs else None
        away_avg = sum(l.get_stat(stat_type) for l in away_logs) / len(away_logs) if away_logs else None

        # Calculate trend
        trend = self._calculate_trend(player_stats, stat_type)

        # Model probability using weighted average of methods
        model_prob_over = self._calculate_model_prob(
            line=prop.line,
            season_avg=season_avg,
            season_median=season_median,
            last5_avg=last5_avg,
            last10_avg=last10_avg,
            hit_rate_season=hit_rate_season,
            hit_rate_last10=hit_rate_last10,
            std=player_stats.get_stat_std(stat_type),
            vs_opponent_avg=vs_opponent_avg,
            is_home=True,  # We'd need to know this from the prop
            home_avg=home_avg,
            away_avg=away_avg,
        )

        # Market implied probability
        market_prob_over = american_to_implied_prob(prop.over_odds)
        market_prob_under = american_to_implied_prob(prop.under_odds)
        # De-vig
        total = market_prob_over + market_prob_under
        market_prob_over_fair = market_prob_over / total
        market_prob_under_fair = market_prob_under / total

        # Shrink model toward market
        w = max(0.0, min(1.0, self.shrink_weight))
        model_prob_over_adj = w * model_prob_over + (1 - w) * market_prob_over_fair

        # Calculate edge and EV
        edge_pct = (model_prob_over_adj - market_prob_over_fair) * 100
        decimal_over = american_to_decimal(prop.over_odds)
        decimal_under = american_to_decimal(prop.under_odds)
        ev_over = expected_value(model_prob_over_adj, decimal_over)
        ev_under = expected_value(1 - model_prob_over_adj, decimal_under)

        kelly_over = max(0.0, (model_prob_over_adj * decimal_over - 1) / (decimal_over - 1)) if decimal_over > 1 else 0.0
        kelly_under = max(0.0, ((1 - model_prob_over_adj) * decimal_under - 1) / (decimal_under - 1)) if decimal_under > 1 else 0.0
        stake_frac_over = max(0.0, min(kelly_over * self.kelly_mult, self.max_stake))
        stake_frac_under = max(0.0, min(kelly_under * self.kelly_mult, self.max_stake))
        stake_dollars_over = stake_frac_over * self.bankroll
        stake_dollars_under = stake_frac_under * self.bankroll

        # Determine recommendation
        recommended_side = None
        confidence = "low"

        if player_stats.games_played >= self.min_games:
            if ev_over > 0 and edge_pct >= self.edge_threshold:
                recommended_side = "over"
                confidence = self._get_confidence(edge_pct, ev_over, player_stats.games_played)
            elif ev_under > 0 and -edge_pct >= self.edge_threshold:
                recommended_side = "under"
                confidence = self._get_confidence(-edge_pct, ev_under, player_stats.games_played)

        # Calculate projected value (weighted average)
        projected_value = self._calculate_projection(
            season_avg=season_avg,
            last5_avg=last5_avg,
            last10_avg=last10_avg,
            vs_opponent_avg=vs_opponent_avg,
        )

        return PropEdge(
            prop=prop,
            player_stats=player_stats,
            projected_value=projected_value,
            hit_rate_season=hit_rate_season,
            hit_rate_last10=hit_rate_last10,
            hit_rate_last5=hit_rate_last5,
            model_prob_over=model_prob_over_adj,
            market_prob_over=market_prob_over_fair,
            edge_pct=edge_pct,
            ev_over=ev_over,
            ev_under=ev_under,
            decimal_over=decimal_over,
            decimal_under=decimal_under,
            stake_frac_over=stake_frac_over,
            stake_frac_under=stake_frac_under,
            stake_dollars_over=stake_dollars_over,
            stake_dollars_under=stake_dollars_under,
            recommended_side=recommended_side,
            confidence=confidence,
            sample_size=player_stats.games_played,
            vs_opponent_avg=vs_opponent_avg,
            home_avg=home_avg,
            away_avg=away_avg,
            trend=trend,
        )

    def analyze_props(
        self,
        props: List[PropBet],
        player_stats_map: Dict[str, PlayerStats],
    ) -> List[PropEdge]:
        """
        Analyze multiple props.

        Args:
            props: List of props to analyze
            player_stats_map: Dict mapping player_id OR player_name to PlayerStats

        Returns:
            List of PropEdge results
        """
        # Build a name-based lookup as well
        name_to_stats = {stats.player_name.lower(): stats for stats in player_stats_map.values()}

        edges = []
        for prop in props:
            player_stats = None

            # Try ID first
            if prop.player_id in player_stats_map:
                player_stats = player_stats_map[prop.player_id]
            # Then try name match
            elif prop.player_name.lower() in name_to_stats:
                player_stats = name_to_stats[prop.player_name.lower()]

            if player_stats:
                edge = self.analyze_prop(prop, player_stats)
                edges.append(edge)

        return edges

    def get_best_edges(
        self,
        edges: List[PropEdge],
        min_edge: float = 5.0,
        min_ev: float = 0.03,
        top_n: int = 10,
    ) -> List[PropEdge]:
        """
        Filter and rank edges by value.

        Args:
            edges: List of analyzed props
            min_edge: Minimum edge percentage
            min_ev: Minimum expected value
            top_n: Number of top picks to return

        Returns:
            Top edges sorted by EV
        """
        qualified = [
            e for e in edges
            if e.recommended_side is not None
            and abs(e.edge_pct) >= min_edge
            and max(e.ev_over, e.ev_under) >= min_ev
            and e.sample_size >= self.min_games
        ]

        # Sort by best EV
        qualified.sort(key=lambda e: max(e.ev_over, e.ev_under), reverse=True)
        return qualified[:top_n]

    def _prop_type_to_stat(self, prop_type: PropType) -> str:
        """Map prop type to stat key."""
        mapping = {
            PropType.POINTS: "points",
            PropType.REBOUNDS: "rebounds",
            PropType.ASSISTS: "assists",
            PropType.THREES: "threes",
            PropType.STEALS: "steals",
            PropType.BLOCKS: "blocks",
            PropType.PTS_REB_AST: "pts_reb_ast",
            PropType.PTS_REB: "pts_reb",
            PropType.PTS_AST: "pts_ast",
            PropType.REB_AST: "reb_ast",
            PropType.PASSING_YARDS: "passing_yards",
            PropType.PASSING_TDS: "passing_tds",
            PropType.RUSHING_YARDS: "rushing_yards",
            PropType.RUSHING_TDS: "rushing_tds",
            PropType.RECEIVING_YARDS: "receiving_yards",
            PropType.RECEPTIONS: "receptions",
            PropType.RECEIVING_TDS: "receiving_tds",
            PropType.GOALS: "goals",
            PropType.NHL_ASSISTS: "assists",
            PropType.NHL_POINTS: "points",
            PropType.SHOTS: "shots",
            PropType.SAVES: "saves",
        }
        return mapping.get(prop_type, prop_type.value)

    def _calculate_model_prob(
        self,
        line: float,
        season_avg: float,
        season_median: float,
        last5_avg: float,
        last10_avg: float,
        hit_rate_season: float,
        hit_rate_last10: float,
        std: float,
        vs_opponent_avg: Optional[float] = None,
        is_home: bool = True,
        home_avg: Optional[float] = None,
        away_avg: Optional[float] = None,
    ) -> float:
        """
        Calculate model probability of hitting the over.

        Uses multiple approaches and weights them:
        1. Hit rate (empirical) - 35%
        2. Gaussian model based on avg/std - 30%
        3. Recent form weighted - 25%
        4. Opponent/venue adjustments - 10%
        """
        # 1. Empirical hit rate (weighted recent more)
        empirical_prob = 0.6 * hit_rate_last10 + 0.4 * hit_rate_season

        # 2. Gaussian model (if we have enough variance info)
        if std > 0:
            # P(X > line) using normal approximation
            z = (line - season_avg) / std
            # Approximate CDF using logistic function
            gaussian_prob = 1 / (1 + math.exp(1.7 * z))
        else:
            # Fallback: simple comparison
            gaussian_prob = 0.5 + 0.5 * max(-1, min(1, (season_avg - line) / max(line, 1)))

        # 3. Recent form signal
        recent_avg = 0.6 * last5_avg + 0.4 * last10_avg
        if recent_avg > line:
            recent_prob = 0.5 + 0.3 * min(1, (recent_avg - line) / max(line * 0.2, 1))
        else:
            recent_prob = 0.5 - 0.3 * min(1, (line - recent_avg) / max(line * 0.2, 1))

        # 4. Context adjustments (opponent, venue)
        context_adj = 0.0
        if vs_opponent_avg is not None:
            if vs_opponent_avg > season_avg:
                context_adj += 0.05
            elif vs_opponent_avg < season_avg:
                context_adj -= 0.05

        # Combine with weights
        model_prob = (
            0.35 * empirical_prob +
            0.30 * gaussian_prob +
            0.25 * recent_prob +
            0.10 * (0.5 + context_adj)
        )

        # Clamp to valid probability range
        return max(0.05, min(0.95, model_prob))

    def _calculate_projection(
        self,
        season_avg: float,
        last5_avg: float,
        last10_avg: float,
        vs_opponent_avg: Optional[float] = None,
    ) -> float:
        """Calculate projected stat value."""
        # Weight recent performance more
        base = 0.3 * season_avg + 0.35 * last10_avg + 0.35 * last5_avg

        # Adjust for opponent if available
        if vs_opponent_avg is not None:
            # Blend in opponent factor
            base = 0.85 * base + 0.15 * vs_opponent_avg

        return base

    def _calculate_trend(self, player_stats: PlayerStats, stat_type: str) -> str:
        """Determine if player is trending up or down."""
        if len(player_stats.game_logs) < 6:
            return "neutral"

        last3 = player_stats.get_stat_average(stat_type, last_n=3)
        last6 = player_stats.get_stat_average(stat_type, last_n=6)
        season = player_stats.get_stat_average(stat_type)

        if last3 > last6 * 1.1 and last3 > season:
            return "up"
        elif last3 < last6 * 0.9 and last3 < season:
            return "down"
        return "neutral"

    def _get_confidence(self, edge: float, ev: float, sample_size: int) -> str:
        """Determine confidence level based on edge strength and sample."""
        score = 0

        # Edge contribution
        if edge > 15:
            score += 3
        elif edge > 10:
            score += 2
        elif edge > 5:
            score += 1

        # EV contribution
        if ev > 0.10:
            score += 3
        elif ev > 0.06:
            score += 2
        elif ev > 0.03:
            score += 1

        # Sample size contribution
        if sample_size >= 30:
            score += 2
        elif sample_size >= 15:
            score += 1

        if score >= 6:
            return "high"
        elif score >= 3:
            return "medium"
        return "low"


if __name__ == "__main__":
    # Example usage
    from datetime import datetime, timedelta

    # Create sample player stats
    logs = []
    for i in range(20):
        logs.append(GameLog(
            game_id=f"game_{i}",
            date=datetime.now() - timedelta(days=20-i),
            opponent="OPP",
            is_home=i % 2 == 0,
            stats={
                "points": 22 + (i % 5) * 2,
                "rebounds": 5 + (i % 3),
                "assists": 4 + (i % 4),
            }
        ))

    player = PlayerStats(
        player_id="player1",
        player_name="Test Player",
        team="TEST",
        league="NBA",
        position="SG",
        game_logs=logs,
    )

    # Create sample prop
    prop = PropBet(
        player_id="player1",
        player_name="Test Player",
        team="TEST",
        opponent="OPP2",
        game_date=datetime.now(),
        prop_type=PropType.POINTS,
        line=23.5,
        over_odds=-115,
        under_odds=-105,
    )

    # Analyze
    analyzer = PropsAnalyzer()
    edge = analyzer.analyze_prop(prop, player)

    print("=" * 60)
    print(f"PROP ANALYSIS: {prop.prop_name}")
    print("=" * 60)
    print(f"Season Avg: {player.get_stat_average('points'):.1f}")
    print(f"Last 10 Avg: {player.get_stat_average('points', 10):.1f}")
    print(f"Last 5 Avg: {player.get_stat_average('points', 5):.1f}")
    print(f"Projected: {edge.projected_value:.1f}")
    print()
    print(f"Hit Rate (Season): {edge.hit_rate_season*100:.1f}%")
    print(f"Hit Rate (Last 10): {edge.hit_rate_last10*100:.1f}%")
    print()
    print(f"Model Prob Over: {edge.model_prob_over*100:.1f}%")
    print(f"Market Prob Over: {edge.market_prob_over*100:.1f}%")
    print(f"Edge: {edge.edge_pct:+.1f}%")
    print()
    print(f"EV Over: {edge.ev_over:+.3f}")
    print(f"EV Under: {edge.ev_under:+.3f}")
    print()
    if edge.recommended_side:
        print(f"✅ RECOMMENDED: {edge.recommended_side.upper()} ({edge.confidence} confidence)")
    else:
        print("❌ No edge found")
