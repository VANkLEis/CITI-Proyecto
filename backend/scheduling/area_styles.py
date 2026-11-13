from accounts.models import Area

# Paleta UCC aplicada a las franjas del calendario:
# - Sistemas: azul diversidad (institucional)
# - Civil: verde solidario (institucional)
# - Mi cita: azul fundadores (se distingue de las franjas disponibles)
# `texto`/`cita_texto` permiten mantener contraste legible sobre cada fondo.
AREA_CALENDAR_COLORS = {
    Area.SISTEMAS: {
        'disponible': '#00acc9', 'borde': '#00879d', 'texto': '#062a33',
        'cita': '#132740', 'cita_texto': '#ffffff', 'cita_borde': '#0c1a2b',
    },
    Area.CIVIL: {
        'disponible': '#80ba27', 'borde': '#5f8c17', 'texto': '#1f3307',
        'cita': '#132740', 'cita_texto': '#ffffff', 'cita_borde': '#0c1a2b',
    },
    Area.MIXTO: {
        'disponible': '#cad400', 'borde': '#a6b000', 'texto': '#2b2e00',
        'cita': '#132740', 'cita_texto': '#ffffff', 'cita_borde': '#0c1a2b',
    },
}

AREA_BADGE_CLASS = {
    Area.SISTEMAS: 'badge-area-sistemas',
    Area.CIVIL: 'badge-area-civil',
    Area.MIXTO: 'badge-area-mixto',
}


def colores_para_area(area):
    return AREA_CALENDAR_COLORS.get(area, AREA_CALENDAR_COLORS[Area.SISTEMAS])
