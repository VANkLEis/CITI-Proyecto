#!/bin/sh
# Arranque plug-and-play para la exposición: migra, siembra datos demo y sirve
# con Gunicorn. El seed es idempotente: re-ejecutar no duplica.
set -e

cd /app/backend

echo "[entrypoint] Aplicando migraciones..."
python manage.py migrate --noinput

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
