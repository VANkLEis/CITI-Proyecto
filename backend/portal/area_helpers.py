from django.core.exceptions import PermissionDenied

from accounts.models import Area, Role


def area_coordinador(user):
    """Área estricta del coordinador (Sistemas o Civil)."""
    if user.role != Role.COORDINADOR or user.area not in (Area.SISTEMAS, Area.CIVIL):
        raise PermissionDenied('Coordinador sin área académica definida.')
    return user.area


def filtrar_citas_por_area(queryset, area):
    return queryset.filter(franja__area=area)
