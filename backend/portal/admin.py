"""Admin del contenido público (Fase 05).

El Director CITI puede editar portafolio y talleres sin tocar código. Las
imágenes son opcionales: si no se sube ninguna se usa el respaldo de `static/`.
"""

from django.contrib import admin
from django.utils.html import format_html

from portal.models import ProyectoPortafolio, Taller


class ImagenPreviewMixin:
    @admin.display(description='Vista previa')
    def vista_previa(self, obj):
        if not obj.imagen_url:
            return '—'
        return format_html(
            '<img src="{}" alt="" style="height:54px;border-radius:6px;object-fit:cover;">',
            obj.imagen_url,
        )


@admin.register(ProyectoPortafolio)
class ProyectoPortafolioAdmin(ImagenPreviewMixin, admin.ModelAdmin):
    list_display = ('titulo', 'linea', 'organizacion', 'anio', 'destacado',
                    'publicado', 'orden', 'vista_previa')
    list_filter = ('publicado', 'destacado', 'linea')
    list_editable = ('destacado', 'publicado', 'orden')
    search_fields = ('titulo', 'organizacion', 'resumen', 'reto', 'solucion')
    prepopulated_fields = {'slug': ('titulo',)}
    readonly_fields = ('creado_en', 'actualizado_en', 'vista_previa')
    fieldsets = (
        ('Tarjeta pública', {'fields': (
            'titulo', 'slug', 'linea', 'organizacion', 'anio', 'resumen',
        )}),
        ('Caso completo', {'fields': ('reto', 'solucion', 'resultados')}),
        ('Cifras', {'fields': ('metricas',),
                    'description': 'JSON: [{"label": "Organizaciones", "valor": "12"}]'}),
        ('Imagen', {'fields': ('imagen', 'imagen_static', 'imagen_alt', 'vista_previa')}),
        ('Publicación', {'fields': ('destacado', 'publicado', 'orden')}),
        ('Auditoría', {'classes': ('collapse',),
                       'fields': ('creado_en', 'actualizado_en')}),
    )


@admin.register(Taller)
class TallerAdmin(ImagenPreviewMixin, admin.ModelAdmin):
    list_display = ('titulo', 'publico_objetivo', 'modalidad', 'nivel',
                    'duracion', 'activo', 'orden', 'vista_previa')
    list_filter = ('activo', 'publico_objetivo', 'modalidad', 'nivel')
    list_editable = ('activo', 'orden')
    search_fields = ('titulo', 'tematica', 'descripcion')
    prepopulated_fields = {'slug': ('titulo',)}
    readonly_fields = ('creado_en', 'actualizado_en', 'vista_previa')
    fieldsets = (
        ('Ficha pública', {'fields': (
            'titulo', 'slug', 'tematica', 'descripcion',
        )}),
        ('Dirigido a', {'fields': (
            'publico_objetivo', 'modalidad', 'nivel', 'duracion',
        )}),
        ('Temario', {'fields': ('puntos_clave',),
                     'description': 'JSON: una lista de 3 ideas clave, por ejemplo '
                                    '["Qué es la IA", "Casos de uso", "Buenas prácticas"]'}),
        ('Imagen', {'fields': ('imagen', 'imagen_static', 'imagen_alt', 'vista_previa')}),
        ('Publicación', {'fields': ('activo', 'orden')}),
        ('Auditoría', {'classes': ('collapse',),
                       'fields': ('creado_en', 'actualizado_en')}),
    )
