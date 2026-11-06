from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from accounts.models import Area, Role, StudentType
from scheduling.subespecialidades import Subespecialidad


class FranjaHoraria(models.Model):
    """Ventana de tiempo disponible para agendar asesoría en el CITI."""
    inicio = models.DateTimeField()
    fin = models.DateTimeField()
    area = models.CharField(max_length=20, choices=Area.choices, default=Area.SISTEMAS)
    capacidad = models.PositiveSmallIntegerField(default=1)
    activa = models.BooleanField(default=True)
    creada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='franjas_creadas',
    )

    class Meta:
        verbose_name = 'Franja horaria'
        verbose_name_plural = 'Franjas horarias'
        ordering = ['inicio']
        indexes = [models.Index(fields=['inicio', 'fin'])]

    def __str__(self):
        return f'{self.inicio:%Y-%m-%d %H:%M} — {self.get_area_display()}'

    def clean(self):
        if self.fin <= self.inicio:
            raise ValidationError('La hora de fin debe ser posterior al inicio.')
        if self.inicio < timezone.now() and self.pk is None:
            raise ValidationError('No se pueden crear franjas en el pasado.')

    @property
    def cupos_ocupados(self):
        return self.citas.filter(
            estado__in=CitaAsesoria.Estado.ocupan_cupo()
        ).count()

    @property
    def cupos_disponibles(self):
        return max(0, self.capacidad - self.cupos_ocupados)

    @property
    def esta_disponible(self):
        return self.activa and self.cupos_disponibles > 0 and self.inicio > timezone.now()


class TipoServicio(models.TextChoices):
    ORIENTACION_TECNICA = 'orientacion', 'Orientación Técnica / Especificaciones (Atendido por Estudiante)'
    CONSULTORIA_ESPECIALIZADA = 'especializada', 'Consultoría Especializada / Proyecto (Atendido por Docente)'


class CitaAsesoria(models.Model):
    class Estado(models.TextChoices):
        SOLICITADA = 'solicitada', 'Solicitada'
        ASIGNADA = 'asignada', 'Asignada'
        EN_PROCESO = 'en_proceso', 'En proceso'
        FINALIZADA = 'finalizada', 'Finalizada'
        CANCELADA = 'cancelada', 'Cancelada'

        @classmethod
        def ocupan_cupo(cls):
            return (cls.SOLICITADA, cls.ASIGNADA, cls.EN_PROCESO)

    franja = models.ForeignKey(FranjaHoraria, on_delete=models.CASCADE, related_name='citas')
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='citas_asesoria',
        limit_choices_to={'role': Role.CLIENTE},
    )
    asunto = models.CharField(max_length=255, blank=True)
    subespecialidad = models.CharField(max_length=30, blank=True)
    tipo_servicio = models.CharField(
        max_length=30,
        choices=TipoServicio.choices,
        default=TipoServicio.ORIENTACION_TECNICA,
        help_text='Define el alcance y quién lidera la atención.'
    )
    archivo_adjunto = models.FileField(
        upload_to='documentos_citas/%Y/%m/',
        blank=True,
        null=True,
        help_text='Documentación base o requerimientos subidos por el cliente.'
    )
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.SOLICITADA,
    )
    docente_asignado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='citas_docente',
        limit_choices_to={'role': Role.DOCENTE},
    )
    estudiante_apoyo = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='citas_apoyo_estudiante',
        limit_choices_to={'role': Role.ESTUDIANTE, 'student_type': StudentType.TUTOR},
    )
    resumen_cierre = models.TextField(blank=True, help_text='Notas finales del docente al cerrar el caso.')
    calificacion = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    comentario_cliente = models.TextField(blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cita de asesoría'
        verbose_name_plural = 'Citas de asesoría'
        constraints = [
            models.UniqueConstraint(
                fields=['franja', 'cliente'],
                condition=Q(estado__in=['solicitada', 'asignada', 'en_proceso']),
                name='unique_cita_activa_por_cliente_franja',
            ),
        ]

    def __str__(self):
        return f'Cita {self.cliente.email} — {self.franja}'

    @property
    def area(self):
        return self.franja.area

    @property
    def nit_empresa(self):
        if self.cliente.empresa_id:
            return self.cliente.empresa.nit or '—'
        return '—'

    def get_subespecialidad_display(self):
        return Subespecialidad.label(self.subespecialidad) if self.subespecialidad else '—'

    @property
    def timeline(self):
        """Pasos del flujo con estado alcanzado y fecha disponible."""
        pasos = (
            (self.Estado.SOLICITADA, 'Solicitada'),
            (self.Estado.ASIGNADA, 'Asignada'),
            (self.Estado.EN_PROCESO, 'En proceso'),
            (self.Estado.FINALIZADA, 'Finalizada'),
        )
        orden = [estado for estado, _ in pasos]
        try:
            actual_idx = orden.index(self.estado)
        except ValueError:
            actual_idx = -1

        resultado = []
        for idx, (estado, label) in enumerate(pasos):
            hecho = actual_idx >= idx
            actual = actual_idx == idx
            if idx == 0:
                fecha = self.creada_en
            elif actual:
                fecha = self.actualizada_en
            else:
                fecha = None
            resultado.append({
                'estado': estado,
                'label': label,
                'hecho': hecho,
                'actual': actual,
                'fecha': fecha,
            })
        return resultado

    @property
    def esta_cancelada(self):
        return self.estado == self.Estado.CANCELADA

    def clean(self):
        if self.cliente.role != Role.CLIENTE:
            raise ValidationError('Solo usuarios con rol Cliente pueden reservar citas.')
        if self.subespecialidad and not Subespecialidad.valid_for_area(
            self.subespecialidad, self.franja.area
        ):
            raise ValidationError(
                {'subespecialidad': 'La subespecialidad no corresponde al área de la franja.'}
            )
        if self.estado == self.Estado.SOLICITADA and not self.pk and not self.franja.esta_disponible:
            raise ValidationError('La franja seleccionada ya no tiene cupos disponibles.')
        if self.docente_asignado_id:
            if self.docente_asignado.role != Role.DOCENTE:
                raise ValidationError('El docente asignado debe tener rol Docente.')
            if self.docente_asignado.area not in (self.franja.area, Area.MIXTO):
                raise ValidationError('El docente debe pertenecer al área de la asesoría.')
        if self.estudiante_apoyo_id:
            if self.estudiante_apoyo.role != Role.ESTUDIANTE:
                raise ValidationError('El apoyo debe ser un estudiante.')
            perfil = getattr(self.estudiante_apoyo, 'perfil_estudiante', None)
            if (
                self.estudiante_apoyo.student_type != StudentType.TUTOR
                or not perfil
                or not perfil.cumple_requisitos_tutor()
            ):
                raise ValidationError(
                    'El estudiante de apoyo debe cumplir los requisitos CITI: '
                    'semestre, promedio y créditos mínimos.'
                )
            if self.estudiante_apoyo.area not in (self.franja.area, Area.MIXTO):
                raise ValidationError('El estudiante debe pertenecer al área de la asesoría.')


class NotaBitacora(models.Model):
    cita = models.ForeignKey(CitaAsesoria, on_delete=models.CASCADE, related_name='notas')
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notas_bitacora',
    )
    texto = models.TextField()
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Nota de bitácora'
        verbose_name_plural = 'Notas de bitácora'
        ordering = ['-creada_en']

    def __str__(self):
        return f'Nota {self.pk} — cita {self.cita_id}'
