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

# Rutas de imagen de iteraciones anteriores. El seed las migra a las nuevas
# rutas, pero respeta cualquier imagen personalizada desde /admin/.
LEGACY_IMAGE_PATHS = frozenset({
    'images/landing/area-civil.jpg',
    'images/landing/area-sistemas.jpg',
    'images/landing/banner-asesoria.jpg',
    'images/landing/banner-campo.jpg',
    'images/landing/hero-equipo.jpg',
    'images/landing/proceso-revision.jpg',
    'images/landing/reportes-manos.jpg',
})

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
        'imagen_static': 'images/landing/proyecto-trazabilidad-ong.jpg',
        'imagen_alt': 'Profesionales de una fundación revisando casos y documentos en una mesa de trabajo',
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
        'imagen_static': 'images/landing/proyecto-ciberseguridad-pyme.jpg',
        'imagen_alt': 'Rack de servidores y cableado de red en un centro de datos',
        'orden': 5,
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
        'imagen_static': 'images/landing/proyecto-suelos-geotecnia.jpg',
        'imagen_alt': 'Equipo de perforación para un estudio geotécnico de suelos',
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
        'imagen_static': 'images/landing/proyecto-red-hidraulica.jpg',
        'imagen_alt': 'Válvulas y tuberías de una red de distribución de agua',
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
        'imagen_static': 'images/landing/proyecto-asistente-ia.jpg',
        'imagen_alt': 'Puestos de atención con computadores en un centro de servicios',
        'destacado': True,
        'orden': 3,
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
        'imagen_static': 'images/landing/proyecto-alfabetizacion-digital.jpg',
        'imagen_alt': 'Persona mayor usando un computador portátil',
        'orden': 7,
    },
    {
        'slug': 'patologia-estructural-sede-comunitaria',
        'titulo': 'Patología estructural en una sede comunitaria',
        'linea': 'civil',
        'organizacion': 'Junta de Acción Comunal El Espinal',
        'anio': 2026,
        'resumen': 'Diagnóstico de fisuras, humedad y vulnerabilidad antes de intervenir.',
        'reto': 'La sede presentaba fisuras y humedad, y la comunidad no sabía si '
                'el edificio era seguro para seguir usándolo.',
        'solucion': 'Inspección visual, levantamiento de lesiones, análisis de '
                    'causas probables y recomendaciones priorizadas por riesgo.',
        'resultados': 'Un informe claro para decidir la intervención y evitar '
                      'reparaciones cosméticas que ocultaran el problema.',
        'metricas': [
            {'label': 'Lesiones identificadas', 'valor': '11'},
            {'label': 'Acciones priorizadas', 'valor': '3'},
        ],
        'imagen_static': 'images/landing/proyecto-patologia-estructural.jpg',
        'imagen_alt': 'Vivienda antigua con grietas y humedad visibles en su fachada',
        'destacado': True,
        'orden': 6,
    },
    {
        'slug': 'topografia-drenaje-vial-rural',
        'titulo': 'Topografía y drenaje vial en zona rural del Tolima',
        'linea': 'civil',
        'organizacion': 'Juntas Veredales del Tolima',
        'anio': 2026,
        'resumen': 'Levantamiento topográfico y diseño de drenaje para una vía terciaria.',
        'reto': 'La vía se inundaba en temporada de lluvias y no existía un '
                'levantamiento confiable del trazado.',
        'solucion': 'Levantamiento topográfico, perfil longitudinal, análisis de '
                    'escorrentía y diseño de obras de drenaje.',
        'resultados': 'Planos y memoria de cálculo para priorizar las obras con '
                      'la comunidad y la administración local.',
        'metricas': [
            {'label': 'Kilómetros levantados', 'valor': '4,2'},
            {'label': 'Obras de drenaje', 'valor': '7'},
        ],
        'imagen_static': 'images/landing/proyecto-topografia-drenaje.jpg',
        'imagen_alt': 'Topógrafos con estación total en una vía rural',
        'orden': 8,
    },
)

# Proyectos sembrados en versiones anteriores que ya no forman parte del set
# vigente. Se despublican (no se borran) para conservar el historial.
PROYECTOS_RETIRADOS = (
    'validacion-tecnica-emprendimiento-juvenil',
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
        'area': 'sistemas',
        'publico_objetivo': 'fundaciones',
        'duracion': '2 sesiones de 90 minutos',
        'modalidad': 'hibrida',
        'nivel': 'basico',
        'puntos_clave': [
            'Qué es la IA y qué no resuelve.',
            'Casos de uso en informes, encuestas y atención.',
            'Uso responsable y revisión humana.',
        ],
        'imagen_static': 'images/landing/taller-ia-fundaciones.jpg',
        'imagen_alt': 'Participantes en un taller de capacitación con pantalla y proyector',
        'orden': 1,
    },
    {
        'slug': 'autoconstruccion-segura-vivienda',
        'titulo': 'Autoconstrucción segura y prevención de fallas en vivienda',
        'tematica': 'Decisiones básicas de estructura, materiales y drenaje para construir o ampliar sin riesgo.',
        'descripcion': 'Taller para comunidad y maestros de obra: lectura de planos '
                       'básicos, buenas prácticas de cimentación, control de humedad '
                       'y señales de alerta estructural.',
        'area': 'civil',
        'publico_objetivo': 'pymes',
        'duracion': '2 sesiones de 3 horas',
        'modalidad': 'presencial',
        'nivel': 'basico',
        'puntos_clave': [
            'Lectura de planos y cimentación básica.',
            'Materiales y control de humedad.',
            'Señales de alerta estructural.',
        ],
        'imagen_static': 'images/landing/taller-autoconstruccion.jpg',
        'imagen_alt': 'Maestro de obra revisando planos de construcción',
        'orden': 2,
    },
    {
        'slug': 'herramientas-digitales-emprendedores',
        'titulo': 'Herramientas digitales para emprendedores jóvenes',
        'tematica': 'Organiza tu operación, tus clientes y tus finanzas con herramientas accesibles.',
        'descripcion': 'Taller de productividad y gestión: hojas de cálculo, '
                       'gestión de clientes, presencia digital básica y respaldos '
                       'seguros para un emprendimiento.',
        'area': 'sistemas',
        'publico_objetivo': 'jovenes',
        'duracion': '1 sesión de 3 horas',
        'modalidad': 'presencial',
        'nivel': 'basico',
        'puntos_clave': [
            'Organización de clientes y finanzas.',
            'Presencia digital básica.',
            'Respaldos y contraseñas seguras.',
        ],
        'imagen_static': 'images/landing/taller-emprendimiento-digital.jpg',
        'imagen_alt': 'Equipo joven trabajando con portátiles alrededor de una mesa',
        'orden': 3,
    },
    {
        'slug': 'cosecha-aguas-lluvias-saneamiento',
        'titulo': 'Cosecha de aguas lluvias y saneamiento básico comunitario',
        'tematica': 'Captación, almacenamiento y tratamiento básico del agua en sedes y juntas veredales.',
        'descripcion': 'Taller para juntas veredales y fundaciones: diseño simple '
                       'de captación de aguas lluvias, filtros, mantenimiento y '
                       'criterios de saneamiento básico.',
        'area': 'civil',
        'publico_objetivo': 'fundaciones',
        'duracion': '2 sesiones de 2 horas',
        'modalidad': 'presencial',
        'nivel': 'basico',
        'puntos_clave': [
            'Captación y almacenamiento de agua.',
            'Filtros y tratamiento básico.',
            'Mantenimiento y saneamiento comunitario.',
        ],
        'imagen_static': 'images/landing/taller-aguas-lluvias.jpg',
        'imagen_alt': 'Tanque comunitario de almacenamiento de aguas lluvias',
        'orden': 4,
    },
    {
        'slug': 'alfabetizacion-digital-adultos-mayores',
        'titulo': 'Alfabetización digital y trámites seguros para adultos mayores',
        'tematica': 'Uso seguro del celular, banca digital y trámites en línea, a su ritmo.',
        'descripcion': 'Sesiones guiadas para personas mayores y pensionados: '
                       'correo, trámites, videollamadas, contraseñas seguras y '
                       'cómo reconocer intentos de fraude.',
        'area': 'sistemas',
        'publico_objetivo': 'adultos_mayores',
        'duracion': '4 sesiones de 2 horas',
        'modalidad': 'presencial',
        'nivel': 'basico',
        'puntos_clave': [
            'Uso seguro del celular y la banca digital.',
            'Prevención de estafas en internet.',
            'Trámites en línea y comunicación cotidiana.',
        ],
        'imagen_static': 'images/landing/taller-adultos-mayores-digital.jpg',
        'imagen_alt': 'Persona mayor usando un portátil en su casa',
        'orden': 5,
    },
    {
        'slug': 'mantenimiento-preventivo-hogar',
        'titulo': 'Mantenimiento preventivo del hogar y detección de humedad o grietas',
        'tematica': 'Revisa tu vivienda a tiempo: humedad, grietas y mantenimiento sin obras costosas.',
        'descripcion': 'Taller para propietarios y personas mayores: recorrido de '
                       'autodiagnóstico, señales de humedad y grietas, y rutinas '
                       'sencillas de mantenimiento preventivo.',
        'area': 'civil',
        'publico_objetivo': 'adultos_mayores',
        'duracion': '1 sesión de 2 horas',
        'modalidad': 'presencial',
        'nivel': 'basico',
        'puntos_clave': [
            'Señales de humedad y grietas.',
            'Autodiagnóstico y priorización.',
            'Rutinas de mantenimiento preventivo.',
        ],
        'imagen_static': 'images/landing/taller-mantenimiento-hogar.jpg',
        'imagen_alt': 'Grieta en el muro de una vivienda como señal de mantenimiento',
        'orden': 6,
    },
)

# Talleres de iteraciones anteriores que salen del set vigente. Se desactivan
# (no se borran) para conservar solicitudes e historial asociados.
TALLERES_RETIRADOS = (
    'gestion-tecnologica-pymes',
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
        proyecto, creado = ProyectoPortafolio.objects.get_or_create(
            slug=datos['slug'], defaults=datos)
        # No sobrescribe contenido editado en admin: solo migra imágenes
        # heredadas o vacías y sincroniza el orden editorial del set demo.
        if not creado:
            cambios = []
            if not proyecto.imagen_static or proyecto.imagen_static in LEGACY_IMAGE_PATHS:
                proyecto.imagen_static = datos['imagen_static']
                proyecto.imagen_alt = datos['imagen_alt']
                cambios.extend(['imagen_static', 'imagen_alt'])
            if proyecto.orden != datos['orden']:
                proyecto.orden = datos['orden']
                cambios.append('orden')
            if cambios:
                proyecto.save(update_fields=cambios + ['actualizado_en'])
        nuevos['proyectos'] += 1 if creado else 0

    # Los proyectos retirados se despublican, no se borran.
    ProyectoPortafolio.objects.filter(
        slug__in=PROYECTOS_RETIRADOS).update(publicado=False)

    talleres = {}
    for datos in TALLERES:
        taller, creado = Taller.objects.get_or_create(slug=datos['slug'], defaults=datos)
        if not creado:
            # Backfill no destructivo: completa temario/área/orden e imágenes
            # heredadas si faltan, sin sobrescribir ediciones hechas en admin.
            cambios = []
            if not taller.imagen_static or taller.imagen_static in LEGACY_IMAGE_PATHS:
                taller.imagen_static = datos['imagen_static']
                taller.imagen_alt = datos['imagen_alt']
                cambios.extend(['imagen_static', 'imagen_alt'])
            if not taller.puntos_clave and datos.get('puntos_clave'):
                taller.puntos_clave = datos['puntos_clave']
                cambios.append('puntos_clave')
            if taller.area != datos['area']:
                taller.area = datos['area']
                cambios.append('area')
            if taller.orden != datos['orden']:
                taller.orden = datos['orden']
                cambios.append('orden')
            if cambios:
                taller.save(update_fields=cambios + ['actualizado_en'])
        talleres[datos['slug']] = taller
        nuevos['talleres'] += 1 if creado else 0

    # Los talleres retirados se desactivan, no se borran.
    Taller.objects.filter(slug__in=TALLERES_RETIRADOS).update(activo=False)

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
