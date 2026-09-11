#!/usr/bin/env bash
# One command to get the whole thing running.
set -euo pipefail
cd "$(dirname "$0")/backend"

# optional settings such as GOOGLE_MAPS_API_KEY (copy .env.example to .env)
if [ -f .env ]; then set -a; . ./.env; set +a; fi

if [ ! -d .venv ]; then
  echo "creating virtualenv..."
  python3 -m venv .venv
  ./.venv/bin/pip install --quiet -r requirements.txt
fi

echo "Taapmaan -> http://localhost:8000   (API docs at /docs)"
exec ./.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --reload
