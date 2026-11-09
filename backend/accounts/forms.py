from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

from accounts.models import CustomUser, Empresa, Role


class ClientRegistrationForm(forms.Form):
    """Registro público: únicamente rol Cliente."""
    razon_social = forms.CharField(max_length=200, label='Razón social de la empresa')
    nit = forms.CharField(max_length=20, required=False, label='NIT')
    first_name = forms.CharField(max_length=120, label='Nombre del contacto')
    last_name = forms.CharField(max_length=120, label='Apellido del contacto')
    email = forms.EmailField(label='Correo electrónico')
    password1 = forms.CharField(widget=forms.PasswordInput, label='Contraseña')
    password2 = forms.CharField(widget=forms.PasswordInput, label='Confirmar contraseña')

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError('Ya existe una cuenta con este correo.')
        return email

    def clean(self):
        data = super().clean()
        if data.get('password1') != data.get('password2'):
            raise forms.ValidationError('Las contraseñas no coinciden.')
        if data.get('password1'):
            # (B-5 / SEG-13) Aplica AUTH_PASSWORD_VALIDATORS del proyecto al
            # registro público: longitud mínima, complejidad y similitud con
            # los datos del usuario.
            usuario_prov = CustomUser(
                email=data.get('email', ''),
                first_name=data.get('first_name', ''),
                last_name=data.get('last_name', ''),
            )
            try:
                validate_password(data['password1'], usuario_prov)
            except DjangoValidationError as exc:
                raise forms.ValidationError(exc.messages)
        return data

    def save(self):
        empresa = Empresa.objects.create(
            razon_social=self.cleaned_data['razon_social'],
            nit=self.cleaned_data.get('nit', ''),
        )
        user = CustomUser.objects.create_user(
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password1'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
            role=Role.CLIENTE,
            empresa=empresa,
        )
        return user


class RoleLoginForm(AuthenticationForm):
    username = forms.EmailField(label='Correo electrónico')
    expected_role = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'id_expected_role'}),
    )

    def clean_expected_role(self):
        role = (self.cleaned_data.get('expected_role') or '').strip()
        if role not in dict(Role.choices):
            raise forms.ValidationError(
                'Seleccione un portal de acceso en el panel izquierdo antes de ingresar.'
            )
        return role

    def clean(self):
        email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        expected_role = self.cleaned_data.get('expected_role')

        if email and password:
            self.user_cache = authenticate(
                self.request,
                username=email.lower(),
                password=password,
            )
            if self.user_cache is None:
                raise forms.ValidationError('Correo o contraseña incorrectos.')
            if self.user_cache.role != expected_role:
                raise forms.ValidationError(
                    f'Esta cuenta pertenece al portal «{self.user_cache.get_role_display()}», '
                    f'no al seleccionado.'
                )
        return self.cleaned_data
