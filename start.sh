#!/usr/bin/env bash
set -e
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"
python -m venv .venv >/dev/null 2>&1 || true
if [ -f .venv/bin/activate ]; then
  . .venv/bin/activate
fi
pip install -r requirements.txt >/dev/null
cd frontend && npm install && npm run dev -- --host 0.0.0.0 --port 5173
