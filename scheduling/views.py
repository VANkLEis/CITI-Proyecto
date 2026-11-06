from django.http import JsonResponse
from portal.models import CitaAsesoria, FranjaHoraria


def api_reservar(request):
    if request.method == 'POST':
        # Leemos los campos enviados por FormData
        franja_id = request.POST.get('franja_id')
        asunto = request.POST.get('asunto', '')
        subespecialidad = request.POST.get('subespecialidad', '')
        tipo_servicio = request.POST.get('tipo_servicio', 'orientacion')

        # Capturamos el archivo subido si existe
        archivo = request.FILES.get('archivo_adjunto')

        if not franja_id:
            return JsonResponse(
                {'ok': False, 'error': 'Debe seleccionar una franja.'}
            )

        try:
            franja = FranjaHoraria.objects.get(pk=franja_id)
            if not franja.esta_disponible:
                return JsonResponse(
                    {'ok': False, 'error': 'La franja ya no está disponible.'}
                )

            # Creamos la cita guardando el tipo de servicio y el archivo
            cita = CitaAsesoria.objects.create(
                franja=franja,
                cliente=request.user,
                asunto=asunto,
                subespecialidad=subespecialidad,
                tipo_servicio=tipo_servicio,
                archivo_adjunto=archivo,
            )

            return JsonResponse({
                'ok': True,
                'message': 'Solicitud de asesoría registrada correctamente.',
            })

        except FranjaHoraria.DoesNotExist:
            return JsonResponse(
                {'ok': False, 'error': 'La franja seleccionada no existe.'}
            )
        except Exception as e:
            return JsonResponse(
                {'ok': False, 'error': f'Error al guardar: {str(e)}'}
            )

    return JsonResponse(
        {'ok': False, 'error': 'Método no permitido.'}, status=405
    )