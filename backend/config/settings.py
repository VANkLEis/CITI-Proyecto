import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE_DIR.parent

try:  # Carga .env local si existe (B-3); NO sustituye variables del shell.
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / '.env')
except ImportError:
    pass

# —— Entornos explícitos (B-3 / auditoría SEG-03) ——
# desarrollo (default, demostración local) | produccion (exige secretos y HTTPS)
DJANGO_ENV = os.environ.get('DJANGO_ENV', 'desarrollo').strip().lower()
IS_PRODUCTION = DJANGO_ENV in ('produccion', 'production', 'prod')

DEBUG = os.environ.get('DJANGO_DEBUG', '0' if IS_PRODUCTION else '1') == '1'

_DEV_SECRET_FALLBACK = 'django-insecure-dev-citi-ucc-solo-desarrollo'
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', '' if IS_PRODUCTION else _DEV_SECRET_FALLBACK)

ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '127.0.0.1,localhost').split(',')

if IS_PRODUCTION:
    if DEBUG:
        raise ImproperlyConfigured(
            'DJANGO_DEBUG=1 no esta permitido con DJANGO_ENV=produccion.'
        )
    if not SECRET_KEY:
        raise ImproperlyConfigured(
            'DJANGO_SECRET_KEY es obligatorio en produccion (vea .env.example).'
        )
    if not os.environ.get('DJANGO_ALLOWED_HOSTS'):
        raise ImproperlyConfigured(
            'DJANGO_ALLOWED_HOSTS es obligatorio en produccion.'
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
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

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

# SQLite por defecto; PostgreSQL en producción:
# DATABASE_URL=postgres://user:pass@localhost:5432/citi
if os.environ.get('DATABASE_URL', '').startswith('postgres'):
    import urllib.parse as up

    url = up.urlparse(os.environ['DATABASE_URL'])
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': url.path[1:],
            'USER': url.username,
            'PASSWORD': url.password,
            'HOST': url.hostname,
            'PORT': url.port or 5432,
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
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
    PROJECT_ROOT / 'assets',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'accounts:login'
LOGIN_REDIRECT_URL = 'portal:landing'
LOGOUT_REDIRECT_URL = 'portal:landing'

# —— Filtro académico estudiante tutor (ajustables) ——
CITI_MIN_SEMESTRE_TUTOR = int(os.environ.get('CITI_MIN_SEMESTRE_TUTOR', '8'))
CITI_MIN_CREDITOS_TUTOR = int(os.environ.get('CITI_MIN_CREDITOS_TUTOR', '130'))
CITI_MIN_PROMEDIO_TUTOR = os.environ.get('CITI_MIN_PROMEDIO_TUTOR', '4.0')


MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# —— Endurecimiento solo en producción (no rompe la demo local en HTTP) ——
if IS_PRODUCTION:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = int(os.environ.get('DJANGO_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'same-origin'
    X_FRAME_OPTIONS = 'DENY'
    # detrás de proxy/reverse-proxy (nginx): descomentar
    # SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')