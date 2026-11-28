from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Area, CustomUser, Role


@override_settings(
    IS_PRODUCTION=True,
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    },
)
class ProductionDemoLoginTests(TestCase):
    """El seed de Render deja las 5 cuentas activas y con la clave exacta."""

    LOGINS = (
        (Role.DIRECTOR, 'director@citi.ucc.edu.co', 'portal:director_dashboard'),
        (Role.COORDINADOR, 'coordinador@citi.ucc.edu.co', 'portal:coordinador_dashboard'),
        (Role.DOCENTE, 'docente@citi.ucc.edu.co', 'portal:docente_dashboard'),
        (Role.ESTUDIANTE, 'estudiante@citi.ucc.edu.co', 'portal:estudiante_dashboard'),
        (Role.CLIENTE, 'cliente@empresa.com', 'portal:cliente_dashboard'),
    )

    def setUp(self):
        cache.clear()

    def test_seed_demo_y_login_de_los_cinco_roles_en_produccion(self):
        # Simula una cuenta creada antes con clave incorrecta y desactivada:
        # el seed debe repararla en el arranque, no solo crear cuentas nuevas.
        CustomUser.objects.create_user(
            email='coordinador@citi.ucc.edu.co',
            password='clave-vieja',
            role=Role.COORDINADOR,
            area=Area.SISTEMAS,
            is_active=False,
        )

        call_command('seed_demo_data', '--solo-usuarios', verbosity=0)
        cache.clear()

        for role, email, dashboard_name in self.LOGINS:
            with self.subTest(role=role, email=email):
                self.client.logout()
                response = self.client.post(
                    reverse('accounts:login'),
                    {
                        'username': email,
                        'password': 'CITIPass2026*',
                        'expected_role': role,
                    },
                    secure=True,
                    HTTP_HOST='localhost',
                )
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.url, reverse(dashboard_name))
                user = CustomUser.objects.get(email=email)
                self.assertTrue(user.is_active)
                self.assertTrue(user.check_password('CITIPass2026*'))
