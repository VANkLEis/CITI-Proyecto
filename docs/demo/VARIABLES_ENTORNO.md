# Variables de entorno — CITI

Configuración por variables de entorno (B-3). `backend/.env` se carga
automáticamente (python-dotenv); la fuente de ejemplo es
`backend/.env.example` (nunca subir `.env` al repositorio).

## Modos de operación

| Modo | Cómo se activa | Comportamiento |
|---|---|---|
| **desarrollo/demo** (default) | Sin `DJANGO_ENV`, o `DJANGO_ENV=desarrollo` | `DEBUG=1` por defecto; `SECRET_KEY` de fallback para desarrollo; `/media/` servido por `runserver`; `seed_demo` disponible |
| **producción** | `DJANGO_ENV=produccion` | `DEBUG` forzado a `0`; **falla el arranque** si falta `DJANGO_SECRET_KEY` o `DJANGO_ALLOWED_HOSTS`; cookies `Secure`, SSL redirect, HSTS; `seed_demo` rechazado |

## Variables reconocidas

| Variable | Default | Descripción |
|---|---|---|
| `DJANGO_ENV` | `desarrollo` | `desarrollo` \| `produccion` (también acepta `production`/`prod`) |
| `DJANGO_DEBUG` | `1` (0 en producción) | `1`/`0`. En producción se rechaza `1` |
| `DJANGO_SECRET_KEY` | fallback de desarrollo | **Obligatoria en producción.** Generar: `python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"` |
| `DJANGO_ALLOWED_HOSTS` | `127.0.0.1,localhost` | **Obligatoria en producción.** Lista separada por comas |
| `DATABASE_URL` | — (SQLite) | Si empieza con `postgres://` / `postgresql://` usa PostgreSQL; cualquier otro esquema mantiene SQLite silenciosamente |
| `DJANGO_HSTS_SECONDS` | `31536000` | HSTS en modo producción (`0` para desactivar) |
| `CITI_DEMO_PASSWORD` | `CITIPass2026*` | Contraseña que asigna `seed_demo` a las cuentas locales de prueba. **Solo para datos de demostración locales** |
| `CITI_MIN_SEMESTRE_TUTOR` | `8` | Semestre mínimo para tutor |
| `CITI_MIN_CREDITOS_TUTOR` | `130` | Créditos mínimos para tutor |
| `CITI_MIN_PROMEDIO_TUTOR` | `4.0` | Promedio mínimo para tutor |

## Comprobaciones de seguridad del modo producción

Aplicadas por `config/settings.py` cuando `DJANGO_ENV=produccion`:
`SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT`,
`SECURE_HSTS_SECONDS`/`INCLUDE_SUBDOMAINS`, `SECURE_CONTENT_TYPE_NOSNIFF`,
`SECURE_REFERRER_POLICY=same-origin`, `X_FRAME_OPTIONS=DENY`.
Detrás de reverse-proxy HTTPS, descomentar `SECURE_PROXY_SSL_HEADER` en settings.

## Ejemplos

### Demo local (lo que se usa en la presentación)
```powershell
# Sin configurar nada: valores de desarrollo.
cd backend
..\venv\Scripts\python.exe manage.py migrate
..\venv\Scripts\python.exe manage.py seed_demo
..\venv\Scripts\python.exe manage.py runserver
# http://127.0.0.1:8000/
```

### Producción académica local con DEBUG apagado (recomendado al exponer en LAN)
```powershell
$env:DJANGO_ENV='produccion'
$env:DJANGO_SECRET_KEY='<generada>'
$env:DJANGO_ALLOWED_HOSTS='192.168.1.40,citi.local'
$env:DATABASE_URL='postgres://citi:****@localhost:5432/citi'  # opcional
# HTTPS termina en el proxy; en la demo LAN puede servirse con runserver --insecure
# para los estáticos:
..\venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000 --insecure
```
Nota: `--insecure` sirve estáticos sin DEBUG; los uploads (`/media/`) **no** se
sirven fuera de DEBUG y requieren la vista de descarga con permisos pendiente
del plan (I-3) antes de exponerlos.

## Regeneración de datos de demo

```powershell
..\venv\Scripts\python.exe manage.py seed_demo            # todo (idempotente)
..\venv\Scripts\python.exe manage.py seed_demo --solo-usuarios
..\venv\Scripts\python.exe manage.py seed_demo_users      # equivalente antiguo (solo usuarios)
```
El comando **no elimina datos existentes** y se niega a ejecutarse en producción.
Ver `DATOS_DEMO.md` para el contenido exacto del conjunto.
