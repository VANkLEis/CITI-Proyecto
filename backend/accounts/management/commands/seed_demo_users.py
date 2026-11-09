from django.core.management.base import BaseCommand

from accounts.demo_seed import DEMO_USERS, ensure_demo_users


class Command(BaseCommand):
    help = (
        'Crea/verifica las cuentas de demostración del CITI (idempotente). '
        'Para el conjunto completo de datos use: manage.py seed_demo.'
    )

    def handle(self, *args, **options):
        ensure_demo_users()
        self.stdout.write(self.style.SUCCESS(
            f'Usuarios demo verificados ({len(DEMO_USERS)} cuentas), con sus '
            'perfiles académicos. Credenciales: docs/demo/CUENTAS_DE_PRUEBA.md.'
        ))
