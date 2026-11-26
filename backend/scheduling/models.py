import secrets

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import (
    FileExtensionValidator, MaxValueValidator, MinValueValidator)
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from accounts.models import Area, Role, StudentType
from scheduling.subespecialidades import Subespecialidad
from scheduling.validators import ALLOWED_EXTENSIONS, validate_adjunto_size


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


class LineaAtencion(models.TextChoices):
    """Clasificación del alcance de la atención (Fase 05 - triage público).

    Es la etiqueta que ve el solicitante y la que decide quién lidera el caso:
    proyección social = acompañamiento con estudiante tutor + dirección docente;
    consultoría profesional = docente responsable con entregables formales.
    """
    PROYECCION_SOCIAL = 'proyeccion_social', 'Proyección y Extensión Social'
    CONSULTORIA_PROFESIONAL = 'consultoria_profesional', 'Consultoría Profesional'


class TipoServicio(models.TextChoices):
    ORIENTACION_TECNICA = 'orientacion', 'Orientación Técnica / Especificaciones (Atendido por Estudiante)'
    CONSULTORIA_ESPECIALIZADA = 'especializada', 'Consultoría Especializada / Proyecto (Atendido por Docente)'


# Correspondencia única línea -> tipo de servicio. El tipo de servicio es el
# que dispara las reglas operativas (I-6 exige docente en consultoría), por eso
# se deriva de la línea y no se captura por separado.
LINEA_A_TIPO_SERVICIO = {
    LineaAtencion.PROYECCION_SOCIAL: TipoServicio.ORIENTACION_TECNICA,
    LineaAtencion.CONSULTORIA_PROFESIONAL: TipoServicio.CONSULTORIA_ESPECIALIZADA,
}


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
    linea_atencion = models.CharField(
        max_length=30,
        choices=LineaAtencion.choices,
        blank=True,
        default='',
        help_text='Proyección social o consultoría profesional. Se deriva del tipo de servicio.',
    )
    archivo_adjunto = models.FileField(
        upload_to='documentos_citas/%Y/%m/',
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(allowed_extensions=ALLOWED_EXTENSIONS),
            validate_adjunto_size,
        ],
        help_text='Documentación base o requerimientos subidos por el cliente '
                  '(PDF, Word, Excel, TXT o imagen; máximo 10 MB).'
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
        if self.linea_atencion:
            esperado = LINEA_A_TIPO_SERVICIO.get(self.linea_atencion)
            if esperado and self.tipo_servicio != esperado:
                raise ValidationError({
                    'linea_atencion': 'La línea de atención no corresponde al tipo de servicio.'
                })
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


class SolicitudPublica(models.Model):
    """Intake público previo a la cita (Fase 05).

    El formulario de la web pública NO crea `CitaAsesoria`: registra aquí la
    necesidad, el tipo de solicitante y una preferencia de fecha. El triage
    (Director / Coordinador) aprueba el alcance y, solo para asesorías y
    consultorías, convierte la solicitud en una cita con cliente, franja y
    equipo asignado. Los talleres se aprueban y quedan cerrados aquí.

    Por qué no se crea la cita directamente: `CitaAsesoria.cliente` es
    obligatorio y su `clean()` exige rol Cliente con empresa. Permitir citas
    anónimas obligaría a hacer nullable esa FK y a inventar cuentas fantasma.
    """

    class TipoSolicitante(models.TextChoices):
        EMPRESA = 'empresa', 'Empresa / Pyme'
        FUNDACION = 'fundacion', 'Fundación / ONG'
        EMPRENDIMIENTO = 'emprendimiento', 'Emprendimiento juvenil'
        COMUNIDAD = 'comunidad', 'Grupo de pensionados / adultos mayores'
        OTRO = 'otro', 'Comunidad / Otro'

    class TipoNecesidad(models.TextChoices):
        ASESORIA = 'asesoria', 'Orientación / Diagnóstico inicial'
        CONSULTORIA = 'consultoria', 'Desarrollo o estudio técnico a medida'
        CAPACITACION = 'capacitacion', 'Charla, capacitación o taller grupal'

    class Madurez(models.TextChoices):
        IDEA = 'idea', 'Solo tengo una idea inicial'
        PROCESO = 'proceso', 'Tengo un proceso que quiero mejorar'
        REQUERIMIENTOS = 'requerimientos', 'Ya tengo requerimientos definidos para desarrollar'

    class Estado(models.TextChoices):
        RECIBIDA = 'recibida', 'Recibida'
        EN_REVISION = 'en_revision', 'En revisión'
        APROBADA = 'aprobada', 'Aprobada'
        CONVERTIDA = 'convertida', 'Convertida en cita'
        RECHAZADA = 'rechazada', 'Rechazada'

    class Turno(models.TextChoices):
        MANANA = 'manana', 'Mañana'
        TARDE = 'tarde', 'Tarde'
        INDIFERENTE = 'indiferente', 'Indiferente'

    class Modalidad(models.TextChoices):
        PRESENCIAL = 'presencial', 'Presencial'
        VIRTUAL = 'virtual', 'Virtual'
        INDIFERENTE = 'indiferente', 'Indiferente'

    # Misma disciplina que CitaAsesoria.TRANSICIONES: una sola tabla, aplicada
    # por los servicios de triage. `recibida -> aprobada` existe para talleres,
    # que se aprueban sin pasar por conversión.
    TRANSICIONES = {
        'recibida': {'en_revision', 'aprobada', 'rechazada'},
        'en_revision': {'aprobada', 'rechazada'},
        'aprobada': {'convertida', 'rechazada'},
        'convertida': set(),
        'rechazada': set(),
    }

    @classmethod
    def transicion_legal(cls, anterior, nuevo):
        return nuevo in cls.TRANSICIONES.get(anterior, set())

    codigo = models.CharField(
        max_length=20, unique=True, editable=False, blank=True,
        help_text='Radicado público generado automáticamente (SOL-XXXXXXXX).',
    )
    nombre_contacto = models.CharField(max_length=150)
    cargo = models.CharField(max_length=120, blank=True)
    organizacion = models.CharField(max_length=200)
    nit = models.CharField(max_length=20, blank=True)
    email = models.EmailField()
    telefono = models.CharField(max_length=30, blank=True)
    tipo_solicitante = models.CharField(
        max_length=20, choices=TipoSolicitante.choices,
        default=TipoSolicitante.EMPRESA)
    tipo_necesidad = models.CharField(
        max_length=20, choices=TipoNecesidad.choices,
        default=TipoNecesidad.ASESORIA)
    madurez = models.CharField(
        max_length=20, choices=Madurez.choices, blank=True, default='',
        help_text='Estado de madurez declarado por el solicitante.')
    linea_atencion = models.CharField(
        max_length=30, choices=LineaAtencion.choices, blank=True, default='',
        help_text='Se deriva del tipo de necesidad; el triage puede ajustarla.')
    area = models.CharField(
        max_length=20, choices=Area.choices, default=Area.MIXTO,
        help_text='Mixto = el solicitante no está seguro del área.')
    subespecialidad = models.CharField(max_length=30, blank=True)
    descripcion = models.TextField(help_text='Reto o necesidad concreta.')
    objetivo = models.TextField(blank=True, help_text='Resultado esperado.')
    # Solo talleres / capacitaciones
    publico_objetivo = models.CharField(max_length=150, blank=True)
    numero_participantes = models.PositiveSmallIntegerField(null=True, blank=True)
    taller = models.ForeignKey(
        'portal.Taller', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='solicitudes',
        help_text='Taller del catálogo, si el solicitante eligió uno.')
    tema_interes = models.CharField(
        max_length=200, blank=True,
        help_text='Tema propuesto cuando no elige un taller del catálogo.')
    fecha_preferida = models.DateField(null=True, blank=True)
    turno_preferido = models.CharField(
        max_length=15, choices=Turno.choices, default=Turno.INDIFERENTE)
    modalidad_preferida = models.CharField(
        max_length=15, choices=Modalidad.choices, default=Modalidad.INDIFERENTE)
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.RECIBIDA)
    observaciones_internas = models.TextField(blank=True)
    motivo_rechazo = models.TextField(blank=True)
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='solicitudes_publicas',
        help_text='Cliente vinculado o creado durante el triage.')
    cita = models.OneToOneField(
        CitaAsesoria, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='solicitud_origen',
        help_text='Cita creada al convertir la solicitud (nunca en talleres).')
    revisada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='solicitudes_revisadas')
    revisada_en = models.DateTimeField(null=True, blank=True)
    aprobada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='solicitudes_aprobadas')
    aprobada_en = models.DateTimeField(null=True, blank=True)
    convertida_en = models.DateTimeField(null=True, blank=True)
    acepta_contacto = models.BooleanField(
        default=False,
        help_text='Consentimiento para ser contactado por el CITI.')
    creada_en = models.DateTimeField(auto_now_add=True, db_index=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Solicitud pública'
        verbose_name_plural = 'Solicitudes públicas'
        ordering = ['-creada_en']
        indexes = [
            models.Index(fields=['estado', 'creada_en']),
            models.Index(fields=['linea_atencion']),
        ]

    def __str__(self):
        return f'{self.codigo} — {self.organizacion}'

    def get_absolute_url(self):
        return reverse('portal:solicitud_publica_detalle', args=[self.pk])

    @staticmethod
    def linea_para(tipo_necesidad):
        """La consultoría técnica es profesional; asesoría y taller son sociales."""
        if tipo_necesidad == SolicitudPublica.TipoNecesidad.CONSULTORIA:
            return LineaAtencion.CONSULTORIA_PROFESIONAL
        return LineaAtencion.PROYECCION_SOCIAL

    @property
    def linea_sugerida(self):
        """Pre-clasificación derivada de la necesidad declarada (no editable)."""
        return self.linea_para(self.tipo_necesidad)

    @property
    def accion_sugerida(self):
        """Guía de un renglón para el triage del Director/Coordinador."""
        if self.tipo_necesidad == self.TipoNecesidad.CAPACITACION:
            return ('Aprobar y coordinar fecha con la organización. '
                    'Una capacitación no genera cita en el calendario.')
        if self.linea_sugerida == LineaAtencion.CONSULTORIA_PROFESIONAL:
            return ('Convertir en cita y asignar docente responsable + estudiantes '
                    'tutores; cronograma por hitos y acta de cierre.')
        return ('Aprobar como orientación o mentoría; asignar estudiante tutor '
                'con dirección docente.')

    def _generar_codigo(self):
        for _ in range(20):
            candidato = f'SOL-{secrets.token_hex(4).upper()}'
            if not SolicitudPublica.objects.filter(codigo=candidato).exists():
                return candidato
        raise ValidationError('No fue posible generar un radicado único.')

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        if not self.linea_atencion:
            self.linea_atencion = self.linea_para(self.tipo_necesidad)
        if not self.codigo:
            self.codigo = self._generar_codigo()
        super().save(*args, **kwargs)

    def clean(self):
        if self.tipo_necesidad == self.TipoNecesidad.CAPACITACION:
            if not (self.taller_id or self.tema_interes.strip()):
                raise ValidationError({
                    'tema_interes': 'Indica el taller del catálogo o el tema de interés.'
                })
        if self.cita_id and self.tipo_necesidad == self.TipoNecesidad.CAPACITACION:
            raise ValidationError(
                'Una capacitación no se convierte en cita de asesoría; se aprueba directamente.')
        if (self.subespecialidad and self.area != Area.MIXTO
                and not Subespecialidad.valid_for_area(self.subespecialidad, self.area)):
            raise ValidationError({
                'subespecialidad': 'La subespecialidad no corresponde al área indicada.'
            })
        if (self.fecha_preferida and self.pk is None
                and self.fecha_preferida < timezone.localdate()):
            raise ValidationError({'fecha_preferida': 'La fecha preferida no puede estar en el pasado.'})
        if self.estado == self.Estado.RECHAZADA and not self.motivo_rechazo.strip():
            raise ValidationError({'motivo_rechazo': 'Indica el motivo del rechazo.'})
        if self.estado == self.Estado.CONVERTIDA and not self.cita_id:
            raise ValidationError('Una solicitud convertida debe tener cita asociada.')

    @property
    def es_taller(self):
        return self.tipo_necesidad == self.TipoNecesidad.CAPACITACION

    @property
    def requiere_cita(self):
        return not self.es_taller

    @property
    def puede_convertirse(self):
        return (self.estado == self.Estado.APROBADA and not self.cita_id
                and self.requiere_cita)

    @property
    def es_abierta(self):
        return self.estado in (self.Estado.RECIBIDA, self.Estado.EN_REVISION)

    @property
    def descripcion_corta(self):
        texto = ' '.join(self.descripcion.split())
        return texto if len(texto) <= 110 else f'{texto[:107]}…'
