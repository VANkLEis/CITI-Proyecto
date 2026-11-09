from django import forms
from django.contrib import admin, messages
from django.utils import timezone

from accounts.models import Area
from scheduling.models import CitaAsesoria, CitaEvento, CitaInteraccion, FranjaHoraria, NotaBitacora
from scheduling.trazabilidad import cambio_estado, registrar_evento


class CitaEventoInline(admin.TabularInline):
    model = CitaEvento
    extra = 0
    can_delete = False
    fields = ('fecha', 'tipo', 'actor_label', 'estado_anterior', 'estado_nuevo', 'descripcion')
    readonly_fields = ('fecha', 'tipo', 'actor_label', 'estado_anterior', 'estado_nuevo', 'descripcion')

    def has_add_permission(self, request, obj=None):
        return False  # los eventos solo se generan desde el backend


class CitaInteraccionInline(admin.TabularInline):
    """Interacciones del portal (comentarios, entregables, decisiones).

    Solo lectura: su autoría y trazabilidad dependen del flujo autenticado del
    portal; crearlas desde admin rompería la correspondencia actor/rol."""
    model = CitaInteraccion
    extra = 0
    can_delete = False
    fields = ('fecha', 'autor', 'rol_autor', 'tipo', 'para_cliente', 'texto')
    readonly_fields = ('fecha', 'autor', 'rol_autor', 'tipo', 'para_cliente', 'texto')

    def has_add_permission(self, request, obj=None):
        return False


class NotaBitacoraInline(admin.TabularInline):
    model = NotaBitacora
    extra = 0
    fields = ('creada_en', 'autor', 'texto')
    readonly_fields = ('creada_en',)

    def has_add_permission(self, request, obj=None):
        return False  # la bitácora se escribe desde el portal


class CitaAsesoriaAdminForm(forms.ModelForm):
    """Valida reglas de negocio del cierre: no se finaliza sin resumen."""

    class Meta:
        model = CitaAsesoria
        fields = '__all__'

    def clean(self):
        data = super().clean()
        if data.get('estado') == CitaAsesoria.Estado.FINALIZADA and not data.get('resumen_cierre'):
            self.add_error('resumen_cierre', 'Para finalizar se requiere el resumen de cierre '
                                             '(consistencia con el portal).')
        return data


@admin.register(CitaAsesoria)
class CitaAsesoriaAdmin(admin.ModelAdmin):
    form = CitaAsesoriaAdminForm
    list_display = (
        'codigo', 'empresa', 'franja', 'area_franja', 'subespecialidad',
        'estado', 'docente_asignado', 'calificacion', 'creada_en',
    )
    list_filter = ('estado', 'franja__area', 'tipo_servicio', 'subespecialidad')
    search_fields = ('cliente__empresa__razon_social', 'asunto', 'id')
    raw_id_fields = ('cliente', 'franja', 'docente_asignado', 'estudiante_apoyo')
    date_hierarchy = 'creada_en'
    ordering = ('-creada_en',)
    autocomplete_fields = ()
    inlines = [NotaBitacoraInline, CitaInteraccionInline, CitaEventoInline]
    readonly_fields = ('creada_en', 'actualizada_en', 'asignada_en', 'cerrada_en')
    fieldsets = (
        ('Solicitud', {'fields': ('franja', 'cliente', 'asunto', 'subespecialidad', 'tipo_servicio')}),
        ('Documentación', {'fields': ('archivo_adjunto',)}),
        ('Asignación de responsables', {'fields': ('docente_asignado', 'estudiante_apoyo')}),
        ('Estado y cierre', {'fields': ('estado', 'resumen_cierre', 'calificacion', 'comentario_cliente')}),
        ('Marcas de tiempo', {'classes': ('collapse',),
                              'fields': ('creada_en', 'asignada_en', 'cerrada_en', 'actualizada_en')}),
    )
    actions = ['cancelar_solicitudes', 'marcar_revisadas']

    def has_delete_permission(self, request, obj=None):
        """Las solicitudes llevan attached su historial y bitácoras: borrarlas
        rompería la trazabilidad. Solo un superusuario puede granularlas."""
        if not request.user.is_superuser:
            return False
        return super().has_delete_permission(request, obj)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'cliente__empresa', 'franja', 'docente_asignado', 'estudiante_apoyo')

    @admin.display(description='Código')
    def codigo(self, obj):
        return f'CITI-{obj.pk:05d}'

    @admin.display(description='Empresa')
    def empresa(self, obj):
        return obj.cliente.empresa.razon_social if obj.cliente.empresa_id else obj.cliente.email

    @admin.display(description='Área', ordering='franja__area')
    def area_franja(self, obj):
        return obj.franja.get_area_display()

    def save_model(self, request, obj, form, changed):
        """Los cambios administrativos de estado generan su evento, con las
        mismas marcas temporales que el portal (una única verdad)."""
        anterior = CitaAsesoria.objects.filter(pk=obj.pk).values_list('estado', flat=True).first()
        super().save_model(request, obj, form, changed)
        if changed and obj.pk and anterior and anterior != obj.estado:
            # cambio_estado re-salva con validación completa; anterior != estado
            obj.estado = anterior
            cambio_estado(obj, request.user, form.cleaned_data['estado'],
                          descripcion='Cambio registrado desde el panel administrativo.')

    @admin.action(description='Cancelar solicitudes seleccionadas (registra evento)')
    def cancelar_solicitudes(self, request, queryset):
        cancelables = queryset.exclude(
            estado__in=(CitaAsesoria.Estado.FINALIZADA, CitaAsesoria.Estado.CANCELADA))
        omitidas = queryset.count() - cancelables.count()
        for cita in cancelables:
            cambio_estado(cita, request.user, CitaAsesoria.Estado.CANCELADA,
                          descripcion='Cancelada desde el panel administrativo.')
        texto = f'{cancelables.count()} solicitud(es) canceladas con registro en el historial.'
        if omitidas:
            texto += f' Se omitieron {omitidas} ya finalizadas/canceladas.'
        self.message_user(request, texto,
                          messages.WARNING if omitidas else messages.INFO)

    @admin.action(description='Marcar como revisadas (deja constancia en el historial)')
    def marcar_revisadas(self, request, queryset):
        n = 0
        for cita in queryset:
            registrar_evento(cita, request.user, CitaEvento.Tipo.REVISADA,
                             descripcion='Revisión realizada desde el panel administrativo.',
                             anterior=cita.estado, nuevo=cita.estado)
            n += 1
        self.message_user(request, f'{n} solicitud(es) marcadas como revisadas en el historial.')


@admin.register(CitaEvento)
class CitaEventoAdmin(admin.ModelAdmin):
    """Historial auditable: solo lectura (integridad del registro)."""
    list_display = ('fecha', 'cita', 'tipo', 'actor_label', 'estado_anterior', 'estado_nuevo')
    list_filter = ('tipo', 'estado_nuevo')
    search_fields = ('cita__id', 'actor_label', 'descripcion')
    date_hierarchy = 'fecha'
    ordering = ('-fecha',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CitaInteraccion)
class CitaInteraccionAdmin(admin.ModelAdmin):
    """Comunicaciones del portal: solo lectura y filtrado (Fase 04)."""
    list_display = ('fecha', 'cita', 'tipo', 'autor', 'rol_autor', 'para_cliente')
    list_filter = ('tipo', 'para_cliente', 'rol_autor')
    search_fields = ('cita__id', 'texto', 'autor__email')
    date_hierarchy = 'fecha'
    ordering = ('-fecha',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(FranjaHoraria)
class FranjaHorariaAdmin(admin.ModelAdmin):
    list_display = ('inicio', 'fin', 'area', 'capacidad', 'cupos_ocupados', 'cupos_disponibles',
                    'activa', 'futuro')
    list_filter = ('area', 'activa')
    date_hierarchy = 'inicio'
    ordering = ('inicio',)
    autocomplete_fields = ()

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('creada_por')

    @admin.display(boolean=True, description='Futura')
    def futuro(self, obj):
        return obj.inicio > timezone.now()
