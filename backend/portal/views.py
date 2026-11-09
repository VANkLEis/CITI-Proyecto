from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Avg, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from accounts.models import Area, CustomUser, Role
from portal.area_helpers import area_coordinador, filtrar_citas_por_area
from portal.decorators import role_required
from portal.forms import (
    AsignarDocenteForm, DecisionClienteForm, DocenteCasoForm, EntregableForm,
    FeedbackClienteForm, InteraccionClienteForm, InteraccionEquipoForm, NotaBitacoraForm,
)
from scheduling.models import CitaAsesoria, CitaEvento, CitaInteraccion, NotaBitacora, TipoServicio
from scheduling.trazabilidad import (
    asignar_cita, auditar_guardado_form, cambio_estado, interacciones_visibles,
    nota_asignacion, publicar_entrega, registrar_decision_cliente,
    registrar_evento, registrar_interaccion,
)
from scheduling.subespecialidades import Subespecialidad


def _es_responsable(user, cita):
    """Acceso de equipo a UNA solicitud (no al listado de bandeja).

    Docente/tutor asignados; coordinador del área (supervisa todos los casos
    de su área); director global. Usado para interactuar y descargar."""
    if user.role == Role.DIRECTOR:
        return True
    if user.role == Role.DOCENTE and cita.docente_asignado_id == user.pk:
        return True
    if user.role == Role.ESTUDIANTE and cita.estudiante_apoyo_id == user.pk:
        return True
    if user.role == Role.COORDINADOR:
        return cita.franja.area == user.area
    return False


def _cita_interacciones(user, qs):
    return interacciones_visibles(qs, user).select_related('autor')


# (B-4/Auditoría FUN-12) El autoseed de franjas por GET del dashboard cliente fue
# eliminado; las franjas de demostración se crean explícitamente con
# `manage.py seed_demo` (idempotente) desde accounts/demo_seed.py.


@login_required
@role_required(Role.DIRECTOR)
def director_dashboard(request):
    """Panel ejecutivo del Director CITI (Módulo B). Indicadores reales con
    filtros de periodo; el detalle operativo queda en /panel/trazabilidad/."""
    from accounts.models import CustomUser
    from scheduling.models import FranjaHoraria
    from portal import indicadores

    qs, filtros = indicadores.parse_filtros(request.GET)
    kpis = indicadores.kpis_base(qs)
    estados, _ = indicadores.por_estado(qs)
    areas, _ = indicadores.por_area(qs)
    serie = indicadores.evolucion_mensual(qs, meses=6)
    recientes = indicadores.actividad_reciente(qs, 8)
    hoy = timezone.localtime()

    context = {
        'role_label': 'Director CITI',
        'kpis': kpis,
        'estados': estados,
        'areas': areas,
        'serie': serie,
        'serie_max': max([max(s['recibidas'], s['cerradas']) for s in serie] + [1]),
        'recientes': recientes,
        'filtros': filtros,
        'periodos': indicadores.PERIODOS,
        'franjas_activas': FranjaHoraria.objects.filter(
            activa=True, inicio__gt=timezone.now()).count(),
        'total_usuarios': CustomUser.objects.count(),
        'hoy': hoy,
    }
    return render(request, 'portal/dashboard_director.html', context)


@login_required
@role_required(Role.DIRECTOR, Role.COORDINADOR)
def trazabilidad(request):
    """Trazabilidad e indicadores de gestión (Módulo C).

    Director: alcance global. Coordinador: aislamiento de área forzado."""
    from portal import indicadores

    area_forzada = None
    if request.user.role == Role.COORDINADOR:
        area_forzada = area_coordinador(request.user)

    qs, filtros = indicadores.parse_filtros(request.GET, area_forzada=area_forzada)
    kpis = indicadores.kpis_base(qs)
    tiempos = indicadores.tiempos_promedio(qs)
    interaccion = indicadores.metricas_interaccion(qs)
    estados, _ = indicadores.por_estado(qs)
    areas, _ = indicadores.por_area(qs)
    servicios, _ = indicadores.servicios_top(qs)
    serie = indicadores.evolucion_mensual(qs, meses=6)
    tabla = indicadores.resultados_tabla(qs, 100)
    responsables = indicadores.responsables_posibles(qs)

    context = {
        'role_label': ('Trazabilidad — ' + Area(area_forzada).label) if area_forzada
        else 'Trazabilidad · Director CITI',
        'kpis': kpis,
        'tiempos': tiempos,
        'interaccion': interaccion,
        'estados': estados,
        'areas': areas,
        'servicios': servicios,
        'serie': serie,
        'serie_max': max([max(s['recibidas'], s['cerradas']) for s in serie] + [1]),
        'tabla': tabla,
        'filtros': filtros,
        'periodos': indicadores.PERIODOS,
        'estados_choices': CitaAsesoria.Estado.choices,
        'areas_choices': [x for x in Area.choices if x[0] != Area.MIXTO],
        'responsables': responsables,
        'area_lectura': area_forzada,
    }
    return render(request, 'portal/trazabilidad.html', context)


@login_required
@role_required(Role.DIRECTOR, Role.COORDINADOR)
def trazabilidad_csv(request):
    """Exportación CSV con los mismos filtros y el mismo aislamiento de rol."""
    import csv as csv_mod
    from portal import indicadores

    area_forzada = None
    if request.user.role == Role.COORDINADOR:
        area_forzada = area_coordinador(request.user)

    qs, filtros = indicadores.parse_filtros(request.GET, area_forzada=area_forzada)

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    filename = f'reporte-citi-{timezone.localtime():%Y%m%d-%H%M}.csv'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write('\ufeff')  # BOM para Excel

    writer = csv_mod.writer(response)
    periodo_txt = filtros['desde'].strftime('%d/%m/%Y') if filtros['desde'] else 'inicio'
    hasta_txt = filtros['hasta'].strftime('%d/%m/%Y') if filtros['hasta'] else 'hoy'
    area_txt = Area(filtros['area']).label if filtros['area'] else 'Todas las áreas'
    writer.writerow([f'Reporte CITI — período {periodo_txt} a {hasta_txt} — {area_txt}'])
    writer.writerow([f'Generado {timezone.localtime():%d/%m/%Y %H:%M} por '
                     f'{request.user.nombre_completo} · {request.user.get_role_display()}'])
    writer.writerow([])
    for row in indicadores.csv_rows(qs):
        writer.writerow(row)
    return response


def landing(request):
    # Catalogo REAL de servicios: proviene de Subespecialidad (mismo que usa
    # la reserva en el portal cliente). Sin invencion.
    catalog_by_area = {
        Area.SISTEMAS: {
            'value': 'sistemas',
            'label': 'Ingeniería de Sistemas',
            'corto': 'Sistemas',
            'descripcion': ('Software, bases de datos, redes y ciberseguridad '
                            'para PyMEs de la región.'),
            'foto': 'images/landing/area-sistemas.jpg',
            'foto_alt': 'Equipo revisando una solucion de software en portatil',
            'subespecialidades': Subespecialidad.choices_for_area(Area.SISTEMAS),
            'tipos': [
                {'nombre': 'Asesoría / orientación técnica',
                 'quien': ('Respuesta puntual, acompañamiento y recomendaciones; '
                           'la ejecuta el estudiante tutor con dirección docente.')},
                {'nombre': 'Consultoría estructurada',
                 'quien': ('Docente responsable, ficha de diagnóstico/alcance/'
                           'metodología, entregables y aprobación del cliente.')},
            ],
        },
        Area.CIVIL: {
            'value': 'civil',
            'label': 'Ingeniería Civil',
            'corto': 'Civil',
            'descripcion': ('Estructuras, interventoría, vías y planos de obra '
                            'con acompañamiento académico.'),
            'foto': 'images/landing/area-civil.jpg',
            'foto_alt': 'Maqueta arquitectonica revisada por estudiantes de ingenieria',
            'subespecialidades': Subespecialidad.choices_for_area(Area.CIVIL),
            'tipos': [
                {'nombre': 'Asesoría / orientación técnica',
                 'quien': ('Respuesta puntual, acompañamiento y recomendaciones; '
                           'la ejecuta el estudiante tutor con dirección docente.')},
                {'nombre': 'Consultoría estructurada',
                 'quien': ('Docente responsable, ficha de diagnóstico/alcance/'
                           'metodología, entregables y aprobación del cliente.')},
            ],
        },
    }
    catalogo = list(catalog_by_area.values())
    total_especialidades = sum(
        len(Subespecialidad.POR_AREA[area]) for area in (Area.SISTEMAS, Area.CIVIL)
    )
    recursos = [
        {'archivo': 'documentos/solicitud-asesoria.pdf', 'nombre': 'Solicitud de Asesoría',
         'descripcion': 'Registro de la necesidad de la empresa y sus términos de referencia.'},
        {'archivo': 'documentos/catalogo-capacitacion.pdf', 'nombre': 'Catálogo de Capacitación',
         'descripcion': 'Oferta de talleres, seminarios y educación no formal del CITI.'},
        {'archivo': 'documentos/minuta-convenio.pdf', 'nombre': 'Minuta de Convenio',
         'descripcion': 'Modelo de acuerdo de cooperación entre la UCC y empresas aliadas.'},
        {'archivo': 'documentos/manual-citi.pdf', 'nombre': 'Manual CITI',
         'descripcion': 'Funcionamiento, roles, requisitos y flujo de atención del consultorio.'},
        {'archivo': 'documentos/asistencia-consultores.pdf', 'nombre': 'Asistencia de Consultores',
         'descripcion': 'Registro diario de turnos, horarios y firmas de los estudiantes consultores.'},
        {'archivo': 'documentos/registro-consultas.pdf', 'nombre': 'Registro de Consultas',
         'descripcion': 'Atención por empresa: fecha, contacto, consulta y observaciones.'},
        {'archivo': 'documentos/informe-parcial-asesoria.pdf', 'nombre': 'Informe Parcial de Asesoría',
         'descripcion': 'Reporte del consultor sobre el caso, tratamiento y resultados.'},
        {'archivo': 'documentos/informe-final-asesoria.pdf', 'nombre': 'Informe Final de Asesoría',
         'descripcion': 'Cierre del caso con conclusiones y firma de la empresa.'},
        {'archivo': 'documentos/informe-final-capacitacion.pdf', 'nombre': 'Informe Final de Capacitación',
         'descripcion': 'Resultado de talleres: contenido, recursos, asistentes y testigos.'},
        {'archivo': 'documentos/registro-participacion.pdf', 'nombre': 'Registro de Participación',
         'descripcion': 'Control transversal por consultorio, clase, capacitación y programa radial.'},
    ]
    if request.user.is_authenticated:
        from portal.role_routing import dashboard_url_for_role

        return redirect(dashboard_url_for_role(request.user.role))
    return render(request, 'portal/landing.html', {
        'roles': Role.choices,
        'catalogo': catalogo,
        'total_especialidades': total_especialidades,
        'recursos': recursos,
    })


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
    form_interaccion = InteraccionEquipoForm(
        request.POST if request.method == 'POST'
        and request.POST.get('accion') == 'interaccion' else None, prefix='ia')
    if request.method == 'POST' and request.POST.get('accion') == 'interaccion':
        if form_interaccion.is_valid():
            with transaction.atomic():
                registrar_interaccion(cita, request.user,
                                      form_interaccion.cleaned_data['tipo'],
                                      form_interaccion.cleaned_data['texto'])
            messages.success(request, 'Observación registrada.')
            return redirect('portal:coordinador_asignar', cita_id=cita.pk)
    if request.method == 'GET':
        # Trazabilidad: la apertura de la bandeja de asignación deja constancia
        # de revisión (una sola vez por coordinador y solicitud).
        nota_asignacion(cita, request.user)
    
    if request.method == 'POST' and form.is_valid():
        docente = form.cleaned_data.get('docente_id')
        estudiante = form.cleaned_data.get('estudiante_id')

        if not docente and not estudiante:
            messages.error(request, 'Debe asignar al menos un docente asesor o un estudiante consultor (tutor).')
        else:
            try:
                with transaction.atomic():
                    ok = asignar_cita(cita, request.user, docente, estudiante)
                    if not ok:
                        raise Exception('La solicitud ya no está pendiente de asignación.')
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
            'form_interaccion': form_interaccion,
            'interacciones': _cita_interacciones(request.user, cita.interacciones.all()),
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
    # Capturar ANTES de instanciar el form con data: is_valid() muta la
    # instancia ligada y borraría el estado anterior real.
    anterior_estado = cita.estado
    anterior_apoyo = cita.estudiante_apoyo_id
    area = cita.franja.area
    form = DocenteCasoForm(request.POST or None, instance=cita, area=area)
    form_interaccion = InteraccionEquipoForm(request.POST if request.method == 'POST'
                                             and request.POST.get('accion') == 'interaccion'
                                             else None, prefix='ia')
    form_entrega = EntregableForm(request.POST if request.method == 'POST'
                                  and request.POST.get('accion') == 'entrega'
                                  else None, prefix='ed')
    if request.method == 'POST':
        accion = request.POST.get('accion', 'gestionar')
        if accion == 'estado_rapido':
            nuevo = request.POST.get('nuevo_estado')
            if nuevo in (
                CitaAsesoria.Estado.EN_PROCESO,
                CitaAsesoria.Estado.FINALIZADA,
            ) and CitaAsesoria.transicion_legal(cita.estado, nuevo):
                try:
                    with transaction.atomic():
                        cambio_estado(
                            cita, request.user, nuevo,
                            descripcion='Acción rápida del docente desde el portal.',
                        )
                except Exception as exc:
                    messages.error(request, str(exc))
                else:
                    messages.success(request, 'Estado actualizado.')
            elif nuevo != cita.estado:
                messages.error(
                    request, f'Transición no permitida: {cita.estado} → {nuevo}.')
            return redirect('portal:docente_caso_detalle', cita_id=cita.pk)
        if accion == 'interaccion':
            if form_interaccion.is_valid():
                with transaction.atomic():
                    registrar_interaccion(cita, request.user,
                                          form_interaccion.cleaned_data['tipo'],
                                          form_interaccion.cleaned_data['texto'])
                messages.success(request, 'Mensaje registrado.')
            return redirect('portal:docente_caso_detalle', cita_id=cita.pk)
        if accion == 'entrega':
            if form_entrega.is_valid():
                try:
                    with transaction.atomic():
                        publicar_entrega(cita, request.user,
                                         form_entrega.cleaned_data['titulo'],
                                         form_entrega.cleaned_data['contenido'],
                                         ficha=form_entrega.ficha())
                except Exception as exc:
                    messages.error(request, str(exc))
                else:
                    messages.success(
                        request, 'Entregable publicado para revisión del cliente. '
                                 'La aprobación del cliente no cierra el caso: '
                                 'el cierre administrativo lo hace el docente.')
            return redirect('portal:docente_caso_detalle', cita_id=cita.pk)
        if form.is_valid():
            nuevo_estado = form.cleaned_data['estado']
            if nuevo_estado != anterior_estado and not CitaAsesoria.transicion_legal(
                    anterior_estado, nuevo_estado):
                messages.error(
                    request, f'Transición no permitida: {anterior_estado} → '
                             f'{nuevo_estado}. (Flujo formal de estados, I-2)')
                return redirect('portal:docente_caso_detalle', cita_id=cita.pk)
            with transaction.atomic():
                cita = form.save()
                auditar_guardado_form(cita, request.user, anterior_estado, anterior_apoyo)
                nota = form.cleaned_data.get('nota_avance', '').strip()
                if nota:
                    nota_obj = NotaBitacora.objects.create(cita=cita, autor=request.user, texto=nota)
                    registrar_evento(cita, request.user, CitaEvento.Tipo.BITACORA,
                                     descripcion='Nueva nota de bitácora del docente.')
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
            'interacciones': _cita_interacciones(request.user, cita.interacciones.all()),
            'form_interaccion': form_interaccion,
            'form_entrega': form_entrega,
            'entrega_pendiente': cita.entrega_pendiente,
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
    # Trazabilidad: primera emisión del acta queda registrada (no se repite).
    if not cita.eventos.filter(tipo=CitaEvento.Tipo.ACTA_REGISTRADA).exists():
        registrar_evento(cita, request.user, CitaEvento.Tipo.ACTA_REGISTRADA,
                         descripcion='Acta de cierre emitida por el docente responsable.')
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
    # KPIs reales: el anterior 'horas/créditos acumulados' era una fórmula
    # arbitraria señalada en la auditoría (FUN-11) y se eliminó.
    cerrados = citas_qs.filter(estado=CitaAsesoria.Estado.FINALIZADA)
    promedio_valoracion = round(
        float(cerrados.filter(calificacion__isnull=False)
              .aggregate(avg=Avg('calificacion'))['avg'] or 0), 1)
    kpis = {
        'casos_asignados': casos_asignados,
        'casos_cerrados': cerrados.count(),
        'promedio_valoracion': promedio_valoracion if cerrados.filter(
            calificacion__isnull=False).exists() else None,
    }

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
            'kpis': kpis,
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
        with transaction.atomic():
            nota = form.save(commit=False)
            nota.cita = cita
            nota.autor = request.user
            nota.save()
            registrar_evento(cita, request.user, CitaEvento.Tipo.BITACORA,
                             descripcion='Nota de bitácora del tutor de apoyo.')
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
    # Fase 04: entregables publicados que esperan decisión del cliente.
    citas_pendientes_aprobacion = [
        c for c in citas_base.prefetch_related('interacciones')[:60]
        if c.entrega_pendiente
    ]
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
            'citas_pendientes_aprobacion': citas_pendientes_aprobacion,
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
        with transaction.atomic():
            cita.calificacion = form.cleaned_data['calificacion']
            cita.comentario_cliente = form.cleaned_data.get('comentario_cliente', '')
            cita.save(update_fields=['calificacion', 'comentario_cliente', 'actualizada_en'])
            registrar_evento(cita, request.user, CitaEvento.Tipo.FEEDBACK,
                             descripcion=f'Valoración del cliente: {cita.calificacion}/5.',
                             metadata={'calificacion': cita.calificacion})
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
        form_interaccion = InteraccionEquipoForm(
            request.POST if request.method == 'POST'
            and request.POST.get('accion') == 'interaccion' else None, prefix='ia')

        if request.method == 'POST' and request.POST.get('accion') == 'interaccion':
            if form_interaccion.is_valid():
                with transaction.atomic():
                    registrar_interaccion(cita, user,
                                          form_interaccion.cleaned_data['tipo'],
                                          form_interaccion.cleaned_data['texto'])
                messages.success(request, 'Observación registrada.')
            return redirect('portal:coordinador_dashboard')

        if request.method == 'POST' and puede_asignar and form_asignar.is_valid():
            docente = form_asignar.cleaned_data.get('docente_id')
            estudiante = form_asignar.cleaned_data.get('estudiante_id')

            if not docente and not estudiante:
                messages.error(request, 'Debe asignar al menos un docente asesor o un estudiante consultor (tutor).')
            else:
                try:
                    with transaction.atomic():
                        if not asignar_cita(cita, user, docente, estudiante):
                            raise Exception('La solicitud ya no está pendiente.')
                except Exception as exc:
                    messages.error(request, str(exc))
                else:
                    messages.success(request, 'Cita asignada correctamente.')
                    redir = _redirect_tras_embed(request, 'portal:coordinador_dashboard')
                    if redir:
                        return redir
                    return redirect('portal:coordinador_dashboard')

        if request.method == 'GET':
            nota_asignacion(cita, user)

        ctx = {
            'cita': cita,
            'form_asignar': form_asignar,
            'puede_asignar': puede_asignar,
            'form_interaccion': form_interaccion,
            'interacciones': _cita_interacciones(user, cita.interacciones.all()),
        }
        return render(request, 'portal/partials/cita_detalle_coordinador.html', ctx)

    if role == Role.DOCENTE:
        cita = get_object_or_404(
            _cita_queryset_detalle(),
            pk=cita_id,
            docente_asignado=user,
        )
        # Capturar antes de ligar el form (is_valid muta la instancia).
        anterior_estado = cita.estado
        anterior_apoyo = cita.estudiante_apoyo_id
        area = cita.franja.area
        accion = request.POST.get('accion') if request.method == 'POST' else None
        form_gestion = DocenteCasoForm(request.POST or None, instance=cita, area=area)
        form_interaccion = InteraccionEquipoForm(
            request.POST if accion == 'interaccion' else None, prefix='ia')
        form_entrega = EntregableForm(
            request.POST if accion == 'entrega' else None, prefix='ed')

        if request.method == 'POST':
            if accion == 'estado_rapido':
                nuevo = request.POST.get('nuevo_estado')
                if nuevo in (
                    CitaAsesoria.Estado.EN_PROCESO,
                    CitaAsesoria.Estado.FINALIZADA,
                ) and CitaAsesoria.transicion_legal(cita.estado, nuevo):
                    try:
                        with transaction.atomic():
                            cambio_estado(cita, user, nuevo,
                                          descripcion='Acción rápida del docente (modal).')
                    except Exception as exc:
                        messages.error(request, str(exc))
                    else:
                        messages.success(request, 'Estado actualizado.')
                elif nuevo != cita.estado:
                    messages.error(
                        request, f'Transición no permitida: {cita.estado} → {nuevo}.')
                redir = _redirect_tras_embed(request, 'portal:docente_dashboard')
                return redir or redirect('portal:docente_dashboard')

            if accion == 'interaccion':
                if form_interaccion.is_valid():
                    with transaction.atomic():
                        registrar_interaccion(cita, user,
                                              form_interaccion.cleaned_data['tipo'],
                                              form_interaccion.cleaned_data['texto'])
                    messages.success(request, 'Mensaje registrado.')
                redir = _redirect_tras_embed(request, 'portal:docente_dashboard')
                return redir or redirect('portal:docente_caso_detalle', cita_id=cita.pk)

            if accion == 'entrega':
                if form_entrega.is_valid():
                    try:
                        with transaction.atomic():
                            publicar_entrega(cita, user,
                                             form_entrega.cleaned_data['titulo'],
                                             form_entrega.cleaned_data['contenido'],
                                             ficha=form_entrega.ficha())
                    except Exception as exc:
                        messages.error(request, str(exc))
                    else:
                        messages.success(request, 'Entregable publicado para el cliente.')
                redir = _redirect_tras_embed(request, 'portal:docente_dashboard')
                return redir or redirect('portal:docente_caso_detalle', cita_id=cita.pk)

            if accion == 'gestionar' and form_gestion.is_valid():
                nuevo_estado = form_gestion.cleaned_data['estado']
                if nuevo_estado != anterior_estado and not CitaAsesoria.transicion_legal(
                        anterior_estado, nuevo_estado):
                    messages.error(
                        request, f'Transición no permitida: {anterior_estado} → '
                                 f'{nuevo_estado}. (Flujo formal de estados)')
                    return redirect('portal:docente_dashboard')
                with transaction.atomic():
                    cita = form_gestion.save()
                    auditar_guardado_form(cita, user, anterior_estado, anterior_apoyo)
                messages.success(request, 'Caso actualizado.')
                redir = _redirect_tras_embed(request, 'portal:docente_dashboard')
                return redir or redirect('portal:docente_dashboard')

        notas = cita.notas.select_related('autor').all()
        return render(
            request,
            'portal/partials/cita_detalle_docente.html',
            {'cita': cita, 'form_gestion': form_gestion, 'notas': notas,
             'interacciones': _cita_interacciones(user, cita.interacciones.all()),
             'form_interaccion': form_interaccion, 'form_entrega': form_entrega,
             'entrega_pendiente': cita.entrega_pendiente},
        )

    if role == Role.CLIENTE:
        cita = get_object_or_404(
            _cita_queryset_detalle(),
            pk=cita_id,
            cliente=user,
        )
        form_interaccion = InteraccionClienteForm(
            request.POST if request.method == 'POST'
            and request.POST.get('accion') == 'interaccion' else None, prefix='ic')
        if request.method == 'POST' and request.POST.get('accion') == 'interaccion':
            if form_interaccion.is_valid():
                with transaction.atomic():
                    registrar_interaccion(cita, user,
                                          form_interaccion.cleaned_data['tipo'],
                                          form_interaccion.cleaned_data['texto'])
                messages.success(request, 'Mensaje enviado al equipo del CITI.')
                redir = _redirect_tras_embed(request, 'portal:cliente_dashboard')
                return redir or redirect('portal:cliente_dashboard')
        ctx = {
            'cita': cita,
            'form_interaccion': form_interaccion,
            'entrega_pendiente': cita.entrega_pendiente,
            'interacciones': _cita_interacciones(user, cita.interacciones.all()),
        }
        return render(request, 'portal/partials/cita_detalle_cliente.html', ctx)

    if role == Role.ESTUDIANTE:
        cita = get_object_or_404(
            _cita_queryset_detalle(),
            pk=cita_id,
            estudiante_apoyo=user,
        )
        form_bitacora = NotaBitacoraForm(request.POST or None)
        if request.method == 'POST' and request.POST.get('accion') == 'bitacora':
            if form_bitacora.is_valid():
                with transaction.atomic():
                    nota = form_bitacora.save(commit=False)
                    nota.cita = cita
                    nota.autor = user
                    nota.save()
                    registrar_evento(cita, user, CitaEvento.Tipo.BITACORA,
                                     descripcion='Nota de bitácora del tutor (modal).')
                messages.success(request, 'Bitácora registrada.')
                redir = _redirect_tras_embed(request, 'portal:estudiante_dashboard')
                return redir or redirect('portal:estudiante_dashboard')

        notas = cita.notas.select_related('autor').all()
        return render(
            request,
            'portal/partials/cita_detalle_estudiante.html',
            {'cita': cita, 'form_bitacora': form_bitacora, 'notas': notas,
             'interacciones': _cita_interacciones(user, cita.interacciones.all())},
        )

    raise PermissionDenied


# ===========================================================================
# Fase 04 — Portal de seguimiento del cliente e interacción
# ===========================================================================

def _cliente_citas_qs(user):
    return (CitaAsesoria.objects.filter(cliente=user)
            .select_related('franja', 'docente_asignado', 'estudiante_apoyo'))


@login_required
@role_required(Role.CLIENTE)
def cliente_mis_solicitudes(request):
    """4.1 «Mis solicitudes»: filtros por estado y tipo de servicio, con
    código, área, especialidad, profesional, estado y última actualización."""
    citas = _cliente_citas_qs(request.user)
    estado = request.GET.get('estado', '')
    tipo = request.GET.get('tipo', '')
    if estado in dict(CitaAsesoria.Estado.choices):
        citas = citas.filter(estado=estado)
    if tipo in dict(TipoServicio.choices):
        citas = citas.filter(tipo_servicio=tipo)
    context = {
        'role_label': 'Cliente / Empresa',
        'citas': citas.order_by('-actualizada_en')[:100],
        'estados': CitaAsesoria.Estado.choices,
        'tipos': [(k, v.split(' (')[0]) for k, v in TipoServicio.choices],
        'f_estado': estado,
        'f_tipo': tipo,
    }
    return render(request, 'portal/cliente_mis_solicitudes.html', context)


@login_required
@role_required(Role.CLIENTE)
@require_http_methods(['GET', 'POST'])
def cliente_seguimiento(request, cita_id):
    """4.2 Página de seguimiento individual + 5.x interacciones.

    Pertenencia forzada en servidor (cliente solo ve SUS solicitudes)."""
    cita = get_object_or_404(
        _cliente_citas_qs(request.user).prefetch_related('eventos', 'interacciones__autor'),
        pk=cita_id)
    accion_post = request.POST.get('accion') if request.method == 'POST' else None
    form_interaccion = InteraccionClienteForm(
        request.POST if accion_post in ('interaccion', 'aprobar', 'ajustes') else None,
        prefix='ic')
    form_decision = DecisionClienteForm(
        request.POST if accion_post in ('aprobar', 'ajustes') else None,
        prefix='dc')

    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion == 'cancelar':
            # I-4: cancelación desde el portal. POST autenticado + propiedad
            # + confirmación ('confirmar=si'); el estado se valida otra vez
            # en el servicio.
            if request.POST.get('confirmar') != 'si':
                messages.error(request, 'Debes confirmar la cancelación.')
            else:
                try:
                    with transaction.atomic():
                        if not cita.puede_cancelar_cliente():
                            raise Exception(
                                'Solo puedes cancelar mientras la solicitud está '
                                'solicitada o asignada.')
                        cambio_estado(cita, request.user, CitaAsesoria.Estado.CANCELADA,
                                      descripcion='Cancelación registrada por el cliente '
                                                  'desde el portal.')
                except Exception as exc:
                    messages.error(request, str(exc))
                else:
                    messages.success(request, 'Solicitud cancelada. El historial conserva '
                                              'el registro de tu decisión.')
            return redirect('portal:cliente_seguimiento', cita_id=cita.pk)

        if accion == 'interaccion':
            if form_interaccion.is_valid():
                try:
                    with transaction.atomic():
                        registrar_interaccion(cita, request.user,
                                              form_interaccion.cleaned_data['tipo'],
                                              form_interaccion.cleaned_data['texto'])
                except Exception as exc:
                    messages.error(request, str(exc))
                else:
                    messages.success(request, 'Mensaje enviado al equipo del CITI.')
            return redirect('portal:cliente_seguimiento', cita_id=cita.pk)

        if accion in ('aprobar', 'ajustes'):
            aprobar = accion == 'aprobar'
            observacion = None
            if form_interaccion.is_bound and form_interaccion.is_valid():
                observacion = form_interaccion.cleaned_data['texto'].strip() or None
            elif form_decision.is_bound and form_decision.is_valid():
                observacion = form_decision.cleaned_data['observacion'].strip() or None
            error = None
            if observacion is None:
                # Sin observación válida no se registra nada: re-render con error.
                error = 'Completa la observación que justifica tu decisión.'
            else:
                try:
                    with transaction.atomic():
                        registrar_decision_cliente(cita, request.user, aprobar, observacion)
                except Exception as exc:
                    error = str(exc)
            if error:
                messages.error(request, error)
            else:
                if aprobar:
                    messages.success(
                        request, 'Entregable aprobado. Recuerda: la aprobación no '
                                 'finaliza administrativamente la solicitud; el '
                                 'cierre lo realiza el docente responsable.')
                else:
                    messages.success(request, 'Ajustes solicitados. La solicitud '
                                              'regresó al flujo operativo del equipo.')
                return redirect('portal:cliente_seguimiento', cita_id=cita.pk)

    context = {
        'role_label': 'Cliente / Empresa',
        'cita': cita,
        'interacciones': _cita_interacciones(request.user, cita.interacciones.all()),
        'form_interaccion': form_interaccion,
        'form_decision': form_decision,
        'entrega_pendiente': cita.entrega_pendiente,
        'coordinador': (CustomUser.objects.filter(
            role=Role.COORDINADOR, area=cita.franja.area).first()),
    }
    return render(request, 'portal/cliente_seguimiento.html', context)


@login_required
@role_required(Role.CLIENTE)
def cliente_notificaciones(request):
    """Notificaciones reales del cliente: entregables pendientes de aprobación,
    solicitudes sin valorar y actividad reciente de sus interacciones."""
    citas = _cliente_citas_qs(request.user).prefetch_related('interacciones')
    pendientes = [c for c in citas if c.entrega_pendiente]
    sin_valorar = citas.filter(estado=CitaAsesoria.Estado.FINALIZADA,
                               calificacion__isnull=True)
    actividad = (CitaInteraccion.objects
                 .filter(cita__cliente=request.user, para_cliente=True)
                 .exclude(autor=request.user)
                 .select_related('cita', 'autor').order_by('-fecha')[:20])
    return render(request, 'portal/cliente_notificaciones.html', {
        'role_label': 'Cliente / Empresa',
        'pendientes': pendientes,
        'sin_valorar': sin_valorar,
        'actividad': actividad,
    })


@login_required
def perfil_propio(request):
    """Perfil real y solo lectura: cuenta, rol, empresa/perfil académico y
    enlace al cambio de contraseña autenticado de Django."""
    user = request.user
    perfil = getattr(user, 'perfil_estudiante', None)
    return render(request, 'portal/perfil_propio.html', {
        'role_label': user.get_role_display(),
        'perfil': perfil,
    })


@login_required
@require_http_methods(['GET'])
def cita_adjunto(request, cita_id):
    """I-3: descarga del adjunto SOLO para partes autorizadas.

    Dueña (cliente), docente/tutor asignados, coordinador del área o
    director. Sustituye el enlace directo a /media/ (que exponía la carpeta
    de uploads cuando se sirve en producción)."""
    import os

    from django.http import FileResponse, Http404

    user = request.user
    cita = get_object_or_404(
        CitaAsesoria.objects.select_related('franja', 'cliente'), pk=cita_id)
    autorizado = (user.role == Role.CLIENTE and cita.cliente_id == user.pk) or (
        user.role != Role.CLIENTE and _es_responsable(user, cita))
    if not autorizado:
        raise PermissionDenied('No tienes acceso a esta documentación.')
    if not cita.archivo_adjunto:
        raise Http404('Esta solicitud no tiene documentación adjunta.')
    if not os.path.exists(cita.archivo_adjunto.path):
        raise Http404('El archivo ya no está disponible en el servidor.')
    return FileResponse(
        open(cita.archivo_adjunto.path, 'rb'),
        as_attachment=True,
        filename=os.path.basename(cita.archivo_adjunto.name))


@login_required
@role_required(Role.COORDINADOR, Role.DIRECTOR, Role.DOCENTE)
def staff_seguimiento(request):
    """7.x «Seguimiento»: interacciones y decisiones del cliente por alcance.

    Director global; coordinador de su área; docente solo de SUS casos
    (asignados como docente o tutor). Filtros: estado de aprobación, área,
    tipo de servicio y búsqueda por código/empresa."""
    user = request.user
    qs = (CitaAsesoria.objects
          .select_related('franja', 'cliente__empresa', 'docente_asignado',
                          'estudiante_apoyo')
          .prefetch_related('interacciones__autor'))
    if user.role == Role.COORDINADOR:
        qs = filtrar_citas_por_area(qs, area_coordinador(user))
    elif user.role == Role.DOCENTE:
        qs = qs.filter(Q(docente_asignado=user) | Q(estudiante_apoyo=user))

    enfoque = request.GET.get('enfoque', '')
    estado = request.GET.get('estado', '')
    tipo = request.GET.get('tipo', '')
    q = (request.GET.get('q') or '').strip()
    if estado in dict(CitaAsesoria.Estado.choices):
        qs = qs.filter(estado=estado)
    tipo_key = dict(TipoServicio.choices)
    if tipo in tipo_key:
        qs = qs.filter(tipo_servicio=tipo)
    if q:
        if q.isdigit():
            qs = qs.filter(pk=int(q))
        else:
            qs = qs.filter(Q(asunto__icontains=q)
                           | Q(cliente__empresa__razon_social__icontains=q))

    citas = list(qs.order_by('-actualizada_en')[:200])
    if enfoque == 'aprobacion':
        citas = [c for c in citas if c.entrega_pendiente]
    elif enfoque == 'ajustes':
        citas = [c for c in citas if c.ajustes_solicitados_total]
    elif enfoque == 'interaccion':
        citas = [c for c in citas if c.interacciones.exists()]

    resumen = {
        'con_entregas': sum(1 for c in citas
                            if c.interacciones.filter(
                                tipo=CitaInteraccion.Tipo.ENTREGA_RESULTADOS).exists()),
        'pendientes_aprobacion': sum(1 for c in citas if c.entrega_pendiente),
        'con_ajustes': sum(1 for c in citas if c.ajustes_solicitados_total),
    }
    return render(request, 'portal/staff_seguimiento.html', {
        'role_label': ('Seguimiento — ' + (Area(area_coordinador(user)).label
                       if user.role == Role.COORDINADOR else
                       ('global' if user.role == Role.DIRECTOR else 'mis casos'))),
        'citas': citas,
        'resumen': resumen,
        'f_enfoque': enfoque,
        'f_estado': estado,
        'f_tipo': tipo,
        'f_q': q,
        'estados': CitaAsesoria.Estado.choices,
        'tipos': [(k, v.split(' (')[0]) for k, v in tipo_key.items()],
        'tipo_labels': tipo_key,
    })
