"""
Feature engineering with strict point-in-time constraints.
All features for date D must use only games < D.

Implements Elo rating system for baseline model.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Tuple, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_schema import get_session, Game, TeamRating


# Elo parameters
DEFAULT_INITIAL_ELO = 1500
DEFAULT_K_FACTOR = 20
DEFAULT_HOME_ADVANTAGE = 100


class EloRatingSystem:
    """
    Elo rating system for NBA teams with point-in-time tracking.

    Key properties:
    - Ratings update only after games complete
    - Ratings for date D use only games before D
    - No data leakage
    """

    def __init__(
        self,
        initial_elo: float = DEFAULT_INITIAL_ELO,
        k_factor: float = DEFAULT_K_FACTOR,
        home_advantage: float = DEFAULT_HOME_ADVANTAGE
    ):
        """
        Initialize Elo rating system.

        Args:
            initial_elo: Starting rating for all teams
            k_factor: How much ratings change per game (higher = more volatile)
            home_advantage: Elo points added to home team (typically 50-100)
        """
        self.initial_elo = initial_elo
        self.k_factor = k_factor
        self.home_advantage = home_advantage
        self.ratings: Dict[str, float] = {}

    def get_rating(self, team: str, date: Optional[datetime] = None) -> float:
        """
        Get team's current Elo rating.

        Args:
            team: Team name
            date: Optional date for historical rating

        Returns:
            Current Elo rating
        """
        if team not in self.ratings:
            self.ratings[team] = self.initial_elo
        return self.ratings[team]

    def expected_score(self, rating_a: float, rating_b: float) -> float:
        """
        Calculate expected score for team A vs team B.

        Formula: E_a = 1 / (1 + 10^((rating_b - rating_a) / 400))

        Args:
            rating_a: Elo rating of team A
            rating_b: Elo rating of team B

        Returns:
            Expected score (probability of A winning)
        """
        return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

    def update_ratings(
        self,
        home_team: str,
        away_team: str,
        home_score: int,
        away_score: int
    ) -> Tuple[float, float, float, float]:
        """
        Update Elo ratings after a game.

        Args:
            home_team: Home team name
            away_team: Away team name
            home_score: Final home score
            away_score: Final away score

        Returns:
            Tuple of (home_elo_before, away_elo_before, home_elo_after, away_elo_after)
        """
        # Get current ratings
        home_elo_before = self.get_rating(home_team)
        away_elo_before = self.get_rating(away_team)

        # Apply home advantage
        home_elo_adjusted = home_elo_before + self.home_advantage

        # Calculate expected scores
        expected_home = self.expected_score(home_elo_adjusted, away_elo_before)
        expected_away = 1 - expected_home

        # Actual scores (1 for win, 0 for loss)
        if home_score > away_score:
            actual_home, actual_away = 1, 0
        elif away_score > home_score:
            actual_home, actual_away = 0, 1
        else:
            actual_home, actual_away = 0.5, 0.5  # Tie

        # Update ratings
        home_elo_after = home_elo_before + self.k_factor * (actual_home - expected_home)
        away_elo_after = away_elo_before + self.k_factor * (actual_away - expected_away)

        # Store new ratings
        self.ratings[home_team] = home_elo_after
        self.ratings[away_team] = away_elo_after

        return home_elo_before, away_elo_before, home_elo_after, away_elo_after

    def predict_game(
        self,
        home_team: str,
        away_team: str
    ) -> Tuple[float, float]:
        """
        Predict outcome of a game using current Elo ratings.

        Args:
            home_team: Home team name
            away_team: Away team name

        Returns:
            Tuple of (p_home_win, p_away_win)
        """
        home_elo = self.get_rating(home_team)
        away_elo = self.get_rating(away_team)

        # Apply home advantage
        home_elo_adjusted = home_elo + self.home_advantage

        # Calculate probabilities
        p_home = self.expected_score(home_elo_adjusted, away_elo)
        p_away = 1 - p_home

        return p_home, p_away


def build_elo_features(
    games_df: pd.DataFrame,
    initial_elo: float = DEFAULT_INITIAL_ELO,
    k_factor: float = DEFAULT_K_FACTOR,
    home_advantage: float = DEFAULT_HOME_ADVANTAGE
) -> pd.DataFrame:
    """
    Build Elo-based features with strict point-in-time constraints.

    CRITICAL: Features for game at time T use only games before T.

    Args:
        games_df: DataFrame with columns [game_id, date, home_team, away_team, home_score, away_score]
        initial_elo: Starting Elo rating
        k_factor: Elo update rate
        home_advantage: Home court advantage in Elo points

    Returns:
        DataFrame with features: [game_id, date, home_team, away_team,
                                  home_elo, away_elo, elo_diff, p_home, p_away]
    """
    # Sort by date to ensure chronological processing
    games_df = games_df.sort_values('date').reset_index(drop=True)

    # If league column exists, maintain separate Elo systems per league
    if 'league' in games_df.columns:
        elo_systems = {}
        features = []

        for _, game in games_df.iterrows():
            league = game['league']

            # Initialize Elo system for this league if needed
            if league not in elo_systems:
                elo_systems[league] = EloRatingSystem(initial_elo, k_factor, home_advantage)

            elo_system = elo_systems[league]

            # Get ratings BEFORE the game (point-in-time)
            home_elo = elo_system.get_rating(game['home_team'])
            away_elo = elo_system.get_rating(game['away_team'])

            # Calculate prediction BEFORE the game
            p_home, p_away = elo_system.predict_game(game['home_team'], game['away_team'])

            # Store features
            features.append({
                'game_id': game['game_id'],
                'date': game['date'],
                'league': league,
                'home_team': game['home_team'],
                'away_team': game['away_team'],
                'home_elo': home_elo,
                'away_elo': away_elo,
                'elo_diff': home_elo - away_elo,
                'p_home': p_home,
                'p_away': p_away,
                'winner': game.get('winner')
            })

            # Update ratings AFTER processing (for next game)
            if pd.notna(game['home_score']) and pd.notna(game['away_score']):
                elo_system.update_ratings(
                    game['home_team'],
                    game['away_team'],
                    int(game['home_score']),
                    int(game['away_score'])
                )

    else:
        # Single Elo system for all games
        elo_system = EloRatingSystem(initial_elo, k_factor, home_advantage)
        features = []

        for _, game in games_df.iterrows():
            # Get ratings BEFORE the game (point-in-time)
            home_elo = elo_system.get_rating(game['home_team'])
            away_elo = elo_system.get_rating(game['away_team'])

            # Calculate prediction BEFORE the game
            p_home, p_away = elo_system.predict_game(game['home_team'], game['away_team'])

            # Store features
            features.append({
                'game_id': game['game_id'],
                'date': game['date'],
                'home_team': game['home_team'],
                'away_team': game['away_team'],
                'home_elo': home_elo,
                'away_elo': away_elo,
                'elo_diff': home_elo - away_elo,
                'p_home': p_home,
                'p_away': p_away,
                'winner': game.get('winner')
            })

            # Update ratings AFTER processing (for next game)
            if pd.notna(game['home_score']) and pd.notna(game['away_score']):
                elo_system.update_ratings(
                    game['home_team'],
                    game['away_team'],
                    int(game['home_score']),
                    int(game['away_score'])
                )

    return pd.DataFrame(features)


def save_team_ratings_to_db(
    elo_system: EloRatingSystem,
    date: datetime,
    session=None
) -> int:
    """
    Save current team ratings to database.

    Args:
        elo_system: EloRatingSystem instance
        date: Date of ratings
        session: Database session

    Returns:
        Number of ratings saved
    """
    close_session = False
    if session is None:
        session = get_session()
        close_session = True

    try:
        count = 0
        for team, elo in elo_system.ratings.items():
            rating = TeamRating(
                team_id=team,
                date=date,
                elo=elo
            )
            session.add(rating)
            count += 1

        session.commit()
        return count

    finally:
        if close_session:
            session.close()


def build_features_from_db(
    league: Optional[str] = None,
    initial_elo: float = DEFAULT_INITIAL_ELO,
    k_factor: float = DEFAULT_K_FACTOR,
    home_advantage: float = DEFAULT_HOME_ADVANTAGE
) -> pd.DataFrame:
    """
    Build features from games in database.

    Args:
        league: League to filter games (None = all leagues)
        initial_elo: Starting Elo rating
        k_factor: Elo update rate
        home_advantage: Home court advantage

    Returns:
        DataFrame with Elo features
    """
    session = get_session()

    try:
        # Load games from database
        query = session.query(Game).order_by(Game.date)

        if league:
            query = query.filter(Game.league == league)

        games = query.all()

        # Convert to DataFrame
        games_df = pd.DataFrame([{
            'game_id': g.game_id,
            'date': g.date,
            'league': g.league,
            'home_team': g.home_team,
            'away_team': g.away_team,
            'home_score': g.home_score,
            'away_score': g.away_score,
            'winner': g.winner
        } for g in games])

        # Build features
        features_df = build_elo_features(games_df, initial_elo, k_factor, home_advantage)

        return features_df

    finally:
        session.close()


if __name__ == "__main__":
    # Example usage
    print("Building Elo features from database...")

    features_df = build_features_from_db()

    print(f"\n✓ Built features for {len(features_df)} games")
    print(f"\nSample features:")
    print(features_df.head(10).to_string(index=False))

    print(f"\n✓ Elo rating range:")
    print(f"  Min: {features_df['home_elo'].min():.0f}")
    print(f"  Max: {features_df['home_elo'].max():.0f}")
    print(f"  Mean: {features_df['home_elo'].mean():.0f}")
