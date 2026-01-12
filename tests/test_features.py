"""
Unit tests for features/build.py
Tests Elo rating system and validates anti-leakage constraints.

Run with: python -m pytest tests/test_features.py -v
"""

import sys
import os
import pandas as pd
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from features.build import (
    EloRatingSystem,
    build_elo_features,
    DEFAULT_INITIAL_ELO,
    DEFAULT_K_FACTOR,
    DEFAULT_HOME_ADVANTAGE
)


def test_elo_initialization():
    """Test Elo system initializes correctly."""
    elo = EloRatingSystem()

    assert elo.initial_elo == DEFAULT_INITIAL_ELO
    assert elo.k_factor == DEFAULT_K_FACTOR
    assert elo.home_advantage == DEFAULT_HOME_ADVANTAGE
    assert len(elo.ratings) == 0


def test_get_rating_new_team():
    """Test getting rating for new team initializes to default."""
    elo = EloRatingSystem(initial_elo=1500)

    rating = elo.get_rating("Boston Celtics")
    assert rating == 1500
    assert "Boston Celtics" in elo.ratings


def test_expected_score():
    """Test Elo expected score calculation."""
    elo = EloRatingSystem()

    # Equal ratings should give 50/50
    assert abs(elo.expected_score(1500, 1500) - 0.5) < 0.001

    # Higher rating should have better odds
    assert elo.expected_score(1600, 1400) > 0.5
    assert elo.expected_score(1400, 1600) < 0.5

    # 400 point difference should give ~91% win probability
    assert abs(elo.expected_score(1900, 1500) - 0.909) < 0.01


def test_update_ratings_home_win():
    """Test rating updates when home team wins."""
    elo = EloRatingSystem(initial_elo=1500, k_factor=20, home_advantage=100)

    home_before, away_before, home_after, away_after = elo.update_ratings(
        "Team A", "Team B", 100, 95
    )

    assert home_before == 1500
    assert away_before == 1500
    assert home_after > home_before  # Winner gains rating
    assert away_after < away_before  # Loser loses rating
    assert abs((home_after - home_before) + (away_after - away_before)) < 0.01  # Zero-sum


def test_update_ratings_away_win():
    """Test rating updates when away team wins."""
    elo = EloRatingSystem(initial_elo=1500, k_factor=20)

    home_before, away_before, home_after, away_after = elo.update_ratings(
        "Team A", "Team B", 95, 100
    )

    assert home_after < home_before  # Loser loses rating
    assert away_after > away_before  # Winner gains rating


def test_predict_game():
    """Test game prediction."""
    elo = EloRatingSystem()
    elo.ratings["Strong Team"] = 1700
    elo.ratings["Weak Team"] = 1300

    p_home, p_away = elo.predict_game("Strong Team", "Weak Team")

    assert p_home > 0.5  # Strong team at home should be favored
    assert abs(p_home + p_away - 1.0) < 0.001  # Probabilities sum to 1

    p_home2, p_away2 = elo.predict_game("Weak Team", "Strong Team")
    assert p_home2 < 0.5  # Weak team at home should be underdog


def test_build_elo_features_chronological_order():
    """Test that features are built in chronological order."""
    # Create sample games
    games_df = pd.DataFrame([
        {
            'game_id': 'G3',
            'date': datetime(2023, 1, 3),
            'home_team': 'Team A',
            'away_team': 'Team B',
            'home_score': 100,
            'away_score': 95,
            'winner': 'home'
        },
        {
            'game_id': 'G1',
            'date': datetime(2023, 1, 1),
            'home_team': 'Team A',
            'away_team': 'Team B',
            'home_score': 105,
            'away_score': 100,
            'winner': 'home'
        },
        {
            'game_id': 'G2',
            'date': datetime(2023, 1, 2),
            'home_team': 'Team B',
            'away_team': 'Team A',
            'home_score': 98,
            'away_score': 102,
            'winner': 'away'
        },
    ])

    features_df = build_elo_features(games_df)

    # Check sorted by date
    assert features_df.iloc[0]['game_id'] == 'G1'
    assert features_df.iloc[1]['game_id'] == 'G2'
    assert features_df.iloc[2]['game_id'] == 'G3'


def test_point_in_time_constraint():
    """
    CRITICAL TEST: Validate no data leakage.
    Features for game N must not use information from game N or later.
    """
    # Create two games
    games_df = pd.DataFrame([
        {
            'game_id': 'G1',
            'date': datetime(2023, 1, 1),
            'home_team': 'Team A',
            'away_team': 'Team B',
            'home_score': 100,
            'away_score': 95,
            'winner': 'home'
        },
        {
            'game_id': 'G2',
            'date': datetime(2023, 1, 2),
            'home_team': 'Team A',
            'away_team': 'Team B',
            'home_score': 90,
            'away_score': 95,
            'winner': 'away'
        },
    ])

    features_df = build_elo_features(games_df, initial_elo=1500)

    # Game 1: Both teams should start at initial rating
    g1 = features_df[features_df['game_id'] == 'G1'].iloc[0]
    assert g1['home_elo'] == 1500
    assert g1['away_elo'] == 1500

    # Game 2: Ratings should reflect G1 outcome (Team A won)
    g2 = features_df[features_df['game_id'] == 'G2'].iloc[0]
    assert g2['home_elo'] > 1500  # Team A won G1, rating increased
    assert g2['away_elo'] < 1500  # Team B lost G1, rating decreased

    print(f"✓ Point-in-time constraint validated")
    print(f"  G1: Team A={g1['home_elo']:.0f}, Team B={g1['away_elo']:.0f}")
    print(f"  G2: Team A={g2['home_elo']:.0f}, Team B={g2['away_elo']:.0f}")


def test_no_future_information_leakage():
    """
    Test that ratings at time T don't include game T.
    """
    elo = EloRatingSystem(initial_elo=1500)

    # Get rating before any games
    rating_before = elo.get_rating("Team A")
    assert rating_before == 1500

    # Update after a win
    elo.update_ratings("Team A", "Team B", 100, 95)

    # Rating should have changed after the game
    rating_after = elo.get_rating("Team A")
    assert rating_after > rating_before

    print(f"✓ No future information leakage")
    print(f"  Before game: {rating_before:.0f}")
    print(f"  After game: {rating_after:.0f}")


def test_home_advantage_applied():
    """Test that home advantage affects predictions."""
    elo = EloRatingSystem(initial_elo=1500, home_advantage=100)

    # Set equal ratings
    elo.ratings["Team A"] = 1500
    elo.ratings["Team B"] = 1500

    # Team A at home should be favored due to home advantage
    p_home, p_away = elo.predict_game("Team A", "Team B")
    assert p_home > 0.5

    # Team B at home should be favored
    p_home2, p_away2 = elo.predict_game("Team B", "Team A")
    assert p_home2 > 0.5


def test_feature_columns():
    """Test that all required columns are present."""
    games_df = pd.DataFrame([
        {
            'game_id': 'G1',
            'date': datetime(2023, 1, 1),
            'home_team': 'Team A',
            'away_team': 'Team B',
            'home_score': 100,
            'away_score': 95,
            'winner': 'home'
        },
    ])

    features_df = build_elo_features(games_df)

    required_columns = [
        'game_id', 'date', 'home_team', 'away_team',
        'home_elo', 'away_elo', 'elo_diff', 'p_home', 'p_away', 'winner'
    ]

    for col in required_columns:
        assert col in features_df.columns, f"Missing column: {col}"


def test_elo_diff_calculation():
    """Test that elo_diff is calculated correctly."""
    games_df = pd.DataFrame([
        {
            'game_id': 'G1',
            'date': datetime(2023, 1, 1),
            'home_team': 'Team A',
            'away_team': 'Team B',
            'home_score': 100,
            'away_score': 95,
            'winner': 'home'
        },
    ])

    features_df = build_elo_features(games_df, initial_elo=1500)

    row = features_df.iloc[0]
    expected_diff = row['home_elo'] - row['away_elo']
    assert abs(row['elo_diff'] - expected_diff) < 0.001


def test_multiple_teams():
    """Test Elo with multiple different teams."""
    games_df = pd.DataFrame([
        {
            'game_id': 'G1',
            'date': datetime(2023, 1, 1),
            'home_team': 'Team A',
            'away_team': 'Team B',
            'home_score': 100,
            'away_score': 95,
            'winner': 'home'
        },
        {
            'game_id': 'G2',
            'date': datetime(2023, 1, 2),
            'home_team': 'Team C',
            'away_team': 'Team D',
            'home_score': 105,
            'away_score': 100,
            'winner': 'home'
        },
        {
            'game_id': 'G3',
            'date': datetime(2023, 1, 3),
            'home_team': 'Team A',
            'away_team': 'Team C',
            'home_score': 110,
            'away_score': 105,
            'winner': 'home'
        },
    ])

    features_df = build_elo_features(games_df, initial_elo=1500)

    assert len(features_df) == 3

    # All teams should start at 1500
    g1 = features_df.iloc[0]
    assert g1['home_elo'] == 1500
    assert g1['away_elo'] == 1500

    g2 = features_df.iloc[1]
    assert g2['home_elo'] == 1500
    assert g2['away_elo'] == 1500

    # G3: Team A and Team C should have updated ratings from G1 and G2
    g3 = features_df.iloc[2]
    assert g3['home_elo'] > 1500  # Team A won G1
    assert g3['away_elo'] > 1500  # Team C won G2


if __name__ == "__main__":
    print("Running feature engineering tests...")

    test_elo_initialization()
    print("✓ elo_initialization passed")

    test_get_rating_new_team()
    print("✓ get_rating_new_team passed")

    test_expected_score()
    print("✓ expected_score passed")

    test_update_ratings_home_win()
    print("✓ update_ratings_home_win passed")

    test_update_ratings_away_win()
    print("✓ update_ratings_away_win passed")

    test_predict_game()
    print("✓ predict_game passed")

    test_build_elo_features_chronological_order()
    print("✓ chronological_order passed")

    test_point_in_time_constraint()
    print("✓ point_in_time_constraint passed")

    test_no_future_information_leakage()
    print("✓ no_future_information_leakage passed")

    test_home_advantage_applied()
    print("✓ home_advantage_applied passed")

    test_feature_columns()
    print("✓ feature_columns passed")

    test_elo_diff_calculation()
    print("✓ elo_diff_calculation passed")

    test_multiple_teams()
    print("✓ multiple_teams passed")

    print("\n" + "=" * 60)
    print("All feature tests passed!")
    print("=" * 60)
    print("\n✓ No data leakage detected")
    print("✓ Point-in-time constraints validated")
    print("✓ Elo system working correctly")
