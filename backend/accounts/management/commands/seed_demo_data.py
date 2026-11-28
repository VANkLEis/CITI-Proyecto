from django.core.management.base import BaseCommand

from accounts import demo_seed
from portal.models import ProyectoPortafolio, Taller


class Command(BaseCommand):
    help = (
        'Carga el conjunto completo de demostración: usuarios de los 5 roles, '
        'franjas, citas, portafolio, talleres y solicitudes públicas. '
        'Idempotente; se ejecuta en el entrypoint de Docker/Render.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--solo-usuarios',
            action='store_true',
            help='Crear/actualizar únicamente las cuentas demo y sus perfiles.',
        )

    def _print_accounts(self):
        self.stdout.write(
            '  Cuentas demo (contraseña: CITI_DEMO_PASSWORD, '
            'default CITIPass2026*):')
        for spec in demo_seed.DEMO_USERS:
            self.stdout.write(f"    {spec['role']}: {spec['email']}")

    def handle(self, *args, **options):
        if options['solo_usuarios']:
            demo_seed.ensure_demo_users()
            self.stdout.write(self.style.SUCCESS(
                f'Usuarios demo verificados ({len(demo_seed.DEMO_USERS)} cuentas).'))
            self._print_accounts()
            return

        resumen = demo_seed.seed_all()

        self.stdout.write(self.style.SUCCESS('Datos de demostración listos.'))
        self.stdout.write(
            '  Nuevos en esta corrida: '
            f"{resumen['proyectos_nuevos']} proyectos, "
            f"{resumen['talleres_nuevos']} talleres, "
            f"{resumen['solicitudes_nuevas']} solicitudes públicas, "
            f"{resumen['clientes_nuevos']} clientes, "
            f"{resumen['franjas_nuevas']} franjas, "
            f"{resumen['citas_nuevas']} citas."
        )
        self.stdout.write(
            '  Contenido total publicado: '
            f'{ProyectoPortafolio.objects.filter(publicado=True).count()} '
            'proyectos y '
            f'{Taller.objects.filter(activo=True).count()} talleres.'
        )
        self._print_accounts()
        self.stdout.write(
            '  Credenciales y guion: docs/demo/CUENTAS_DE_PRUEBA.md '
            'y docs/demo/GUIA_DEMOSTRACION.md'
        )
