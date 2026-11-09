"""Registro centralizado de trazabilidad (Fase 03, Módulo C).

Toda mutación relevante de una CitaAsesoria pasa por aquí, de modo que el
estado, sus marcas temporales y el evento histórico queden consistentes y en
la misma transacción. Si la operación falla, no se registra evento de éxito.

Diseño: funciones llamadas explícitamente desde vistas/API/admin (no señales
globales) para evitar eventos duplicados o fuera de orden.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import Role
from scheduling.models import CitaAsesoria, CitaEvento, CitaInteraccion, TipoServicio


def registrar_evento(cita, actor, tipo, descripcion='', anterior=None, nuevo=None,
                     metadata=None):
    """Crea un CitaEvento. actor puede ser None (sistema/seed)."""
    return CitaEvento.objects.create(
        cita=cita,
        usuario=actor if getattr(actor, 'pk', None) else None,
        actor_label=(getattr(actor, 'email', '') or str(actor) if actor else 'sistema'),
        tipo=tipo,
        estado_anterior=anterior if anterior is not None else (cita.estado),
        estado_nuevo=nuevo if nuevo is not None else cita.estado,
        descripcion=descripcion,
        metadata=metadata,
    )


def cambio_estado(cita, usuario, nuevo_estado, descripcion=''):
    """Aplica un cambio de estado LEGÍTIMO + evento + marcas temporales.

    Debe llamarse DENTRO de transaction.atomic del flujo que corresponda.
    Devuelve False si el estado ya era igual (no registra nada).
    Levanta ValidationError si la transición no está en la tabla formal
    (I-2, Fase 04): si falla, la transacción revierta y no queda evento."""
    anterior = cita.estado
    if anterior == nuevo_estado:
        return False
    if not CitaAsesoria.transicion_legal(anterior, nuevo_estado):
        raise ValidationError(
            f"Transición no permitida: {anterior} → {nuevo_estado}.")
    cita.estado = nuevo_estado
    if nuevo_estado == CitaAsesoria.Estado.ASIGNADA and not cita.asignada_en:
        cita.asignada_en = timezone.now()
    if nuevo_estado == CitaAsesoria.Estado.FINALIZADA:
        cita.cerrada_en = timezone.now()
    if nuevo_estado == CitaAsesoria.Estado.CANCELADA:
        cita.cerrada_en = None
    cita.full_clean()
    cita.save()

    tipo = {
        CitaAsesoria.Estado.ASIGNADA: CitaEvento.Tipo.ASIGNADA,
        CitaAsesoria.Estado.EN_PROCESO: CitaEvento.Tipo.INICIADA,
        CitaAsesoria.Estado.FINALIZADA: CitaEvento.Tipo.FINALIZADA,
        CitaAsesoria.Estado.CANCELADA: CitaEvento.Tipo.CANCELADA,
    }.get(nuevo_estado, CitaEvento.Tipo.ESTADO_CAMBIADO)
    registrar_evento(cita, usuario, tipo, descripcion=descripcion,
                     anterior=anterior, nuevo=nuevo_estado)
    return True


def eventos_de(cita):
    return cita.eventos.select_related('usuario').all().order_by('fecha', 'id')


def asignar_cita(cita, usuario, docente, estudiante, descripcion=''):
    """Asignación coordinador: eventos de responsable + transición ASIGNADA.

    Llamar dentro de transaction.atomic(). Devuelve True si la cita quedó
    asignada; False si ya no estaba pendiente."""
    if docente:
        cita.docente_asignado = docente
    if estudiante:
        cita.estudiante_apoyo = estudiante
    # I-6 (Fase 04): una consultoría especializada no puede asignarse sin
    # docente responsable; el modelo lo refuerza en clean() al persistir.
    if (cita.tipo_servicio == TipoServicio.CONSULTORIA_ESPECIALIZADA
            and not cita.docente_asignado_id):
        raise ValidationError(
            'Las consultorías especializadas requieren un docente asesor como '
            'responsable. Asigne el docente para continuar.')
    if docente:
        registrar_evento(cita, usuario, CitaEvento.Tipo.DOCENTE_ASIGNADO,
                        descripcion=f'Docente responsable: {docente.nombre_completo}',
                        anterior=cita.estado, nuevo=cita.estado)
    if estudiante:
        registrar_evento(cita, usuario, CitaEvento.Tipo.TUTOR_ASIGNADO,
                        descripcion=f'Tutor de apoyo: {estudiante.nombre_completo}',
                        anterior=cita.estado, nuevo=cita.estado)
    return cambio_estado(cita, usuario, CitaAsesoria.Estado.ASIGNADA,
                         descripcion=descripcion or 'Asignación registrada por coordinación')


def nota_asignacion(cita, usuario):
    """Marca 'Solicitud revisada' sin duplicar si el coordinador ya la revisó."""
    ya_revisada = cita.eventos.filter(
        tipo=CitaEvento.Tipo.REVISADA, usuario=usuario).exists()
    if ya_revisada:
        return None
    return registrar_evento(cita, usuario, CitaEvento.Tipo.REVISADA,
                            descripcion='La solicitud aparece en la bandeja del coordinador.',
                            anterior=cita.estado, nuevo=cita.estado)


def auditar_guardado_form(cita, usuario, anterior_estado, anterior_apoyo_id):
    """Normaliza marcas/eventos tras un ModelForm.save() del portal.

    El formulario ya guardó; aquí detectamos diferencias reales y registramos
    (estado gestionado, tutor reasignado). Si la cita está finalizada sin
    marca de cierre, se completa (aunque el estado no haya cambiado)."""
    if cita.estudiante_apoyo_id != anterior_apoyo_id and cita.estudiante_apoyo_id:
        registrar_evento(cita, usuario, CitaEvento.Tipo.TUTOR_ASIGNADO,
                         descripcion=f'Tutor de apoyo: {cita.estudiante_apoyo.nombre_completo}',
                         anterior=cita.estado, nuevo=cita.estado)
    if cita.estado == CitaAsesoria.Estado.FINALIZADA and not cita.cerrada_en:
        cita.cerrada_en = timezone.now()
        cita.save(update_fields=['cerrada_en'])
    if cita.estado != anterior_estado:
        if cita.estado == CitaAsesoria.Estado.ASIGNADA and not cita.asignada_en:
            cita.asignada_en = timezone.now()
            cita.save(update_fields=['asignada_en'])
        registrar_evento(cita, usuario, CitaEvento.Tipo.ESTADO_CAMBIADO,
                         descripcion='Cambio de estado desde la gestión del caso.',
                         anterior=anterior_estado, nuevo=cita.estado)


# ---------------------------------------------------------------------------
# Fase 04 — interacciones, entregables y decisiones del cliente.
# Toda escritura de CitaInteraccion pasa por aquí, SIEMPRE dentro de
# transaction.atomic del flujo llamador (comentario + evento atómicos).


def registrar_interaccion(cita, autor, tipo, texto, datos_extra=None):
    """Crea la interacción + su evento espejo. No cambia el estado.

    Las notas internas crean un evento MARCADO como privado: el texto no se
    copia a la descripción (no filtraría contenido al historial que lee el
    cliente) y el partial lo oculta a roles distintos del equipo."""
    interna = tipo == CitaInteraccion.Tipo.NOTA_INTERNA
    inter = CitaInteraccion(
        cita=cita, autor=autor, rol_autor=autor.role, tipo=tipo,
        texto=texto, datos_extra=datos_extra)
    inter.full_clean()
    inter.save()
    if interna:
        desc = 'Nota técnica interna registrada por el equipo (contenido privado).'
    else:
        desc = f'{inter.get_tipo_display()}: {texto[:180]}'
    registrar_evento(
        cita, autor, CitaEvento.Tipo.INTERACCION,
        descripcion=desc,
        anterior=cita.estado, nuevo=cita.estado,
        metadata={'interaccion_id': inter.pk, 'tipo_interaccion': tipo,
                  'privada': True if interna else None})
    return inter


def publicar_entrega(cita, autor, titulo, contenido, ficha=None):
    """Publica una entrega de resultados visible al cliente + evento.

    `ficha`: campos estructurados de consultoría (diagnostico, alcance,
    metodologia, entregables, objetivos); opcional por diseño."""
    datos = dict(ficha or {})
    datos['titulo'] = titulo
    inter = registrar_interaccion(cita, autor, CitaInteraccion.Tipo.ENTREGA_RESULTADOS,
                                  contenido, datos_extra=datos)
    registrar_evento(
        cita, autor, CitaEvento.Tipo.ENTREGA_PUBLICADA,
        descripcion=f'Se publicó el entregable "{titulo}" para revisión del cliente.',
        anterior=cita.estado, nuevo=cita.estado,
        metadata={'interaccion_id': inter.pk})
    return inter


def registrar_decision_cliente(cita, cliente, aprobar, observacion=''):
    """Aprobación o solicitud de ajustes sobre la entrega pendiente.

    Reglas (brief Fase 04):
    - No se puede decidir sin entrega pendiente.
    - Aprobar NO finaliza administrativamente la solicitud: el estado no se
      toca en ese camino.
    - Con ajustes, si el caso estaba finalizado, vuelve a 'en_proceso'
      (única arista de reapertura de la tabla I-2) para regresar al flujo
      operativo; en cualquier otro estado activo el estado se conserva.
    Debe llamarse dentro de transaction.atomic()."""
    entrega = cita.entrega_pendiente
    if entrega is None:
        raise ValidationError(
            'No hay un entregable pendiente de aprobación para esta solicitud.')
    tipo = (CitaInteraccion.Tipo.APROBACION if aprobar
            else CitaInteraccion.Tipo.RECHAZO_AJUSTE)
    reopened = False
    if not aprobar and cita.estado == CitaAsesoria.Estado.FINALIZADA:
        reopened = cambio_estado(
            cita, cliente, CitaAsesoria.Estado.EN_PROCESO,
            descripcion='Reapertura por ajuste solicitado por el cliente.')
    decision = registrar_interaccion(cita, cliente, tipo,
                                     observacion or ('Entregable aprobado.'
                                                     if aprobar else
                                                     'Se solicitan ajustes al entregable.'))
    registrar_evento(
        cita, cliente, CitaEvento.Tipo.DECISION_CLIENTE,
        descripcion=('El cliente aprobó el entregable.' if aprobar else
                     'El cliente rechazó el entregable y solicitó correcciones.'
                     + (' El caso regresó a "En proceso".' if reopened else '')),
        anterior=cita.estado, nuevo=cita.estado,
        metadata={'interaccion_id': decision.pk, 'aprobada': aprobar,
                  'entrega_id': entrega.pk})
    return decision


def interacciones_visibles(qs, user):
    """Filtro de visibilidad aplicado en SERVIDOR (nunca en el frontend)."""
    if user.role == Role.CLIENTE:
        return qs.filter(Q(para_cliente=True) | Q(autor_id=user.pk))
    if user.role in (Role.DOCENTE, Role.ESTUDIANTE, Role.COORDINADOR, Role.DIRECTOR):
        return qs
    return qs.none()
