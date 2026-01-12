#!/usr/bin/env bash
set -euo pipefail

# Run live injuries + predictions + ROI in one command.
# Requires ODDS_API_KEY to be set in the environment.

if [[ -z "${ODDS_API_KEY:-}" ]]; then
  echo "❌ ODDS_API_KEY is not set"
  echo "   export ODDS_API_KEY=your_key_here"
  exit 1
fi

python scripts/fetch_live_injuries.py
rm -f data/live_bets.csv
python scripts/predict_with_injuries.py
python scripts/update_results.py
python scripts/roi_report.py

if [[ "${AUTO_SETTLE:-0}" == "1" ]]; then
  echo ""
  echo "Auto-settle enabled. Checking for completed games every 15 minutes..."
  for _ in {1..48}; do
    pending=$(python scripts/roi_report.py | awk -F': ' '/Pending bets/ {print $2}' | tr -d '\r')
    if [[ "${pending}" == "0" ]]; then
      echo "All bets settled."
      exit 0
    fi
    sleep 900
    python scripts/update_results.py >/dev/null
  done
fi
