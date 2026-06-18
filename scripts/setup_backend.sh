#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/setup_backend.sh
# Creates a venv, installs Python deps, and copies .env.example -> .env if missing.

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR/backend"

echo "[backend] Working in: $PWD"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but not found. Install Python 3.11+ and retry." >&2
  exit 1
fi

if [ ! -d "venv" ]; then
  echo "Creating virtual environment at backend/venv..."
  python3 -m venv venv
else
  echo "Virtual environment backend/venv already exists." 
fi

PIP="$PWD/venv/bin/pip"
PY="$PWD/venv/bin/python"

echo "Upgrading pip and installing requirements..."
"$PIP" install --upgrade pip
"$PIP" install -r requirements.txt

if [ ! -f ".env" ]; then
  if [ -f ".env.example" ]; then
    cp .env.example .env
    echo "Created .env from .env.example — edit backend/.env and set SARVAM_API_KEY before running." 
  else
    echo ".env.example not found. Please create backend/.env manually and set SARVAM_API_KEY." >&2
  fi
else
  echo "backend/.env already exists — leaving as-is." 
fi

echo "Backend setup complete. To activate venv: source backend/venv/bin/activate"

echo "To run the backend locally:"
echo "  source backend/venv/bin/activate"
echo "  uvicorn main:app --reload --host 0.0.0.0 --port 8000"
