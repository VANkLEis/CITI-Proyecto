from django.urls import reverse

from accounts.models import Role


def dashboard_url_for_role(role: str) -> str:
    mapping = {
        Role.DIRECTOR: 'portal:director_dashboard',
        Role.COORDINADOR: 'portal:coordinador_dashboard',
        Role.DOCENTE: 'portal:docente_dashboard',
        Role.ESTUDIANTE: 'portal:estudiante_dashboard',
        Role.CLIENTE: 'portal:cliente_dashboard',
    }
    name = mapping.get(role, 'portal:landing')
    return reverse(name)
