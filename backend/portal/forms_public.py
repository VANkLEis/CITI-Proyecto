"""Formularios de la zona pública y del triage privado (Fase 05).

Los formularios públicos construyen `SolicitudPublica` (nunca `CitaAsesoria`).
El formulario de conversión solo elige franja y equipo: las reglas de negocio
viven en `scheduling.solicitudes`.
"""

from django import forms
from django.utils import timezone

from accounts.models import Area, CustomUser, Role
from portal.forms import estudiantes_elegibles
from scheduling.models import FranjaHoraria, LineaAtencion, SolicitudPublica
from scheduling.subespecialidades import Subespecialidad

# Campos que el solicitante ve siempre. `website` es un honeypot: los humanos
# lo dejan vacío porque está oculto; los bots lo rellenan.
HONEYPOT_FIELD = 'website'


class _BasePublica(forms.ModelForm):
    """Estilo y validaciones comunes de los dos formularios públicos.

    El honeypot se declara aquí (no en un mixin plano): `ModelFormMetaclass`
    solo recoge campos declarados en clases que ya son Form/ModelForm.
    """

    website = forms.CharField(required=False, label='')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[HONEYPOT_FIELD].widget = forms.HiddenInput(attrs={
            'autocomplete': 'off', 'tabindex': '-1', 'aria-hidden': 'true'})
        for nombre, campo in self.fields.items():
            if nombre == HONEYPOT_FIELD:
                continue
            if isinstance(campo.widget, forms.CheckboxInput):
                continue
            css = 'form-control'
            if isinstance(campo.widget, forms.Select):
                css = 'form-select'
            campo.widget.attrs.setdefault('class', css)
        self.fields['descripcion'].widget.attrs.update(
            {'rows': 5, 'placeholder': 'Cuéntanos el reto, el contexto y qué esperas lograr.'})

    @property
    def es_spam(self):
        return bool(self.data.get(HONEYPOT_FIELD, '').strip())

    def clean_descripcion(self):
        texto = (self.cleaned_data.get('descripcion') or '').strip()
        if len(texto) < 30:
            raise forms.ValidationError(
                'Describe el reto con al menos 30 caracteres para poder evaluar el alcance.')
        return texto

    def clean_email(self):
        return (self.cleaned_data.get('email') or '').strip().lower()

    def clean_acepta_contacto(self):
        acepta = self.cleaned_data.get('acepta_contacto')
        if not acepta:
            raise forms.ValidationError(
                'Necesitamos tu autorización para contactarte y dar trámite a la solicitud.')
        return acepta


class SolicitudDiagnosticoForm(_BasePublica):
    """Diagnóstico / asesoría / consultoría desde la web pública."""

    class Meta:
        model = SolicitudPublica
        fields = (
            'tipo_solicitante', 'nombre_contacto', 'cargo', 'organizacion', 'nit',
            'email', 'telefono', 'area', 'tipo_necesidad', 'descripcion', 'objetivo',
            'fecha_preferida', 'turno_preferido', 'modalidad_preferida',
            'acepta_contacto',
        )
        widgets = {
            'fecha_preferida': forms.DateInput(attrs={'type': 'date'}),
            'objetivo': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # La web pública no ofrece "capacitación" en este formulario: tiene su
        # propio flujo con catálogo de talleres.
        self.fields['tipo_necesidad'].choices = [
            (SolicitudPublica.TipoNecesidad.ASESORIA, 'Asesoría / Orientación inicial'),
            (SolicitudPublica.TipoNecesidad.CONSULTORIA, 'Desarrollo / Consultoría técnica'),
        ]
        self.fields['area'].help_text = 'Si no estás seguro, elige "Ambas áreas".'
        self.order_fields([
            'tipo_solicitante', 'nombre_contacto', 'cargo', 'organizacion', 'nit',
            'email', 'telefono', 'tipo_necesidad', 'area', 'descripcion', 'objetivo',
            'fecha_preferida', 'turno_preferido', 'modalidad_preferida',
            'acepta_contacto',
        ])


class SolicitudTallerForm(_BasePublica):
    """Solicitud de charla / taller para un grupo u organización."""

    class Meta:
        model = SolicitudPublica
        fields = (
            'nombre_contacto', 'cargo', 'organizacion', 'nit', 'email', 'telefono',
            'taller', 'tema_interes', 'publico_objetivo', 'numero_participantes',
            'descripcion', 'fecha_preferida', 'turno_preferido',
            'modalidad_preferida', 'acepta_contacto',
        )
        widgets = {
            'fecha_preferida': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['taller'].queryset = self.fields['taller'].queryset.filter(activo=True)
        self.fields['taller'].empty_label = 'Aún no lo sé / proponer un tema'
        self.fields['publico_objetivo'].widget.attrs.update({
            'placeholder': 'Ej.: jóvenes de 16 a 22 años, personas mayores, equipo de la fundación'})

    def clean(self):
        data = super().clean()
        if not data.get('taller') and not (data.get('tema_interes') or '').strip():
            raise forms.ValidationError(
                'Elige un taller del catálogo o escribe el tema que te interesa.')
        return data

    def save(self, commit=True):
        solicitud = super().save(commit=False)
        solicitud.tipo_necesidad = SolicitudPublica.TipoNecesidad.CAPACITACION
        solicitud.linea_atencion = LineaAtencion.PROYECCION_SOCIAL
        if not solicitud.tema_interes and solicitud.taller_id:
            solicitud.tema_interes = solicitud.taller.titulo
        if commit:
            solicitud.full_clean()
            solicitud.save()
        return solicitud


class AprobarSolicitudForm(forms.Form):
    """Clasificación del alcance por Director/Coordinador."""

    linea_atencion = forms.ChoiceField(
        choices=LineaAtencion.choices, label='Línea de atención')
    area = forms.ChoiceField(
        choices=[(Area.SISTEMAS, 'Ingeniería de Sistemas'),
                 (Area.CIVIL, 'Ingeniería Civil')],
        label='Área responsable')
    subespecialidad = forms.ChoiceField(
        choices=[('', '— Sin subespecialidad —')] + list(Subespecialidad.LABELS.items()),
        required=False, label='Subespecialidad')
    observaciones = forms.CharField(
        required=False, label='Observaciones internas',
        widget=forms.Textarea(attrs={'rows': 3}))

    def __init__(self, *args, solicitud=None, actor=None, **kwargs):
        self.solicitud = solicitud
        self.actor = actor
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            if isinstance(campo.widget, forms.Select):
                campo.widget.attrs.setdefault('class', 'form-select')
            else:
                campo.widget.attrs.setdefault('class', 'form-control')
        if solicitud and solicitud.tipo_necesidad != SolicitudPublica.TipoNecesidad.CAPACITACION:
            self.fields['linea_atencion'].initial = (
                solicitud.linea_atencion
                or SolicitudPublica.linea_para(solicitud.tipo_necesidad))
        if solicitud:
            self.fields['area'].initial = (
                solicitud.area if solicitud.area in (Area.SISTEMAS, Area.CIVIL)
                else getattr(actor, 'area', Area.SISTEMAS))

    def clean(self):
        data = super().clean()
        area = data.get('area')
        sub = data.get('subespecialidad')
        if sub and area and not Subespecialidad.valid_for_area(sub, area):
            self.add_error(
                'subespecialidad',
                'Esa subespecialidad no pertenece al área seleccionada.')
        return data


class RechazarSolicitudForm(forms.Form):
    motivo = forms.CharField(
        label='Motivo del rechazo', widget=forms.Textarea(attrs={'rows': 3}),
        help_text='Queda registrado en el radicado de la solicitud.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['motivo'].widget.attrs.setdefault('class', 'form-control')


class ConvertirSolicitudForm(forms.Form):
    """Elección de franja y equipo para crear la cita."""

    franja = forms.ModelChoiceField(
        queryset=FranjaHoraria.objects.none(), label='Franja de diagnóstico')
    docente = forms.ModelChoiceField(
        queryset=CustomUser.objects.none(), required=False,
        label='Docente responsable')
    estudiante = forms.ModelChoiceField(
        queryset=CustomUser.objects.none(), required=False,
        label='Estudiante tutor de apoyo')

    def __init__(self, *args, solicitud=None, **kwargs):
        self.solicitud = solicitud
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.widget.attrs.setdefault('class', 'form-select')
        if not solicitud:
            return
        self.fields['franja'].queryset = (
            FranjaHoraria.objects
            .filter(activa=True, area=solicitud.area, inicio__gt=timezone.now())
            .order_by('inicio'))
        self.fields['docente'].queryset = CustomUser.objects.filter(
            role=Role.DOCENTE, is_active=True,
            area__in=[solicitud.area, Area.MIXTO]).order_by('first_name', 'email')
        self.fields['estudiante'].queryset = estudiantes_elegibles(
            solicitud.area).order_by('first_name', 'email')

    def clean(self):
        data = super().clean()
        franja = data.get('franja')
        if franja and self.solicitud and franja.area != self.solicitud.area:
            self.add_error('franja', 'La franja no corresponde al área de la solicitud.')
        return data
