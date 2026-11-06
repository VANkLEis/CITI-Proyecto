from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from accounts.forms import ClientRegistrationForm, RoleLoginForm
from accounts.models import Role
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


@require_http_methods(['GET', 'POST'])
def login_view(request):
    from accounts.demo_seed import ensure_demo_users

    ensure_demo_users()
    if request.user.is_authenticated:
        return redirect(dashboard_url_for_role(request.user.role))

    initial = {}
    preset_role = request.GET.get('rol') or request.GET.get('role')
    if preset_role in dict(Role.choices):
        initial['expected_role'] = preset_role

    form = RoleLoginForm(
        request,
        data=request.POST or None,
        initial=initial if request.method == 'GET' else None,
    )
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect(dashboard_url_for_role(user.role))

    return render(request, 'accounts/login.html', {'form': form, 'roles': Role.choices})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'Sesión cerrada.')
    return redirect('portal:landing')

