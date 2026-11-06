from django.core.management.base import BaseCommand

from accounts.demo_seed import DEMO_PASSWORD, DEMO_USERS, ensure_demo_users


class Command(BaseCommand):
    help = 'Crea usuarios de demostración del CITI si no existen en la base de datos.'

    def handle(self, *args, **options):
        ensure_demo_users()
        self.stdout.write(self.style.SUCCESS(
            f'Usuarios demo listos ({len(DEMO_USERS)} cuentas). Contraseña: {DEMO_PASSWORD}'
        ))
