"""
Model training and evaluation with time-based splits.
For M3, we evaluate the Elo model (already trained in features).
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Tuple, Dict
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from features.build import build_features_from_db


def brier_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Calculate Brier score (lower is better).
    Brier = mean((y_pred - y_true)^2)

    Perfect predictions: 0.0
    Random guessing: 0.25
    """
    return np.mean((y_pred - y_true) ** 2)


def log_loss(y_true: np.ndarray, y_pred: np.ndarray, eps: float = 1e-15) -> float:
    """
    Calculate log loss (lower is better).
    """
    y_pred = np.clip(y_pred, eps, 1 - eps)
    return -np.mean(y_true * np.log(y_pred) + (1 - y_true) * np.log(1 - y_pred))


def accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculate accuracy (predict winner correctly)."""
    predictions = (y_pred > 0.5).astype(int)
    return np.mean(predictions == y_true)


def time_split_evaluation(
    features_df: pd.DataFrame,
    split_date: str = None,
    test_size: float = 0.25
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split data by time for training/testing.

    Args:
        features_df: DataFrame with features and outcomes
        split_date: Date to split on (if None, uses test_size)
        test_size: Fraction for test set (if split_date is None)

    Returns:
        Tuple of (train_df, test_df)
    """
    features_df = features_df.sort_values('date').reset_index(drop=True)

    if split_date:
        split_date = pd.to_datetime(split_date)
        train_df = features_df[features_df['date'] < split_date].copy()
        test_df = features_df[features_df['date'] >= split_date].copy()
    else:
        split_idx = int(len(features_df) * (1 - test_size))
        train_df = features_df.iloc[:split_idx].copy()
        test_df = features_df.iloc[split_idx:].copy()

    return train_df, test_df


def evaluate_model(
    features_df: pd.DataFrame,
    split_date: str = None,
    test_size: float = 0.25
) -> Dict:
    """
    Evaluate Elo model with time-split.

    Args:
        features_df: DataFrame with Elo features
        split_date: Date to split on
        test_size: Test set fraction

    Returns:
        Dictionary with metrics
    """
    # Split data
    train_df, test_df = time_split_evaluation(features_df, split_date, test_size)

    # Convert winner to binary (1 = home win, 0 = away win)
    train_y = (train_df['winner'] == 'home').astype(int).values
    test_y = (test_df['winner'] == 'home').astype(int).values

    # Get Elo predictions
    train_pred = train_df['p_home'].values
    test_pred = test_df['p_home'].values

    # Calculate metrics
    results = {
        'train_size': len(train_df),
        'test_size': len(test_df),
        'train_date_range': f"{train_df['date'].min().date()} to {train_df['date'].max().date()}",
        'test_date_range': f"{test_df['date'].min().date()} to {test_df['date'].max().date()}",
        'train_brier': brier_score(train_y, train_pred),
        'test_brier': brier_score(test_y, test_pred),
        'train_logloss': log_loss(train_y, train_pred),
        'test_logloss': log_loss(test_y, test_pred),
        'train_accuracy': accuracy(train_y, train_pred),
        'test_accuracy': accuracy(test_y, test_pred),
        'baseline_brier': 0.25,  # Random guessing
    }

    return results


def calibration_curve(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    n_bins: int = 5
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Calculate calibration curve (binned).

    Returns:
        Tuple of (predicted_probs, actual_frequencies)
    """
    bins = np.linspace(0, 1, n_bins + 1)
    bin_indices = np.digitize(y_pred, bins) - 1
    bin_indices = np.clip(bin_indices, 0, n_bins - 1)

    pred_probs = []
    actual_freqs = []

    for i in range(n_bins):
        mask = bin_indices == i
        if mask.sum() > 0:
            pred_probs.append(y_pred[mask].mean())
            actual_freqs.append(y_true[mask].mean())

    return np.array(pred_probs), np.array(actual_freqs)


if __name__ == "__main__":
    print("=" * 50)
    print("M3: Model Evaluation")
    print("=" * 50)

    # Load features
    print("\n1. Loading features...")
    features_df = build_features_from_db()
    print(f"   {len(features_df)} games")

    # Evaluate
    print("\n2. Time-split evaluation...")
    results = evaluate_model(features_df, test_size=0.25)

    print(f"\n   Train: {results['train_size']} games ({results['train_date_range']})")
    print(f"   Test:  {results['test_size']} games ({results['test_date_range']})")

    print(f"\n3. Metrics:")
    print(f"   Brier Score:")
    print(f"     Train: {results['train_brier']:.4f}")
    print(f"     Test:  {results['test_brier']:.4f}")
    print(f"     Baseline: {results['baseline_brier']:.4f} (random)")

    print(f"\n   Log Loss:")
    print(f"     Train: {results['train_logloss']:.4f}")
    print(f"     Test:  {results['test_logloss']:.4f}")

    print(f"\n   Accuracy:")
    print(f"     Train: {results['train_accuracy']:.1%}")
    print(f"     Test:  {results['test_accuracy']:.1%}")

    # Calibration
    print(f"\n4. Calibration check...")
    test_df = features_df.iloc[int(len(features_df) * 0.75):]
    test_y = (test_df['winner'] == 'home').astype(int).values
    test_pred = test_df['p_home'].values

    pred_probs, actual_freqs = calibration_curve(test_y, test_pred, n_bins=5)

    print(f"   Predicted → Actual:")
    for pred, actual in zip(pred_probs, actual_freqs):
        print(f"     {pred:.2f} → {actual:.2f}")

    print(f"\n✓ Model evaluation complete")
    print("=" * 50)
