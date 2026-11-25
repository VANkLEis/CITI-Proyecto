from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('portal.urls')),
    path('cuenta/', include('accounts.urls')),
    path('agenda/', include('scheduling.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif getattr(settings, 'CITI_SERVE_MEDIA', False):
    # Solo demo en contenedor (Gunicorn no sirve /media/). En un despliegue
    # real los medios los publica Nginx o un almacenamiento externo.
    urlpatterns += [
        path('media/<path:path>', serve, {'document_root': settings.MEDIA_ROOT}),
    ]