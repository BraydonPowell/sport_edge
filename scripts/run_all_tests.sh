#!/bin/bash
# Comprehensive test suite for M0+M1

set -e

echo "=========================================="
echo "Running All Tests"
echo "=========================================="
echo ""

# Activate venv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Test 1: Unit tests
echo "Test 1: Odds Math Unit Tests"
echo "------------------------------------------"
python tests/test_odds_math.py
echo ""

# Test 2: Database schema
echo "Test 2: Database Schema"
echo "------------------------------------------"
python -c "
from db_schema import init_db, get_session, Game, Odds
import os

# Clean test
if os.path.exists('data/test.db'):
    os.remove('data/test.db')

engine = init_db('sqlite:///data/test.db')
print('✓ Database schema created')

session = get_session(engine)
print('✓ Session created')
print('✓ Schema test passed')

os.remove('data/test.db')
"
echo ""

# Test 3: CSV ingestion
echo "Test 3: CSV Ingestion"
echo "------------------------------------------"
python -c "
from ingest.games import load_games_from_csv
from ingest.odds import load_odds_from_csv
import pandas as pd

games_df = load_games_from_csv('data/sample_games.csv')
assert len(games_df) == 40
assert 'winner' in games_df.columns
print(f'✓ Loaded {len(games_df)} games')

odds_df = load_odds_from_csv('data/sample_odds.csv')
assert len(odds_df) == 80
assert 'home_ml' in odds_df.columns
print(f'✓ Loaded {len(odds_df)} odds records')
print('✓ Ingestion test passed')
"
echo ""

# Test 4: Edge calculations
echo "Test 4: Edge Calculations"
echo "------------------------------------------"
python -c "
from edge.odds_math import compute_edge_from_american

# Test realistic scenario
edge_info = compute_edge_from_american(0.60, -110, -110, 'home')
assert edge_info['edge_pct'] > 5.0
assert edge_info['ev'] > 0
print('✓ Positive edge detected correctly')

edge_info = compute_edge_from_american(0.45, -110, -110, 'home')
assert edge_info['edge_pct'] < 0
assert edge_info['ev'] < 0
print('✓ Negative edge detected correctly')

print('✓ Edge calculation test passed')
"
echo ""

# Test 5: End-to-end with real DB
echo "Test 5: End-to-End Database Test"
echo "------------------------------------------"
python -c "
from db_schema import get_session, Game, Odds
from ingest.games import ingest_games_to_db
from ingest.odds import ingest_odds_to_db

session = get_session()

# Count records
games_count = session.query(Game).count()
odds_count = session.query(Odds).count()

print(f'✓ Found {games_count} games in database')
print(f'✓ Found {odds_count} odds records in database')

# Verify join
games_with_odds = session.query(Game).join(Odds).distinct().count()
print(f'✓ {games_with_odds} games have odds ({games_with_odds/games_count*100:.0f}% coverage)')

assert games_count > 0, 'No games in database'
assert odds_count > 0, 'No odds in database'
assert games_with_odds > 0, 'No games with odds'

print('✓ End-to-end test passed')

session.close()
"
echo ""

echo "=========================================="
echo "All Tests Passed! ✓"
echo "=========================================="
echo ""
echo "Summary:"
echo "  ✓ Odds math functions working"
echo "  ✓ Database schema valid"
echo "  ✓ CSV ingestion working"
echo "  ✓ Edge calculations accurate"
echo "  ✓ End-to-end pipeline operational"
echo ""
echo "M0 + M1 are fully complete and tested."
