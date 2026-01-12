# AI Sports Edge MVP

AI-powered probability model and edge detection system for sports betting markets.

## Overview

This system:
1. Ingests historical game results and odds data
2. Trains a calibrated probability model
3. Compares model probabilities to market-implied probabilities
4. Backtests an EV-based betting strategy
5. Generates alerts and reports

## Project Structure

```
Sports_edge/
├── ingest/          # Data ingestion (games, odds)
├── edge/            # Market math and EV calculations
├── features/        # Point-in-time feature engineering
├── models/          # Model training and prediction
├── backtest/        # Strategy backtesting
├── report/          # Report generation and alerts
├── data/            # SQLite database and raw data files
├── reports/         # Generated reports
├── logs/            # Execution logs
├── db_schema.py     # Database schema definition
└── config.yaml      # Configuration settings
```

## Quick Start (Single Command)

Get up and running with sample data in one command:

```bash
python scripts/init_db.py && python scripts/load_sample_data.py && python scripts/verify_data.py
```

This will:
1. Create the SQLite database with all tables
2. Load 40 sample NBA games (Oct-Nov 2023) with closing odds
3. Verify the data and show sample edge calculations

## Setup

### 1. Install Dependencies

```bash
pip install -e .
```

Required packages:
- pandas, numpy, scikit-learn
- sqlalchemy (database)
- pyyaml, python-dotenv (config)
- requests (future API integration)

### 2. Environment Configuration

```bash
cp .env.example .env
```

Edit `.env` if you want to:
- Change database location
- Add API keys (for future live odds)
- Configure alert channels

### 3. Initialize Database

```bash
python scripts/init_db.py
```

Creates SQLite database at `data/sports_edge.db` with tables:
- `games` - game results
- `odds` - odds snapshots
- `team_ratings` - Elo/rating history
- `predictions` - model predictions
- `backtest_runs` - backtest results

## Usage

### Load Sample Data

```bash
python scripts/load_sample_data.py
```

Loads sample CSV files:
- `data/sample_games.csv` - 40 NBA games
- `data/sample_odds.csv` - Closing odds from DraftKings & FanDuel

### Verify Data

```bash
python scripts/verify_data.py
```

Shows:
- Record counts
- Sample games and odds
- Date range coverage
- Example edge calculation

### Manual Ingestion

For your own data:

```bash
# Ingest games
python ingest/games.py data/your_games.csv --league NBA

# Ingest odds
python ingest/odds.py data/your_odds.csv
```

CSV format requirements in docstrings.

### Run Tests

```bash
# Run all tests (comprehensive)
./scripts/run_all_tests.sh

# Or run individual test suites
python tests/test_odds_math.py

# Or use pytest (if installed)
pytest tests/ -v
```

The comprehensive test suite validates:
- Odds math functions
- Database schema
- CSV ingestion
- Edge calculations
- End-to-end pipeline

### Future Milestones

See STATUS.md for implementation roadmap.

## Configuration

Edit `config.yaml` to adjust:
- League and market type
- Date ranges
- Model parameters
- Backtest thresholds
- Alert channels

## Development Status

Currently at M0/M1: Scaffolding and ingestion complete.

See full documentation in:
- SYSTEM.md - System design
- DEEP_RESEARCH.md - Research and methodology
- STATUS.md - Implementation status
