"""Servicios de triage de solicitudes públicas (Fase 05).

Toda escritura del intake pasa por aquí, dentro de `transaction.atomic`, para
que bandeja, cita e historial queden consistentes. Las vistas solo orquestan y
traducen los errores a mensajes; no duplican reglas.

Principio: la solicitud pública NO crea citas por sí sola. `CitaAsesoria`
mantiene su `cliente` obligatorio y su `clean()` intactos.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import Area, CustomUser, Empresa, Role
from scheduling.models import (
    LINEA_A_TIPO_SERVICIO, CitaAsesoria, CitaEvento, FranjaHoraria,
    LineaAtencion, SolicitudPublica, TipoServicio,
)
from scheduling.subespecialidades import Subespecialidad
from scheduling.trazabilidad import asignar_cita, registrar_evento

# Un coordinador solo puede aprobar/convertir en su propia área o en solicitudes
# que aún no declaran área (MIXTO = "no estoy seguro").
AREAS_ACADEMICAS = (Area.SISTEMAS, Area.CIVIL)


def area_de(user):
    """Área impuesta al coordinador; None para el director (alcance global)."""
    if user.role == Role.COORDINADOR and user.area in AREAS_ACADEMICAS:
        return user.area
    return None


def solicitudes_visibles(user):
    """Alcance en SERVIDOR: el coordinador nunca ve el área ajena."""
    qs = SolicitudPublica.objects.select_related(
        'cliente', 'cita', 'taller', 'revisada_por', 'aprobada_por')
    area = area_de(user)
    if area:
        return qs.filter(Q(area=area) | Q(area=Area.MIXTO))
    return qs


def tiene_acceso(user, solicitud):
    area = area_de(user)
    if not area:
        return True
    return solicitud.area in (area, Area.MIXTO)


def _validar_transicion(solicitud, nuevo):
    if not SolicitudPublica.transicion_legal(solicitud.estado, nuevo):
        raise ValidationError(
            f'La solicitud {solicitud.codigo} no puede pasar de '
            f'"{solicitud.get_estado_display()}" a "{dict(SolicitudPublica.Estado.choices)[nuevo]}".')


def marcar_en_revision(solicitud, actor):
    """Deja constancia de que el triage la abrió. Idempotente."""
    if solicitud.estado != SolicitudPublica.Estado.RECIBIDA:
        return solicitud
    _validar_transicion(solicitud, SolicitudPublica.Estado.EN_REVISION)
    solicitud.estado = SolicitudPublica.Estado.EN_REVISION
    solicitud.revisada_por = actor
    solicitud.revisada_en = timezone.now()
    solicitud.save()
    return solicitud


def aprobar_solicitud(solicitud, actor, linea_atencion, area, subespecialidad='',
                      observaciones=''):
    """Aprueba el alcance y fija la clasificación. No crea cita todavía.

    Los talleres quedan aprobados aquí (no se convierten). Asesorías y
    consultorías quedan listas para `convertir_solicitud`.
    """
    _validar_transicion(solicitud, SolicitudPublica.Estado.APROBADA)

    if area not in AREAS_ACADEMICAS:
        raise ValidationError('Debes clasificar la solicitud en un área académica concreta.')

    area_actor = area_de(actor)
    if area_actor and area != area_actor:
        raise ValidationError('Solo puedes aprobar solicitudes de tu propia área.')
    if not tiene_acceso(actor, solicitud):
        raise ValidationError('La solicitud pertenece a otra área.')

    if linea_atencion not in dict(LineaAtencion.choices):
        raise ValidationError('Selecciona una línea de atención válida.')

    if subespecialidad and not Subespecialidad.valid_for_area(subespecialidad, area):
        raise ValidationError(
            {'subespecialidad': 'La subespecialidad no corresponde al área elegida.'})

    solicitud.linea_atencion = linea_atencion
    solicitud.area = area
    solicitud.subespecialidad = subespecialidad
    if observaciones:
        solicitud.observaciones_internas = observaciones
    solicitud.estado = SolicitudPublica.Estado.APROBADA
    solicitud.aprobada_por = actor
    solicitud.aprobada_en = timezone.now()
    if not solicitud.revisada_por_id:
        solicitud.revisada_por = actor
        solicitud.revisada_en = solicitud.aprobada_en
    solicitud.full_clean()
    solicitud.save()
    return solicitud


def rechazar_solicitud(solicitud, actor, motivo):
    motivo = (motivo or '').strip()
    if not motivo:
        raise ValidationError('Indica el motivo del rechazo (queda en el radicado).')
    _validar_transicion(solicitud, SolicitudPublica.Estado.RECHAZADA)
    if not tiene_acceso(actor, solicitud):
        raise ValidationError('La solicitud pertenece a otra área.')
    solicitud.estado = SolicitudPublica.Estado.RECHAZADA
    solicitud.motivo_rechazo = motivo
    solicitud.save()
    return solicitud


def _empresa_para(solicitud):
    """Empresa del cliente. El NIT vacío se reemplaza por un placeholder legible.

    `Empresa.nit` no tiene validador de formato hoy, pero se deja explícito
    para que quede claro en admin que el dato está pendiente de completar.
    """
    nit = (solicitud.nit or '').strip()
    if nit:
        existente = Empresa.objects.filter(nit=nit).first()
        if existente:
            return existente
    placeholder = nit or f'PENDIENTE-{solicitud.codigo[-8:].upper()}'
    return Empresa.objects.create(
        razon_social=solicitud.organizacion[:200],
        nit=placeholder[:20],
        telefono=solicitud.telefono[:30],
        sector=solicitud.get_tipo_solicitante_display()[:100],
    )


def vincular_cliente(solicitud):
    """Vincula el cliente existente por email o crea uno inactivo.

    Si el correo ya pertenece a un usuario que no es Cliente (docente,
    estudiante...), NO se reutiliza: se informa para que el triage resuelva el
    caso manualmente. Crear un duplicado rompería el `unique` del email.
    """
    if solicitud.cliente_id:
        return solicitud.cliente

    existente = CustomUser.objects.filter(email=solicitud.email).first()
    if existente:
        if existente.role != Role.CLIENTE:
            raise ValidationError(
                f'El correo {solicitud.email} ya pertenece a una cuenta con rol '
                f'{existente.get_role_display()}. Usa otro correo de contacto o '
                f'gestiona la cuenta en /admin/.')
        solicitud.cliente = existente
        solicitud.save()
        return existente

    partes = solicitud.nombre_contacto.strip().split()
    empresa = _empresa_para(solicitud)
    cliente = CustomUser(
        email=solicitud.email,
        first_name=partes[0][:120] if partes else 'Contacto',
        last_name=' '.join(partes[1:])[:120] if len(partes) > 1 else '',
        role=Role.CLIENTE,
        empresa=empresa,
        is_active=False,
    )
    cliente.set_unusable_password()
    cliente.save()  # full_clean interno: exige empresa y email único
    solicitud.cliente = cliente
    solicitud.save()
    return cliente


def franjas_candidatas(solicitud):
    """Franjas futuras con cupo en el área ya aprobada."""
    return (FranjaHoraria.objects
            .filter(activa=True, area=solicitud.area, inicio__gt=timezone.now())
            .order_by('inicio'))


def convertir_solicitud(solicitud, actor, franja, docente=None, estudiante=None):
    """Convierte una solicitud aprobada en `CitaAsesoria` + la asigna si aplica.

    Todo ocurre en una transacción con bloqueo de la solicitud y de la franja,
    para que dos triages simultáneos no creen dos citas ni sobrevendan cupo.
    """
    with transaction.atomic():
        # Sin select_related: PostgreSQL no permite FOR UPDATE sobre el lado
        # nullable de un LEFT OUTER JOIN (cliente y taller son nullable).
        fresh = (SolicitudPublica.objects
                 .select_for_update()
                 .get(pk=solicitud.pk))

        if fresh.cita_id or fresh.estado == SolicitudPublica.Estado.CONVERTIDA:
            raise ValidationError('Esta solicitud ya fue convertida en una cita.')
        if fresh.es_taller:
            raise ValidationError(
                'Una capacitación no se convierte en cita: se aprueba y se agenda '
                'directamente con la organización.')
        if fresh.estado != SolicitudPublica.Estado.APROBADA:
            raise ValidationError(
                'Primero aprueba el alcance de la solicitud antes de convertirla.')
        if not tiene_acceso(actor, fresh):
            raise ValidationError('La solicitud pertenece a otra área.')

        franja = FranjaHoraria.objects.select_for_update().get(pk=franja.pk)
        if franja.area != fresh.area:
            raise ValidationError(
                f'La franja pertenece a {franja.get_area_display()} y la solicitud '
                f'fue clasificada en {dict(Area.choices)[fresh.area]}.')
        if not franja.esta_disponible:
            raise ValidationError('La franja seleccionada ya no tiene cupo disponible.')

        area_actor = area_de(actor)
        if area_actor and franja.area != area_actor:
            raise ValidationError('Solo puedes convertir solicitudes de tu área.')

        cliente = vincular_cliente(fresh)
        linea = fresh.linea_atencion or SolicitudPublica.linea_para(fresh.tipo_necesidad)
        tipo_servicio = LINEA_A_TIPO_SERVICIO.get(
            linea, TipoServicio.ORIENTACION_TECNICA)

        cita = CitaAsesoria(
            franja=franja,
            cliente=cliente,
            asunto=f'{fresh.get_tipo_necesidad_display()} — {fresh.organizacion}'[:255],
            subespecialidad=fresh.subespecialidad,
            tipo_servicio=tipo_servicio,
            linea_atencion=linea,
            estado=CitaAsesoria.Estado.SOLICITADA,
        )
        cita.full_clean()
        cita.save()
        registrar_evento(
            cita, actor, CitaEvento.Tipo.CREADA,
            descripcion=f'Creada desde la solicitud pública {fresh.codigo} '
                        f'({fresh.get_tipo_solicitante_display()}).',
            metadata={'solicitud_codigo': fresh.codigo, 'solicitud_id': fresh.pk},
        )

        if docente or estudiante:
            asignar_cita(
                cita, actor, docente, estudiante,
                descripcion=f'Asignación al convertir la solicitud {fresh.codigo}.')

        fresh.cita = cita
        fresh.cliente = cliente
        fresh.estado = SolicitudPublica.Estado.CONVERTIDA
        fresh.convertida_en = timezone.now()
        fresh.save()
        return cita
