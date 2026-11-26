"""Contenido editorial de la zona pública (Fase 05).

Estos modelos existen para que el portafolio y el catálogo de talleres sean
EDITABLES desde /admin/ y no contenido hardcodeado en la plantilla. El seed
(`seed_demo_data`) crea el contenido inicial de demostración.
"""

from django.db import models
from django.templatetags.static import static
from django.utils.text import slugify

from accounts.models import Area


class LineaPortafolio(models.TextChoices):
    SISTEMAS = 'sistemas', 'Ingeniería de Sistemas'
    CIVIL = 'civil', 'Ingeniería Civil'
    INNOVACION_IA = 'innovacion_ia', 'Innovación / IA'
    IMPACTO_SOCIAL = 'impacto_social', 'Impacto Social'


# Agrupación de público para los filtros de /talleres/. Se mantienen los cinco
# códigos del modelo (compatibilidad de datos) y se agrupan en cuatro entradas
# visibles; `pymes` y `comunidad` comparten el grupo "Pymes y comunidad".
GRUPOS_PUBLICO = (
    ('fundaciones', 'Fundaciones / ONG', ('fundaciones',)),
    ('jovenes', 'Emprendimientos juveniles', ('jovenes',)),
    ('adultos_mayores', 'Pensionados y adultos mayores', ('adultos_mayores',)),
    ('pymes_comunidad', 'Pymes y comunidad', ('pymes', 'comunidad')),
)


class ImagenMixta(models.Model):
    """Imagen subida en admin con respaldo a un archivo de `static/`.

    En Docker el media es un volumen y puede estar vacío la primera vez; si no
    hay imagen subida se usa `imagen_static` (un asset versionado) para que la
    tarjeta nunca se vea rota. Las subclases declaran `imagen` con su carpeta.
    """

    imagen_static = models.CharField(
        max_length=255, blank=True,
        help_text='Ruta dentro de static/, por ejemplo images/landing/proyecto-trazabilidad-ong.jpg')
    imagen_alt = models.CharField(max_length=200, blank=True)

    class Meta:
        abstract = True

    @property
    def imagen_url(self):
        if self.imagen:
            return self.imagen.url
        if self.imagen_static:
            return static(self.imagen_static)
        return ''


class ProyectoPortafolio(ImagenMixta):
    """Caso de éxito / avance publicable en el portafolio público."""

    titulo = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    linea = models.CharField(
        max_length=20, choices=LineaPortafolio.choices, default=LineaPortafolio.SISTEMAS)
    organizacion = models.CharField(max_length=200, blank=True)
    anio = models.PositiveSmallIntegerField(null=True, blank=True)
    resumen = models.CharField(
        max_length=300, help_text='Una o dos frases para la tarjeta del listado.')
    reto = models.TextField(blank=True)
    solucion = models.TextField(blank=True)
    resultados = models.TextField(blank=True)
    metricas = models.JSONField(
        default=list, blank=True,
        help_text='Lista de {"label": "...", "valor": "..."} para mostrar cifras del caso.')
    imagen = models.ImageField(
        upload_to='portafolio/', blank=True, null=True,
        help_text='Opcional. Si se omite se usa la imagen de respaldo.')
    destacado = models.BooleanField(default=False)
    publicado = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Proyecto del portafolio'
        verbose_name_plural = 'Portafolio (proyectos)'
        ordering = ['orden', '-creado_en']
        indexes = [models.Index(fields=['publicado', 'linea'])]

    def __str__(self):
        return self.titulo

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.titulo)[:170] or 'proyecto'
            candidato, n = base, 2
            while ProyectoPortafolio.objects.filter(slug=candidato).exclude(pk=self.pk).exists():
                candidato = f'{base}-{n}'
                n += 1
            self.slug = candidato
        super().save(*args, **kwargs)

    @property
    def metricas_validas(self):
        if not isinstance(self.metricas, list):
            return []
        return [
            m for m in self.metricas
            if isinstance(m, dict) and m.get('label') and m.get('valor')
        ]


class Taller(ImagenMixta):
    """Taller / capacitación ofertada en la zona pública."""

    class Publico(models.TextChoices):
        FUNDACIONES = 'fundaciones', 'Fundaciones / ONG'
        JOVENES = 'jovenes', 'Emprendimientos juveniles'
        ADULTOS_MAYORES = 'adultos_mayores', 'Pensionados y adultos mayores'
        PYMES = 'pymes', 'Pymes y comunidad'
        COMUNIDAD = 'comunidad', 'Comunidad en general'

    class Modalidad(models.TextChoices):
        PRESENCIAL = 'presencial', 'Presencial'
        VIRTUAL = 'virtual', 'Virtual'
        HIBRIDA = 'hibrida', 'Híbrida'

    class Nivel(models.TextChoices):
        BASICO = 'basico', 'Desde cero / sin conocimientos previos'
        INTERMEDIO = 'intermedio', 'Intermedio'
        AVANZADO = 'avanzado', 'Avanzado'

    titulo = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    tematica = models.CharField(
        max_length=200, help_text='Bajada corta: qué se trabaja en el taller.')
    descripcion = models.TextField(help_text='Contenido y alcance del taller.')
    publico_objetivo = models.CharField(
        max_length=30, choices=Publico.choices, default=Publico.COMUNIDAD)
    area = models.CharField(
        max_length=20, choices=Area.choices, default=Area.SISTEMAS,
        help_text='Carrera que lidera el taller: equilibra Sistemas y Civil.')
    duracion = models.CharField(
        max_length=80, blank=True, help_text='Por ejemplo: 2 sesiones de 90 minutos.')
    modalidad = models.CharField(
        max_length=20, choices=Modalidad.choices, default=Modalidad.PRESENCIAL)
    nivel = models.CharField(
        max_length=20, choices=Nivel.choices, default=Nivel.BASICO)
    puntos_clave = models.JSONField(
        default=list, blank=True,
        help_text='Tres ideas clave del temario, una por elemento de la lista.')
    imagen = models.ImageField(
        upload_to='talleres/', blank=True, null=True,
        help_text='Opcional. Si se omite se usa la imagen de respaldo.')
    activo = models.BooleanField(default=True)
    orden = models.PositiveSmallIntegerField(default=0)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Taller'
        verbose_name_plural = 'Talleres y capacitaciones'
        ordering = ['orden', 'titulo']
        indexes = [models.Index(fields=['activo', 'publico_objetivo'])]

    def __str__(self):
        return self.titulo

    @property
    def puntos_clave_validos(self):
        """Máximo tres viñetas, ignorando valores vacíos o malformados."""
        if not isinstance(self.puntos_clave, list):
            return []
        return [str(p).strip() for p in self.puntos_clave if str(p).strip()][:3]

    @property
    def grupo_publico(self):
        for code, _label, codes in GRUPOS_PUBLICO:
            if self.publico_objetivo in codes:
                return code
        return self.publico_objetivo

    @property
    def grupo_publico_label(self):
        for _code, label, codes in GRUPOS_PUBLICO:
            if self.publico_objetivo in codes:
                return label
        return self.get_publico_objetivo_display()

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.titulo)[:170] or 'taller'
            candidato, n = base, 2
            while Taller.objects.filter(slug=candidato).exclude(pk=self.pk).exists():
                candidato = f'{base}-{n}'
                n += 1
            self.slug = candidato
        super().save(*args, **kwargs)
