"""Conjunto de datos de demostración del CITI (B-2 / B-4 de la auditoría).

Diseño:
- EXPLÍCITO: solo se ejecuta desde `manage.py seed_demo` (o seed_demo_users).
  Las vistas públicas (landing/login) y los dashboards ya NO siembran datos.
- IDEMPOTENTE: puede ejecutarse varias veces sin duplicar registros.
- NO DESTRUCTIVO: no elimina datos existentes; únicamente archiva (desactiva)
  franjas vencidas y cancela con nota de bitácora las solicitudes activas
  heredadas sobre franjas terminadas.
- Las cuentas demo son locales de prueba; nunca usar en producción.
"""

import os
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.utils import timezone

from accounts.models import Area, CustomUser, Empresa, Role, StudentType
from scheduling.models import (
    CitaAsesoria, CitaEvento, CitaInteraccion, FranjaHoraria, NotaBitacora,
)
from scheduling.trazabilidad import registrar_evento, registrar_interaccion

# Contraseña única para todas las cuentas demo locales (documentada en
# docs/demo/CUENTAS_DE_PRUEBA.md). Sobrepornible con CITI_DEMO_PASSWORD.
DEMO_PASSWORD = os.environ.get('CITI_DEMO_PASSWORD', 'CITIPass2026*')

DEMO_USERS = (
    {
        'email': 'director@citi.ucc.edu.co',
        'role': Role.DIRECTOR,
        'first_name': 'Ricardo',
        'last_name': 'Pérez',
        'is_staff': True,
    },
    {
        'email': 'coordinador@citi.ucc.edu.co',
        'role': Role.COORDINADOR,
        'first_name': 'María',
        'last_name': 'Coordinadora Sistemas',
        'area': Area.SISTEMAS,
    },
    {
        'email': 'coordinador.civil@citi.ucc.edu.co',
        'role': Role.COORDINADOR,
        'first_name': 'Jorge',
        'last_name': 'Coordinador Civil',
        'area': Area.CIVIL,
    },
    {
        'email': 'docente@citi.ucc.edu.co',
        'role': Role.DOCENTE,
        'first_name': 'Carlos',
        'last_name': 'Docente Sistemas',
        'area': Area.SISTEMAS,
    },
    {
        'email': 'docente.civil@citi.ucc.edu.co',
        'role': Role.DOCENTE,
        'first_name': 'Pedro',
        'last_name': 'Docente Civil',
        'area': Area.CIVIL,
    },
    {
        'email': 'estudiante@citi.ucc.edu.co',
        'role': Role.ESTUDIANTE,
        'first_name': 'Ana',
        'last_name': 'Estudiante Sistemas',
        'area': Area.SISTEMAS,
        'student_type': StudentType.CONSULTOR,
        # Perfil académico real: supera los umbrales y el modelo la PROMUEVE
        # a tutor vía save()/señal (no se fuerza student_type a mano).
        'perfil': {'semestre': 9, 'creditos_aprobados': 150, 'promedio_general': Decimal('4.5')},
    },
    {
        'email': 'estudiante.civil@citi.ucc.edu.co',
        'role': Role.ESTUDIANTE,
        'first_name': 'Luis',
        'last_name': 'Estudiante Civil',
        'area': Area.CIVIL,
        'student_type': StudentType.CONSULTOR,
        'perfil': {'semestre': 10, 'creditos_aprobados': 168, 'promedio_general': Decimal('4.3')},
    },
    {
        'email': 'cliente@empresatolima.co',
        'role': Role.CLIENTE,
        'first_name': 'Laura',
        'last_name': 'Gerente',
        'empresa_razon_social': 'Empresa Tolima Demo',
        'empresa_nit': '900123456',
    },
)


def _director_id():
    d = CustomUser.objects.filter(role=Role.DIRECTOR).first()
    return d.pk if d else None


def ensure_demo_users():
    """Crea (o completa) las cuentas demo y sus perfiles. Idempotente."""
    for spec in DEMO_USERS:
        email = spec['email'].lower()
        user = CustomUser.objects.filter(email=email).first()
        if user is None:
            extra = {
                'first_name': spec['first_name'],
                'last_name': spec['last_name'],
                'role': spec['role'],
            }
            if spec['role'] == Role.CLIENTE:
                empresa = Empresa.objects.create(
                    razon_social=spec.get('empresa_razon_social', 'Empresa demo'),
                    nit=spec.get('empresa_nit', ''),
                )
                extra['empresa'] = empresa
            else:
                if 'area' in spec:
                    extra['area'] = spec['area']
                if spec['role'] == Role.ESTUDIANTE:
                    extra['student_type'] = spec.get('student_type', StudentType.CONSULTOR)
            if spec.get('is_staff'):
                extra['is_staff'] = True
            user = CustomUser.objects.create_user(email=email, password=DEMO_PASSWORD, **extra)

        # Director demo con acceso a /admin/ (la demo muestra indicadores + admin).
        if spec['role'] == Role.DIRECTOR:
            if not user.is_staff:
                user.is_staff = True
                user.save(update_fields=['is_staff'], skip_validation=True)
            _dar_permisos_admin_citi(user)

        # Perfil académico coherente: solo se SUBE si está por debajo del plan
        # (nunca degrada ediciones manuales del usuario).
        perfil_spec = spec.get('perfil')
        if perfil_spec:
            perfil = user.perfil_estudiante
            if (
                perfil.semestre < perfil_spec['semestre']
                or perfil.creditos_aprobados < perfil_spec['creditos_aprobados']
                or perfil.promedio_general < perfil_spec['promedio_general']
            ):
                perfil.semestre = perfil_spec['semestre']
                perfil.creditos_aprobados = perfil_spec['creditos_aprobados']
                perfil.promedio_general = perfil_spec['promedio_general']
                perfil.save()  # save() promueve a tutor si cumple umbrales


def _dar_permisos_admin_citi(user):
    """Mínimo privilegio: el director gestiona SOLO las entidades del dominio
    CITI (apps accounts/scheduling); no es superusuario."""
    from django.contrib.auth.models import Permission

    codes = list(Permission.objects.filter(
        content_type__app_label__in=['accounts', 'scheduling']
    ).values_list('id', flat=True))
    current = set(user.user_permissions.values_list('id', flat=True))
    missing = set(codes) - current
    if missing:
        user.user_permissions.add(*missing)


def _franja_futura(area, indice):
    """La franja futura activa n-ésima del área; la crea si no alcanza."""
    now = timezone.now()
    qs = FranjaHoraria.objects.filter(activa=True, area=area, inicio__gt=now).order_by('inicio')
    franja = qs[indice] if qs.count() > indice else None
    if franja is not None:
        return franja
    tz = timezone.get_current_timezone()
    dia = timezone.localdate()
    hora = 9 if area == Area.SISTEMAS else 14
    while True:
        dia = dia + timedelta(days=1)
        if dia.weekday() >= 5:
            continue
        inicio = timezone.make_aware(datetime.combine(dia, time(hora, 0)), tz)
        fin = timezone.make_aware(datetime.combine(dia, time(hora + 2, 0)), tz)
        if inicio <= now:
            continue
        franja, _ = FranjaHoraria.objects.get_or_create(
            inicio=inicio, fin=fin, area=area,
            defaults={'capacidad': 2, 'creada_por_id': _director_id()},
        )
        return franja


def _siguiente_franja_libre(area, cliente):
    """Franja futura activa del área sin cita activa de `cliente` (con cupo)."""
    now = timezone.now()
    ocupadas = list(CitaAsesoria.objects.filter(
        cliente=cliente, franja__area=area,
        estado__in=CitaAsesoria.Estado.ocupan_cupo()).values_list('franja_id', flat=True))
    for franja in FranjaHoraria.objects.filter(
            activa=True, area=area, inicio__gt=now).order_by('inicio'):
        if franja.pk in ocupadas:
            continue
        if franja.esta_disponible:
            return franja
    return None


def ensure_demo_franjas(dias=12):
    """Garantiza franjas FUTURAS, válidas y reservables en ambas áreas.

    Patrón estable documentado en la guía de demo (días hábiles):
    - Sistemas: 09:00–11:00 y 15:00–17:00
    - Civil:    11:00–13:00 y 16:00–18:00
    Capacidad 2; una franja por día y bloque. Horas construidas con la zona
    horaria activa de Django (America/Bogota).
    """
    created = 0
    tz = timezone.get_current_timezone()
    hoy = timezone.localdate()
    for offset in range(1, dias + 1):
        dia = hoy + timedelta(days=offset)
        if dia.weekday() >= 5:
            continue
        for hora_inicio, area in (
            (9, Area.SISTEMAS),
            (11, Area.CIVIL),
            (15, Area.SISTEMAS),
            (16, Area.CIVIL),
        ):
            inicio = timezone.make_aware(datetime.combine(dia, time(hora_inicio, 0)), tz)
            fin = timezone.make_aware(datetime.combine(dia, time(hora_inicio + 2, 0)), tz)
            if inicio <= timezone.now():
                continue
            _, nueva = FranjaHoraria.objects.get_or_create(
                inicio=inicio,
                fin=fin,
                area=area,
                defaults={'capacidad': 2, 'creada_por_id': _director_id()},
            )
            if nueva:
                created += 1
    return created


def archive_vencidas():
    """Archiva (NO elimina) franjas vencidas y solicitudes activas sobre ellas.

    Soluciona FUN-12: bandejas y KPIs con basura histórica que confundía la
    demo. Franja vencida -> activa=False (queda consultable como historial);
    cita en estado activo sobre franja terminada -> 'cancelada' con nota de
    bitácora que deja trazabilidad del cambio.
    """
    now = timezone.now()
    archivadas = 0
    canceladas = 0
    for franja in FranjaHoraria.objects.filter(activa=True, fin__lt=now):
        franja.activa = False
        franja.save(update_fields=['activa'])
        archivadas += 1
    autor = (
        CustomUser.objects.filter(role=Role.DIRECTOR).first()
        or CustomUser.objects.filter(role=Role.COORDINADOR).first()
    )
    if autor is None:
        return archivadas, canceladas
    activas = CitaAsesoria.objects.filter(
        estado__in=CitaAsesoria.Estado.ocupan_cupo(), franja__fin__lt=now
    ).select_related('franja')
    for cita in activas:
        cita.estado = CitaAsesoria.Estado.CANCELADA
        cita.full_clean()
        cita.save()
        NotaBitacora.objects.get_or_create(
            cita=cita,
            autor=autor,
            texto='Archivo automático (seed_demo): la franja venció con la '
                  'solicitud sin cerrar; se cancela para dejar la bandeja coherente.',
        )
        canceladas += 1
    return archivadas, canceladas


# Plan de solicitudes del cliente demo. Tuplas:
# (área, subespecialidad, tipo_servicio, (docente, estudiante)|None,
#  (estado, calificación, comentario)|None, estado_base)
# estado_base se aplica cuando hay asignación (asignada | en_proceso).
_CITAS_PLAN = (
    ('sistemas', 'web', 'especializada', None, None, None),
    ('sistemas', 'bd', 'especializada', ('docente', None), None, 'asignada'),
    ('civil', 'vias', 'orientacion', ('docente_civil', 'estudiante_civil'), None, 'en_proceso'),
    ('sistemas', 'ciber', 'especializada', ('docente', None),
     ('finalizada', 5, 'Atención excelente: resolvieron la vulnerabilidad detectada.'), None),
    ('civil', 'estructuras', 'orientacion', ('docente_civil', 'estudiante_civil'),
     ('finalizada', 4, 'Buen acompañamiento del tutor y del docente.'), None),
    ('sistemas', 'redes', 'orientacion', ('docente', 'estudiante'), None, 'asignada'),
    ('civil', 'planos', 'especializada', None, None, None),
)

_ASIG = {
    'docente': 'docente@citi.ucc.edu.co',
    'docente_civil': 'docente.civil@citi.ucc.edu.co',
    'estudiante': 'estudiante@citi.ucc.edu.co',
    'estudiante_civil': 'estudiante.civil@citi.ucc.edu.co',
}


def ensure_demo_citas():
    """Solicitudes demo del cliente sembrado, cubriendo todos los estados.

    Idempotente: a lo sumo una cita por (cliente, franja). Al menos una franja
    futura de cada área queda SIN reservas para la demostración en vivo.
    """
    cliente = CustomUser.objects.get(email='cliente@empresatolima.co')
    usadas = {Area.SISTEMAS: 0, Area.CIVIL: 0}
    creadas = 0
    reubicadas = 0
    for area, subesp, tipo, asignacion, cierre, estado_base in _CITAS_PLAN:
        # Clave de idempotencia: cada fila del plan usa una subespecialidad
        # distinta para este cliente.
        cita = CitaAsesoria.objects.filter(cliente=cliente, subespecialidad=subesp).first()
        es_nueva = cita is None

        if cita is not None:
            # Si su franja quedó en el pasado (sembrada hace días), se
            # REUBICA a la siguiente franja futura libre del área: así basta
            # re-ejecutar el seed la mañana de la demo para ver todos los
            # estados vigentes. No toca otras citas fuera del plan.
            if cita.franja.area == area and cita.franja.fin > timezone.now() and cita.franja.activa:
                continue
            nueva = _siguiente_franja_libre(area, cliente)
            if nueva is None:
                continue
            cita.franja = nueva
            if asignacion:
                docente_email, estudiante_email = asignacion
                cita.docente_asignado = CustomUser.objects.get(email=_ASIG[docente_email])
                cita.estudiante_apoyo = (
                    CustomUser.objects.get(email=_ASIG[estudiante_email])
                    if estudiante_email else None)
                cita.estado = estado_base or CitaAsesoria.Estado.ASIGNADA
            if cierre:
                # finalizada conserva resumen/calificación ya registrados
                cita.estado = CitaAsesoria.Estado.FINALIZADA
            elif not asignacion:
                cita.estado = CitaAsesoria.Estado.SOLICITADA
            cita.full_clean()
            cita.save()
            reubicadas += 1
            continue

        franja = _franja_futura(area, usadas[area])
        usadas[area] += 1

        cita = CitaAsesoria(
            franja=franja,
            cliente=cliente,
            asunto=f'Asesoría demo ({subesp}) — caso de demostración CITI',
            subespecialidad=subesp,
            tipo_servicio=tipo,
            estado=CitaAsesoria.Estado.SOLICITADA,
        )
        if asignacion:
            docente_email, estudiante_email = asignacion
            cita.docente_asignado = CustomUser.objects.get(email=_ASIG[docente_email])
            if estudiante_email:
                cita.estudiante_apoyo = CustomUser.objects.get(email=_ASIG[estudiante_email])
            cita.estado = estado_base or CitaAsesoria.Estado.ASIGNADA
        if cierre:
            estado, calificacion, comentario = cierre
            cita.estado = estado
            cita.resumen_cierre = (
                'Sesión completada: diagnóstico, propuesta técnica y acuerdos de '
                'seguimiento documentados en el acta del CITI.'
            )
            cita.calificacion = calificacion
            cita.comentario_cliente = comentario
        cita.full_clean()
        cita.save()
        if asignacion and asignacion[1]:
            NotaBitacora.objects.get_or_create(
                cita=cita,
                autor=cita.estudiante_apoyo,
                texto='Bitácora de demostración: levantamiento inicial de '
                      'requerimientos completado con el cliente.',
            )
        creadas += 1
    return creadas, reubicadas


def _ajuste_temporal_demo():
    """Da a las citas del plan una línea de tiempo de demo coherente,
    EXPLÍCITAMENTE etiquetada como simulación.

    Solo actúa sobre citas del cliente demo del plan que aún no tienen eventos
    (idempotente; nunca reescribe historiales ya registrados ni citas de otros
    clientes). Los eventos creados describen la acción real hecha por el seed
    y sus fechas se retroceden con update() para el relato de demo.
    """
    now = timezone.now()
    cliente = CustomUser.objects.filter(email='cliente@empresatolima.co').first()
    if cliente is None:
        return 0

    ajustes = 0
    guion = (12, 11, 9, 7, 6, 5, 3)  # días atrás por fila del plan
    for idx, (area, subesp, tipo, asignacion, cierre, estado_base) in enumerate(_CITAS_PLAN):
        cita = CitaAsesoria.objects.filter(cliente=cliente, subespecialidad=subesp).first()
        if cita is None or cita.eventos.exists():
            continue
        atras = guion[idx % len(guion)]
        creada = now - timedelta(days=atras, hours=2)
        CitaAsesoria.objects.filter(pk=cita.pk).update(creada_en=creada)
        cita.refresh_from_db()

        def ev(tipo_ev, offset_d, desc, anterior='', nuevo='', update_fields=None):
            evento = registrar_evento(cita, None, tipo_ev,
                                      descripcion=f'{desc} (simulación seed_demo)',
                                      anterior=anterior or cita.estado,
                                      nuevo=nuevo or cita.estado)
            CitaEvento.objects.filter(pk=evento.pk).update(
                fecha=creada + timedelta(days=offset_d))
            actor = _actor_para(tipo_ev, cita)
            if actor:
                CitaEvento.objects.filter(pk=evento.pk).update(
                    usuario_id=actor.pk, actor_label=actor.email)
            return evento

        actor_cli = cita.cliente
        ev(CitaEvento.Tipo.CREADA, 0, 'Reserva registrada por el cliente.',
           anterior='', nuevo=CitaAsesoria.Estado.SOLICITADA)
        CitaEvento.objects.filter(cita=cita, tipo=CitaEvento.Tipo.CREADA).update(
            usuario_id=actor_cli.pk, actor_label=actor_cli.email)
        coord = CustomUser.objects.filter(
            role=Role.COORDINADOR,
            area=(Area.SISTEMAS if area == 'sistemas' else Area.CIVIL)).first()
        ev(CitaEvento.Tipo.REVISADA, 1, 'La solicitud aparece en la bandeja del coordinador.',
           anterior=CitaAsesoria.Estado.SOLICITADA)
        if asignacion:
            docente_email, estudiante_email = asignacion
            docente = CustomUser.objects.get(email=_ASIG[docente_email])
            ev(CitaEvento.Tipo.DOCENTE_ASIGNADO, 2,
               f'Docente responsable: {docente.nombre_completo}',
               anterior=CitaAsesoria.Estado.SOLICITADA)
            if estudiante_email:
                est = CustomUser.objects.get(email=_ASIG[estudiante_email])
                ev(CitaEvento.Tipo.TUTOR_ASIGNADO, 2,
                   f'Tutor de apoyo: {est.nombre_completo}',
                   anterior=CitaAsesoria.Estado.SOLICITADA)
            asig = creada + timedelta(days=2, hours=1)
            cita.asignada_en = asig
            cita.estado = estado_base or CitaAsesoria.Estado.ASIGNADA
            cita.save(update_fields=['asignada_en', 'estado'])
            ev(CitaEvento.Tipo.ASIGNADA, 2, 'Asignación registrada por coordinación.',
               anterior=CitaAsesoria.Estado.SOLICITADA, nuevo=CitaAsesoria.Estado.ASIGNADA)
        if estado_base == CitaAsesoria.Estado.EN_PROCESO or cierre:
            cita.estado = CitaAsesoria.Estado.EN_PROCESO
            cita.save(update_fields=['estado'])
            ev(CitaEvento.Tipo.INICIADA, 3, 'Asesoría iniciada por el docente.',
               anterior=CitaAsesoria.Estado.ASIGNADA, nuevo=CitaAsesoria.Estado.EN_PROCESO)
        if cierre:
            estado, calificacion, comentario = cierre
            cita.estado = estado
            cita.cerrada_en = creada + timedelta(days=5)
            cita.save(update_fields=['estado', 'cerrada_en'])
            ev(CitaEvento.Tipo.FINALIZADA, 5, 'Asesoría finalizada con resumen de cierre.',
               anterior=CitaAsesoria.Estado.EN_PROCESO, nuevo=estado)
            ev(CitaEvento.Tipo.ACTA_REGISTRADA, 5.2,
               'Acta de cierre emitida por el docente responsable.',
               anterior=estado, nuevo=estado)
            ev(CitaEvento.Tipo.FEEDBACK, 6,
               f'Valoración del cliente: {calificacion}/5.',
               anterior=estado, nuevo=estado, )
            CitaEvento.objects.filter(cita=cita, tipo=CitaEvento.Tipo.FEEDBACK).update(
                usuario_id=actor_cli.pk, actor_label=actor_cli.email)
        ajustes += 1
    return ajustes


def _actor_para(tipo_ev, cita):
    """Responsable plausible de cada evento de demo según el tipo."""
    if tipo_ev in (CitaEvento.Tipo.REVISADA, CitaEvento.Tipo.DOCENTE_ASIGNADO,
                   CitaEvento.Tipo.TUTOR_ASIGNADO, CitaEvento.Tipo.ASIGNADA):
        return CustomUser.objects.filter(
            role=Role.COORDINADOR,
            area=(Area.SISTEMAS if cita.franja.area == Area.SISTEMAS else Area.CIVIL)).first()
    if tipo_ev in (CitaEvento.Tipo.INICIADA, CitaEvento.Tipo.FINALIZADA,
                   CitaEvento.Tipo.ACTA_REGISTRADA, CitaEvento.Tipo.BITACORA):
        return cita.docente_asignado
    return None


def _simular_interacciones_demo():
    """Interacciones de demostración (Fase 04) EXPLÍCITAMENTE simuladas.

    Solo citas del plan del seed con timeline ya sembrada y SIN
    interacciones previas (idempotente). Cada texto va etiquetado como
    simulación y las fechas se retro-proyectan con update() para que la
    correlación entrega→decisión (pendiente/aprobada/ajustes) sea coherente
    con la línea de tiempo de la cita."""
    created = 0
    cliente = CustomUser.objects.filter(email='cliente@empresatolima.co').first()
    if cliente is None:
        return 0

    def _sim(inter, fecha):
        CitaInteraccion.objects.filter(pk=inter.pk).update(fecha=fecha)

    def _ev_interaccion(cita, autor, inter, fecha, desc):
        evento = registrar_evento(cita, autor, CitaEvento.Tipo.INTERACCION,
                                  descripcion=f'{desc} (simulación seed_demo)',
                                  anterior=cita.estado, nuevo=cita.estado,
                                  metadata={'interaccion_id': inter.pk})
        CitaEvento.objects.filter(pk=evento.pk).update(
            fecha=fecha,
            actor_label=(autor.email if autor else 'sistema'),
            usuario_id=autor.pk if autor else None)
        return evento

    def _ev_simple(cita, autor, tipo_ev, fecha, desc):
        evento = registrar_evento(cita, autor, tipo_ev,
                                  descripcion=f'{desc} (simulación seed_demo)',
                                  anterior=cita.estado, nuevo=cita.estado)
        CitaEvento.objects.filter(pk=evento.pk).update(
            fecha=fecha,
            actor_label=(autor.email if autor else 'sistema'),
            usuario_id=autor.pk if autor else None)
        return evento

    for subesp, guion in _INTERACCIONES_GUIÓN.items():
        cita = CitaAsesoria.objects.filter(cliente=cliente, subespecialidad=subesp).first()
        if cita is None or cita.interacciones.exists():
            continue
        if not (cita.docente_asignado_id or cita.estudiante_apoyo_id):
            continue  # sin responsable no hay narración de comunicación honesta
        if not cita.eventos.filter(descripcion__icontains='simulación seed_demo').exists():
            continue
        base = (cita.asignada_en or cita.creada_en) + timedelta(hours=6)
        autor_equipo = cita.docente_asignado or cita.estudiante_apoyo
        for offset, rol, tipo, texto, ficha in guion:
            fecha = base + timedelta(days=offset)
            quien = cliente if rol == 'cliente' else autor_equipo
            inter = registrar_interaccion(cita, quien, tipo,
                                          texto + ' (simulación seed_demo)',
                                          datos_extra=ficha)
            _sim(inter, fecha)
            _ev_interaccion(cita, quien, inter, fecha, inter.get_tipo_display())
            if tipo == CitaInteraccion.Tipo.ENTREGA_RESULTADOS:
                _ev_simple(cita, autor_equipo, CitaEvento.Tipo.ENTREGA_PUBLICADA,
                           fecha, f'Se publicó el entregable "{(ficha or {}).get("titulo", "Entrega")}" para revisión del cliente.')
            elif tipo == CitaInteraccion.Tipo.APROBACION:
                _ev_simple(cita, cliente, CitaEvento.Tipo.DECISION_CLIENTE,
                           fecha, 'El cliente aprobó el entregable.')
            elif tipo == CitaInteraccion.Tipo.RECHAZO_AJUSTE:
                _ev_simple(cita, cliente, CitaEvento.Tipo.DECISION_CLIENTE,
                           fecha, 'El cliente rechazó el entregable y solicitó correcciones.')
            created += 1
    return created


# Guión de interacciones por subespecialidad del plan. Tuplas:
# (días desde asignación, 'cliente'|'equipo', Tipo, texto, ficha|None)
_INTERACCIONES_GUIÓN = {
    'vias': (  # civil, en proceso: entrega pendiente de aprobación
        (1, 'equipo', CitaInteraccion.Tipo.OBSERVACION,
         'Revisamos los planos de la vía: faltan perfiles de rasante en dos tramos.', None),
        (2, 'equipo', CitaInteraccion.Tipo.ENTREGA_RESULTADOS,
         'Primer avance de interventoría con observaciones puntuadas por tramo.',
         {'titulo': 'Avance 1 — revisión de planos',
          'diagnostico': 'Divergencias entre rasante de diseño y terreno en los tramos 2 y 4.',
          'alcance': 'Revisión documental y recomendaciones para la interventoría.',
          'metodologia': 'Revisión en escritorio + checklist normativo (INV-2022).'}),
        (3, 'cliente', CitaInteraccion.Tipo.RESPUESTA,
         'Recibido. ¿Incluye también el estudio de drenaje del tramo 3?', None),
    ),
    'ciber': (  # sistemas, finalizada: entrega aprobada por el cliente
        (1, 'equipo', CitaInteraccion.Tipo.ENTREGA_RESULTADOS,
         'Informe con hallazgos de vulnerabilidad y plan de remediación priorizado.',
         {'titulo': 'Informe de diagnóstico de seguridad',
          'diagnostico': 'Se identificaron 3 vulnerabilidades críticas en el perímetro.',
          'alcance': 'Diagnóstico y recomendaciones; no incluye implementación.',
          'entregables': 'Informe técnico + matriz de riesgos + plan de remediación.'}),
        (2, 'cliente', CitaInteraccion.Tipo.APROBACION,
         'Aprobamos el informe; la severidad de los hallazgos coincide con lo observado.', None),
    ),
    'estructuras': (  # civil, finalizada: entregable rechazado -> ajustes -> aprobado
        (1, 'equipo', CitaInteraccion.Tipo.ENTREGA_RESULTADOS,
         'Propuesta preliminar de reforzamiento de losas.',
         {'titulo': 'Propuesta de reforzamiento',
          'metodologia': 'Análisis teórico con normas sismorresistentes NSR-10.'}),
        (2, 'cliente', CitaInteraccion.Tipo.RECHAZO_AJUSTE,
         'Falta considerar la carga de maquinaria pesada del piso 2; solicitamos ajuste.', None),
        (3, 'equipo', CitaInteraccion.Tipo.ENTREGA_RESULTADOS,
         'Versión 2 de la propuesta incluyendo las cargas de maquinaria indicadas.',
         {'titulo': 'Propuesta de reforzamiento — v2',
          'alcance': 'Ahora con combinación de cargas por maquinaria pesada.'}),
        (4, 'cliente', CitaInteraccion.Tipo.APROBACION,
         'Aprobada la v2; procede con el detalle en obra.', None),
    ),
    'redes': (  # sistemas, asignada: solo comunicación temprana
        (1, 'equipo', CitaInteraccion.Tipo.OBSERVACION,
         'Para la sesión necesitamos el inventario de equipos de red y el topológico actual.', None),
    ),
    'bd': (  # sistemas, asignada: nota interna (no visible al cliente)
        (1, 'equipo', CitaInteraccion.Tipo.NOTA_INTERNA,
         'El cliente reporta base lenta en reportes mensuales; presuponer índices faltantes.', None),
    ),
}


def seed_all():
    """Orquestador del seed explícito (lo invoca `manage.py seed_demo`)."""
    ensure_demo_users()
    archivadas, canceladas = archive_vencidas()
    franjas_nuevas = ensure_demo_franjas()
    citas_nuevas, citas_reubicadas = ensure_demo_citas()
    trazabilidad_simulada = _ajuste_temporal_demo()
    interacciones_nuevas = _simular_interacciones_demo()
    return {
        'archivadas': archivadas,
        'canceladas': canceladas,
        'franjas_nuevas': franjas_nuevas,
        'citas_nuevas': citas_nuevas,
        'citas_reubicadas': citas_reubicadas,
        'trazabilidad_simulada': trazabilidad_simulada,
        'interacciones_nuevas': interacciones_nuevas,
    }
