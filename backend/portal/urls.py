from django.urls import path

from portal import views, views_public, views_solicitudes

app_name = 'portal'

urlpatterns = [
    # --- Zona pública (Fase 05) ---
    path('', views_public.landing, name='landing'),
    path('portafolio/', views_public.portafolio_list, name='portafolio'),
    path('portafolio/<slug:slug>/', views_public.portafolio_detail, name='portafolio_detail'),
    path('talleres/', views_public.talleres_list, name='talleres'),
    path('talleres/solicitar/', views_public.taller_solicitud, name='taller_solicitud'),
    path('talleres/<slug:slug>/solicitar/', views_public.taller_solicitud,
         name='taller_solicitud_especifico'),
    path('diagnostico/', views_public.diagnostico_solicitud, name='diagnostico'),
    path('diagnostico/gracias/', views_public.solicitud_gracias, name='diagnostico_gracias'),
    path('solicitud/gracias/', views_public.solicitud_gracias, name='solicitud_gracias'),
    path('privacidad/', views_public.privacidad, name='privacidad'),

    # --- Triage privado de solicitudes públicas ---
    path('panel/solicitudes/', views_solicitudes.solicitudes_publicas,
         name='solicitudes_publicas'),
    path('panel/solicitudes/<int:pk>/', views_solicitudes.solicitud_publica_detalle,
         name='solicitud_publica_detalle'),
    path('panel/solicitudes/<int:pk>/aprobar/', views_solicitudes.solicitud_publica_aprobar,
         name='solicitud_publica_aprobar'),
    path('panel/solicitudes/<int:pk>/rechazar/', views_solicitudes.solicitud_publica_rechazar,
         name='solicitud_publica_rechazar'),
    path('panel/solicitudes/<int:pk>/convertir/', views_solicitudes.solicitud_publica_convertir,
         name='solicitud_publica_convertir'),

    # --- Paneles privados existentes ---
    path('panel/director/', views.director_dashboard, name='director_dashboard'),
    path('panel/trazabilidad/', views.trazabilidad, name='trazabilidad'),
    path('panel/trazabilidad/exportar.csv', views.trazabilidad_csv, name='trazabilidad_csv'),
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
        'panel/cliente/mis-solicitudes/',
        views.cliente_mis_solicitudes,
        name='cliente_mis_solicitudes',
    ),
    path(
        'panel/cliente/solicitud/<int:cita_id>/seguimiento/',
        views.cliente_seguimiento,
        name='cliente_seguimiento',
    ),
    path(
        'panel/cliente/notificaciones/',
        views.cliente_notificaciones,
        name='cliente_notificaciones',
    ),
    path(
        'panel/cliente/feedback/<int:cita_id>/',
        views.cliente_feedback,
        name='cliente_feedback',
    ),
    path('panel/perfil/', views.perfil_propio, name='perfil'),
    path(
        'panel/seguimiento/',
        views.staff_seguimiento,
        name='staff_seguimiento',
    ),
    path(
        'panel/cita/<int:cita_id>/adjunto/',
        views.cita_adjunto,
        name='cita_adjunto',
    ),
    path(
        'panel/cita/<int:cita_id>/detalle/',
        views.cita_detalle_interactivo,
        name='cita_detalle',
    ),
]
