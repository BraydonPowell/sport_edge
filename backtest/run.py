"""
Backtest runner with EV-based betting strategy.
Simulates flat-stake betting on positive EV opportunities.
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
from typing import Dict, List
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from features.build import build_features_from_db
from ingest.odds import get_closing_odds
from edge.odds_math import compute_edge_from_american
from db_schema import get_session, Odds


def run_backtest(
    features_df: pd.DataFrame,
    ev_threshold: float = 0.01,
    stake_size: float = 1.0,
    min_games: int = 0
) -> Dict:
    """
    Run backtest simulation.

    Args:
        features_df: DataFrame with Elo predictions
        ev_threshold: Minimum EV to place bet (default 1%)
        stake_size: Flat stake per bet
        min_games: Minimum games before betting starts

    Returns:
        Dictionary with backtest results
    """
    session = get_session()

    bets = []
    bankroll = []
    current_bankroll = 0.0

    for idx, row in features_df.iterrows():
        if idx < min_games:
            continue

        # Get closing odds from database
        odds_records = (
            session.query(Odds)
            .filter(Odds.game_id == row['game_id'], Odds.source == 'closing')
            .all()
        )

        if not odds_records:
            continue

        # Use first book's odds
        odds = odds_records[0]

        # Calculate edge for both sides
        home_edge = compute_edge_from_american(
            row['p_home'], odds.home_ml, odds.away_ml, 'home'
        )
        away_edge = compute_edge_from_american(
            row['p_away'], odds.home_ml, odds.away_ml, 'away'
        )

        # Determine best bet
        best_side = None
        best_edge = None
        best_odds = None

        if home_edge['ev'] > ev_threshold and home_edge['ev'] > away_edge['ev']:
            best_side = 'home'
            best_edge = home_edge
            best_odds = odds.home_ml
        elif away_edge['ev'] > ev_threshold:
            best_side = 'away'
            best_edge = away_edge
            best_odds = odds.away_ml

        if best_side:
            # Place bet
            won = (row['winner'] == best_side)
            decimal_odds = best_edge['decimal_odds']
            profit = stake_size * (decimal_odds - 1) if won else -stake_size

            current_bankroll += profit

            bets.append({
                'game_id': row['game_id'],
                'date': row['date'],
                'side': best_side,
                'odds': best_odds,
                'stake': stake_size,
                'ev': best_edge['ev'],
                'edge_pct': best_edge['edge_pct'],
                'won': won,
                'profit': profit,
                'bankroll': current_bankroll
            })

        bankroll.append(current_bankroll)

    session.close()

    if not bets:
        return {
            'total_bets': 0,
            'total_staked': 0,
            'total_profit': 0,
            'roi': 0,
            'win_rate': 0,
            'max_drawdown': 0,
            'final_bankroll': 0
        }

    bets_df = pd.DataFrame(bets)

    # Calculate metrics
    total_bets = len(bets_df)
    total_staked = total_bets * stake_size
    total_profit = bets_df['profit'].sum()
    roi = (total_profit / total_staked) * 100 if total_staked > 0 else 0
    win_rate = bets_df['won'].mean() * 100

    # Max drawdown
    cumulative = bets_df['bankroll'].values
    running_max = np.maximum.accumulate(cumulative)
    drawdown = running_max - cumulative
    max_drawdown = drawdown.max()

    return {
        'total_bets': total_bets,
        'total_staked': total_staked,
        'total_profit': total_profit,
        'roi': roi,
        'win_rate': win_rate,
        'max_drawdown': max_drawdown,
        'final_bankroll': current_bankroll,
        'bets': bets_df,
        'avg_ev': bets_df['ev'].mean(),
        'avg_edge': bets_df['edge_pct'].mean()
    }


if __name__ == "__main__":
    print("=" * 50)
    print("M4: Backtest Simulation")
    print("=" * 50)

    # Load features
    print("\n1. Loading features...")
    features_df = build_features_from_db()
    print(f"   {len(features_df)} games")

    # Run backtest
    print("\n2. Running backtest...")
    print(f"   EV threshold: 1%")
    print(f"   Stake: $1 per bet")

    results = run_backtest(
        features_df,
        ev_threshold=0.01,
        stake_size=1.0,
        min_games=5
    )

    print(f"\n3. Results:")
    print(f"   Total bets: {results['total_bets']}")
    print(f"   Win rate: {results['win_rate']:.1f}%")
    print(f"   Total staked: ${results['total_staked']:.2f}")
    print(f"   Total profit: ${results['total_profit']:.2f}")
    print(f"   ROI: {results['roi']:.1f}%")
    print(f"   Max drawdown: ${results['max_drawdown']:.2f}")

    if results['total_bets'] > 0:
        print(f"\n4. Edge stats:")
        print(f"   Avg EV: {results['avg_ev']:.4f}")
        print(f"   Avg edge: {results['avg_edge']:.2f}%")

        print(f"\n5. Sample bets:")
        sample = results['bets'].head(5)[['date', 'side', 'odds', 'edge_pct', 'won', 'profit']]
        for _, bet in sample.iterrows():
            won_str = "W" if bet['won'] else "L"
            print(f"   {bet['date'].date()} {bet['side']:4s} {bet['odds']:+5.0f} edge={bet['edge_pct']:+.1f}% [{won_str}] ${bet['profit']:+.2f}")

    print(f"\n✓ Backtest complete")
    print("=" * 50)
