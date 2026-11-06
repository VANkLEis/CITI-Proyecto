from django.urls import path

from portal import views

app_name = 'portal'

urlpatterns = [
    path('', views.landing, name='landing'),
    path('panel/director/', views.director_dashboard, name='director_dashboard'),
    path('panel/coordinador/', views.coordinador_dashboard, name='coordinador_dashboard'),
    path(
        'panel/coordinador/asignar/<int:cita_id>/',
        views.coordinador_asignar,
        name='coordinador_asignar',
    ),
    path('panel/docente/', views.docente_dashboard, name='docente_dashboard'),
    path(
        'panel/docente/caso/<int:cita_id>/',
        views.docente_caso_detalle,
        name='docente_caso_detalle',
    ),
    path(
        'panel/docente/caso/<int:cita_id>/acta/',
        views.docente_generar_acta,
        name='docente_generar_acta',
    ),
    path('panel/estudiante/', views.estudiante_dashboard, name='estudiante_dashboard'),
    path(
        'panel/estudiante/caso/<int:cita_id>/nota/',
        views.estudiante_caso_nota,
        name='estudiante_caso_nota',
    ),
    path('panel/cliente/', views.cliente_dashboard, name='cliente_dashboard'),
    path(
        'panel/cliente/feedback/<int:cita_id>/',
        views.cliente_feedback,
        name='cliente_feedback',
    ),
    path(
        'panel/cita/<int:cita_id>/detalle/',
        views.cita_detalle_interactivo,
        name='cita_detalle',
    ),
]
