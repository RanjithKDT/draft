#!/bin/bash
set -e

# Change to project root (works wherever script is called from)
cd "$(dirname "$0")/.."

# Run setup if venv doesn't exist yet
if [ ! -f ".venv/bin/python" ]; then
    echo "[Hyva Simulator] venv not found — running setup first..."
    python3 setup.py
fi

# Activate venv and launch
source .venv/bin/activate
python main.py
