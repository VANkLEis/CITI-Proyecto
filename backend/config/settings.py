import os
from pathlib import Path
from urllib.parse import unquote, urlparse

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

try:  # Carga .env local si existe (B-3); NO sustituye variables del shell.
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / '.env')
except ImportError:
    pass

# —— Entornos explícitos (B-3 / auditoría SEG-03) ——
# desarrollo (default, demostración local) | produccion (exige secretos y HTTPS).
# Render activa IS_PRODUCTION=true; DJANGO_ENV=produccion sigue siendo válido.
DJANGO_ENV = os.environ.get('DJANGO_ENV', 'desarrollo').strip().lower()
_IS_PRODUCTION_ENV = os.environ.get('IS_PRODUCTION', '').strip().lower()
IS_PRODUCTION = (
    _IS_PRODUCTION_ENV in ('1', 'true', 'yes', 'on')
    or DJANGO_ENV in ('produccion', 'production', 'prod')
)

DEBUG = os.environ.get('DJANGO_DEBUG', '0' if IS_PRODUCTION else '1') == '1'

_DEV_SECRET_FALLBACK = 'django-insecure-dev-citi-ucc-solo-desarrollo'
SECRET_KEY = (
    os.environ.get('DJANGO_SECRET_KEY')
    or os.environ.get('SECRET_KEY')
    or ('' if IS_PRODUCTION else _DEV_SECRET_FALLBACK)
)

RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '').strip()


def _env_list(value):
    return [item.strip() for item in (value or '').split(',') if item.strip()]


def _normalize_render_hostname(value):
    host = (value or '').strip()
    for prefix in ('https://', 'http://'):
        if host.startswith(prefix):
            host = host[len(prefix):]
    return host.strip('/').split('/')[0]


def _build_allowed_hosts(raw_hosts, render_hostname):
    hosts = _env_list(raw_hosts) or ['127.0.0.1', 'localhost']
    render_host = _normalize_render_hostname(render_hostname)
    if render_host and render_host not in hosts:
        hosts.append(render_host)
    return hosts


def _build_csrf_origins(raw_origins, render_hostname):
    origins = _env_list(raw_origins)
    render_host = _normalize_render_hostname(render_hostname)
    if render_host:
        origin = f'https://{render_host}'
        if origin not in origins:
            origins.append(origin)
    return origins


def _proxy_security(is_production):
    if is_production:
        return ('HTTP_X_FORWARDED_PROTO', 'https'), True
    return None, False


_RENDER_HOST = _normalize_render_hostname(RENDER_EXTERNAL_HOSTNAME)
ALLOWED_HOSTS = _build_allowed_hosts(
    os.environ.get('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost'),
    _RENDER_HOST,
)
CSRF_TRUSTED_ORIGINS = _build_csrf_origins(
    os.environ.get('CSRF_TRUSTED_ORIGINS', ''),
    _RENDER_HOST,
)

if IS_PRODUCTION:
    if DEBUG:
        raise ImproperlyConfigured(
            'DJANGO_DEBUG=1 no esta permitido cuando IS_PRODUCTION es True '
            '(DJANGO_ENV=produccion o IS_PRODUCTION=1).'
        )
    if not SECRET_KEY:
        raise ImproperlyConfigured(
            'DJANGO_SECRET_KEY o SECRET_KEY es obligatorio en produccion '
            '(vea .env.example).'
        )
    if not _env_list(os.environ.get('DJANGO_ALLOWED_HOSTS')) and not _RENDER_HOST:
        raise ImproperlyConfigured(
            'DJANGO_ALLOWED_HOSTS o RENDER_EXTERNAL_HOSTNAME es obligatorio '
            'en produccion.'
        )

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts.apps.AccountsConfig',
    'scheduling',
    'portal',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'portal.middleware.PrivateNoCacheMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# WhiteNoise sirve los estáticos desde Gunicorn (imagen Docker/Render). Se
# activa por defecto en producción y sigue siendo opcional en local/tests.
CITI_USE_WHITENOISE = os.environ.get(
    'CITI_USE_WHITENOISE', '1' if IS_PRODUCTION else '0') == '1'
if CITI_USE_WHITENOISE:
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

# Demo en contenedor: Gunicorn no sirve /media/ por sí solo. NUNCA en producción
# real (allí los medios los sirve Nginx/S3).
CITI_SERVE_MEDIA = os.environ.get('CITI_SERVE_MEDIA', '0') == '1'

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

def _parse_database_url(url):
    """Convierte una URL postgres(ql):// en la config de Django."""
    parsed = urlparse(url)
    return {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': unquote(parsed.path.lstrip('/')),
        'USER': unquote(parsed.username or ''),
        'PASSWORD': unquote(parsed.password or ''),
        'HOST': parsed.hostname or '',
        'PORT': parsed.port or 5432,
        'CONN_MAX_AGE': 60,
    }


def _database_from_postgres_env():
    return {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'citi'),
        'USER': os.environ.get('POSTGRES_USER', 'citi'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
        'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
        'PORT': int(os.environ.get('POSTGRES_PORT', '5432')),
        'CONN_MAX_AGE': 60,
    }


# Prioridad: DATABASE_URL (Render) -> POSTGRES_* (Docker/legacy) -> SQLite local.
_DATABASE_URL = os.environ.get('DATABASE_URL', '').strip()
if _DATABASE_URL.startswith(('postgres://', 'postgresql://')):
    DATABASES = {'default': _parse_database_url(_DATABASE_URL)}
elif os.environ.get('POSTGRES_HOST'):
    DATABASES = {'default': _database_from_postgres_env()}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Caché compartida por los workers de Gunicorn (bloqueo de login). En tests se
# sustituye por LocMemCache; en producción con varias réplicas usar Redis.
CITI_CACHE_DIR = os.environ.get('CITI_CACHE_DIR') or str(BASE_DIR / '.cache')
os.makedirs(CITI_CACHE_DIR, exist_ok=True)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': CITI_CACHE_DIR,
        'TIMEOUT': 300,
        'OPTIONS': {'MAX_ENTRIES': 1000},
    }
}

AUTH_USER_MODEL = 'accounts.CustomUser'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

if CITI_USE_WHITENOISE:
    # Manifest + compresión: las plantillas reciben URLs con hash y un asset
    # faltante falla en collectstatic en vez de producir un 404 silencioso.
    STORAGES = {
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
        },
    }

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'portal:landing'
LOGOUT_REDIRECT_URL = 'accounts:login'

# —— Filtro académico estudiante tutor (ajustables) ——
CITI_MIN_SEMESTRE_TUTOR = int(os.environ.get('CITI_MIN_SEMESTRE_TUTOR', '8'))
CITI_MIN_CREDITOS_TUTOR = int(os.environ.get('CITI_MIN_CREDITOS_TUTOR', '130'))
CITI_MIN_PROMEDIO_TUTOR = os.environ.get('CITI_MIN_PROMEDIO_TUTOR', '4.0')

# Bloqueo temporal de login: 6 fallos consecutivos por correo+IP durante 5 min.
CITI_LOGIN_MAX_ATTEMPTS = int(os.environ.get('CITI_LOGIN_MAX_ATTEMPTS', '6'))
CITI_LOGIN_LOCK_SECONDS = int(os.environ.get('CITI_LOGIN_LOCK_SECONDS', '300'))


MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# —— Cabeceras y cookies seguras también en desarrollo (no rompen HTTP local) ——
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

# —— Proxy HTTPS y endurecimiento solo en producción ——
# Render termina TLS y reenvía X-Forwarded-Proto; confiar en esa cabecera evita
# el bucle de SECURE_SSL_REDIRECT. En local (HTTP) queda desactivado.
SECURE_PROXY_SSL_HEADER, USE_X_FORWARDED_HOST = _proxy_security(IS_PRODUCTION)

if IS_PRODUCTION:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True