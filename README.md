# AI Sports Edge MVP

AI-powered probability model and edge detection system for sports betting markets.

## Overview

This system:
1. Ingests historical game results and odds data (NBA, NHL, NFL)
2. Trains calibrated Elo-based probability models per league
3. Compares model probabilities to market-implied probabilities
4. Backtests an EV-based betting strategy
5. Provides live predictions for today's games
6. Generates alerts and reports

**Supported Leagues:** NBA, NHL, NFL

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

## Live Predictions for Today's Games

### Option 1: Automatic (Recommended) - Fetch Live Data

Get today's games and odds automatically from The Odds API:

```bash
# Get a free API key from https://the-odds-api.com/ (500 requests/month free)
export ODDS_API_KEY=your_key_here

# Fetch and analyze today's games
python scripts/fetch_todays_games.py
```

This will:
1. Fetch today's games for NBA, NHL, and NFL
2. Get current odds from major sportsbooks
3. Load historical Elo ratings
4. Calculate edges and recommend positive EV bets
5. Show game times and bookmaker info

### Option 2: Manual Entry

If you prefer to enter games manually or don't have an API key:

```bash
# Single league (NBA)
python scripts/predict_today.py

# All leagues with manual entry
python scripts/predict_all_leagues.py
```

The script will:
1. Load current Elo ratings from historical games
2. Show top teams by rating
3. Prompt you to enter today's games with current odds
4. Calculate model vs market probabilities
5. Recommend positive EV bets (>1% threshold)

**Example:**
```
NBA Game: Boston Celtics, New York Knicks, -150, +130
  ✓ Added: Boston Celtics vs New York Knicks

Boston Celtics vs New York Knicks
Model: Boston Celtics 65.2% | New York Knicks 34.8%
Market: 60.0% | 40.0%

Home edge: +5.2% (EV: +0.078)

✅ BET: Boston Celtics at -150
```

### Live Injury Adjustments (Recommended)

Fetch live injuries from ESPN and apply them to predictions:

```bash
# Fetch live injuries (NBA/NHL/NFL)
python scripts/fetch_live_injuries.py

# Run injury-adjusted predictions
python scripts/predict_with_injuries.py
```

This will:
1. Pull live injuries from ESPN (no API key required)
2. Save to `data/current_injuries.json`
3. Adjust team Elo ratings before predictions
4. Mark impacted teams with 🏥 and show Elo adjustments

### Future Milestones

See STATUS.md for implementation roadmap.

## Configuration

Edit `config.yaml` to adjust:
- Leagues to track (NBA, NHL, NFL)
- Market type (moneyline)
- Date ranges
- League-specific Elo parameters (K-factor, home advantage)
- Backtest thresholds
- Alert channels

**League-Specific Parameters:**
- **NBA**: K=20, Home Advantage=100 (high home court advantage)
- **NHL**: K=20, Home Advantage=50 (moderate home ice advantage)
- **NFL**: K=30, Home Advantage=80 (higher volatility, strong home field)

## Development Status

✅ M0-M4 Complete: Full MVP operational with multi-league support.

**Features:**
- Historical data ingestion (CSV-based)
- Elo rating system with point-in-time tracking
- Model evaluation (Brier: 0.21, Accuracy: 70%)
- Backtest simulation with ROI/drawdown metrics
- Live prediction tools for NBA, NHL, NFL

See full documentation in:
- SYSTEM.md - System design
- DEEP_RESEARCH.md - Research and methodology
- STATUS.md - Implementation status
