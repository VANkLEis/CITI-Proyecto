from accounts.models import Area


class Subespecialidad:
    """Códigos de subespecialidad por consultorio."""

    BD = 'bd'
    WEB = 'web'
    REDES = 'redes'
    CIBER = 'ciber'
    ESTRUCTURAS = 'estructuras'
    INTERVENTORIA = 'interventoria'
    VIAS = 'vias'
    PLANOS = 'planos'
    # Portafolio de laboratorios de Ingeniería Civil (PPTX institucional)
    CONCRETOS = 'concretos'
    SUELOS = 'suelos'
    PAVIMENTOS = 'pavimentos'
    TOPOGRAFIA = 'topografia'
    HIDRAULICA = 'hidraulica'
    TRANSITO = 'transito'

    LABELS = {
        BD: 'Bases de Datos',
        WEB: 'Desarrollo Web',
        REDES: 'Redes',
        CIBER: 'Ciberseguridad',
        ESTRUCTURAS: 'Estructuras',
        INTERVENTORIA: 'Interventoría',
        VIAS: 'Vías',
        PLANOS: 'Planos',
        CONCRETOS: 'Concretos',
        SUELOS: 'Suelos y geotecnia',
        PAVIMENTOS: 'Pavimentos',
        TOPOGRAFIA: 'Topografía y SIG',
        HIDRAULICA: 'Hidráulica',
        TRANSITO: 'Tránsito y transporte',
    }

    POR_AREA = {
        Area.SISTEMAS: [BD, WEB, REDES, CIBER],
        Area.CIVIL: [
            CONCRETOS, SUELOS, PAVIMENTOS, TOPOGRAFIA,
            ESTRUCTURAS, HIDRAULICA, TRANSITO, VIAS,
            INTERVENTORIA, PLANOS,
        ],
    }

    @classmethod
    def choices_for_area(cls, area):
        codes = cls.POR_AREA.get(area, [])
        return [(code, cls.LABELS[code]) for code in codes]

    @classmethod
    def label(cls, code):
        return cls.LABELS.get(code, code)

    @classmethod
    def valid_for_area(cls, code, area):
        return code in cls.POR_AREA.get(area, [])
