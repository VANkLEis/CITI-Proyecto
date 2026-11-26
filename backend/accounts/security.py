import hashlib
import logging

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

CACHE_PREFIX = 'citi:login'
LOCK_MESSAGE = (
    'Demasiados intentos fallidos. Espere {minutes} minutos antes de volver '
    'a intentar.')


def _client_ip(request):
    return request.META.get('REMOTE_ADDR') or 'desconocida'


def _cache_key(email, request):
    raw = f'{(email or "").strip().lower()}|{_client_ip(request)}'
    digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()
    return f'{CACHE_PREFIX}:{digest}'


def lock_message():
    minutes = max(1, settings.CITI_LOGIN_LOCK_SECONDS // 60)
    return LOCK_MESSAGE.format(minutes=minutes)


def is_locked(email, request):
    """True si el par correo+IP acumuló el máximo de fallos recientes."""
    try:
        return bool(cache.get(f'{_cache_key(email, request)}:lock'))
    except Exception:
        logger.warning('No se pudo consultar el bloqueo de login.', exc_info=True)
        return False


def register_failure(email, request):
    """Suma un fallo y devuelve True si este intento disparó el bloqueo."""
    key = f'{_cache_key(email, request)}:fail'
    try:
        intentos = int(cache.get(key, 0) or 0) + 1
        cache.set(key, intentos, timeout=settings.CITI_LOGIN_LOCK_SECONDS)
        if intentos >= settings.CITI_LOGIN_MAX_ATTEMPTS:
            cache.set(
                f'{_cache_key(email, request)}:lock', True,
                timeout=settings.CITI_LOGIN_LOCK_SECONDS)
            cache.delete(key)
            return True
    except Exception:
        logger.warning('No se pudo registrar el fallo de login.', exc_info=True)
    return False


def reset_failures(email, request):
    """Limpia contador y bloqueo tras un login exitoso."""
    key = _cache_key(email, request)
    try:
        cache.delete(f'{key}:fail')
        cache.delete(f'{key}:lock')
    except Exception:
        logger.warning('No se pudo limpiar el contador de login.', exc_info=True)
