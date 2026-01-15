"""
Fetch live moneyline odds for today's games and compute Elo-based edge/EV.
Supports NBA, UFC, and main soccer leagues.
"""

import json
import math
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import requests

CONFIG = {
    "min_edge": float(os.environ.get("MIN_EDGE", "2.0")),
    "shrink_weight": float(os.environ.get("PROB_SHRINK_W", "0.7")),
    "kelly_mult": float(os.environ.get("KELLY_MULT", "0.25")),
    "max_stake": float(os.environ.get("MAX_STAKE", "0.02")),
    "bankroll": float(os.environ.get("BANKROLL", "1000")),
    "min_draw_rate": float(os.environ.get("MIN_DRAW_RATE", "0.05")),
    "min_prob": float(os.environ.get("MIN_PROB", "0.01")),
}


def _load_env(project_root: str) -> None:
    env_path = os.path.join(project_root, ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ.setdefault(key.strip(), value.strip())


def american_to_decimal(american_odds: float) -> float:
    if american_odds < 0:
        return 1 + (100 / abs(american_odds))
    return 1 + (american_odds / 100)


def expected_value(p_true: float, decimal_odds: float) -> float:
    return p_true * (decimal_odds - 1) - (1 - p_true)


def expected_score(rating_a: float, rating_b: float) -> float:
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def _clamp_prob(prob: float, min_prob: float, max_prob: float) -> float:
    return max(min_prob, min(max_prob, prob))


class IsotonicCalibrator:
    def __init__(self) -> None:
        self._bins: List[Tuple[float, float, float]] = []

    def fit(self, probs: List[float], outcomes: List[int], weights: Optional[List[float]] = None) -> None:
        if not probs:
            self._bins = []
            return

        weights = weights or [1.0] * len(probs)
        data = sorted(zip(probs, outcomes, weights), key=lambda x: x[0])

        blocks = []
        for p, y, w in data:
            blocks.append([p, p, y * w, w])
            while len(blocks) >= 2 and blocks[-2][2] / blocks[-2][3] > blocks[-1][2] / blocks[-1][3]:
                b2 = blocks.pop()
                b1 = blocks.pop()
                merged = [
                    b1[0],
                    b2[1],
                    b1[2] + b2[2],
                    b1[3] + b2[3],
                ]
                blocks.append(merged)

        self._bins = [(b[0], b[1], b[2] / b[3]) for b in blocks]

    def predict(self, prob: float) -> float:
        if not self._bins:
            return prob
        for start, end, value in self._bins:
            if prob <= end:
                return value
        return self._bins[-1][2]


def _odds_api_get(url: str, params: Dict[str, str]) -> Dict:
    response = requests.get(url, params=params, timeout=15)
    if response.status_code != 200:
        try:
            payload = response.json()
        except Exception:
            payload = {}
        error_code = payload.get("error_code")
        if error_code:
            raise RuntimeError(f"Odds API error ({error_code}): {payload.get('message', 'Unknown')}")
        response.raise_for_status()
    return response.json()


def _parse_commence_time(raw_time: str) -> datetime:
    return datetime.fromisoformat(raw_time.replace("Z", "+00:00")).astimezone()


def _is_today(dt: datetime) -> bool:
    now = datetime.now().astimezone()
    return dt.date() == now.date()


def fetch_today_odds(sport_key: str) -> List[Dict[str, object]]:
    api_key = os.environ.get("ODDS_API_KEY")
    if not api_key:
        raise RuntimeError("ODDS_API_KEY missing. Set it in .env.")

    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    data = _odds_api_get(url, {
        "apiKey": api_key,
        "regions": "us",
        "markets": "h2h",
        "oddsFormat": "american",
        "dateFormat": "iso",
    })

    events = []
    for event in data:
        commence_time = _parse_commence_time(event.get("commence_time", ""))
        if not _is_today(commence_time):
            continue

        bookmakers = event.get("bookmakers", [])
        if not bookmakers:
            continue
        markets = bookmakers[0].get("markets", [])
        if not markets:
            continue
        outcomes = markets[0].get("outcomes", [])

        odds = {}
        for outcome in outcomes:
            name = outcome.get("name")
            price = outcome.get("price")
            if name and price is not None:
                if name.lower() == "tie":
                    name = "Draw"
                odds[name] = price

        events.append({
            "id": event.get("id"),
            "home_team": event.get("home_team"),
            "away_team": event.get("away_team"),
            "commence_time": commence_time,
            "odds": odds,
            "sport_title": event.get("sport_title"),
            "event_title": event.get("description"),
        })

    return events


def fetch_scores(sport_key: str, days_back: int) -> List[Dict[str, object]]:
    api_key = os.environ.get("ODDS_API_KEY")
    if not api_key:
        raise RuntimeError("ODDS_API_KEY missing. Set it in .env.")

    days_back = max(1, min(days_back, 3))
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/scores"
    data = _odds_api_get(url, {
        "apiKey": api_key,
        "daysFrom": str(days_back),
        "dateFormat": "iso",
    })

    completed = []
    for event in data:
        if not event.get("completed"):
            continue
        commence_time = _parse_commence_time(event.get("commence_time", ""))
        scores = event.get("scores", [])
        if not scores:
            continue
        score_map = {s.get("name"): s.get("score") for s in scores}
        home = event.get("home_team")
        away = event.get("away_team")
        if home not in score_map or away not in score_map:
            continue
        completed.append({
            "home_team": home,
            "away_team": away,
            "home_score": score_map.get(home),
            "away_score": score_map.get(away),
            "date": commence_time,
        })

    completed.sort(key=lambda x: x["date"])
    return completed


def _time_weight(event_date: datetime, half_life_days: float) -> float:
    now = datetime.now().astimezone()
    age_days = max(0.0, (now - event_date).total_seconds() / 86400)
    return math.exp(-math.log(2) * age_days / max(half_life_days, 1))


def _build_elo_from_scores(
    scores: List[Dict[str, object]],
    k_factor: float,
    home_advantage: float,
    half_life_days: float,
    draw_calibration: bool = False,
) -> Tuple[Dict[str, float], Dict[str, int], Dict[str, datetime], Optional[IsotonicCalibrator], Optional[IsotonicCalibrator], Optional[IsotonicCalibrator], Optional[float]]:
    ratings: Dict[str, float] = {}
    counts: Dict[str, int] = {}
    last_played: Dict[str, datetime] = {}

    home_probs: List[float] = []
    away_probs: List[float] = []
    draw_probs: List[float] = []
    home_outcomes: List[int] = []
    away_outcomes: List[int] = []
    draw_outcomes: List[int] = []
    weights: List[float] = []

    draw_weighted = 0.0
    total_weighted = 0.0

    for game in scores:
        home = game["home_team"]
        away = game["away_team"]
        if home not in ratings:
            ratings[home] = 1500.0
            counts[home] = 0
        if away not in ratings:
            ratings[away] = 1500.0
            counts[away] = 0

        event_date = game["date"]
        weight = _time_weight(event_date, half_life_days)
        total_weighted += weight

        home_rating = ratings[home] + home_advantage
        away_rating = ratings[away]
        p_home_raw = expected_score(home_rating, away_rating)
        p_away_raw = 1 - p_home_raw

        try:
            home_score = float(game["home_score"])
            away_score = float(game["away_score"])
        except Exception:
            continue
        if home_score > away_score:
            actual_home = 1.0
            actual_away = 0.0
            actual_draw = 0.0
        elif away_score > home_score:
            actual_home = 0.0
            actual_away = 1.0
            actual_draw = 0.0
        else:
            actual_home = 0.5
            actual_away = 0.5
            actual_draw = 1.0
            draw_weighted += weight

        k_eff = k_factor * weight
        ratings[home] += k_eff * (actual_home - p_home_raw)
        ratings[away] += k_eff * (actual_away - p_away_raw)

        counts[home] += 1
        counts[away] += 1
        last_played[home] = event_date
        last_played[away] = event_date

        if draw_calibration:
            home_probs.append(p_home_raw)
            away_probs.append(p_away_raw)
            draw_probs.append(0.0)
            home_outcomes.append(1 if actual_home == 1 else 0)
            away_outcomes.append(1 if actual_away == 1 else 0)
            draw_outcomes.append(1 if actual_draw == 1 else 0)
            weights.append(weight)

    draw_rate = (draw_weighted / total_weighted) if total_weighted else 0.25
    if draw_rate < CONFIG["min_draw_rate"]:
        draw_rate = 0.25

    home_cal = away_cal = draw_cal = None
    if draw_calibration and home_probs:
        def has_both_classes(outcomes: List[int]) -> bool:
            return 0 in outcomes and 1 in outcomes

        home_cal = IsotonicCalibrator()
        away_cal = IsotonicCalibrator()
        draw_cal = IsotonicCalibrator()
        if has_both_classes(home_outcomes):
            home_cal.fit(home_probs, home_outcomes, weights)
        else:
            home_cal = None
        if has_both_classes(away_outcomes):
            away_cal.fit(away_probs, away_outcomes, weights)
        else:
            away_cal = None
        if has_both_classes(draw_outcomes):
            draw_cal.fit([draw_rate] * len(draw_outcomes), draw_outcomes, weights)
        else:
            draw_cal = None

    return ratings, counts, last_played, home_cal, away_cal, draw_cal, draw_rate


def _build_elo_ufc(scores: List[Dict[str, object]], k_factor: float, half_life_days: float) -> Tuple[Dict[str, float], Dict[str, int], Dict[str, datetime], IsotonicCalibrator]:
    ratings: Dict[str, float] = {}
    counts: Dict[str, int] = {}
    last_played: Dict[str, datetime] = {}

    probs: List[float] = []
    outcomes: List[int] = []
    weights: List[float] = []

    for fight in scores:
        fighter_a = fight["home_team"]
        fighter_b = fight["away_team"]
        if fighter_a not in ratings:
            ratings[fighter_a] = 1500.0
            counts[fighter_a] = 0
        if fighter_b not in ratings:
            ratings[fighter_b] = 1500.0
            counts[fighter_b] = 0

        event_date = fight["date"]
        weight = _time_weight(event_date, half_life_days)

        rating_a = ratings[fighter_a]
        rating_b = ratings[fighter_b]
        p_a = expected_score(rating_a, rating_b)

        try:
            a_score = float(fight["home_score"])
            b_score = float(fight["away_score"])
        except Exception:
            continue
        actual_a = 1.0 if a_score > b_score else 0.0

        fights_a = counts[fighter_a]
        fights_b = counts[fighter_b]
        exp_shrink = min(1.0, (fights_a + fights_b + 2) / 20.0)
        k_eff = k_factor * weight * exp_shrink

        ratings[fighter_a] += k_eff * (actual_a - p_a)
        ratings[fighter_b] += k_eff * ((1 - actual_a) - (1 - p_a))

        counts[fighter_a] += 1
        counts[fighter_b] += 1
        last_played[fighter_a] = event_date
        last_played[fighter_b] = event_date

        probs.append(p_a)
        outcomes.append(1 if actual_a == 1 else 0)
        weights.append(weight)

    calibrator = IsotonicCalibrator()
    calibrator.fit(probs, outcomes, weights)
    return ratings, counts, last_played, calibrator


def _apply_ufc_adjustments(rating: float, fights: int, last_date: Optional[datetime]) -> float:
    if fights <= 0:
        return 1500.0
    shrink = min(1.0, fights / 10.0)
    if last_date:
        layoff_days = (datetime.now().astimezone() - last_date).days
        layoff_shrink = math.exp(-layoff_days / 365.0)
    else:
        layoff_shrink = 0.8
    shrink *= layoff_shrink
    return 1500.0 + (rating - 1500.0) * shrink


def _normalize_probs(home: float, draw: float, away: float) -> Tuple[float, float, float]:
    total = max(home + draw + away, 1e-6)
    return home / total, draw / total, away / total


def _compute_market_probs(odds: Dict[str, int]) -> Dict[str, float]:
    implied = {}
    for name, price in odds.items():
        if price is None:
            continue
        if name.lower() == "tie":
            name = "Draw"
        prob = abs(price) / (abs(price) + 100) if price < 0 else 100 / (price + 100)
        implied[name] = prob
    total = sum(implied.values()) or 1.0
    return {name: prob / total for name, prob in implied.items()}


def _build_predictions() -> Dict[str, object]:
    leagues = [
        ("NBA", "basketball_nba", "basketball"),
        ("NHL", "icehockey_nhl", "hockey"),
        ("UFC", "mma_mixed_martial_arts", "ufc"),
    ]

    predictions = []

    for league_name, sport_key, league_type in leagues:
        try:
            today_events = fetch_today_odds(sport_key)
        except RuntimeError as e:
            return {"games": [], "error": str(e)}

        if league_type == "ufc":
            today_events = [
                event for event in today_events
                if "ufc" in (event.get("sport_title") or "").lower()
            ]

        if not today_events:
            continue

        days_back = 180 if league_type == "soccer" else 365
        scores = []
        try:
            scores = fetch_scores(sport_key, days_back)
        except RuntimeError as e:
            return {"games": [], "error": str(e)}

        if league_type == "soccer":
            ratings, counts, last_played, home_cal, away_cal, draw_cal, draw_rate = _build_elo_from_scores(
                scores,
                k_factor=18,
                home_advantage=80,
                half_life_days=45,
                draw_calibration=True,
            )
        elif league_type == "ufc":
            ratings, counts, last_played, ufc_cal = _build_elo_ufc(
                scores,
                k_factor=24,
                half_life_days=180,
            )
        elif league_type == "hockey":
            ratings, counts, last_played, home_cal, away_cal, _, _ = _build_elo_from_scores(
                scores,
                k_factor=16,
                home_advantage=40,
                half_life_days=60,
            )
        else:
            ratings, counts, last_played, home_cal, away_cal, _, _ = _build_elo_from_scores(
                scores,
                k_factor=20,
                home_advantage=60,
                half_life_days=45,
            )

        for event in today_events:
            home = event["home_team"]
            away = event["away_team"]
            odds = event["odds"]
            if not odds:
                continue

            home_rating = ratings.get(home, 1500.0)
            away_rating = ratings.get(away, 1500.0)
            home_adj = home_rating
            away_adj = away_rating

            if league_type == "soccer":
                p_home_raw = expected_score(home_rating + 80, away_rating)
                p_away_raw = 1 - p_home_raw
                p_draw = draw_rate or 0.25
                p_home = p_home_raw * (1 - p_draw)
                p_away = p_away_raw * (1 - p_draw)
                p_home, p_draw, p_away = _normalize_probs(p_home, p_draw, p_away)
                if home_cal and away_cal and draw_cal:
                    p_home = home_cal.predict(p_home)
                    p_away = away_cal.predict(p_away)
                    p_draw = draw_cal.predict(p_draw)
                    p_home, p_draw, p_away = _normalize_probs(p_home, p_draw, p_away)
                min_prob = CONFIG["min_prob"]
                max_prob = 1 - min_prob
                p_home = _clamp_prob(p_home, min_prob, max_prob)
                p_away = _clamp_prob(p_away, min_prob, max_prob)
                p_draw = _clamp_prob(p_draw, min_prob, max_prob)
                p_home, p_draw, p_away = _normalize_probs(p_home, p_draw, p_away)
            elif league_type == "ufc":
                fights_home = counts.get(home, 0)
                fights_away = counts.get(away, 0)
                home_adj = _apply_ufc_adjustments(home_rating, fights_home, last_played.get(home))
                away_adj = _apply_ufc_adjustments(away_rating, fights_away, last_played.get(away))
                p_home = expected_score(home_adj, away_adj)
                p_away = 1 - p_home
                if ufc_cal:
                    p_home = ufc_cal.predict(p_home)
                    p_away = 1 - p_home
                p_draw = 0.0
            elif league_type == "hockey":
                p_home = expected_score(home_rating + 40, away_rating)
                p_away = 1 - p_home
                p_draw = 0.0
                if home_cal and away_cal:
                    p_home = home_cal.predict(p_home)
                    p_away = away_cal.predict(p_away)
                    p_home, _, p_away = _normalize_probs(p_home, 0.0, p_away)
            else:
                p_home = expected_score(home_rating + 60, away_rating)
                p_away = 1 - p_home
                p_draw = 0.0
                if home_cal and away_cal:
                    p_home = home_cal.predict(p_home)
                    p_away = away_cal.predict(p_away)
                    p_home, _, p_away = _normalize_probs(p_home, 0.0, p_away)

            market_probs = _compute_market_probs(odds)
            home_odds = odds.get(home)
            away_odds = odds.get(away)
            draw_odds = odds.get("Draw")

            def adjusted_prob(outcome_prob: float, outcome_name: str) -> float:
                market_prob = market_probs.get(outcome_name, 0.0)
                w = max(0.0, min(1.0, CONFIG["shrink_weight"]))
                return w * outcome_prob + (1 - w) * market_prob

            def kelly_fraction(prob: float, decimal_odds: float) -> float:
                edge = prob * decimal_odds - 1
                if edge <= 0:
                    return 0.0
                return edge / (decimal_odds - 1)

            def outcome_metrics(outcome_prob: float, price: Optional[int], outcome_name: str) -> Dict[str, float]:
                if price is None:
                    return {
                        "decimal": 0.0,
                        "market_prob": market_probs.get(outcome_name, 0.0),
                        "p_adj": 0.0,
                        "edge": 0.0,
                        "ev": -1.0,
                        "stake_frac": 0.0,
                        "stake_dollars": 0.0,
                    }
                decimal = american_to_decimal(price)
                market_prob = market_probs.get(outcome_name, 0.0)
                p_adj = adjusted_prob(outcome_prob, outcome_name)
                ev = p_adj * decimal - 1
                edge = (p_adj - market_prob) * 100
                kelly = kelly_fraction(p_adj, decimal)
                stake_frac = max(0.0, min(kelly * CONFIG["kelly_mult"], CONFIG["max_stake"]))
                stake_dollars = stake_frac * CONFIG["bankroll"]
                return {
                    "decimal": decimal,
                    "market_prob": market_prob,
                    "p_adj": p_adj,
                    "edge": edge,
                    "ev": ev,
                    "stake_frac": stake_frac,
                    "stake_dollars": stake_dollars,
                }

            home_metrics = outcome_metrics(p_home, home_odds, home)
            away_metrics = outcome_metrics(p_away, away_odds, away)

            draw_metrics = {
                "decimal": 0.0,
                "market_prob": market_probs.get("Draw", 0.0),
                "p_adj": 0.0,
                "edge": 0.0,
                "ev": -1.0,
                "stake_frac": 0.0,
                "stake_dollars": 0.0,
            }
            if draw_odds is not None and p_draw > 0:
                draw_metrics = outcome_metrics(p_draw, draw_odds, "Draw")

            best_side = None
            best_score = -1.0
            min_edge = CONFIG["min_edge"]
            options = [
                ("home", home_metrics),
                ("away", away_metrics),
                ("draw", draw_metrics),
            ]
            for side, metrics in options:
                if metrics["ev"] > 0 and metrics["edge"] >= min_edge:
                    score = metrics["ev"] * metrics["stake_frac"]
                    if score > best_score:
                        best_score = score
                        best_side = side

            predictions.append({
                "id": f"{sport_key}_{event['id']}",
                "homeTeam": home,
                "awayTeam": away,
                "homeElo": round(home_rating),
                "awayElo": round(away_rating),
                "homeEloAdjusted": round(home_adj),
                "awayEloAdjusted": round(away_adj),
                "homeProbability": round(p_home * 100, 1),
                "awayProbability": round(p_away * 100, 1),
                "drawProbability": round(p_draw * 100, 1) if p_draw > 0 else None,
                "homeOdds": home_odds or 0,
                "awayOdds": away_odds or 0,
                "drawOdds": draw_odds,
                "homeMarketProb": round(home_metrics["market_prob"] * 100, 1),
                "awayMarketProb": round(away_metrics["market_prob"] * 100, 1),
                "drawMarketProb": round(draw_metrics["market_prob"] * 100, 1) if draw_odds is not None else None,
                "homeDecimalOdds": round(home_metrics["decimal"], 3),
                "awayDecimalOdds": round(away_metrics["decimal"], 3),
                "drawDecimalOdds": round(draw_metrics["decimal"], 3) if draw_odds is not None else None,
                "homeEdge": round(home_metrics["edge"], 1),
                "awayEdge": round(away_metrics["edge"], 1),
                "drawEdge": round(draw_metrics["edge"], 1) if draw_odds is not None else None,
                "homeEV": round(home_metrics["ev"], 3),
                "awayEV": round(away_metrics["ev"], 3),
                "drawEV": round(draw_metrics["ev"], 3) if draw_odds is not None else None,
                "homeStakeFrac": round(home_metrics["stake_frac"], 4),
                "awayStakeFrac": round(away_metrics["stake_frac"], 4),
                "drawStakeFrac": round(draw_metrics["stake_frac"], 4) if draw_odds is not None else None,
                "homeStakeDollars": round(home_metrics["stake_dollars"], 2),
                "awayStakeDollars": round(away_metrics["stake_dollars"], 2),
                "drawStakeDollars": round(draw_metrics["stake_dollars"], 2) if draw_odds is not None else None,
                "recommendedBet": best_side,
                "league": league_name,
                "gameTime": event["commence_time"].isoformat(),
            })

    def _score(prediction: Dict[str, object]) -> float:
        best = 0.0
        for side in ("home", "away", "draw"):
            ev = prediction.get(f"{side}EV")
            stake = prediction.get(f"{side}StakeFrac")
            if isinstance(ev, (int, float)) and isinstance(stake, (int, float)):
                best = max(best, ev * stake)
        return best

    predictions.sort(key=_score, reverse=True)
    top = [p for p in predictions if p.get("recommendedBet")][:10]
    return {"games": top, "config": CONFIG}


def main() -> None:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    _load_env(project_root)
    payload = _build_predictions()
    print(json.dumps(payload))


if __name__ == "__main__":
    main()
