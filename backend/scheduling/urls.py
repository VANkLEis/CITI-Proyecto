from django.urls import path

from scheduling import views

app_name = 'scheduling'

urlpatterns = [
    path('api/eventos/', views.calendario_eventos_api, name='api_eventos'),
    path('api/reservar/', views.reservar_cita_api, name='api_reservar'),
]
