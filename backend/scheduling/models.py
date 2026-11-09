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

    # Tabla formal de transiciones (Fase 04 / I-2). Las aristas reflejan el
    # negocio real: el cliente puede cancelar antes de que el caso se cierre;
    # finalizada->en_proceso existe SOLO para la reapertura tras ajuste
    # solicitado por el cliente; no hay retrocesos manuales del equipo.
    TRANSICIONES = {
        'solicitada': {'asignada', 'cancelada'},
        'asignada': {'en_proceso', 'finalizada', 'cancelada', 'asignada'},
        'en_proceso': {'finalizada', 'cancelada'},
        'finalizada': {'en_proceso'},
        'cancelada': set(),
    }

    @classmethod
    def transicion_legal(cls, anterior, nuevo):
        return nuevo in cls.TRANSICIONES.get(anterior, set())

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
    # Marcas temporales de trazabilidad: se fijan SOLO al ocurrir la transición
    # real (vistas/API/admin). Null = nunca ocurrió / dato no disponible.
    asignada_en = models.DateTimeField(null=True, blank=True, editable=False)
    cerrada_en = models.DateTimeField(null=True, blank=True, editable=False)
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
    def resolucion_txt(self):
        """Texto legible del tiempo creation→cierre; '' si no está cerrada."""
        if not (self.cerrada_en and self.creada_en):
            return ''
        d = self.cerrada_en - self.creada_en
        dias, resto = divmod(int(d.total_seconds()), 86400)
        horas = resto // 3600
        if dias and horas:
            return f'{dias} d {horas} h'
        if dias:
            return f'{dias} d'
        if horas:
            return f'{horas} h'
        return f'{int(d.total_seconds() // 60)} min'

    @property
    def esta_cancelada(self):
        return self.estado == self.Estado.CANCELADA

    # --- Seguimiento de entregables (Fase 04) ---
    # Todo derivado de CitaInteraccion; no se desnormalizan estados para no
    # crear una segunda fuente de verdad.

    @property
    def entrega_pendiente(self):
        """Última 'entrega_resultados' visible al cliente AÚN sin decisión
        (aprobación o ajuste) posterior. None si no hay nada pendiente."""
        entregas = list(self.interacciones.filter(
            tipo=CitaInteraccion.Tipo.ENTREGA_RESULTADOS, para_cliente=True
        ).order_by('fecha', 'id'))
        if not entregas:
            return None
        ultima = entregas[-1]
        decidio = self.interacciones.filter(
            tipo__in=(CitaInteraccion.Tipo.APROBACION,
                      CitaInteraccion.Tipo.RECHAZO_AJUSTE),
            fecha__gte=ultima.fecha).exists()
        return None if decidio else ultima

    @property
    def pendiente_aprobacion(self):
        return self.entrega_pendiente is not None

    @property
    def ajustes_solicitados_total(self):
        return self.interacciones.filter(
            tipo=CitaInteraccion.Tipo.RECHAZO_AJUSTE).count()

    def puede_cancelar_cliente(self):
        """I-4: el cliente cancela mientras el caso no esté cerrado."""
        return self.estado in (CitaAsesoria.Estado.SOLICITADA,
                               CitaAsesoria.Estado.ASIGNADA)

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
        # I-6 (Fase 04): el tipo de servicio deja de ser decorativo. Una
        # consultoría especializada, al entrar en ejecución (asignada /
        # en_proceso / finalizada), debe tener docente responsable. Las
        # canceladas se eximen: pueden haber sido canceladas antes de asignar
        # (dato histórico real, no se reescribe).
        if (self.tipo_servicio == TipoServicio.CONSULTORIA_ESPECIALIZADA
                and self.estado in (self.Estado.ASIGNADA, self.Estado.EN_PROCESO,
                                    self.Estado.FINALIZADA)
                and not self.docente_asignado_id):
            raise ValidationError(
                'Una consultoría especializada requiere docente responsable antes '
                'de avanzar de solicitada (regla I-6).')
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


class CitaEvento(models.Model):
    """Historial auditable de cada solicitud (Fase 03, Módulo C).

    Registro SOLO desde el backend (vistas/API/admin); sin edición ni borrado
    para usuarios normales. `actor_label` conserva el identificador incluso si
    el usuario se elimina después.
    """

    class Tipo(models.TextChoices):
        CREADA = 'creada', 'Solicitud creada'
        REVISADA = 'revisada', 'Solicitud revisada'
        DOCENTE_ASIGNADO = 'docente_asignado', 'Docente asignado'
        TUTOR_ASIGNADO = 'tutor_asignado', 'Tutor asignado'
        ASIGNADA = 'asignada', 'Asignación completada'
        INICIADA = 'iniciada', 'Asesoría iniciada'
        ESTADO_CAMBIADO = 'estado_cambiado', 'Estado modificado'
        ARCHIVO_ADJUNTADO = 'archivo_adjuntado', 'Archivo adjuntado'
        FINALIZADA = 'finalizada', 'Asesoría finalizada'
        ACTA_REGISTRADA = 'acta_registrada', 'Acta registrada'
        FEEDBACK = 'feedback', 'Valoración del cliente'
        CANCELADA = 'cancelada', 'Solicitud cancelada'
        BITACORA = 'bitacora', 'Nota de bitácora'
        # Tipos Fase 04 (seguimiento e interacción con el cliente)
        INTERACCION = 'interaccion', 'Interacción con el cliente'
        ENTREGA_PUBLICADA = 'entrega_publicada', 'Entregable publicado'
        DECISION_CLIENTE = 'decision_cliente', 'Decisión del cliente sobre el entregable'

    cita = models.ForeignKey(CitaAsesoria, on_delete=models.CASCADE, related_name='eventos')
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='eventos_citas',
        verbose_name='Usuario responsable',
    )
    actor_label = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Actor (instantánea)',
        help_text='Correo capturado al momento del evento; sobrevive a la eliminación del usuario.',
    )
    tipo = models.CharField(max_length=34, choices=Tipo.choices)
    estado_anterior = models.CharField(max_length=20, blank=True)
    estado_nuevo = models.CharField(max_length=20, blank=True)
    descripcion = models.TextField(blank=True)
    metadata = models.JSONField(null=True, blank=True, default=None)
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Evento de solicitud'
        verbose_name_plural = 'Historial de eventos'
        ordering = ['fecha', 'id']
        indexes = [models.Index(fields=['cita', 'fecha'])]

    def __str__(self):
        return f'{self.get_tipo_display()} — cita {self.cita_id} ({self.fecha:%d/%m/%Y %H:%M})'

    @property
    def estado_nuevo_label(self):
        from scheduling.models import CitaAsesoria
        return dict(CitaAsesoria.Estado.choices).get(self.estado_nuevo, self.estado_nuevo)


class CitaInteraccion(models.Model):
    """Interacción cliente ↔ profesional sobre una solicitud (Fase 04).

    NO es un cambio de estado: los comentarios, entregas y decisiones viven
    aquí y se reflejan en el historial mediante CitaEvento (trazabilidad.py).
    `rol_autor` es una instantánea del rol al momento de escribir (el usuario
    podría cambiar de rol después). `para_cliente=False` marca notas técnicas
    internas del equipo (visibles para su área/dirección), manteniendo la
    visibilidad como dato consultable en servidor, no filtrada en el frontend.
    """

    class Tipo(models.TextChoices):
        GENERAL = 'general', 'Comentario general'
        OBSERVACION = 'observacion', 'Observación del profesional'
        RESPUESTA = 'respuesta', 'Respuesta del cliente'
        NOTA_INTERNA = 'nota_interna', 'Nota técnica interna (no visible al cliente)'
        AJUSTE = 'ajuste', 'Solicitud de ajuste (equipo)'
        ENTREGA_RESULTADOS = 'entrega_resultados', 'Entrega de resultados / entregable'
        APROBACION = 'aprobacion', 'Aprobación del cliente'
        RECHAZO_AJUSTE = 'rechazo_ajuste', 'Rechazo / solicitud de corrección'

    TIPOS_CLIENTE = ('general', 'respuesta', 'aprobacion', 'rechazo_ajuste')
    TIPOS_EQUIPO = ('observacion', 'nota_interna', 'ajuste', 'entrega_resultados')

    cita = models.ForeignKey(
        CitaAsesoria, on_delete=models.CASCADE, related_name='interacciones')
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='interacciones')
    rol_autor = models.CharField(max_length=20, blank=True, verbose_name='Rol (instantánea)')
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    texto = models.TextField()
    datos_extra = models.JSONField(
        null=True, blank=True, default=None,
        help_text='Ficha estructurada de consultoría: diagnostico, alcance, '
                  'metodologia, entregables, objetivos. Opcional por diseño.')
    para_cliente = models.BooleanField(default=True)
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Interacción de solicitud'
        verbose_name_plural = 'Interacciones (comentarios, entregables, aprobaciones)'
        ordering = ['fecha', 'id']
        indexes = [models.Index(fields=['cita', 'tipo'])]

    def __str__(self):
        return f'{self.get_tipo_display()} — cita {self.cita_id} ({self.fecha:%d/%m/%Y %H:%M})'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Normalizar temprano: clean()/full_clean() debe ver la visibilidad
        # correcta aunque la instancia se construya con esos kwargs.
        if self.tipo == self.Tipo.NOTA_INTERNA:
            self.para_cliente = False

    def clean(self):
        if self.tipo in self.TIPOS_CLIENTE and self.rol_autor != Role.CLIENTE:
            raise ValidationError('Ese tipo de interacción solo la puede escribir el cliente.')
        if self.tipo in self.TIPOS_EQUIPO and self.rol_autor not in (
                Role.DOCENTE, Role.ESTUDIANTE, Role.COORDINADOR):
            raise ValidationError('Ese tipo de interacción es del equipo profesional.')
        if self.tipo == self.Tipo.NOTA_INTERNA and self.para_cliente:
            raise ValidationError('Una nota técnica interna no puede ser visible al cliente.')

    def save(self, *args, **kwargs):
        # La visibilidad es una consecuencia del tipo, no una elección libre:
        # toda interacción no-interna es visible al cliente.
        if self.tipo == self.Tipo.NOTA_INTERNA:
            self.para_cliente = False
        else:
            self.para_cliente = True
        super().save(*args, **kwargs)
