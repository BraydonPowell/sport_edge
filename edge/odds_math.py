"""
Market math utilities for odds conversion and EV calculation.
Implements the core formulas from SYSTEM.md.
"""

from typing import Tuple


def american_to_implied_prob(american_odds: float) -> float:
    """
    Convert American odds to implied probability (raw, with vig).

    Args:
        american_odds: American odds format (e.g., -110, +150)

    Returns:
        Implied probability as decimal (0-1)

    Examples:
        >>> american_to_implied_prob(-110)
        0.5238095238095238
        >>> american_to_implied_prob(+150)
        0.4
    """
    if american_odds < 0:
        return abs(american_odds) / (abs(american_odds) + 100)
    else:
        return 100 / (american_odds + 100)


def american_to_decimal(american_odds: float) -> float:
    """
    Convert American odds to decimal odds.

    Args:
        american_odds: American odds format (e.g., -110, +150)

    Returns:
        Decimal odds (e.g., 1.91, 2.50)

    Examples:
        >>> american_to_decimal(-110)
        1.9090909090909092
        >>> american_to_decimal(+150)
        2.5
    """
    if american_odds < 0:
        return 1 + (100 / abs(american_odds))
    else:
        return 1 + (american_odds / 100)


def de_vig(p_home_raw: float, p_away_raw: float) -> Tuple[float, float]:
    """
    Remove vig from raw implied probabilities by normalizing.

    Args:
        p_home_raw: raw implied probability for home team
        p_away_raw: raw implied probability for away team

    Returns:
        Tuple of (p_home_fair, p_away_fair) normalized probabilities

    Examples:
        >>> de_vig(0.524, 0.524)
        (0.5, 0.5)
    """
    total = p_home_raw + p_away_raw
    if total == 0:
        raise ValueError("Total probability cannot be zero")

    p_home_fair = p_home_raw / total
    p_away_fair = p_away_raw / total

    return p_home_fair, p_away_fair


def expected_value(p_true: float, decimal_odds: float) -> float:
    """
    Calculate expected value (EV) of a bet.

    Formula: EV = p_true * (decimal_odds - 1) - (1 - p_true)

    Args:
        p_true: true/model probability of outcome
        decimal_odds: decimal odds offered

    Returns:
        Expected value in units

    Examples:
        >>> expected_value(0.55, 2.0)
        0.09999999999999998
        >>> expected_value(0.45, 2.0)
        -0.09999999999999998
    """
    return p_true * (decimal_odds - 1) - (1 - p_true)


def kelly_fraction(p_true: float, decimal_odds: float, fraction: float = 1.0) -> float:
    """
    Calculate Kelly criterion stake size.

    Full Kelly: f = (p * (decimal_odds - 1) - (1 - p)) / (decimal_odds - 1)
    Fractional Kelly: multiply by fraction (e.g., 0.25 for quarter Kelly)

    Args:
        p_true: true/model probability of outcome
        decimal_odds: decimal odds offered
        fraction: fraction of Kelly to use (default 1.0 = full Kelly)

    Returns:
        Fraction of bankroll to bet (0-1), or 0 if no edge

    Examples:
        >>> kelly_fraction(0.55, 2.0)
        0.1
        >>> kelly_fraction(0.45, 2.0)
        0.0
    """
    edge = p_true * decimal_odds - 1
    if edge <= 0:
        return 0.0

    kelly = edge / (decimal_odds - 1)
    return max(0.0, kelly * fraction)


def compute_edge_from_american(
    p_true: float,
    home_ml: float,
    away_ml: float,
    side: str = "home"
) -> dict:
    """
    Complete edge calculation from American odds.

    Args:
        p_true: model probability for the specified side
        home_ml: home team American odds
        away_ml: away team American odds
        side: which side we're considering ("home" or "away")

    Returns:
        Dictionary with all relevant calculations:
        - p_market_raw: raw implied probability
        - p_market_fair: de-vigged fair probability
        - decimal_odds: decimal odds for the side
        - ev: expected value
        - edge_pct: edge as percentage
    """
    if side not in ["home", "away"]:
        raise ValueError("side must be 'home' or 'away'")

    # Get odds and compute probabilities
    odds = home_ml if side == "home" else away_ml
    p_home_raw = american_to_implied_prob(home_ml)
    p_away_raw = american_to_implied_prob(away_ml)

    p_home_fair, p_away_fair = de_vig(p_home_raw, p_away_raw)
    p_market_fair = p_home_fair if side == "home" else p_away_fair

    decimal = american_to_decimal(odds)
    ev = expected_value(p_true, decimal)
    edge_pct = (p_true - p_market_fair) * 100

    return {
        "p_market_raw": p_home_raw if side == "home" else p_away_raw,
        "p_market_fair": p_market_fair,
        "decimal_odds": decimal,
        "ev": ev,
        "edge_pct": edge_pct,
    }


if __name__ == "__main__":
    # Example usage and tests
    print("Testing odds_math module...")

    # Test case 1: Even odds
    print("\nTest 1: Even odds (-110 both sides)")
    home_ml, away_ml = -110, -110
    p_home_raw = american_to_implied_prob(home_ml)
    p_away_raw = american_to_implied_prob(away_ml)
    print(f"Raw probabilities: {p_home_raw:.4f}, {p_away_raw:.4f}")
    print(f"Sum: {p_home_raw + p_away_raw:.4f} (vig)")

    p_home_fair, p_away_fair = de_vig(p_home_raw, p_away_raw)
    print(f"Fair probabilities: {p_home_fair:.4f}, {p_away_fair:.4f}")

    # Test case 2: Edge calculation
    print("\nTest 2: Model thinks home wins 55%, market at 50%")
    p_model = 0.55
    edge_info = compute_edge_from_american(p_model, -110, -110, "home")
    print(f"Market fair: {edge_info['p_market_fair']:.4f}")
    print(f"Edge: {edge_info['edge_pct']:.2f}%")
    print(f"EV: {edge_info['ev']:.4f} units")

    # Test case 3: Underdog
    print("\nTest 3: Underdog at +200")
    p_model = 0.40
    edge_info = compute_edge_from_american(p_model, -250, +200, "away")
    print(f"Market fair: {edge_info['p_market_fair']:.4f}")
    print(f"Edge: {edge_info['edge_pct']:.2f}%")
    print(f"EV: {edge_info['ev']:.4f} units")
