"""Contenido público de demostración (Fase 05).

Portafolio, catálogo de talleres, clientes adicionales y solicitudes de intake
en distintos estados, para que la exposición pueda recorrer el flujo completo.

Convenciones:
- IDEMPOTENTE: `get_or_create` por `slug`/`codigo`; re-ejecutar no duplica.
- NO DESTRUCTIVO: no sobrescribe ediciones hechas en /admin/.
- Igual que el resto del seed, se ejecuta solo en entornos locales
  (`seed_demo` / `seed_demo_data`, bloqueados con DJANGO_ENV=produccion).
"""

from datetime import timedelta

from django.utils import timezone

from accounts.models import Area, CustomUser, Empresa, Role
from portal.models import ProyectoPortafolio, Taller
from scheduling.models import LineaAtencion, SolicitudPublica

DESCRIPCION_LARGA = (
    'La organización necesita ordenar su operación y definir prioridades '
    'técnicas con un equipo que entienda el contexto local y deje evidencia '
    'del trabajo realizado.')

# ---------------------------------------------------------------------------
# Portafolio
# ---------------------------------------------------------------------------
PROYECTOS = (
    {
        'slug': 'trazabilidad-casos-fundacion',
        'titulo': 'Trazabilidad de casos para una fundación',
        'linea': 'sistemas',
        'organizacion': 'Fundación Horizonte',
        'anio': 2026,
        'resumen': 'Un tablero único para saber en qué va cada caso y quién es responsable.',
        'reto': 'La fundación seguía sus casos en hojas de cálculo separadas; '
                'perdía el hilo entre la solicitud y el cierre.',
        'solucion': 'Modelo de datos de solicitudes, estados e historial, con panel '
                    'por rol y registro automático de cada cambio.',
        'resultados': 'Un solo historial por caso, responsabilidad visible y cierre '
                      'con acta. El equipo dejó de reconstruir conversaciones.',
        'metricas': [
            {'label': 'Casos centralizados', 'valor': '180+'},
            {'label': 'Tiempo de reporte', 'valor': '-60%'},
        ],
        'imagen_static': 'images/landing/area-sistemas.jpg',
        'imagen_alt': 'Equipo revisando un tablero de seguimiento en un portátil',
        'destacado': True,
        'orden': 1,
    },
    {
        'slug': 'diagnostico-seguridad-pyme',
        'titulo': 'Diagnóstico de seguridad y redes para una pyme',
        'linea': 'sistemas',
        'organizacion': 'Comercializadora del Tolima',
        'anio': 2026,
        'resumen': 'Inventario de activos, riesgos priorizados y plan de cierre de brechas.',
        'reto': 'Crecimiento rápido sin control de accesos ni respaldo verificable.',
        'solucion': 'Revisión de red, permisos y respaldos; matriz de riesgos con '
                    'acciones ordenadas por impacto.',
        'resultados': 'Plan de trabajo por trimestre y política mínima de respaldo '
                      'aprobada por la gerencia.',
        'metricas': [
            {'label': 'Riesgos priorizados', 'valor': '14'},
            {'label': 'Acciones de cierre', 'valor': '9'},
        ],
        'imagen_static': 'images/landing/banner-asesoria.jpg',
        'imagen_alt': 'Sala de reuniones con documentación técnica sobre la mesa',
        'orden': 3,
    },
    {
        'slug': 'estudio-suelos-vivienda-rural',
        'titulo': 'Estudio de suelos para vivienda rural',
        'linea': 'civil',
        'organizacion': 'Constructora Andina',
        'anio': 2025,
        'resumen': 'Caracterización geotécnica para definir la cimentación segura.',
        'reto': 'El terreno presentaba indicios de baja capacidad portante y no '
                'había estudio previo.',
        'solucion': 'Ensayos de laboratorio, clasificación del suelo y recomendación '
                    'de cimentación con memoria de cálculo.',
        'resultados': 'Diseño ajustado al terreno real, evitando sobrecostos de '
                      'excavación y riesgos de asentamiento.',
        'metricas': [
            {'label': 'Apiques', 'valor': '6'},
            {'label': 'Ensayos de laboratorio', 'valor': '12'},
        ],
        'imagen_static': 'images/landing/area-civil.jpg',
        'imagen_alt': 'Estudiantes de ingeniería civil revisando una maqueta estructural',
        'destacado': True,
        'orden': 2,
    },
    {
        'slug': 'optimizacion-red-agua',
        'titulo': 'Optimización de red de distribución de agua',
        'linea': 'civil',
        'organizacion': 'Junta de Acción Comunal El Espinal',
        'anio': 2025,
        'resumen': 'Diagnóstico hidráulico y priorización de reparaciones en la red.',
        'reto': 'Pérdidas de presión en los tramos altos y reclamos recurrentes.',
        'solucion': 'Modelación hidráulica del trazado, revisión de diámetros y '
                    'propuesta de intervención por fases.',
        'resultados': 'Tramos críticos identificados y plan de obra priorizado con '
                      'la comunidad.',
        'metricas': [
            {'label': 'Tramos evaluados', 'valor': '9'},
            {'label': 'Fases de intervención', 'valor': '3'},
        ],
        'imagen_static': 'images/landing/banner-campo.jpg',
        'imagen_alt': 'Trabajo de campo en infraestructura de redes',
        'orden': 4,
    },
    {
        'slug': 'asistente-ia-atencion',
        'titulo': 'Asistente de IA para atención de usuarios',
        'linea': 'innovacion_ia',
        'organizacion': 'Centro de Servicios Regional',
        'anio': 2026,
        'resumen': 'Respuestas frecuentes automatizadas con revisión humana del contenido.',
        'reto': 'El equipo respondía las mismas preguntas cientos de veces por semana.',
        'solucion': 'Base de conocimiento curada y asistente de consulta con '
                    'validación previa del equipo.',
        'resultados': 'Menos tiempo en preguntas repetidas y respuestas consistentes, '
                      'sin reemplazar la atención humana.',
        'metricas': [
            {'label': 'Consultas frecuentes cubiertas', 'valor': '35'},
            {'label': 'Revisión humana', 'valor': '100%'},
        ],
        'imagen_static': 'images/landing/reportes-manos.jpg',
        'imagen_alt': 'Persona revisando indicadores y reportes impresos',
        'destacado': True,
        'orden': 5,
    },
    {
        'slug': 'alfabetizacion-digital-mayores',
        'titulo': 'Alfabetización digital para personas mayores',
        'linea': 'impacto_social',
        'organizacion': 'Club de Pensionados del Tolima',
        'anio': 2026,
        'resumen': 'Taller práctico de trámites seguros, contraseñas y comunicación digital.',
        'reto': 'Muchas personas dependían de terceros para trámites básicos y '
                'estaban expuestas a fraudes.',
        'solucion': 'Sesiones prácticas con ejercicios guiados, material impreso y '
                    'acompañamiento entre pares.',
        'resultados': 'Participantes capaces de hacer trámites en línea y reconocer '
                      'intentos de fraude.',
        'metricas': [
            {'label': 'Participantes', 'valor': '40'},
            {'label': 'Sesiones', 'valor': '4'},
        ],
        'imagen_static': 'images/landing/proceso-revision.jpg',
        'imagen_alt': 'Grupo de personas en una sesión de capacitación',
        'orden': 6,
    },
    {
        'slug': 'validacion-tecnica-emprendimiento-juvenil',
        'titulo': 'Validación técnica de un producto digital juvenil',
        'linea': 'innovacion_ia',
        'organizacion': 'Colectivo Juvenil Ibagué',
        'anio': 2026,
        'resumen': 'De la idea al alcance técnico: qué construir primero y con qué riesgos.',
        'reto': 'El equipo tenía una idea de aplicación, pero no sabía si era '
                'técnicamente viable ni por dónde empezar.',
        'solucion': 'Sesión de diagnóstico, definición de alcance mínimo y '
                    'prototipo de flujo con criterios de validación.',
        'resultados': 'Plan de producto priorizado y decisión informada antes de '
                      'invertir en desarrollo.',
        'metricas': [
            {'label': 'Flujos validados', 'valor': '3'},
            {'label': 'Semanas de diagnóstico', 'valor': '2'},
        ],
        'imagen_static': 'images/landing/hero-equipo.jpg',
        'imagen_alt': 'Jóvenes trabajando en el diseño de un producto digital',
        'orden': 7,
    },
)

# ---------------------------------------------------------------------------
# Talleres
# ---------------------------------------------------------------------------
TALLERES = (
    {
        'slug': 'ia-aplicada-fundaciones-ong',
        'titulo': 'IA aplicada para fundaciones y ONG',
        'tematica': 'Qué puede y qué no puede resolver la inteligencia artificial en una organización social.',
        'descripcion': 'Recorrido práctico por casos de uso reales: redacción de '
                       'informes, análisis de encuestas y atención de consultas '
                       'frecuentes, con criterios de uso responsable.',
        'publico_objetivo': 'fundaciones',
        'duracion': '2 sesiones de 90 minutos',
        'modalidad': 'hibrida',
        'nivel': 'basico',
        'puntos_clave': [
            'Qué es la IA y qué no resuelve.',
            'Casos de uso en informes, encuestas y atención.',
            'Uso responsable y revisión humana.',
        ],
        'imagen_static': 'images/landing/banner-asesoria.jpg',
        'imagen_alt': 'Equipo de una fundación en una sesión de capacitación',
        'orden': 1,
    },
    {
        'slug': 'herramientas-digitales-emprendedores',
        'titulo': 'Herramientas digitales para emprendedores jóvenes',
        'tematica': 'Organiza tu operación, tus clientes y tus finanzas con herramientas accesibles.',
        'descripcion': 'Taller de productividad y gestión: hojas de cálculo, '
                       'gestión de clientes, presencia digital básica y respaldos '
                       'seguros para un emprendimiento.',
        'publico_objetivo': 'jovenes',
        'duracion': '1 sesión de 3 horas',
        'modalidad': 'presencial',
        'nivel': 'basico',
        'puntos_clave': [
            'Organización de clientes y finanzas.',
            'Presencia digital básica.',
            'Respaldos y contraseñas seguras.',
        ],
        'imagen_static': 'images/landing/hero-equipo.jpg',
        'imagen_alt': 'Jóvenes trabajando con herramientas digitales',
        'orden': 2,
    },
    {
        'slug': 'alfabetizacion-digital-adultos-mayores',
        'titulo': 'Alfabetización digital y trámites seguros para adultos mayores',
        'tematica': 'Uso seguro del celular, banca digital y trámites en línea, a su ritmo.',
        'descripcion': 'Sesiones guiadas para personas mayores y pensionados: '
                       'correo, trámites, videollamadas, contraseñas seguras y '
                       'cómo reconocer intentos de fraude.',
        'publico_objetivo': 'adultos_mayores',
        'duracion': '4 sesiones de 2 horas',
        'modalidad': 'presencial',
        'nivel': 'basico',
        'puntos_clave': [
            'Uso seguro del celular y la banca digital.',
            'Prevención de estafas en internet.',
            'Trámites en línea y comunicación cotidiana.',
        ],
        'imagen_static': 'images/landing/proceso-revision.jpg',
        'imagen_alt': 'Personas mayores en un taller de herramientas digitales',
        'orden': 3,
    },
    {
        'slug': 'gestion-tecnologica-pymes',
        'titulo': 'Gestión tecnológica para pymes y comunidad',
        'tematica': 'Prioriza inversión tecnológica, riesgos y continuidad del negocio.',
        'descripcion': 'Taller para equipos directivos: inventario de activos '
                       'digitales, respaldos, accesos, proveedores y plan de '
                       'continuidad ante incidentes.',
        'publico_objetivo': 'pymes',
        'duracion': '1 sesión de 4 horas',
        'modalidad': 'virtual',
        'nivel': 'intermedio',
        'puntos_clave': [
            'Inventario de activos digitales.',
            'Respaldos, accesos y proveedores.',
            'Plan de continuidad ante incidentes.',
        ],
        'imagen_static': 'images/landing/reportes-manos.jpg',
        'imagen_alt': 'Directivos revisando indicadores de gestión tecnológica',
        'orden': 4,
    },
)

# ---------------------------------------------------------------------------
# Clientes adicionales (misma contraseña demo)
# ---------------------------------------------------------------------------
CLIENTES = (
    ('fundacion@citi.ucc.edu.co', 'Fundación', 'Horizonte',
     {'razon_social': 'Fundación Horizonte', 'nit': '901-555-010', 'sector': 'Social'}),
    ('emprendimiento@citi.ucc.edu.co', 'Juan', 'Ríos',
     {'razon_social': 'Ríos Tech', 'nit': 'PENDIENTE-RIOSTECH', 'sector': 'Tecnología'}),
    ('pyme@citi.ucc.edu.co', 'Comercializadora', 'del Tolima',
     {'razon_social': 'Comercializadora del Tolima', 'nit': '890-777-020', 'sector': 'Comercio'}),
)


def _ensure_cliente(email, nombre, apellido, empresa_datos, password):
    existente = CustomUser.objects.filter(email=email).first()
    if existente:
        return existente, 0
    empresa = Empresa.objects.filter(nit=empresa_datos['nit']).first()
    if not empresa:
        empresa = Empresa.objects.create(**empresa_datos)
    usuario = CustomUser.objects.create_user(
        email=email, password=password, first_name=nombre, last_name=apellido,
        role=Role.CLIENTE, empresa=empresa)
    return usuario, 1


def _solicitud_defaults(**extra):
    datos = {
        'nombre_contacto': 'Contacto demo',
        'organizacion': 'Organización demo',
        'email': 'contacto@demo.local',
        'telefono': '3000000000',
        'descripcion': DESCRIPCION_LARGA,
        'objetivo': 'Definir el alcance y el siguiente paso con el equipo del CITI.',
        'fecha_preferida': timezone.localdate() + timedelta(days=14),
        'acepta_contacto': True,
    }
    datos.update(extra)
    return datos


def seed_public_content(password):
    """Crea/verifica portafolio, talleres, clientes y solicitudes demo."""
    nuevos = {'proyectos': 0, 'talleres': 0, 'clientes': 0, 'solicitudes': 0}

    for datos in PROYECTOS:
        _, creado = ProyectoPortafolio.objects.get_or_create(
            slug=datos['slug'], defaults=datos)
        nuevos['proyectos'] += 1 if creado else 0

    talleres = {}
    for datos in TALLERES:
        taller, creado = Taller.objects.get_or_create(slug=datos['slug'], defaults=datos)
        # Backfill no destructivo: completa el temario solo si quedó vacío
        # (los talleres sembrados antes de existir `puntos_clave`).
        if not creado and not taller.puntos_clave and datos.get('puntos_clave'):
            taller.puntos_clave = datos['puntos_clave']
            taller.save(update_fields=['puntos_clave', 'actualizado_en'])
        talleres[datos['slug']] = taller
        nuevos['talleres'] += 1 if creado else 0

    for email, nombre, apellido, empresa_datos in CLIENTES:
        _, creado = _ensure_cliente(email, nombre, apellido, empresa_datos, password)
        nuevos['clientes'] += creado

    director = CustomUser.objects.filter(email='director@citi.ucc.edu.co').first()
    ahora = timezone.now()

    plan = [
        {
            'codigo': 'DEMO-SOL-001',
            'estado': SolicitudPublica.Estado.RECIBIDA,
            'nombre_contacto': 'Clara Restrepo',
            'cargo': 'Directora',
            'organizacion': 'Fundación Horizonte',
            'nit': '901-555-010',
            'email': 'fundacion@citi.ucc.edu.co',
            'tipo_solicitante': SolicitudPublica.TipoSolicitante.FUNDACION,
            'tipo_necesidad': SolicitudPublica.TipoNecesidad.CAPACITACION,
            'linea_atencion': LineaAtencion.PROYECCION_SOCIAL,
            'area': Area.MIXTO,
            'taller': talleres['ia-aplicada-fundaciones-ong'],
            'tema_interes': 'IA aplicada para fundaciones y ONG',
            'publico_objetivo': 'Equipo de la fundación (12 personas)',
            'numero_participantes': 12,
        },
        {
            'codigo': 'DEMO-SOL-002',
            'estado': SolicitudPublica.Estado.EN_REVISION,
            'nombre_contacto': 'Juan Ríos',
            'cargo': 'Fundador',
            'organizacion': 'Ríos Tech',
            'nit': '',
            'email': 'emprendimiento@citi.ucc.edu.co',
            'tipo_solicitante': SolicitudPublica.TipoSolicitante.EMPRENDIMIENTO,
            'tipo_necesidad': SolicitudPublica.TipoNecesidad.ASESORIA,
            'linea_atencion': LineaAtencion.PROYECCION_SOCIAL,
            'area': Area.SISTEMAS,
            'subespecialidad': 'web',
            'tema_interes': '',
            'revisada_por': director,
            'revisada_en': ahora,
        },
        {
            'codigo': 'DEMO-SOL-003',
            'estado': SolicitudPublica.Estado.APROBADA,
            'nombre_contacto': 'Comercializadora del Tolima',
            'cargo': 'Gerencia',
            'organizacion': 'Comercializadora del Tolima',
            'nit': '890-777-020',
            'email': 'pyme@citi.ucc.edu.co',
            'tipo_solicitante': SolicitudPublica.TipoSolicitante.EMPRESA,
            'tipo_necesidad': SolicitudPublica.TipoNecesidad.CONSULTORIA,
            'linea_atencion': LineaAtencion.CONSULTORIA_PROFESIONAL,
            'area': Area.SISTEMAS,
            'subespecialidad': 'bd',
            'aprobada_por': director,
            'aprobada_en': ahora,
        },
        {
            'codigo': 'DEMO-SOL-004',
            'estado': SolicitudPublica.Estado.APROBADA,
            'nombre_contacto': 'Marta Gómez',
            'cargo': 'Representante',
            'organizacion': 'Club de Pensionados del Tolima',
            'nit': '',
            'email': 'comunidad@citi.ucc.edu.co',
            'tipo_solicitante': SolicitudPublica.TipoSolicitante.COMUNIDAD,
            'tipo_necesidad': SolicitudPublica.TipoNecesidad.CAPACITACION,
            'linea_atencion': LineaAtencion.PROYECCION_SOCIAL,
            'area': Area.SISTEMAS,
            'taller': talleres['alfabetizacion-digital-adultos-mayores'],
            'tema_interes': 'Alfabetización digital y trámites seguros',
            'publico_objetivo': 'Personas mayores y pensionados',
            'numero_participantes': 25,
            'aprobada_por': director,
            'aprobada_en': ahora,
        },
    ]

    for item in plan:
        codigo = item.pop('codigo')
        _, creado = SolicitudPublica.objects.get_or_create(
            codigo=codigo, defaults=_solicitud_defaults(**item))
        nuevos['solicitudes'] += 1 if creado else 0

    return nuevos
