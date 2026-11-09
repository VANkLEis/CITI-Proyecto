from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from accounts.models import CustomUser, Empresa, PerfilEstudiante, Role


class PerfilEstudianteInline(admin.StackedInline):
    model = PerfilEstudiante
    can_delete = False
    extra = 0
    fields = ('semestre', 'creditos_aprobados', 'promedio_general', 'autorizado_como_tutor')
    readonly_fields = ('autorizado_como_tutor',)
    verbose_name = 'Perfil académico'
    verbose_name_plural = 'Perfil académico (controla elegibilidad de tutor)'


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    """Registro administrativo de usuarios. La creación de roles internos y
    la edición de credenciales ocurren SOLO aquí (el portal público solo
    registra clientes)."""
    ordering = ('email',)
    list_display = ('email', 'nombre_completo', 'rol_badge', 'student_type', 'area', 'is_active', 'es_staff')
    list_filter = ('role', 'student_type', 'area', 'is_active')
    search_fields = ('email', 'first_name', 'last_name', 'empresa__razon_social')

    def es_staff(self, obj):
        return 'sí' if obj.is_staff else '—'
    es_staff.short_description = 'Admin'

    def rol_badge(self, obj):
        color = {'director': '#0a2540', 'coordinador': '#6da020', 'docente': '#2563eb',
                 'estudiante': '#00a896', 'cliente': '#5f5e5e'}.get(obj.role, '#5f5e5e')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;border-radius:10px;'
            'font-size:11px;">{}</span>', color, obj.get_role_display())
    rol_badge.short_description = 'Rol'

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Datos personales', {'fields': ('first_name', 'last_name')}),
        ('Rol CITI', {
            'fields': ('role', 'student_type', 'area', 'empresa'),
            'description': 'student_type de estudiantes es promovido/degradado por el perfil académico; no lo fuerce.',
        }),
        ('Permisos Django', {
            'classes': ('collapse',),
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Fechas', {'classes': ('collapse',), 'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name',
                       'role', 'student_type', 'area', 'empresa'),
        }),
    )

    inlines = [PerfilEstudianteInline]

    def get_inlines(self, request, obj):
        if obj and obj.role == Role.ESTUDIANTE:
            return [PerfilEstudianteInline]
        return []


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('razon_social', 'nit', 'telefono', 'sector', 'n_clientes')
    search_fields = ('razon_social', 'nit')

    @admin.display(description='Contactos clientes')
    def n_clientes(self, obj):
        return obj.usuarios.filter(role=Role.CLIENTE).count()

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('usuarios')
