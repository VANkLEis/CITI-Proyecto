#!/bin/sh
# Arranque para Docker local y Render: espera PostgreSQL, migra, recolecta
# estáticos, siembra la demo (idempotente) y sirve con Gunicorn.
set -e

cd /app/backend

wait_for_database() {
  python - <<'PY'
import os
import socket
import sys
import time
from urllib.parse import urlparse

url = (os.environ.get('DATABASE_URL') or '').strip()
host = (os.environ.get('POSTGRES_HOST') or '').strip()
port = int(os.environ.get('POSTGRES_PORT', '5432'))

if url.startswith(('postgres://', 'postgresql://')):
    parsed = urlparse(url)
    host = parsed.hostname or host
    port = parsed.port or port

if not host:
    print('[entrypoint] Sin PostgreSQL configurado; se omite la espera.')
    sys.exit(0)

deadline = time.time() + int(os.environ.get('CITI_DB_WAIT_SECONDS', '60'))
while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=3):
            print(f'[entrypoint] PostgreSQL disponible en {host}:{port}.')
            sys.exit(0)
    except OSError:
        time.sleep(2)

print(f'[entrypoint] ERROR: PostgreSQL no respondió en {host}:{port}.', file=sys.stderr)
sys.exit(1)
PY
}

echo "[entrypoint] Esperando a PostgreSQL..."
wait_for_database

echo "[entrypoint] Aplicando migraciones..."
python manage.py migrate --noinput

echo "[entrypoint] Recolectando estáticos..."
python manage.py collectstatic --noinput

if [ "${CITI_SEED_ON_START:-1}" = "1" ]; then
  echo "[entrypoint] Cargando datos de demostración (idempotente)..."
  if ! python manage.py seed_demo_data; then
    echo "[entrypoint] ADVERTENCIA: seed_demo_data falló; la app arranca sin datos demo." >&2
  fi
else
  echo "[entrypoint] CITI_SEED_ON_START=0: se omite el seed."
fi

echo "[entrypoint] Iniciando Gunicorn en 0.0.0.0:${PORT:-8000}"
exec gunicorn config.wsgi:application \
  --bind "0.0.0.0:${PORT:-8000}" \
  --workers "${GUNICORN_WORKERS:-3}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --access-logfile - \
  --error-logfile -
