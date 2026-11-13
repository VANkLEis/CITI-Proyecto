"""Indicadores de gestión CITI (Fase 03, Módulos B y C).

Fórmulas (documentadas; todo desde la base de datos real):

- Solicitudes recibidas      = citas cuyo `creada_en` cae en el periodo.
- Pendientes                 = recibidas con estado `solicitada` (sin responsable).
- Asignadas / En proceso / Finalizadas / Canceladas = recibidas por estado.
- Atendidas (asesorías realizadas) = citas con estado `finalizada`
  (las canceladas NO cuentan como atendidas).
- Tasa de finalización       = finalizadas / recibidas × 100  (base: recibidas
  del periodo, incluyendo canceladas; se muestra el numerador/denominador).
- Tiempo promedio de asignación = media(cerrada… no: media(`asignada_en` -
  `creada_en`)) sobre citas con ambas marcas en el periodo; "No disponible"
  si < 1 muestra.
- Tiempo promedio de resolución = media(`cerrada_en` - `creada_en`) sobre
  citas finalizadas con ambas marcas; "No disponible" si no hay datos.
- Evolución mensual  = citas agrupadas por mes de `creada_en` vs por mes de
  `cerrada_en` (últimos 6 meses del filtro).
- Demanda por área   = conteo por `franja__area`.
- Servicios más solicitados = conteo por `subespecialidad` (etiqueta real).

Permisos: el Director consulta global; el Coordinador SOLO su área
(`area_forzada`). Los filtros nunca amplían el alcance del rol.
"""

from datetime import timedelta
from statistics import mean

from django.db.models import Avg, Count, Q
from django.utils import timezone

from accounts.models import Area, Role
from scheduling.models import CitaAsesoria
from scheduling.subespecialidades import Subespecialidad

PERIODOS = {
    '7': 'Últimos 7 días',
    '30': 'Últimos 30 días',
    '90': 'Últimos 90 días',
    'anio': 'Año actual',
    'custom': 'Rango personalizado',
    'todos': 'Todo el histórico',
}


def parse_filtros(request_GET, area_forzada=None):
    """Queryset base + metadatos del filtro. Nunca devuelve más alcance que
    el permitido al rol (`area_forzada` gana si existe)."""
    g = request_GET
    periodo = g.get('periodo', '90')
    now = timezone.now()
    if periodo == '7':
        desde = now - timedelta(days=7)
    elif periodo == '30':
        desde = now - timedelta(days=30)
    elif periodo == '90':
        desde = now - timedelta(days=90)
    elif periodo == 'anio':
        desde = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    elif periodo == 'todos':
        desde = None
    else:  # custom
        desde = None
    hasta = None

    def _parse_fecha(valor):
        if not valor:
            return None
        from django.utils.dateparse import parse_date
        d = parse_date(valor)
        if not d:
            return None
        return timezone.make_aware(
            timezone.datetime.combine(d, timezone.datetime.min.time()))

    if periodo == 'custom':
        desde = _parse_fecha(g.get('desde'))
        hasta = _parse_fecha(g.get('hasta'))
        if hasta:
            hasta = hasta + timedelta(days=1)  # día inclusive

    filtros = {
        'periodo': periodo if periodo in PERIODOS else '90',
        'desde': desde,
        'hasta': hasta,
        'area': area_forzada or (g.get('area') if g.get('area') in dict(Area.choices) else ''),
        'estado': g.get('estado') if g.get('estado') in dict(CitaAsesoria.Estado.choices) else '',
        'tipo': g.get('tipo') if g.get('tipo') in ('orientacion', 'especializada') else '',
        'responsable': g.get('responsable') or '',
        'area_forzada': area_forzada or '',
    }

    qs = CitaAsesoria.objects.select_related(
        'franja', 'cliente', 'cliente__empresa', 'docente_asignado', 'estudiante_apoyo')
    if filtros['desde']:
        qs = qs.filter(creada_en__gte=filtros['desde'])
    if filtros['hasta']:
        qs = qs.filter(creada_en__lt=filtros['hasta'])
    if filtros['area']:
        qs = qs.filter(franja__area=filtros['area'])
    if filtros['estado']:
        qs = qs.filter(estado=filtros['estado'])
    if filtros['tipo']:
        qs = qs.filter(tipo_servicio=filtros['tipo'])
    if filtros['responsable']:
        qs = qs.filter(Q(docente_asignado_id=filtros['responsable'])
                       | Q(estudiante_apoyo_id=filtros['responsable']))
    return qs, filtros


def kpis_base(qs):
    totales = qs.aggregate(
        recibidas=Count('id'),
        pendientes=Count('id', filter=Q(estado=CitaAsesoria.Estado.SOLICITADA)),
        asignadas=Count('id', filter=Q(estado=CitaAsesoria.Estado.ASIGNADA)),
        en_proceso=Count('id', filter=Q(estado=CitaAsesoria.Estado.EN_PROCESO)),
        finalizadas=Count('id', filter=Q(estado=CitaAsesoria.Estado.FINALIZADA)),
        canceladas=Count('id', filter=Q(estado=CitaAsesoria.Estado.CANCELADA)),
    )
    finalizadas = totales['finalizadas']
    recibidas = totales['recibidas']
    tasa = round(finalizadas * 100 / recibidas, 1) if recibidas else None
    return {
        **totales,
        'tasa_finalizacion': tasa,
    }


def metricas_interaccion(qs):
    """Indicadores de seguimiento con el cliente (Fase 04, sección 8).

    Fórmulas, sobre el queryset de citas ya filtrado por periodo/área/etc.:
    - Entregables publicados   = interacciones tipo 'entrega_resultados'.
    - Casos con entrega        = citas del filtro con al menos una entrega.
    - Pendientes de aprobación = citas cuya entrega MÁS RECIENTE no tiene
      decisión ('aprobacion' o 'rechazo_ajuste') de fecha posterior. Coincide
      1:1 con `CitaAsesoria.entrega_pendiente` (misma semántica, vista por
      caso en el portal). El estado es de la ENTREGA: aprobar no finaliza.
    - Ajustes solicitados      = interacciones tipo 'rechazo_ajuste'.
    - Aprobaciones             = interacciones tipo 'aprobacion'.
    - Valoración media         = AVG(calificacion) sobre citas finalizadas
      calificadas del filtro; n=0 -> None ('No disponible', nunca estimado).
    Implementación: 2 agregaciones por cita (máximos de fecha por tipo) +
    comparación en Python sobre ids; sin N+1.
    """
    from django.db.models import Max

    from scheduling.models import CitaInteraccion as CI

    inter = CI.objects.filter(cita__in=qs)
    publicados = inter.filter(tipo=CI.Tipo.ENTREGA_RESULTADOS).count()
    aprobaciones = inter.filter(tipo=CI.Tipo.APROBACION).count()
    ajustes = inter.filter(tipo=CI.Tipo.RECHAZO_AJUSTE).count()

    entregas_max = dict(
        inter.filter(tipo=CI.Tipo.ENTREGA_RESULTADOS)
        .values_list('cita_id')
        .annotate(m=Max('fecha'))
        .values_list('cita_id', 'm'))
    decisiones_max = dict(
        inter.filter(tipo__in=(CI.Tipo.APROBACION, CI.Tipo.RECHAZO_AJUSTE))
        .values_list('cita_id')
        .annotate(m=Max('fecha'))
        .values_list('cita_id', 'm'))
    pendientes = sum(
        1 for cita_id, fent in entregas_max.items()
        if decisiones_max.get(cita_id) is None or
        decisiones_max[cita_id] < fent)

    calif = qs.filter(estado=CitaAsesoria.Estado.FINALIZADA,
                      calificacion__isnull=False).aggregate(
        avg=Avg('calificacion'), n=Count('id'))
    valoracion = round(float(calif['avg']), 2) if calif['avg'] is not None else None

    return {
        'entregas_publicadas': publicados,
        'casos_con_entrega': len(entregas_max),
        'pendientes_aprobacion': pendientes,
        'aprobaciones': aprobaciones,
        'ajustes_solicitados': ajustes,
        'valoracion_media': valoracion,
        'valoracion_n': calif['n'],
    }


def _promedio_horas(pares):
    """pares = [(delta, delta)...]; devuelve horas promedio o None."""
    deltas = [d for d in pares if d is not None]
    if not deltas:
        return None
    seg = mean(d.total_seconds() for d in deltas)
    return round(seg / 3600, 1)


def tiempos_promedio(qs):
    """Promedios calculados en Python (las marcas son datetime; fórmula y
    n en el contexto). Muestras pequeñas por diseño académico."""
    datos_asig, datos_cierre = [], []
    for creada, asignada, cerrada, estado in (
            qs.exclude(estado=CitaAsesoria.Estado.CANCELADA)
            .values_list('creada_en', 'asignada_en', 'cerrada_en', 'estado')):
        if asignada and creada:
            datos_asig.append(asignada - creada)
        if estado == CitaAsesoria.Estado.FINALIZADA and cerrada and creada:
            datos_cierre.append(cerrada - creada)
    return {
        'asignacion_horas': _promedio_horas(datos_asig),
        'asignacion_n': len(datos_asig),
        'resolucion_horas': _promedio_horas(datos_cierre),
        'resolucion_n': len(datos_cierre),
    }


def por_estado(qs):
    conteo = dict(qs.values_list('estado').annotate(n=Count('id')).values_list('estado', 'n'))
    filas = []
    total = sum(conteo.values())
    for valor, label in CitaAsesoria.Estado.choices:
        n = conteo.get(valor, 0)
        filas.append({'estado': valor, 'label': label, 'n': n,
                      'pct': round(n * 100 / total, 1) if total else 0})
    return filas, total


def por_area(qs):
    total = qs.count()
    filas = []
    for valor, label in Area.choices:
        if valor == Area.MIXTO:
            continue  # área sin flujo operativo (ver auditoría FUN-09)
        n = qs.filter(franja__area=valor).count()
        filas.append({'label': label, 'n': n,
                      'pct': round(n * 100 / total, 1) if total else 0})
    return filas, total


def servicios_top(qs, n=8):
    filas = []
    total = qs.exclude(subespecialidad='').count()
    for code, total_code in (qs.exclude(subespecialidad='')
                             .values_list('subespecialidad')
                             .annotate(c=Count('id'))
                             .order_by('-c')[:n]):
        filas.append({
            'label': Subespecialidad.label(code),
            'n': total_code,
            'pct': round(total_code * 100 / total, 1) if total else 0,
        })
    return filas, total


def evolucion_mensual(qs, meses=6, hasta=None):
    """[(etiqueta, recibidas, cerradas)] para los `meses` meses que terminan
    en `hasta` (o el actual). Cerradas = finalizadas cuyo `cerrada_en` cae en
    el mes (no el estado actual, para que la serie sea histórica)."""
    ahora = hasta or timezone.now()
    y, m = ahora.year, ahora.month
    etiquetas = []
    for _ in range(meses):
        etiquetas.append((y, m))
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    etiquetas.reverse()
    nombres = ['ene', 'feb', 'mar', 'abr', 'may', 'jun',
               'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

    serie = []
    for anyo, mes in etiquetas:
        ini = timezone.datetime(anyo, mes, 1, tzinfo=ahora.tzinfo)
        if mes == 12:
            fin = timezone.datetime(anyo + 1, 1, 1, tzinfo=ahora.tzinfo)
        else:
            fin = timezone.datetime(anyo, mes + 1, 1, tzinfo=ahora.tzinfo)
        recibidas = qs.filter(creada_en__gte=ini, creada_en__lt=fin).count()
        cerradas = qs.filter(cerrada_en__gte=ini, cerrada_en__lt=fin,
                             estado=CitaAsesoria.Estado.FINALIZADA).count()
        serie.append({'mes': f'{nombres[mes - 1]} {anyo % 100}',
                      'recibidas': recibidas, 'cerradas': cerradas})
    return serie


def actividad_reciente(qs, n=10):
    return (qs.order_by('-actualizada_en')[:n]
            .select_related('franja', 'cliente__empresa', 'docente_asignado'))


def resultados_tabla(qs, n=100):
    return qs.order_by('-creada_en')[:n]


def _mapa_aprobacion_citas(qs):
    """cita_id -> 'pendiente' | 'aprobada' | 'con ajustes' | '' (sin entregas).
    Mismo criterio que metricas_interaccion/entrega_pendiente."""
    from django.db.models import Max

    from scheduling.models import CitaInteraccion as CI

    inter = CI.objects.filter(cita__in=qs)
    entregas_max = dict(
        inter.filter(tipo=CI.Tipo.ENTREGA_RESULTADOS).values_list('cita_id')
        .annotate(m=Max('fecha')).values_list('cita_id', 'm'))
    decisiones = dict(
        inter.filter(tipo__in=(CI.Tipo.APROBACION, CI.Tipo.RECHAZO_AJUSTE))
        .values_list('cita_id')
        .annotate(m=Max('fecha')).values_list('cita_id', 'm'))
    ultima_tipo = dict(
        inter.filter(tipo__in=(CI.Tipo.APROBACION, CI.Tipo.RECHAZO_AJUSTE))
        .order_by('fecha', 'id').values_list('cita_id', 'tipo'))
    mapa = {}
    for cita_id, fent in entregas_max.items():
        fdec = decisiones.get(cita_id)
        if fdec is None or fdec < fent:
            mapa[cita_id] = 'pendiente'
        else:
            mapa[cita_id] = ('con ajustes'
                             if ultima_tipo.get(cita_id) == CI.Tipo.RECHAZO_AJUSTE
                             else 'aprobada')
    return mapa


def csv_rows(qs):
    """Filas del reporte CSV (sin datos sensibles innecesarios: no incluye
    correos personales, solo razón social y nombres de responsables).
    Columna 'Aprobación de entregables' derivada del mismo criterio que la
    métrica `pendientes_aprobacion` (Fase 04)."""
    aprob = _mapa_aprobacion_citas(qs)
    yield ['Código', 'Estado', 'Empresa', 'Área', 'Servicio', 'Tipo de servicio',
           'Docente responsable', 'Tutor de apoyo', 'Fecha solicitud',
           'Fecha asignación', 'Fecha cierre', 'Días de resolución', 'Valoración',
           'Aprobación de entregables']
    for c in qs.order_by('id'):
        resolucion = ''
        if c.cerrada_en and c.creada_en:
            resolucion = str(round((c.cerrada_en - c.creada_en).total_seconds() / 86400, 1))
        yield [
            f'CITI-{c.pk:05d}',
            c.get_estado_display(),
            c.cliente.empresa.razon_social if c.cliente.empresa_id else c.cliente.email.split('@')[0],
            c.franja.get_area_display(),
            c.get_subespecialidad_display(),
            c.get_tipo_servicio_display(),
            c.docente_asignado.nombre_completo if c.docente_asignado else '',
            c.estudiante_apoyo.nombre_completo if c.estudiante_apoyo else '',
            timezone.localtime(c.creada_en).strftime('%Y-%m-%d %H:%M') if c.creada_en else '',
            timezone.localtime(c.asignada_en).strftime('%Y-%m-%d %H:%M') if c.asignada_en else '',
            timezone.localtime(c.cerrada_en).strftime('%Y-%m-%d %H:%M') if c.cerrada_en else '',
            resolucion,
            str(c.calificacion) if c.calificacion else '',
            aprob.get(c.pk, ''),
        ]


def responsables_posibles(qs):
    """Users that appear as docente/tutor en el alcance, para el filtro."""
    ids_doc = set(qs.exclude(docente_asignado__isnull=True).values_list('docente_asignado_id', flat=True))
    ids_est = set(qs.exclude(estudiante_apoyo__isnull=True).values_list('estudiante_apoyo_id', flat=True))
    ids = ids_doc | ids_est
    from accounts.models import CustomUser
    return CustomUser.objects.filter(pk__in=ids).order_by('first_name', 'last_name')
