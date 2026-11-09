from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from portal.role_routing import dashboard_url_for_role


def role_required(*roles):
    """Restringe la vista a uno o más roles del CustomUser."""
    roles = tuple(roles)

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if user.role not in roles:
                if hasattr(user, 'role'):
                    return redirect(dashboard_url_for_role(user.role))
                raise PermissionDenied('No tiene permiso para acceder a esta sección.')
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator
