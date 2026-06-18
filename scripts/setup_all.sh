#!/usr/bin/env bash
set -euo pipefail

# Usage: ./scripts/setup_all.sh
# Runs both backend and frontend setup scripts.

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

./scripts/setup_backend.sh
./scripts/setup_frontend.sh

echo "All setup tasks finished. Review backend/.env and frontend/.env.local and fill secrets as needed."