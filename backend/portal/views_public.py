"""Vistas de la zona pública (Fase 05).

Solo leen contenido publicado y crean `SolicitudPublica`. Ninguna vista
pública siembra datos ni crea citas: el intake es explícito y el triage ocurre
en el panel privado.
"""

from datetime import timedelta

from django.contrib import messages
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import Area, Role
from portal.forms_public import SolicitudDiagnosticoForm, SolicitudTallerForm
from portal.models import (
    GRUPOS_PUBLICO, LineaPortafolio, ProyectoPortafolio, Taller,
)
from portal.role_routing import dashboard_url_for_role
from scheduling.models import SolicitudPublica
from scheduling.subespecialidades import Subespecialidad

# Ventana anti-duplicados del intake público: mismo correo + misma necesidad.
VENTANA_DUPLICADOS = timedelta(minutes=10)


def _catalogo_capacidades():
    """Catálogo real por área (4 Sistemas + 10 Civil). Sin inventar servicios."""
    return [
        {
            'value': Area.SISTEMAS,
            'label': 'Ingeniería de Sistemas',
            'descripcion': 'Software, datos, redes, ciberseguridad e inteligencia artificial.',
            'subespecialidades': Subespecialidad.choices_for_area(Area.SISTEMAS),
        },
        {
            'value': Area.CIVIL,
            'label': 'Ingeniería Civil',
            'descripcion': 'Estudios técnicos, materiales, geotecnia, vías y estructura.',
            'subespecialidades': Subespecialidad.choices_for_area(Area.CIVIL),
        },
    ]


def landing(request):
    proyectos = ProyectoPortafolio.objects.filter(publicado=True)[:3]
    talleres = Taller.objects.filter(activo=True)[:3]
    catalogo = _catalogo_capacidades()
    contexto = {
        'proyectos_destacados': proyectos,
        'talleres_destacados': talleres,
        'catalogo': catalogo,
        'total_proyectos': ProyectoPortafolio.objects.filter(publicado=True).count(),
        'total_talleres': Taller.objects.filter(activo=True).count(),
        'total_especialidades': sum(len(c['subespecialidades']) for c in catalogo),
        'mi_panel': (dashboard_url_for_role(request.user.role)
                     if request.user.is_authenticated and getattr(request.user, 'role', None)
                     else None),
    }
    return render(request, 'portal/index.html', contexto)


def portafolio_list(request):
    linea = (request.GET.get('linea') or '').strip()
    proyectos = ProyectoPortafolio.objects.filter(publicado=True)
    if linea in dict(LineaPortafolio.choices):
        proyectos = proyectos.filter(linea=linea)
    else:
        linea = ''

    conteo = dict(
        ProyectoPortafolio.objects.filter(publicado=True)
        .values_list('linea').annotate(n=Count('id')).values_list('linea', 'n'))

    lineas_con_conteo = [
        {'code': code, 'label': label, 'n': conteo.get(code, 0)}
        for code, label in LineaPortafolio.choices
    ]

    return render(request, 'portal/portafolio_list.html', {
        'proyectos': proyectos,
        'linea_activa': linea,
        'lineas_con_conteo': lineas_con_conteo,
        'total': sum(conteo.values()),
    })


def portafolio_detail(request, slug):
    proyecto = get_object_or_404(
        ProyectoPortafolio.objects.filter(publicado=True), slug=slug)
    relacionados = (ProyectoPortafolio.objects
                    .filter(publicado=True, linea=proyecto.linea)
                    .exclude(pk=proyecto.pk)[:3])
    return render(request, 'portal/portafolio_detail.html', {
        'proyecto': proyecto,
        'relacionados': relacionados,
    })


def talleres_list(request):
    publico = (request.GET.get('publico') or '').strip()
    grupos = [{'code': code, 'label': label}
              for code, label, _codigos in GRUPOS_PUBLICO]
    grupo = next((g for g in GRUPOS_PUBLICO if g[0] == publico), None)

    talleres = Taller.objects.filter(activo=True)
    if grupo:
        talleres = talleres.filter(publico_objetivo__in=grupo[2])
    else:
        publico = ''

    return render(request, 'portal/talleres_list.html', {
        'talleres': talleres,
        'publico_activo': publico,
        'grupos': grupos,
    })


def _duplicado_reciente(email, tipo_necesidad):
    return SolicitudPublica.objects.filter(
        email=email,
        tipo_necesidad=tipo_necesidad,
        creada_en__gte=timezone.now() - VENTANA_DUPLICADOS,
    ).exists()


def _registrar_y_agradecer(request, form):
    """Guarda el intake y deja el radicado en sesión para la pantalla de gracias."""
    if _duplicado_reciente(form.cleaned_data['email'],
                           form.instance.tipo_necesidad):
        messages.info(
            request,
            'Ya recibimos una solicitud con este correo en los últimos minutos. '
            'Te contactaremos con la información registrada.')
        return redirect('portal:solicitud_gracias')
    solicitud = form.save()
    request.session['solicitud_codigo'] = solicitud.codigo
    request.session['solicitud_es_taller'] = solicitud.es_taller
    return redirect('portal:solicitud_gracias')


def diagnostico_solicitud(request):
    form = SolicitudDiagnosticoForm(request.POST or None)
    if request.method == 'POST':
        if form.es_spam:
            return redirect('portal:solicitud_gracias')
        if form.is_valid():
            return _registrar_y_agradecer(request, form)
    return render(request, 'portal/diagnostico_form.html', {'form': form})


def taller_solicitud(request, slug=None):
    taller = None
    if slug:
        taller = get_object_or_404(Taller.objects.filter(activo=True), slug=slug)
    else:
        # Enlaces de tarjeta: /talleres/solicitar/?taller=<slug>. Un slug
        # inexistente se ignora (no rompe un enlace compartido).
        slug_query = (request.GET.get('taller') or '').strip()
        if slug_query:
            taller = Taller.objects.filter(activo=True, slug=slug_query).first()
    inicial = {'taller': taller} if taller else {}
    form = SolicitudTallerForm(request.POST or None, initial=inicial)
    if request.method == 'POST':
        if form.es_spam:
            return redirect('portal:solicitud_gracias')
        if form.is_valid():
            return _registrar_y_agradecer(request, form)
    return render(request, 'portal/taller_solicitud.html', {
        'form': form,
        'taller': taller,
    })


def solicitud_gracias(request):
    codigo = request.session.pop('solicitud_codigo', '')
    es_taller = request.session.pop('solicitud_es_taller', False)
    return render(request, 'portal/diagnostico_gracias.html', {
        'codigo': codigo,
        'es_taller': es_taller,
    })


def privacidad(request):
    return render(request, 'portal/privacidad.html')
