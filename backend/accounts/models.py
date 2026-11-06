from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from accounts.managers import CustomUserManager


class Role(models.TextChoices):
    DIRECTOR = 'director', 'Director CITI'
    COORDINADOR = 'coordinador', 'Coordinador de área'
    DOCENTE = 'docente', 'Docente asesor'
    ESTUDIANTE = 'estudiante', 'Estudiante'
    CLIENTE = 'cliente', 'Cliente / Empresa'


class StudentType(models.TextChoices):
    CONSULTOR = 'consultor', 'Consultor de recepción'
    TUTOR = 'tutor', 'Tutor de casos'


class Area(models.TextChoices):
    SISTEMAS = 'sistemas', 'Ingeniería de Sistemas'
    CIVIL = 'civil', 'Ingeniería Civil'
    MIXTO = 'mixto', 'Ambas áreas'


class Empresa(models.Model):
    razon_social = models.CharField(max_length=200)
    nit = models.CharField(max_length=20, blank=True)
    direccion = models.CharField(max_length=255, blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    sector = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'

    def __str__(self):
        return self.razon_social


class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, verbose_name='Correo electrónico')
    first_name = models.CharField(max_length=120, blank=True)
    last_name = models.CharField(max_length=120, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CLIENTE)
    student_type = models.CharField(
        max_length=20,
        choices=StudentType.choices,
        blank=True,
        null=True,
        help_text='Solo aplica si el rol es Estudiante.',
    )
    area = models.CharField(max_length=20, choices=Area.choices, blank=True, null=True)
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='usuarios',
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return self.email

    @property
    def nombre_completo(self):
        return f'{self.first_name} {self.last_name}'.strip() or self.email

    def clean(self):
        super().clean()
        if self.role == Role.ESTUDIANTE and not self.student_type:
            raise ValidationError(
                {'student_type': 'El estudiante debe tener tipo consultor o tutor.'}
            )
        if self.role != Role.ESTUDIANTE and self.student_type:
            raise ValidationError(
                {'student_type': 'Solo los usuarios con rol Estudiante pueden tener tipo.'}
            )
        if self.role == Role.ESTUDIANTE and self.student_type == StudentType.TUTOR:
            perfil = getattr(self, 'perfil_estudiante', None)
            if not perfil or not perfil.cumple_requisitos_tutor():
                raise ValidationError(
                    {'student_type': 'Solo estudiantes que cumplen los requisitos académicos pueden ser tutores.'}
                )
        if self.role == Role.CLIENTE and not self.empresa_id:
            raise ValidationError({'empresa': 'Los clientes deben estar vinculados a una empresa.'})

    def save(self, *args, **kwargs):
        if self.role != Role.ESTUDIANTE:
            self.student_type = None
        if kwargs.pop('skip_validation', False):
            return super().save(*args, **kwargs)
        self.full_clean()
        super().save(*args, **kwargs)


class PerfilEstudiante(models.Model):
    """
    Filtro académico: solo puede actuar como tutor/asesor si cumple umbrales configurables.
    """
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='perfil_estudiante',
        limit_choices_to={'role': Role.ESTUDIANTE},
    )
    semestre = models.PositiveIntegerField(
        default=0,
        help_text='Semestre académico actual. Mínimo 8 para ser tutor CITI.',
    )
    creditos_aprobados = models.PositiveIntegerField(default=0)
    promedio_general = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('5'))],
    )
    autorizado_como_tutor = models.BooleanField(
        default=False,
        help_text='Se actualiza según semestre, créditos y promedio mínimos.',
    )

    class Meta:
        verbose_name = 'Perfil de estudiante'
        verbose_name_plural = 'Perfiles de estudiantes'

    def __str__(self):
        return f'Perfil académico — {self.usuario.email}'

    def cumple_requisitos_tutor(self) -> bool:
        min_semestre = getattr(settings, 'CITI_MIN_SEMESTRE_TUTOR', 8)
        min_creditos = getattr(settings, 'CITI_MIN_CREDITOS_TUTOR', 130)
        min_promedio = Decimal(str(getattr(settings, 'CITI_MIN_PROMEDIO_TUTOR', '4.0')))
        return (
            self.semestre >= min_semestre
            and self.creditos_aprobados >= min_creditos
            and self.promedio_general >= min_promedio
        )

    def actualizar_autorizacion_tutor(self):
        """Sincroniza autorizado_como_tutor y tipo estudiante tutor/consultor."""
        puede = self.cumple_requisitos_tutor()
        self.autorizado_como_tutor = puede
        user = self.usuario
        if puede and user.student_type != StudentType.TUTOR:
            user.student_type = StudentType.TUTOR
            user.save(update_fields=['student_type'])
        elif not puede and user.student_type == StudentType.TUTOR:
            user.student_type = StudentType.CONSULTOR
            user.save(update_fields=['student_type'])
        return puede

    def clean(self):
        super().clean()
        if self.usuario.role != Role.ESTUDIANTE:
            raise ValidationError('El perfil académico solo aplica a usuarios con rol Estudiante.')
        if self.usuario.student_type == StudentType.TUTOR and not self.cumple_requisitos_tutor():
            min_s = getattr(settings, 'CITI_MIN_SEMESTRE_TUTOR', 8)
            min_c = getattr(settings, 'CITI_MIN_CREDITOS_TUTOR', 130)
            min_p = getattr(settings, 'CITI_MIN_PROMEDIO_TUTOR', '4.0')
            raise ValidationError(
                f'No cumple requisitos de tutor: mínimo {min_s}° semestre, '
                f'{min_c} créditos y promedio {min_p}.'
            )

    def save(self, *args, **kwargs):
        if (
            self.usuario_id
            and self.usuario.student_type == StudentType.TUTOR
            and not self.cumple_requisitos_tutor()
        ):
            self.usuario.student_type = StudentType.CONSULTOR
            self.usuario.save(update_fields=['student_type'])
        self.full_clean()
        super().save(*args, **kwargs)
        self.actualizar_autorizacion_tutor()
        super().save(update_fields=['autorizado_como_tutor'])
