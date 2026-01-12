"""
Compute ROI for logged live bets by matching results in the database.

Usage:
    python scripts/roi_report.py
"""

import csv
from datetime import datetime, timedelta
from pathlib import Path

from db_schema import get_session, Game


def american_profit(odds, stake=1.0):
    """Return profit on a win for American odds."""
    if odds > 0:
        return (odds / 100.0) * stake
    return (100.0 / abs(odds)) * stake


def find_game(session, league, home_team, away_team, commence_time):
    """Find a matching game by league, teams, and date window."""
    start = datetime.combine(commence_time.date(), datetime.min.time())
    end = datetime.combine(commence_time.date(), datetime.max.time())

    return (
        session.query(Game)
        .filter(Game.league == league)
        .filter(Game.home_team == home_team)
        .filter(Game.away_team == away_team)
        .filter(Game.date >= start)
        .filter(Game.date <= end)
        .first()
    )


def compute_roi(bets):
    """Compute ROI metrics for settled bets."""
    total_staked = 0.0
    total_profit = 0.0
    wins = 0
    losses = 0

    for bet in bets:
        total_staked += bet["stake"]
        total_profit += bet["profit"]
        if bet["profit"] > 0:
            wins += 1
        else:
            losses += 1

    roi = (total_profit / total_staked) if total_staked > 0 else 0.0
    return {
        "total_staked": total_staked,
        "total_profit": total_profit,
        "wins": wins,
        "losses": losses,
        "roi": roi,
    }


def main():
    bets_file = Path("data/live_bets.csv")
    if not bets_file.exists():
        print("❌ No live bets found. Run predict_with_injuries.py first.")
        return

    session = get_session()

    settled_bets = []
    pending_bets = 0

    with open(bets_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            league = row["league"]
            home_team = row["home_team"]
            away_team = row["away_team"]
            bet_team = row["bet_team"]
            odds = float(row["odds"])
            commence_time = datetime.fromisoformat(row["commence_time"])

            game = find_game(session, league, home_team, away_team, commence_time)
            if not game or game.home_score is None or game.away_score is None:
                pending_bets += 1
                continue

            winner = game.winner
            if not winner:
                if game.home_score > game.away_score:
                    winner = "home"
                elif game.away_score > game.home_score:
                    winner = "away"
                else:
                    winner = "draw"

            bet_side = "home" if bet_team == home_team else "away"
            stake = 1.0

            if winner == bet_side:
                profit = american_profit(odds, stake=stake)
            else:
                profit = -stake

            settled_bets.append({
                "profit": profit,
                "stake": stake,
            })

    session.close()

    print("=" * 60)
    print("ROI REPORT (Live Bets)")
    print("=" * 60)
    print(f"Total logged bets: {len(settled_bets) + pending_bets}")
    print(f"Settled bets: {len(settled_bets)}")
    print(f"Pending bets: {pending_bets}")

    if settled_bets:
        metrics = compute_roi(settled_bets)
        total = metrics["wins"] + metrics["losses"]
        win_rate = (metrics["wins"] / total) if total > 0 else 0.0
        print("\nResults:")
        print(f"  Wins: {metrics['wins']}")
        print(f"  Losses: {metrics['losses']}")
        print(f"  Win rate: {win_rate:.1%}")
        print(f"  Total staked: ${metrics['total_staked']:.2f}")
        print(f"  Total profit: ${metrics['total_profit']:+.2f}")
        print(f"  ROI: {metrics['roi']:+.1%}")
    else:
        print("\nNo settled bets yet. Check back after games finish.")

    print("=" * 60)


if __name__ == "__main__":
    main()
