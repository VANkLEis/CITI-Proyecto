from django.apps import AppConfig


class PortalConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'portal'
    verbose_name = 'Portales del CITI'

    def ready(self):
        # Identidad institucional del sitio administrativo nativo (Módulo B).
        # No se sustituye el site por uno propio para conservar señales de
        # admin y atajos estándar del proyecto.
        from django.contrib import admin

        admin.site.site_header = 'Administración CITI — UCC'
        admin.site.site_title = 'CITI Admin'
        admin.site.index_title = 'Gestión de registros del consultorio'
