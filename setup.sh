#!/usr/bin/env bash
set -euo pipefail

# Create python venv and install requirements
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create data directories
mkdir -p data/recordings data/db

# Initialize sqlite file (will be created on first run)
python - <<'PY'
from pathlib import Path
p = Path('data/db')
p.mkdir(parents=True, exist_ok=True)
print('Setup complete')
PY
