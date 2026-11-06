from datetime import datetime, time, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from accounts.models import Area, Role
from portal.area_helpers import area_coordinador, filtrar_citas_por_area
from portal.decorators import role_required
from portal.forms import AsignarDocenteForm, DocenteCasoForm, FeedbackClienteForm, NotaBitacoraForm
from scheduling.models import CitaAsesoria, NotaBitacora
from scheduling.subespecialidades import Subespecialidad


def _ensure_demo_franjas_horarias():
    from scheduling.models import FranjaHoraria

    if FranjaHoraria.objects.filter(activa=True).exists():
        return

    tz = timezone.get_current_timezone()
    hoy = timezone.localdate()
    candidatas = []

    for offset in range(7):
        dia = hoy + timedelta(days=offset)
        if dia.weekday() >= 5:
            continue
        for hora_inicio, hora_fin, area in (
            (9, 11, Area.SISTEMAS),
            (14, 16, Area.CIVIL),
        ):
            inicio = timezone.make_aware(datetime.combine(dia, time(hora_inicio, 0)), tz)
            fin = timezone.make_aware(datetime.combine(dia, time(hora_fin, 0)), tz)
            if inicio <= timezone.now():
                continue
            candidatas.append(
                FranjaHoraria(
                    inicio=inicio,
                    fin=fin,
                    area=area,
                    capacidad=2,
                    activa=True,
                )
            )

    if candidatas:
        FranjaHoraria.objects.bulk_create(candidatas[:6])


@login_required
@role_required(Role.DIRECTOR)
def director_dashboard(request):
    from accounts.models import CustomUser
    from scheduling.models import FranjaHoraria

    context = {
        'total_usuarios': CustomUser.objects.count(),
        'franjas_activas': FranjaHoraria.objects.filter(activa=True).count(),
        'citas_reservadas': CitaAsesoria.objects.filter(
            estado__in=CitaAsesoria.Estado.ocupan_cupo()
        ).count(),
        'role_label': 'Director CITI',
    }
    return render(request, 'portal/dashboard_director.html', context)


def landing(request):
    from accounts.demo_seed import ensure_demo_users

    ensure_demo_users()
    if request.user.is_authenticated:
        from portal.role_routing import dashboard_url_for_role

        return redirect(dashboard_url_for_role(request.user.role))
    return render(request, 'portal/landing.html', {'roles': Role.choices})


@login_required
@role_required(Role.COORDINADOR)
def coordinador_dashboard(request):
    area = area_coordinador(request.user)
    base = filtrar_citas_por_area(
        CitaAsesoria.objects.select_related('cliente', 'cliente__empresa', 'franja'),
        area
    )

    kpis = {
        'nuevas': base.filter(estado=CitaAsesoria.Estado.SOLICITADA).count(),
        'en_proceso': base.filter(estado=CitaAsesoria.Estado.EN_PROCESO).count(),
        'finalizadas': base.filter(estado=CitaAsesoria.Estado.FINALIZADA).count(),
    }
    solicitudes = base.filter(estado=CitaAsesoria.Estado.SOLICITADA).order_by('-creada_en')

    return render(
        request,
        'portal/dashboard_coordinador.html',
        {
            'role_label': f'Coordinador — {Area(area).label}',
            'area': area,
            'area_label': Area(area).label,
            'kpis': kpis,
            'solicitudes': solicitudes,
        },
    )


@login_required
@role_required(Role.COORDINADOR)
@require_http_methods(['GET', 'POST'])
def coordinador_asignar(request, cita_id):
    area = area_coordinador(request.user)
    cita = get_object_or_404(
        CitaAsesoria.objects.select_related('franja', 'cliente', 'cliente__empresa'),
        pk=cita_id,
        estado=CitaAsesoria.Estado.SOLICITADA,
        franja__area=area,
    )
    form = AsignarDocenteForm(request.POST or None, area=area)
    
    if request.method == 'POST' and form.is_valid():
        docente = form.cleaned_data.get('docente_id')
        estudiante = form.cleaned_data.get('estudiante_id')

        if not docente and not estudiante:
            messages.error(request, 'Debe asignar al menos un docente asesor o un estudiante consultor (tutor).')
        else:
            cita.docente_asignado = docente
            cita.estudiante_apoyo = estudiante
            cita.estado = CitaAsesoria.Estado.ASIGNADA
            try:
                cita.full_clean()
                cita.save()
            except Exception as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, 'Cita asignada correctamente.')
                return redirect('portal:coordinador_dashboard')

    return render(
        request,
        'portal/coordinador_asignar.html',
        {
            'role_label': f'Coordinador — {Area(area).label}',
            'cita': cita,
            'form': form,
            'area_label': Area(area).label,
        },
    )


@login_required
@role_required(Role.DOCENTE)
def docente_dashboard(request):
    user = request.user
    citas_qs = CitaAsesoria.objects.filter(docente_asignado=user).select_related(
        'franja', 'cliente', 'cliente__empresa'
    )
    if user.area in (Area.SISTEMAS, Area.CIVIL):
        citas_qs = citas_qs.filter(franja__area=user.area)

    now = timezone.now()
    inicio_semana = now - timedelta(days=now.weekday())
    fin_semana = inicio_semana + timedelta(days=7)

    kpis = {
        'asignados': citas_qs.filter(
            estado__in=(CitaAsesoria.Estado.ASIGNADA, CitaAsesoria.Estado.EN_PROCESO)
        ).count(),
        'semana': citas_qs.filter(
            franja__inicio__gte=inicio_semana,
            franja__inicio__lt=fin_semana,
        ).exclude(estado=CitaAsesoria.Estado.CANCELADA).count(),
        'pendientes_cierre': citas_qs.filter(estado=CitaAsesoria.Estado.EN_PROCESO).count(),
    }
    casos_activos = citas_qs.filter(
        estado__in=(CitaAsesoria.Estado.ASIGNADA, CitaAsesoria.Estado.EN_PROCESO)
    ).order_by('franja__inicio')

    return render(
        request,
        'portal/dashboard_docente.html',
        {
            'role_label': 'Docente asesor',
            'kpis': kpis,
            'casos_activos': casos_activos,
        },
    )


@login_required
@role_required(Role.DOCENTE)
@require_http_methods(['GET', 'POST'])
def docente_caso_detalle(request, cita_id):
    cita = get_object_or_404(
        CitaAsesoria.objects.select_related('franja', 'cliente', 'cliente__empresa'),
        pk=cita_id,
        docente_asignado=request.user,
    )
    area = cita.franja.area
    form = DocenteCasoForm(request.POST or None, instance=cita, area=area)
    if request.method == 'POST':
        accion = request.POST.get('accion', 'gestionar')
        if accion == 'estado_rapido':
            nuevo = request.POST.get('nuevo_estado')
            if nuevo in (
                CitaAsesoria.Estado.EN_PROCESO,
                CitaAsesoria.Estado.FINALIZADA,
            ):
                cita.estado = nuevo
                try:
                    cita.full_clean()
                    cita.save(update_fields=['estado', 'actualizada_en'])
                except Exception as exc:
                    messages.error(request, str(exc))
                else:
                    messages.success(request, 'Estado actualizado.')
            return redirect('portal:docente_caso_detalle', cita_id=cita.pk)
        if form.is_valid():
            cita = form.save()
            nota = form.cleaned_data.get('nota_avance', '').strip()
            if nota:
                NotaBitacora.objects.create(cita=cita, autor=request.user, texto=nota)
            if cita.estado == CitaAsesoria.Estado.FINALIZADA and not cita.resumen_cierre:
                messages.warning(request, 'Se recomienda completar el resumen de cierre al finalizar.')
            messages.success(request, 'Caso actualizado.')
            return redirect('portal:docente_caso_detalle', cita_id=cita.pk)

    notas = cita.notas.select_related('autor').all()
    return render(
        request,
        'portal/docente_caso_detalle.html',
        {
            'role_label': 'Docente asesor',
            'cita': cita,
            'form': form,
            'notas': notas,
        },
    )


@login_required
@role_required(Role.DOCENTE)
def docente_generar_acta(request, cita_id):
    cita = get_object_or_404(
        CitaAsesoria.objects.select_related(
            'franja', 'cliente', 'cliente__empresa', 'docente_asignado'
        ),
        pk=cita_id,
        docente_asignado=request.user,
        estado=CitaAsesoria.Estado.FINALIZADA,
    )
    html = render_to_string('portal/acta_asesoria.html', {'cita': cita})
    response = HttpResponse(html)
    response['Content-Type'] = 'text/html; charset=utf-8'
    response['Content-Disposition'] = f'inline; filename="acta-cita-{cita.pk}.html"'
    return response


@login_required
@role_required(Role.ESTUDIANTE)
def estudiante_dashboard(request):
    perfil = getattr(request.user, 'perfil_estudiante', None)
    citas_qs = CitaAsesoria.objects.filter(estudiante_apoyo=request.user).select_related(
        'franja', 'cliente', 'docente_asignado'
    )
    if request.user.area in (Area.SISTEMAS, Area.CIVIL):
        citas_qs = citas_qs.filter(franja__area=request.user.area)

    casos_asignados = citas_qs.exclude(estado=CitaAsesoria.Estado.CANCELADA).count()
    horas_acum = casos_asignados * 2 + (perfil.creditos_aprobados // 10 if perfil else 0)

    tareas = citas_qs.filter(
        estado__in=(CitaAsesoria.Estado.ASIGNADA, CitaAsesoria.Estado.EN_PROCESO)
    ).order_by('franja__inicio')

    return render(
        request,
        'portal/dashboard_estudiante.html',
        {
            'role_label': 'Estudiante',
            'perfil': perfil,
            'puede_ser_tutor': bool(perfil and perfil.cumple_requisitos_tutor()),
            'kpis': {'horas_creditos': horas_acum, 'casos_asignados': casos_asignados},
            'tareas': tareas,
        },
    )


@login_required
@role_required(Role.ESTUDIANTE)
@require_http_methods(['GET', 'POST'])
def estudiante_caso_nota(request, cita_id):
    cita = get_object_or_404(
        _cita_queryset_detalle(),
        pk=cita_id,
        estudiante_apoyo=request.user,
    )
    form = NotaBitacoraForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        nota = form.save(commit=False)
        nota.cita = cita
        nota.autor = request.user
        nota.save()
        messages.success(request, 'Bitácora registrada.')
        return redirect('portal:estudiante_dashboard')

    return render(
        request,
        'portal/estudiante_caso_nota.html',
        {
            'role_label': 'Estudiante',
            'cita': cita,
            'form': form,
            'notas': cita.notas.select_related('autor').all(),
        },
    )


@login_required
@role_required(Role.CLIENTE)
def cliente_dashboard(request):
    _ensure_demo_franjas_horarias()
    citas_base = (
        CitaAsesoria.objects.filter(cliente=request.user)
        .select_related('franja', 'docente_asignado')
        .order_by('-franja__inicio')
    )
    citas = citas_base[:30]
    areas_consultorio = [
        (Area.SISTEMAS, Area.SISTEMAS.label),
        (Area.CIVIL, Area.CIVIL.label),
    ]
    subespecialidades_json = {
        'sistemas': Subespecialidad.choices_for_area(Area.SISTEMAS),
        'civil': Subespecialidad.choices_for_area(Area.CIVIL),
    }
    citas_feedback = citas_base.filter(
        estado=CitaAsesoria.Estado.FINALIZADA,
        calificacion__isnull=True,
    )
    citas_evaluadas = citas_base.filter(
        estado=CitaAsesoria.Estado.FINALIZADA,
        calificacion__isnull=False,
    )[:10]
    return render(
        request,
        'portal/dashboard_cliente.html',
        {
            'citas': citas,
            'role_label': 'Cliente / Empresa',
            'areas_consultorio': areas_consultorio,
            'subespecialidades_json': subespecialidades_json,
            'citas_feedback': citas_feedback,
            'citas_evaluadas': citas_evaluadas,
        },
    )


@login_required
@role_required(Role.CLIENTE)
@require_http_methods(['GET', 'POST'])
def cliente_feedback(request, cita_id):
    cita = get_object_or_404(
        CitaAsesoria,
        pk=cita_id,
        cliente=request.user,
        estado=CitaAsesoria.Estado.FINALIZADA,
        calificacion__isnull=True,
    )
    form = FeedbackClienteForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        cita.calificacion = form.cleaned_data['calificacion']
        cita.comentario_cliente = form.cleaned_data.get('comentario_cliente', '')
        cita.save(update_fields=['calificacion', 'comentario_cliente', 'actualizada_en'])
        messages.success(request, 'Gracias por su retroalimentación.')
        return redirect('portal:cliente_dashboard')

    return render(
        request,
        'portal/cliente_feedback.html',
        {
            'role_label': 'Cliente / Empresa',
            'cita': cita,
            'form': form,
        },
    )


def _cita_queryset_detalle():
    return CitaAsesoria.objects.select_related(
        'franja', 'cliente', 'cliente__empresa', 'docente_asignado', 'estudiante_apoyo'
    )


def _redirect_tras_embed(request, default_name):
    if request.POST.get('embed') or request.GET.get('embed'):
        return redirect(default_name)
    return None


@login_required
@require_http_methods(['GET', 'POST'])
def cita_detalle_interactivo(request, cita_id):
    """Detalle interactivo de cita (modal en bandeja o POST de acciones por rol)."""
    user = request.user
    role = user.role

    if role == Role.COORDINADOR:
        area = area_coordinador(user)
        cita = get_object_or_404(
            _cita_queryset_detalle(),
            pk=cita_id,
            franja__area=area,
        )
        puede_asignar = cita.estado == CitaAsesoria.Estado.SOLICITADA
        form_asignar = AsignarDocenteForm(request.POST or None, area=area)

        if request.method == 'POST' and puede_asignar and form_asignar.is_valid():
            docente = form_asignar.cleaned_data.get('docente_id')
            estudiante = form_asignar.cleaned_data.get('estudiante_id')

            if not docente and not estudiante:
                messages.error(request, 'Debe asignar al menos un docente asesor o un estudiante consultor (tutor).')
            else:
                cita.docente_asignado = docente
                cita.estudiante_apoyo = estudiante
                cita.estado = CitaAsesoria.Estado.ASIGNADA
                try:
                    cita.full_clean()
                    cita.save()
                except Exception as exc:
                    messages.error(request, str(exc))
                else:
                    messages.success(request, 'Cita asignada correctamente.')
                    redir = _redirect_tras_embed(request, 'portal:coordinador_dashboard')
                    if redir:
                        return redir
                    return redirect('portal:coordinador_dashboard')

        ctx = {
            'cita': cita,
            'form_asignar': form_asignar,
            'puede_asignar': puede_asignar,
        }
        return render(request, 'portal/partials/cita_detalle_coordinador.html', ctx)

    if role == Role.DOCENTE:
        cita = get_object_or_404(
            _cita_queryset_detalle(),
            pk=cita_id,
            docente_asignado=user,
        )
        area = cita.franja.area
        form_gestion = DocenteCasoForm(request.POST or None, instance=cita, area=area)

        if request.method == 'POST':
            accion = request.POST.get('accion')
            if accion == 'estado_rapido':
                nuevo = request.POST.get('nuevo_estado')
                if nuevo in (
                    CitaAsesoria.Estado.EN_PROCESO,
                    CitaAsesoria.Estado.FINALIZADA,
                ):
                    cita.estado = nuevo
                    try:
                        cita.full_clean()
                        cita.save(update_fields=['estado', 'actualizada_en'])
                    except Exception as exc:
                        messages.error(request, str(exc))
                    else:
                        messages.success(request, 'Estado actualizado.')
                redir = _redirect_tras_embed(request, 'portal:docente_dashboard')
                return redir or redirect('portal:docente_dashboard')

            if accion == 'gestionar' and form_gestion.is_valid():
                cita = form_gestion.save()
                messages.success(request, 'Caso actualizado.')
                redir = _redirect_tras_embed(request, 'portal:docente_dashboard')
                return redir or redirect('portal:docente_dashboard')

        notas = cita.notas.select_related('autor').all()
        return render(
            request,
            'portal/partials/cita_detalle_docente.html',
            {'cita': cita, 'form_gestion': form_gestion, 'notas': notas},
        )

    if role == Role.CLIENTE:
        cita = get_object_or_404(
            _cita_queryset_detalle(),
            pk=cita_id,
            cliente=user,
        )
        return render(
            request,
            'portal/partials/cita_detalle_cliente.html',
            {'cita': cita},
        )

    if role == Role.ESTUDIANTE:
        cita = get_object_or_404(
            _cita_queryset_detalle(),
            pk=cita_id,
            estudiante_apoyo=user,
        )
        form_bitacora = NotaBitacoraForm(request.POST or None)
        if request.method == 'POST' and request.POST.get('accion') == 'bitacora':
            if form_bitacora.is_valid():
                nota = form_bitacora.save(commit=False)
                nota.cita = cita
                nota.autor = user
                nota.save()
                messages.success(request, 'Bitácora registrada.')
                redir = _redirect_tras_embed(request, 'portal:estudiante_dashboard')
                return redir or redirect('portal:estudiante_dashboard')

        notas = cita.notas.select_related('autor').all()
        return render(
            request,
            'portal/partials/cita_detalle_estudiante.html',
            {'cita': cita, 'form_bitacora': form_bitacora, 'notas': notas},
        )

    raise PermissionDenied