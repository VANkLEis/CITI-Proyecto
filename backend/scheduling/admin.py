from django.contrib import admin

from scheduling.models import CitaAsesoria, FranjaHoraria, NotaBitacora


@admin.register(FranjaHoraria)
class FranjaHorariaAdmin(admin.ModelAdmin):
    list_display = ('inicio', 'fin', 'area', 'capacidad', 'activa', 'cupos_disponibles')
    list_filter = ('area', 'activa')


@admin.register(CitaAsesoria)
class CitaAsesoriaAdmin(admin.ModelAdmin):
    list_display = (
        'cliente', 'franja', 'subespecialidad', 'estado',
        'docente_asignado', 'calificacion', 'creada_en',
    )
    list_filter = ('estado', 'franja__area', 'subespecialidad')
    raw_id_fields = ('docente_asignado', 'estudiante_apoyo', 'cliente', 'franja')


@admin.register(NotaBitacora)
class NotaBitacoraAdmin(admin.ModelAdmin):
    list_display = ('cita', 'autor', 'creada_en')
    raw_id_fields = ('cita', 'autor')
