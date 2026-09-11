#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
[ -f .env ] || { echo 'ERRO: .env não encontrado. Execute ./setup_linux.sh primeiro.'; exit 1; }
[ -d .venv ] || { echo 'ERRO: .venv não encontrado. Execute ./setup_linux.sh primeiro.'; exit 1; }
if systemctl list-unit-files | grep -q '^mariadb.service'; then
  DB_SERVICE=mariadb
else
  DB_SERVICE=mysql
fi
if ! systemctl is-active --quiet "$DB_SERVICE"; then
  echo "Banco ($DB_SERVICE) não está rodando. Tentando iniciar..."
  sudo systemctl start "$DB_SERVICE"
fi
if ! systemctl is-active --quiet "$DB_SERVICE"; then
  echo "ERRO: não foi possível iniciar o serviço $DB_SERVICE." >&2
  exit 1
fi
source .venv/bin/activate
cd backend
exec python -m uvicorn backendapi:app --host "${APP_HOST:-127.0.0.1}" --port "${APP_PORT:-8000}" --reload
