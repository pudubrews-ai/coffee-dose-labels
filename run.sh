#!/bin/bash
# Creates/updates the venv, starts the label app on 127.0.0.1:8221 and opens the browser.
set -e
cd "$(dirname "$0")"
PORT=8221
if [ ! -x .venv/bin/python ]; then
  PY=$(command -v python3.11 || command -v python3.12 || command -v python3.13 || command -v python3 || true)
  [ -n "$PY" ] || { echo "No python3 found. Install Python 3.11+ (e.g. brew install python@3.12)." >&2; exit 1; }
  "$PY" -m venv .venv
fi
if [ ! -f .venv/.deps-stamp ] || [ requirements.txt -nt .venv/.deps-stamp ]; then
  .venv/bin/pip install -q -r requirements.txt && touch .venv/.deps-stamp
fi
if lsof -iTCP:$PORT -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Already running on port $PORT"; open "http://127.0.0.1:$PORT"; exit 0
fi
(sleep 1.5; open "http://127.0.0.1:$PORT") &
exec .venv/bin/python -m labelapp.server
