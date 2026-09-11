#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

say(){ printf '\n==> %s\n' "$1"; }
fail(){ printf '\nERRO: %s\n' "$1" >&2; exit 1; }

say "Verificando Python"
command -v python3 >/dev/null || fail "Python 3 não encontrado. Instale python3."

say "Instalando dependências do sistema"
if command -v sudo >/dev/null 2>&1; then
  sudo apt update
  sudo apt install -y python3-full python3-venv python3-pip
  if systemctl list-unit-files | grep -q '^mariadb.service' || command -v mariadb >/dev/null 2>&1; then
    DB_SERVICE=mariadb
    DB_CLIENT=mariadb
    sudo apt install -y mariadb-server mariadb-client
  else
    DB_SERVICE=mysql
    DB_CLIENT=mysql
    sudo apt install -y mysql-server
  fi
else
  fail "sudo não encontrado. Execute este instalador em um sistema Ubuntu/Debian com sudo."
fi

say "Iniciando banco ($DB_SERVICE)"
sudo systemctl enable --now "$DB_SERVICE"
if ! sudo systemctl is-active --quiet "$DB_SERVICE"; then
  sudo systemctl status "$DB_SERVICE" --no-pager || true
  fail "O serviço $DB_SERVICE não iniciou."
fi

say "Criando ambiente virtual"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

DB_NAME="${MATCONECTA_DB_NAME:-matconecta_v4}"
DB_PASSWORD="${MATCONECTA_DB_PASSWORD:-}"

# Preserve an existing .env password so rerunning setup cannot silently break
# an already configured database connection.
if [ -z "$DB_PASSWORD" ] && [ -f .env ]; then
  DB_PASSWORD="$(python3 - <<'PY'
from pathlib import Path
from urllib.parse import urlparse
for line in Path('.env').read_text(encoding='utf-8').splitlines():
    if line.startswith('DATABASE_URL='):
        raw=line.split('=',1)[1].strip().strip('"').strip("'")
        try:
            print(urlparse(raw).password or '')
        except Exception:
            pass
        break
PY
)"
fi

if [ -z "$DB_PASSWORD" ]; then
  DB_PASSWORD="$(python3 - <<'PY'
import secrets,string
alphabet=string.ascii_letters+string.digits
print(''.join(secrets.choice(alphabet) for _ in range(24)))
PY
)"
fi

say "Configurando banco MySQL/MariaDB"
sudo "$DB_CLIENT" --protocol=socket <<SQL
CREATE DATABASE IF NOT EXISTS ${DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'matconecta'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
CREATE USER IF NOT EXISTS 'matconecta'@'127.0.0.1' IDENTIFIED BY '${DB_PASSWORD}';
ALTER USER 'matconecta'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
ALTER USER 'matconecta'@'127.0.0.1' IDENTIFIED BY '${DB_PASSWORD}';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO 'matconecta'@'localhost';
GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO 'matconecta'@'127.0.0.1';
FLUSH PRIVILEGES;
SQL

if [ -f .env ] && grep -q '^DATABASE_URL=' .env; then
  say "Preservando .env existente"
else
  if [ -f .env ]; then
    cp .env ".env.backup.$(date +%Y%m%d%H%M%S)"
  fi
  cat > .env <<EOF2
DATABASE_URL=mysql+pymysql://matconecta:${DB_PASSWORD}@127.0.0.1:3306/${DB_NAME}?charset=utf8mb4
APP_HOST=127.0.0.1
APP_PORT=8000
SESSION_DAYS=7
EOF2
  chmod 600 .env
  say "Arquivo .env configurado"
fi

say "Sincronizando conteúdo"
cd backend
python seed.py
cd ..

say "Instalação concluída"
printf '%s\n' \
  "Banco: MySQL/MariaDB / ${DB_NAME}" \
  'Frontend + API: http://127.0.0.1:8000' \
  'Documentação: http://127.0.0.1:8000/docs' \
  'Para iniciar depois: ./run_linux.sh'
