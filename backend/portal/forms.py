from django import forms
from django.conf import settings

from accounts.models import CustomUser, Role
from scheduling.models import CitaAsesoria, NotaBitacora, CitaInteraccion
from scheduling.subespecialidades import Subespecialidad


def estudiantes_elegibles(area=None):
    """Estudiantes que cumplen los tres requisitos CITI para actuar como tutores."""
    desde_semestre = getattr(settings, 'CITI_MIN_SEMESTRE_TUTOR', 8)
    desde_creditos = getattr(settings, 'CITI_MIN_CREDITOS_TUTOR', 130)
    desde_promedio = getattr(settings, 'CITI_MIN_PROMEDIO_TUTOR', '4.0')

    qs = CustomUser.objects.filter(
        role=Role.ESTUDIANTE,
        is_active=True,
        perfil_estudiante__semestre__gte=desde_semestre,
        perfil_estudiante__creditos_aprobados__gte=desde_creditos,
        perfil_estudiante__promedio_general__gte=desde_promedio,
    )
    if area:
        qs = qs.filter(area__in=[area, 'mixto'])
    return qs


class AsignarDocenteForm(forms.Form):
    docente_id = forms.ModelChoiceField(
        queryset=CustomUser.objects.none(),
        label='Docente asesor',
        required=False,
    )
    estudiante_id = forms.ModelChoiceField(
        queryset=CustomUser.objects.none(),
        label='Estudiante consultor (tutor)',
        required=False,
    )

    def __init__(self, *args, area=None, **kwargs):
        super().__init__(*args, **kwargs)
        docentes = CustomUser.objects.filter(role=Role.DOCENTE, is_active=True)
        if area:
            docentes = docentes.filter(area__in=[area, 'mixto'])
        estudiantes = estudiantes_elegibles(area)
        self.fields['docente_id'].queryset = docentes.order_by('first_name', 'last_name')
        self.fields['estudiante_id'].queryset = estudiantes.order_by('first_name', 'last_name')


class DocenteCasoForm(forms.ModelForm):
    nota_avance = forms.CharField(
        label='Nota de avance',
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
    )

    class Meta:
        model = CitaAsesoria
        fields = ('estado', 'resumen_cierre', 'estudiante_apoyo')
        labels = {
            'estado': 'Estado del caso',
            'resumen_cierre': 'Resumen de cierre',
            'estudiante_apoyo':'Estudiante consultor (tutor)',
        }

    def __init__(self, *args, area=None, **kwargs):
        super().__init__(*args, **kwargs)
        allowed = [
            CitaAsesoria.Estado.ASIGNADA,
            CitaAsesoria.Estado.EN_PROCESO,
            CitaAsesoria.Estado.FINALIZADA,
        ]
        self.fields['estado'].choices = [
            (k, v) for k, v in CitaAsesoria.Estado.choices if k in allowed
        ]
        estudiantes = estudiantes_elegibles(area)
        self.fields['estudiante_apoyo'].queryset = estudiantes.order_by('first_name', 'last_name')
        self.fields['estudiante_apoyo'].required = False


class NotaBitacoraForm(forms.ModelForm):
    class Meta:
        model = NotaBitacora
        fields = ('texto',)
        labels = {'texto': 'Bitácora / avance'}
        widgets = {'texto': forms.Textarea(attrs={'rows': 3})}


class FeedbackClienteForm(forms.Form):
    calificacion = forms.IntegerField(
        min_value=1,
        max_value=5,
        label='Calificación (1 a 5)',
        widget=forms.NumberInput(attrs={'min': 1, 'max': 5}),
    )
    comentario_cliente = forms.CharField(
        label='Comentarios',
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
    )


# ---------------------------------------------------------------------------
# Fase 04 — interacción, entregables y decisiones. Los tipos por rol se
# ofrecen SOLO donde el backend los permite; la validación cruzada autor-rol-
# tipo ocurre además en CitaInteraccion.clean (defensa en profundidad).

class InteraccionClienteForm(forms.Form):
    TIPOS = (
        (CitaInteraccion.Tipo.GENERAL, 'Comentario general'),
        (CitaInteraccion.Tipo.RESPUESTA, 'Respuesta al profesional'),
        (CitaInteraccion.Tipo.AJUSTE, 'Solicitar ajuste al avance'),
    )
    tipo = forms.ChoiceField(label='Tipo de mensaje', choices=TIPOS)
    texto = forms.CharField(
        label='Mensaje', widget=forms.Textarea(attrs={'rows': 3, 'maxlength': 4000}))

    def clean_tipo(self):
        valor = self.cleaned_data['tipo']
        if valor not in dict(self.TIPOS):
            raise forms.ValidationError('Tipo no permitido para el cliente.')
        return valor


class InteraccionEquipoForm(forms.Form):
    TIPOS = (
        (CitaInteraccion.Tipo.OBSERVACION, 'Observación para el cliente'),
        (CitaInteraccion.Tipo.NOTA_INTERNA, 'Nota técnica interna (no visible al cliente)'),
        (CitaInteraccion.Tipo.AJUSTE, 'Solicitud de ajuste (interna)'),
    )
    tipo = forms.ChoiceField(label='Tipo de mensaje', choices=TIPOS)
    texto = forms.CharField(
        label='Mensaje', widget=forms.Textarea(attrs={'rows': 3, 'maxlength': 4000}))

    def clean_tipo(self):
        valor = self.cleaned_data['tipo']
        if valor not in dict(self.TIPOS):
            raise forms.ValidationError('Tipo no permitido para el equipo.')
        return valor


class EntregableForm(forms.Form):
    """Publicación de entregable para revisión del cliente.

    Los campos estructurados (diagnóstico, alcance, metodología, entregables)
    son la ficha de CONSULTORÍA; en ASESORÍA basta título + contenido, según
    la diferenciación de modalidades de la Fase 04."""
    titulo = forms.CharField(
        label='Título del entregable', max_length=180,
        widget=forms.TextInput(attrs={'maxlength': 180}))
    contenido = forms.CharField(
        label='Resumen de resultados',
        widget=forms.Textarea(attrs={'rows': 4, 'maxlength': 4000}))
    diagnostico = forms.CharField(label='Diagnóstico técnico', required=False,
                                  widget=forms.Textarea(attrs={'rows': 2}))
    alcance = forms.CharField(label='Alcance y objetivos', required=False,
                              widget=forms.Textarea(attrs={'rows': 2}))
    metodologia = forms.CharField(label='Metodología de trabajo', required=False,
                                  widget=forms.Textarea(attrs={'rows': 2}))
    entregables = forms.CharField(label='Entregables concretos', required=False,
                                  widget=forms.Textarea(attrs={'rows': 2}))

    def ficha(self):
        """Solo los campos con valor; se almacenan en datos_extra."""
        data = {}
        for key in ('diagnostico', 'alcance', 'metodologia', 'entregables'):
            val = (self.cleaned_data.get(key) or '').strip()
            if val:
                data[key] = val
        return data or None


class DecisionClienteForm(forms.Form):
    observacion = forms.CharField(
        label='Observación (justifica tu decisión)',
        widget=forms.Textarea(attrs={'rows': 2, 'maxlength': 2000}),
        required=False)
