#!/bin/bash
# Quickstart script to initialize database and load sample data

set -e  # Exit on error

echo "=========================================="
echo "Sports Edge MVP - Quickstart"
echo "=========================================="
echo ""

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found. Please install Python 3.9+."
    exit 1
fi

# Create venv if needed
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
    echo ""
fi

# Activate venv and install dependencies
echo "Installing dependencies..."
source venv/bin/activate
pip install -e . --quiet
echo "✓ Dependencies installed"
echo ""

# Run initialization
echo "Step 1: Initializing database..."
echo "------------------------------------------"
python scripts/init_db.py
echo ""

echo "Step 2: Loading sample data..."
echo "------------------------------------------"
python scripts/load_sample_data.py
echo ""

echo "Step 3: Verifying data..."
echo "------------------------------------------"
python scripts/verify_data.py
echo ""

echo "=========================================="
echo "Quickstart complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  - Activate venv: source venv/bin/activate"
echo "  - Run tests: python tests/test_odds_math.py"
echo "  - Begin M2: Implement features/build.py"
