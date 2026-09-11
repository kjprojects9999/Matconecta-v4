#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
[ -f .env ] || { echo 'ERRO: .env não encontrado. Execute ./setup_linux.sh primeiro.'; exit 1; }
[ -d .venv ] || { echo 'ERRO: .venv não encontrado. Execute ./setup_linux.sh primeiro.'; exit 1; }
if ! systemctl is-active --quiet mysql; then
  echo 'MySQL não está rodando. Tentando iniciar...'
  sudo systemctl start mysql
fi
source .venv/bin/activate
cd backend
exec python -m uvicorn backendapi:app --host "${APP_HOST:-127.0.0.1}" --port "${APP_PORT:-8000}" --reload
