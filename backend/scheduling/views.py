import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.http import require_GET, require_POST

from accounts.models import Area, Role
from portal.decorators import role_required
from scheduling.area_styles import colores_para_area
from scheduling.models import CitaAsesoria, FranjaHoraria
from scheduling.subespecialidades import Subespecialidad


def _parse_range(request):
    start = parse_datetime(request.GET.get('start', ''))
    end = parse_datetime(request.GET.get('end', ''))
    if not start or not end:
        return None, None
    if timezone.is_naive(start):
        start = timezone.make_aware(start)
    if timezone.is_naive(end):
        end = timezone.make_aware(end)
    return start, end


@login_required
@role_required(Role.CLIENTE)
@require_GET
def calendario_eventos_api(request):
    start, end = _parse_range(request)
    if not start:
        return JsonResponse({'error': 'Parámetros start y end requeridos (ISO 8601).'}, status=400)

    franjas = FranjaHoraria.objects.filter(inicio__lt=end, fin__gt=start, activa=True)
    area_filtro = (request.GET.get('area') or '').strip()
    if area_filtro in dict(Area.choices):
        franjas = franjas.filter(area=area_filtro)

    events = []

    for franja in franjas:
        ocupados = franja.cupos_ocupados
        disponibles = franja.cupos_disponibles
        palette = colores_para_area(franja.area)
        base = {
            'id': f'franja-{franja.pk}',
            'start': franja.inicio.isoformat(),
            'end': franja.fin.isoformat(),
            'extendedProps': {
                'franja_id': franja.pk,
                'area': franja.area,
                'area_label': franja.get_area_display(),
                'cupos_disponibles': disponibles,
                'cupos_ocupados': ocupados,
            },
        }
        if disponibles > 0:
            events.append({
                **base,
                'title': f'Disponible ({disponibles}) — {franja.get_area_display()}',
                'backgroundColor': palette['disponible'],
                'borderColor': palette['borde'],
                'display': 'block',
                'extendedProps': {**base['extendedProps'], 'disponible': True},
            })
        else:
            events.append({
                **base,
                'title': f'Ocupado — {franja.get_area_display()}',
                'backgroundColor': '#94a3b8',
                'borderColor': '#64748b',
                'extendedProps': {**base['extendedProps'], 'disponible': False},
            })

    mis_citas = CitaAsesoria.objects.filter(
        cliente=request.user,
        estado__in=CitaAsesoria.Estado.ocupan_cupo() + (CitaAsesoria.Estado.FINALIZADA,),
        franja__inicio__lt=end,
        franja__fin__gt=start,
    ).select_related('franja')

    for cita in mis_citas:
        f = cita.franja
        if area_filtro in dict(Area.choices) and f.area != area_filtro:
            continue
        palette = colores_para_area(f.area)
        events.append({
            'id': f'cita-{cita.pk}',
            'title': f'Mi cita — {f.get_area_display()} — {cita.get_subespecialidad_display()}',
            'start': f.inicio.isoformat(),
            'end': f.fin.isoformat(),
            'backgroundColor': palette['cita'],
            'borderColor': palette['borde'],
            'extendedProps': {
                'cita_id': cita.pk,
                'franja_id': f.pk,
                'area': f.area,
                'area_label': f.get_area_display(),
                'propia': True,
            },
        })

    return JsonResponse(events, safe=False)


@login_required
@role_required(Role.CLIENTE)
@require_POST
def reservar_cita_api(request):
    # Al recibir multipart/form-data (FormData), leemos directamente desde request.POST y request.FILES
    franja_id = request.POST.get('franja_id')
    asunto = (request.POST.get('asunto') or 'Asesoría CITI').strip()[:255]
    subespecialidad = (request.POST.get('subespecialidad') or '').strip()
    tipo_servicio = request.POST.get('tipo_servicio', 'orientacion')
    archivo_adjunto = request.FILES.get('archivo_adjunto')

    if not franja_id:
        return JsonResponse({'ok': False, 'error': 'franja_id requerido.'}, status=400)

    franja = get_object_or_404(FranjaHoraria, pk=franja_id, activa=True)
    if not subespecialidad or not Subespecialidad.valid_for_area(subespecialidad, franja.area):
        return JsonResponse({
            'ok': False,
            'error': 'Seleccione una subespecialidad válida para el área.',
        }, status=400)

    if not franja.esta_disponible:
        return JsonResponse({'ok': False, 'error': 'La franja ya no está disponible.'}, status=409)

    if CitaAsesoria.objects.filter(
        franja=franja,
        cliente=request.user,
        estado__in=CitaAsesoria.Estado.ocupan_cupo(),
    ).exists():
        return JsonResponse({'ok': False, 'error': 'Ya tiene una solicitud activa en esta franja.'}, status=409)

    cita = CitaAsesoria(
        franja=franja,
        cliente=request.user,
        asunto=asunto,
        subespecialidad=subespecialidad,
        tipo_servicio=tipo_servicio,
        archivo_adjunto=archivo_adjunto,
        estado=CitaAsesoria.Estado.SOLICITADA,
    )
    try:
        cita.full_clean()
        cita.save()
    except Exception as exc:
        return JsonResponse({'ok': False, 'error': str(exc)}, status=400)

    return JsonResponse({
        'ok': True,
        'cita_id': cita.pk,
        'message': 'Solicitud registrada. El coordinador asignará un docente.',
        'start': franja.inicio.isoformat(),
        'end': franja.fin.isoformat(),
    })