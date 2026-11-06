from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from accounts.models import CustomUser, Empresa, PerfilEstudiante, Role


class PerfilEstudianteInline(admin.StackedInline):
    model = PerfilEstudiante
    can_delete = False
    extra = 0
    fields = ('semestre', 'creditos_aprobados', 'promedio_general', 'autorizado_como_tutor')
    readonly_fields = ('autorizado_como_tutor',)


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    """
    Creación de Director, Coordinador, Docente y Estudiante solo desde /admin/.
    El registro público (/cuenta/registro/) limita rol Cliente.
    """
    ordering = ('email',)
    list_display = ('email', 'nombre_completo', 'role', 'student_type', 'area', 'is_active')
    list_filter = ('role', 'student_type', 'area', 'is_active')
    search_fields = ('email', 'first_name', 'last_name')

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Datos personales', {'fields': ('first_name', 'last_name')}),
        ('Rol CITI', {'fields': ('role', 'student_type', 'area', 'empresa')}),
        ('Permisos Django', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'first_name', 'last_name', 'role', 'student_type', 'area', 'empresa'),
        }),
    )

    inlines = [PerfilEstudianteInline]

    def get_inlines(self, request, obj):
        if obj and obj.role == Role.ESTUDIANTE:
            return [PerfilEstudianteInline]
        return []


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    search_fields = ('razon_social', 'nit')
