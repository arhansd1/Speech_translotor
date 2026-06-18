#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/setup_frontend.sh
# Installs npm deps and copies .env.local.example -> .env.local if missing.

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR/frontend"

echo "[frontend] Working in: $PWD"

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required but not found. Install Node (18+) and npm and retry." >&2
  exit 1
fi

if [ ! -d "node_modules" ]; then
  echo "Installing frontend dependencies (npm install)..."
  npm install
else
  echo "node_modules already present — skipping npm install." 
fi

if [ ! -f ".env.local" ]; then
  if [ -f ".env.local.example" ]; then
    cp .env.local.example .env.local
    echo "Created .env.local from .env.local.example — edit frontend/.env.local if needed." 
  else
    echo ".env.local.example not found. Please create frontend/.env.local manually if required." >&2
  fi
else
  echo "frontend/.env.local already exists — leaving as-is." 
fi

echo "Frontend setup complete. To run the frontend locally:"
echo "  cd frontend && npm run dev"
