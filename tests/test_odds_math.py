"""
Unit tests for edge/odds_math.py
Run with: python -m pytest tests/test_odds_math.py -v
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from edge.odds_math import (
    american_to_implied_prob,
    american_to_decimal,
    de_vig,
    expected_value,
    kelly_fraction,
    compute_edge_from_american,
)


def test_american_to_implied_prob():
    """Test conversion from American odds to implied probability."""
    # Negative odds (favorite)
    assert abs(american_to_implied_prob(-110) - 0.5238) < 0.001
    assert abs(american_to_implied_prob(-200) - 0.6667) < 0.001

    # Positive odds (underdog)
    assert abs(american_to_implied_prob(+150) - 0.4) < 0.001
    assert abs(american_to_implied_prob(+200) - 0.3333) < 0.001

    # Even odds
    assert abs(american_to_implied_prob(+100) - 0.5) < 0.001


def test_american_to_decimal():
    """Test conversion from American to decimal odds."""
    assert abs(american_to_decimal(-110) - 1.909) < 0.01
    assert abs(american_to_decimal(+150) - 2.5) < 0.01
    assert abs(american_to_decimal(+100) - 2.0) < 0.01
    assert abs(american_to_decimal(-200) - 1.5) < 0.01


def test_de_vig():
    """Test vig removal from implied probabilities."""
    # Standard vig (both -110)
    p_home, p_away = de_vig(0.5238, 0.5238)
    assert abs(p_home - 0.5) < 0.001
    assert abs(p_away - 0.5) < 0.001

    # Asymmetric odds
    p_home, p_away = de_vig(0.6667, 0.3333)
    assert abs(p_home - 0.6667) < 0.001
    assert abs(p_away - 0.3333) < 0.001

    # Sum should be 1.0
    p_home, p_away = de_vig(0.55, 0.50)
    assert abs((p_home + p_away) - 1.0) < 0.0001


def test_expected_value():
    """Test EV calculation."""
    # Positive EV (model has edge)
    ev = expected_value(0.55, 2.0)
    assert abs(ev - 0.1) < 0.001

    # Negative EV (no edge)
    ev = expected_value(0.45, 2.0)
    assert abs(ev - (-0.1)) < 0.001

    # Break-even
    ev = expected_value(0.5, 2.0)
    assert abs(ev) < 0.001


def test_kelly_fraction():
    """Test Kelly criterion calculation."""
    # Positive edge
    kelly = kelly_fraction(0.55, 2.0)
    assert abs(kelly - 0.1) < 0.001

    # No edge (should return 0)
    kelly = kelly_fraction(0.45, 2.0)
    assert kelly == 0.0

    # Fractional Kelly
    kelly = kelly_fraction(0.55, 2.0, fraction=0.5)
    assert abs(kelly - 0.05) < 0.001


def test_compute_edge_from_american():
    """Test complete edge calculation from American odds."""
    # Even matchup with model edge
    result = compute_edge_from_american(0.55, -110, -110, "home")

    assert abs(result["p_market_fair"] - 0.5) < 0.001
    assert result["edge_pct"] > 0
    assert result["ev"] > 0
    assert result["decimal_odds"] > 1.9

    # Underdog bet
    result = compute_edge_from_american(0.40, -200, +150, "away")

    assert result["p_market_fair"] < 0.5
    assert result["decimal_odds"] > 2.0


def test_edge_detection():
    """Test edge detection in realistic scenarios."""
    # Scenario 1: Clear edge
    result = compute_edge_from_american(0.60, -110, -110, "home")
    assert result["edge_pct"] > 5.0
    assert result["ev"] > 0.05

    # Scenario 2: No edge
    result = compute_edge_from_american(0.48, -110, -110, "home")
    assert result["edge_pct"] < 0
    assert result["ev"] < 0

    # Scenario 3: Marginal edge
    result = compute_edge_from_american(0.52, -110, -110, "home")
    assert 0 < result["edge_pct"] < 5.0


if __name__ == "__main__":
    print("Running odds_math unit tests...")

    test_american_to_implied_prob()
    print("✓ american_to_implied_prob tests passed")

    test_american_to_decimal()
    print("✓ american_to_decimal tests passed")

    test_de_vig()
    print("✓ de_vig tests passed")

    test_expected_value()
    print("✓ expected_value tests passed")

    test_kelly_fraction()
    print("✓ kelly_fraction tests passed")

    test_compute_edge_from_american()
    print("✓ compute_edge_from_american tests passed")

    test_edge_detection()
    print("✓ edge_detection tests passed")

    print("\nAll tests passed!")
