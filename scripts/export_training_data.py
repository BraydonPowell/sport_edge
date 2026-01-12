"""
Export training dataset with Elo features.
Saves features to both CSV and Parquet formats.

Usage:
    python scripts/export_training_data.py
"""

import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from features.build import build_features_from_db


def main():
    """Export training dataset to CSV and Parquet."""
    print("=" * 60)
    print("Exporting Training Dataset")
    print("=" * 60)

    # Build features from database
    print("\n1. Building Elo features from database...")
    print("-" * 60)
    features_df = build_features_from_db()

    print(f"✓ Built features for {len(features_df)} games")
    print(f"  Date range: {features_df['date'].min().date()} to {features_df['date'].max().date()}")
    print(f"  Teams: {len(set(features_df['home_team']) | set(features_df['away_team']))}")

    # Create output directory
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    os.makedirs(output_dir, exist_ok=True)

    # Export to CSV
    print("\n2. Exporting to CSV...")
    print("-" * 60)
    csv_path = os.path.join(output_dir, "training_features.csv")
    features_df.to_csv(csv_path, index=False)
    print(f"✓ Saved to: {csv_path}")
    print(f"  Size: {os.path.getsize(csv_path) / 1024:.1f} KB")

    # Export to Parquet
    print("\n3. Exporting to Parquet...")
    print("-" * 60)
    parquet_path = os.path.join(output_dir, "training_features.parquet")
    features_df.to_parquet(parquet_path, index=False, engine='pyarrow')
    print(f"✓ Saved to: {parquet_path}")
    print(f"  Size: {os.path.getsize(parquet_path) / 1024:.1f} KB")

    # Show sample
    print("\n4. Sample features:")
    print("-" * 60)
    print(features_df.head(5).to_string(index=False))

    # Show statistics
    print("\n5. Feature statistics:")
    print("-" * 60)
    print(f"  Elo ratings:")
    print(f"    Min: {features_df['home_elo'].min():.0f}")
    print(f"    Max: {features_df['home_elo'].max():.0f}")
    print(f"    Mean: {features_df['home_elo'].mean():.0f}")
    print(f"    Std: {features_df['home_elo'].std():.0f}")

    print(f"\n  Win probabilities:")
    print(f"    Home win prob (mean): {features_df['p_home'].mean():.3f}")
    print(f"    Home win prob (std): {features_df['p_home'].std():.3f}")

    # Actual win rate
    actual_home_wins = (features_df['winner'] == 'home').sum()
    total_games = len(features_df)
    print(f"\n  Actual results:")
    print(f"    Home wins: {actual_home_wins}/{total_games} ({actual_home_wins/total_games:.1%})")

    print("\n" + "=" * 60)
    print("Export complete!")
    print("=" * 60)
    print(f"\nFiles created:")
    print(f"  - {csv_path}")
    print(f"  - {parquet_path}")
    print(f"\nNext steps:")
    print(f"  - Use these features for model training (M3)")
    print(f"  - Validate on test set")


if __name__ == "__main__":
    main()
