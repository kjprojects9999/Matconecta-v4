#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -f .env ] || [ ! -d .venv ]; then
  ./setup_linux.sh
fi
./run_linux.sh
