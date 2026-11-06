from accounts.models import Area

AREA_CALENDAR_COLORS = {
    Area.SISTEMAS: {'disponible': '#2563eb', 'borde': '#1d4ed8', 'cita': '#00a0c6'},
    Area.CIVIL: {'disponible': '#d97706', 'borde': '#b45309', 'cita': '#ea580c'},
    Area.MIXTO: {'disponible': '#80ba27', 'borde': '#6da020', 'cita': '#00a0c6'},
}

AREA_BADGE_CLASS = {
    Area.SISTEMAS: 'badge-area-sistemas',
    Area.CIVIL: 'badge-area-civil',
    Area.MIXTO: 'badge-area-mixto',
}


def colores_para_area(area):
    return AREA_CALENDAR_COLORS.get(area, AREA_CALENDAR_COLORS[Area.SISTEMAS])
