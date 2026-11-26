from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from accounts.forms import ClientRegistrationForm, RoleLoginForm
from accounts.models import Role
from accounts.security import (
    is_locked, lock_message, register_failure, reset_failures)
from portal.role_routing import dashboard_url_for_role


@require_http_methods(['GET', 'POST'])
def register_cliente(request):
    """
    Registro público restringido: solo crea usuarios con rol Cliente.
    Director, Coordinador, Docente y Estudiante se crean únicamente en /admin/.
    """
    if request.user.is_authenticated:
        return redirect(dashboard_url_for_role(request.user.role))

    form = ClientRegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        messages.success(request, 'Bienvenido. Su cuenta de empresa está activa.')
        return redirect('portal:cliente_dashboard')

    return render(request, 'accounts/register.html', {'form': form})


@never_cache
@require_http_methods(['GET', 'POST'])
def login_view(request):
    # (B-4/Auditoría SEG-02) No se siembran usuarios demo desde vistas publicas;
    # usar `manage.py seed_demo` de forma explicita.
    if request.user.is_authenticated:
        return redirect(dashboard_url_for_role(request.user.role))

    email = ''
    if request.method == 'POST':
        email = (request.POST.get('username') or '').strip().lower()
        if is_locked(email, request):
            form = RoleLoginForm(request, data=request.POST)
            form.add_error(None, lock_message())
            return render(
                request, 'accounts/login.html',
                {'form': form, 'roles': Role.choices}, status=429)

    initial = {}
    preset_role = request.GET.get('rol') or request.GET.get('role')
    if preset_role in dict(Role.choices):
        initial['expected_role'] = preset_role

    if request.method == 'POST':
        form = RoleLoginForm(request, data=request.POST)
        if form.is_valid():
            reset_failures(email, request)
            user = form.get_user()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect(dashboard_url_for_role(user.role))
        if getattr(form, 'auth_failed', False) and register_failure(email, request):
            form.add_error(None, lock_message())
            return render(
                request, 'accounts/login.html',
                {'form': form, 'roles': Role.choices}, status=429)
    else:
        form = RoleLoginForm(request, initial=initial)

    return render(request, 'accounts/login.html', {'form': form, 'roles': Role.choices})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'Sesión cerrada.')
    return redirect('accounts:login')

