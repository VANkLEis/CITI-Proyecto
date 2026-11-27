# CITI — imagen de demostración (Django + Gunicorn + WhiteNoise)
# PostgreSQL 16 corre como servicio aparte en docker-compose.yml.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# libpq5 es la dependencia de sistema de psycopg2-binary.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Solo se copia el proyecto Django real. Los estáticos institucionales viven
# dentro de backend/static/ (no hay carpeta assets/ en la raíz).
COPY backend/ ./backend/
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

WORKDIR /app/backend

# Demo: sin DEBUG, estáticos por WhiteNoise y media servido por Django.
# IS_PRODUCTION sigue dependiendo solo de DJANGO_ENV (ver config/settings.py),
# por eso el seed funciona con DJANGO_DEBUG=0.
ENV DJANGO_ENV=desarrollo \
    DJANGO_DEBUG=0 \
    CITI_USE_WHITENOISE=1 \
    CITI_SERVE_MEDIA=1

RUN python manage.py collectstatic --noinput

RUN useradd -m -u 1000 citi \
    && mkdir -p /app/backend/media /app/backend/staticfiles \
    && chown -R citi:citi /app
USER citi

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
