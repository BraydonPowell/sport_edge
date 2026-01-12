# Sports Edge MVP - Quick Start Guide

## One-Command Setup

```bash
./scripts/quickstart.sh
```

This single script will:
1. Create a Python virtual environment
2. Install all dependencies
3. Initialize the SQLite database
4. Load 40 sample NBA games with closing odds
5. Verify data integrity

**Expected output:** Database with 40 games, 80 odds records, 100% coverage.

## Alternative: Step-by-Step Setup

### Step 1: Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### Step 2: Initialize Database

```bash
python scripts/init_db.py
```

Creates `data/sports_edge.db` with 5 tables:
- `games` (8 columns)
- `odds` (7 columns)
- `team_ratings` (4 columns)
- `predictions` (6 columns)
- `backtest_runs` (4 columns)

### Step 3: Load Sample Data

```bash
python scripts/load_sample_data.py
```

Ingests:
- `data/sample_games.csv` → 40 NBA games (Oct 24 - Nov 12, 2023)
- `data/sample_odds.csv` → 80 closing odds from DraftKings & FanDuel

### Step 4: Verify Data

```bash
python scripts/verify_data.py
```

Shows:
- Record counts
- Sample games and odds
- Date range (2023-10-24 to 2023-11-12)
- Coverage statistics (100%)
- Example edge calculation

## Run Tests

```bash
# Test odds math utilities
python tests/test_odds_math.py

# Or use pytest (if installed)
pytest tests/ -v
```

All 7 test functions should pass:
- ✓ american_to_implied_prob
- ✓ american_to_decimal
- ✓ de_vig
- ✓ expected_value
- ✓ kelly_fraction
- ✓ compute_edge_from_american
- ✓ edge_detection

## What's Working

### M0 - Scaffolding ✅
- Repository structure
- Configuration files (pyproject.toml, config.yaml, .env.example)
- Database schema

### M1 - Ingestion ✅
- CSV-based game ingestion
- CSV-based odds ingestion
- Sample data (40 games, 80 odds records)
- Data verification tools

### Partial M4 - Market Math ✅
- Complete odds conversion utilities
- EV and edge calculations
- Kelly criterion
- De-vig functions
- Full test coverage

## Next Steps

### M2 - Features (Next Milestone)
Implement `features/build.py`:
- Elo rating computation OR
- Rolling point differential/win percentage
- Point-in-time constraints (no data leakage)
- Unit tests for anti-leakage

### M3 - Model
- Train baseline model (Elo or logistic regression)
- Time-split evaluation
- Calibration check

### M4 - Backtest
- Simulate betting strategy
- Calculate ROI, drawdown, bet count
- Brier score evaluation

### M5 - Reporting
- Daily edges CSV
- Summary markdown reports
- Optional alerts (Discord/Telegram)

## Sample Data Format

### games.csv
```csv
game_id,date,home_team,away_team,home_score,away_score
NBA_20231024_BOS_NYK,2023-10-24,Boston Celtics,New York Knicks,108,104
```

### odds.csv
```csv
game_id,book,timestamp,home_ml,away_ml,source
NBA_20231024_BOS_NYK,DraftKings,2023-10-24 19:00:00,-145,+125,closing
```

## Troubleshooting

### Import errors
Make sure you're in the virtual environment:
```bash
source venv/bin/activate
```

### Database location
Default: `data/sports_edge.db`
Override with `DATABASE_URL` in `.env`

### Python version
Requires Python 3.9+. Check with:
```bash
python3 --version
```

## Key Files

- [README.md](README.md) - Main documentation
- [STATUS.md](STATUS.md) - Implementation status
- [config.yaml](config.yaml) - Configuration settings
- [db_schema.py](db_schema.py) - Database models
- [ingest/games.py](ingest/games.py) - Game ingestion
- [ingest/odds.py](ingest/odds.py) - Odds ingestion
- [edge/odds_math.py](edge/odds_math.py) - Market math utilities
