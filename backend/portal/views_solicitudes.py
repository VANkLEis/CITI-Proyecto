"""Triage privado de solicitudes públicas (Fase 05).

Acceso: Director (global) y Coordinador (su área o MIXTO). El alcance se aplica
en servidor con `scheduling.solicitudes.solicitudes_visibles`; una solicitud de
otra área responde 404, igual que el resto de recursos del portal.
"""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import Area, Role
from portal.decorators import role_required
from portal.forms_public import (
    AprobarSolicitudForm,
    ConvertirSolicitudForm,
    RechazarSolicitudForm,
)
from scheduling import solicitudes as svc
from scheduling.models import LineaAtencion, SolicitudPublica


def _solicitud_o_404(request, pk):
    return get_object_or_404(svc.solicitudes_visibles(request.user), pk=pk)


def _role_label(user):
    if user.role == Role.DIRECTOR:
        return 'Director CITI'
    if user.area in (Area.SISTEMAS, Area.CIVIL):
        return f'Coordinador — {Area(user.area).label}'
    return 'Coordinador de área'


@role_required(Role.DIRECTOR, Role.COORDINADOR)
def solicitudes_publicas(request):
    qs = svc.solicitudes_visibles(request.user)

    estado = (request.GET.get('estado') or '').strip()
    necesidad = (request.GET.get('tipo') or '').strip()
    linea = (request.GET.get('linea') or '').strip()
    area = (request.GET.get('area') or '').strip()
    busqueda = (request.GET.get('q') or '').strip()

    if estado in dict(SolicitudPublica.Estado.choices):
        qs = qs.filter(estado=estado)
    else:
        estado = ''
    if necesidad in dict(SolicitudPublica.TipoNecesidad.choices):
        qs = qs.filter(tipo_necesidad=necesidad)
    else:
        necesidad = ''
    if linea in dict(LineaAtencion.choices):
        qs = qs.filter(linea_atencion=linea)
    else:
        linea = ''
    if area in (Area.SISTEMAS, Area.CIVIL):
        qs = qs.filter(area=area)
    else:
        area = ''
    if busqueda:
        qs = qs.filter(
            Q(codigo__icontains=busqueda)
            | Q(organizacion__icontains=busqueda)
            | Q(nombre_contacto__icontains=busqueda)
            | Q(email__icontains=busqueda))

    visibles = svc.solicitudes_visibles(request.user)
    conteo = dict(visibles.values_list('estado').annotate(n=Count('id'))
                  .values_list('estado', 'n'))

    return render(request, 'portal/panel/solicitudes_list.html', {
        'solicitudes': qs,
        'conteo': conteo,
        'role_label': _role_label(request.user),
        'total_bandeja': sum(conteo.values()),
        'estados': SolicitudPublica.Estado.choices,
        'tipos': SolicitudPublica.TipoNecesidad.choices,
        'lineas': LineaAtencion.choices,
        'areas': [(Area.SISTEMAS, 'Sistemas'), (Area.CIVIL, 'Civil')],
        'f_estado': estado,
        'f_tipo': necesidad,
        'f_linea': linea,
        'f_area': area,
        'q': busqueda,
        'area_actor': svc.area_de(request.user),
    })


def _contexto_detalle(request, solicitud, **overrides):
    es_taller = solicitud.es_taller
    contexto = {
        'solicitud': solicitud,
        'role_label': _role_label(request.user),
        'linea_sugerida': solicitud.linea_sugerida,
        'linea_sugerida_label': dict(LineaAtencion.choices).get(
            solicitud.linea_sugerida, ''),
        'linea_coincide': solicitud.linea_atencion == solicitud.linea_sugerida,
        'accion_sugerida': solicitud.accion_sugerida,
        'form_rechazo': RechazarSolicitudForm(),
        'puede_aprobar': solicitud.es_abierta,
        'puede_convertir': solicitud.puede_convertirse,
        'puede_rechazar': (solicitud.es_abierta
                           or solicitud.estado == SolicitudPublica.Estado.APROBADA),
        'es_taller': es_taller,
    }
    contexto['form_aprobacion'] = overrides.pop(
        'form_aprobacion',
        AprobarSolicitudForm(solicitud=solicitud, actor=request.user,
                             initial=_inicial_aprobacion(solicitud)))
    contexto['form_conversion'] = overrides.pop(
        'form_conversion',
        ConvertirSolicitudForm(solicitud=solicitud) if solicitud.puede_convertirse else None)
    contexto.update(overrides)
    return contexto


def _inicial_aprobacion(solicitud):
    inicial = {}
    if solicitud.area in (Area.SISTEMAS, Area.CIVIL):
        inicial['area'] = solicitud.area
    if solicitud.subespecialidad:
        inicial['subespecialidad'] = solicitud.subespecialidad
    return inicial


@role_required(Role.DIRECTOR, Role.COORDINADOR)
def solicitud_publica_detalle(request, pk):
    solicitud = _solicitud_o_404(request, pk)
    # Abrir la ficha deja constancia de revisión (idempotente, igual que la
    # bandeja de coordinación existente).
    if solicitud.estado == SolicitudPublica.Estado.RECIBIDA:
        try:
            svc.marcar_en_revision(solicitud, request.user)
        except ValidationError:
            pass
    return render(request, 'portal/panel/solicitud_detalle.html',
                  _contexto_detalle(request, solicitud))


@require_POST
@role_required(Role.DIRECTOR, Role.COORDINADOR)
def solicitud_publica_aprobar(request, pk):
    solicitud = _solicitud_o_404(request, pk)
    form = AprobarSolicitudForm(request.POST, solicitud=solicitud, actor=request.user)
    if not form.is_valid():
        return render(request, 'portal/panel/solicitud_detalle.html',
                      _contexto_detalle(request, solicitud, form_aprobacion=form),
                      status=200)
    try:
        svc.aprobar_solicitud(
            solicitud, request.user,
            linea_atencion=form.cleaned_data['linea_atencion'],
            area=form.cleaned_data['area'],
            subespecialidad=form.cleaned_data['subespecialidad'],
            observaciones=form.cleaned_data['observaciones'],
        )
    except ValidationError as exc:
        for mensaje in exc.messages:
            messages.error(request, mensaje)
        return redirect('portal:solicitud_publica_detalle', pk=solicitud.pk)

    if solicitud.es_taller:
        messages.success(
            request,
            f'{solicitud.codigo} aprobada. Es una capacitación: no requiere cita '
            f'en el calendario; coordina la fecha con la organización.')
    else:
        messages.success(
            request,
            f'{solicitud.codigo} aprobada. Ahora puedes convertirla en cita y '
            f'asignar docente y tutor.')
    return redirect('portal:solicitud_publica_detalle', pk=solicitud.pk)


@require_POST
@role_required(Role.DIRECTOR, Role.COORDINADOR)
def solicitud_publica_rechazar(request, pk):
    solicitud = _solicitud_o_404(request, pk)
    form = RechazarSolicitudForm(request.POST)
    if not form.is_valid():
        return render(request, 'portal/panel/solicitud_detalle.html',
                      _contexto_detalle(request, solicitud, form_rechazo=form))
    try:
        svc.rechazar_solicitud(solicitud, request.user, form.cleaned_data['motivo'])
    except ValidationError as exc:
        for mensaje in exc.messages:
            messages.error(request, mensaje)
    else:
        messages.warning(request, f'{solicitud.codigo} rechazada. El motivo quedó registrado.')
    return redirect('portal:solicitud_publica_detalle', pk=solicitud.pk)


@role_required(Role.DIRECTOR, Role.COORDINADOR)
def solicitud_publica_convertir(request, pk):
    solicitud = _solicitud_o_404(request, pk)
    if not solicitud.puede_convertirse:
        messages.error(
            request,
            'Solo se convierten solicitudes aprobadas de asesoría o consultoría.')
        return redirect('portal:solicitud_publica_detalle', pk=solicitud.pk)

    form = ConvertirSolicitudForm(request.POST or None, solicitud=solicitud)
    if request.method == 'POST' and form.is_valid():
        try:
            cita = svc.convertir_solicitud(
                solicitud, request.user,
                franja=form.cleaned_data['franja'],
                docente=form.cleaned_data['docente'],
                estudiante=form.cleaned_data['estudiante'],
            )
        except ValidationError as exc:
            for mensaje in exc.messages:
                messages.error(request, mensaje)
        else:
            messages.success(
                request,
                f'{solicitud.codigo} se convirtió en la cita CITI-{cita.pk:05d}.')
            return redirect('portal:cita_detalle', cita_id=cita.pk)

    if form.errors and not form.non_field_errors():
        for errores in form.errors.values():
            for mensaje in errores:
                messages.error(request, mensaje)

    return render(request, 'portal/panel/solicitud_convertir.html', {
        'solicitud': solicitud,
        'role_label': _role_label(request.user),
        'form': form,
    })
