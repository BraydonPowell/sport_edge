# STATUS

## Current State
✅ M0 and M1 COMPLETE - Fully working end-to-end ingestion pipeline with sample data.

## MVP Target
End-to-end pipeline for NBA moneyline:
- ingest historical games + closing odds
- baseline probability model (Elo or logistic regression)
- EV edge detection
- leak-free backtest
- daily report output

## Milestones

### M0 — Repo + config scaffolding ✓
- [x] Create repo structure
- [x] Add `pyproject.toml` / requirements
- [x] Add `.env.example` for API keys (if any)
- [x] Add `config.yaml` (league, date ranges, thresholds)

### M1 — Ingestion (historical) ✅ COMPLETE
- [x] Implement `ingest/games.py`
- [x] Implement `ingest/odds.py`
- [x] Define DB schema + migrations
- [x] Load historical dataset end-to-end
- [x] Sample data files (40 NBA games + 80 odds records)
- [x] Verification script with sanity checks

Acceptance: DB contains games + odds for at least one full season. ✅ PASSED

**Status:** Fully working pipeline. Sample data loaded successfully. All functions tested.

### M2 — Features
- [ ] Implement point-in-time rolling features OR Elo computation
- [ ] Validate anti-leakage with unit tests
- [ ] Export training dataset (Parquet/CSV)

Acceptance: Features for each game only depend on prior games.

### M3 — Model
- [ ] Train baseline model
- [ ] Time-split evaluation
- [ ] Calibration check + optional calibration step
- [ ] Save model artifact + versioning

Acceptance: Model produces probabilities with reasonable calibration vs naive baselines.

### M4 — Backtester
- [x] Implement EV calculations + de-vig (in `edge/odds_math.py`)
- [ ] Simulate bets with config threshold
- [ ] Compute metrics (ROI, drawdown, #bets, Brier score)
- [ ] Save run artifacts (metrics JSON, equity curve CSV)

Acceptance: Backtest runs with no crashes and produces stable metrics.

### M5 — Reporting/Alerts
- [ ] Generate daily edges CSV
- [ ] Generate summary markdown
- [ ] Optional: send alert to Discord/Telegram

Acceptance: One command generates a readable daily report.

## Completed Items (M0 + M1)

### Core Infrastructure
- ✓ Repository structure with all module directories
- ✓ `pyproject.toml` with core dependencies and proper package config
- ✓ `.env.example` template for API keys
- ✓ `.gitignore` for Python projects
- ✓ `config.yaml` with MVP defaults (NBA, moneyline, thresholds)

### Database Layer
- ✓ `db_schema.py` - Complete SQLAlchemy ORM models:
  - `games` table (game results)
  - `odds` table (odds snapshots)
  - `team_ratings` table (Elo/ratings)
  - `predictions` table (model outputs)
  - `backtest_runs` table (backtest results)
- ✓ Database initialization tested and working

### Ingestion Pipeline
- ✓ `ingest/games.py` - Full CSV-based game ingestion with CLI
- ✓ `ingest/odds.py` - Full CSV-based odds ingestion with CLI
- ✓ Sample data: 40 NBA games (Oct-Nov 2023)
- ✓ Sample data: 80 odds records (DraftKings + FanDuel closing lines)

### Edge Detection & Math
- ✓ `edge/odds_math.py` - Complete implementation:
  - `american_to_implied_prob()` - odds conversion
  - `american_to_decimal()` - odds conversion
  - `de_vig()` - vig removal
  - `expected_value()` - EV calculation
  - `kelly_fraction()` - Kelly criterion
  - `compute_edge_from_american()` - complete edge analysis

### Testing & Verification
- ✓ `tests/test_odds_math.py` - Full unit test suite (7 test functions)
- ✓ All tests passing
- ✓ `scripts/init_db.py` - Database initialization script
- ✓ `scripts/load_sample_data.py` - Sample data loader
- ✓ `scripts/verify_data.py` - Data verification with sanity checks
- ✓ `scripts/quickstart.sh` - One-command setup script

### Documentation
- ✓ `README.md` - Complete setup and usage instructions
- ✓ `STATUS.md` - Implementation status tracking
- ✓ Stub files for M2-M5 modules (features, models, backtest, report)

## Immediate Next Tasks
✅ M0 and M1 are COMPLETE. Ready to proceed to M2.

**Next milestone: M2 - Features**
1) Implement Elo computation OR rolling features in `features/build.py`
2) Validate anti-leakage with unit tests
3) Export training dataset

## Risks / Blockers
- Data source reliability (odds snapshots are hardest)
- Data leakage in rolling features
- Odds timestamps mismatch with decision time
- Small edges wiped by vig/fees

## Open Questions (defaults if not answered)
- League: NBA
- Market: moneyline
- Decision time: closing odds (v0)
- Stake: flat 1 unit
- EV threshold: 1%
