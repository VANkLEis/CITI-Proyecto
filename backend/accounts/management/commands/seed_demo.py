from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from accounts import demo_seed


class Command(BaseCommand):
    help = (
        'Crea el conjunto de datos de DEMOSTRACIÓN local del CITI (usuarios, '
        'franjas futuras y solicitudes en todos los estados). Idempotente: '
        'puede re-ejecutarse sin duplicar registros. No elimina datos.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--solo-usuarios',
            action='store_true',
            help='Crear/actualizar únicamente las cuentas demo y sus perfiles.',
        )

    def handle(self, *args, **options):
        # B-4: el seed no corre solo y está bloqueado en producción.
        if getattr(settings, 'IS_PRODUCTION', False):
            raise CommandError(
                'seed_demo no puede ejecutarse con DJANGO_ENV=produccion. '
                'Las cuentas de demostración solo existen en entornos locales.'
            )

        demo_seed.ensure_demo_users()
        if options['solo_usuarios']:
            self.stdout.write(self.style.SUCCESS(
                f'Usuarios demo verificados ({len(demo_seed.DEMO_USERS)} cuentas).'
            ))
            return

        resumen = demo_seed.seed_all()
        franjas = demo_seed.FranjaHoraria.objects.filter(
            activa=True, inicio__gt=demo_seed.timezone.now()
        ).count()
        citas = demo_seed.CitaAsesoria.objects.count()
        self.stdout.write(self.style.SUCCESS(
            'Datos demo listos — franjas nuevas: {franjas_nuevas}, '
            'citas nuevas: {citas_nuevas}, citas reubicadas a franja futura: '
            '{citas_reubicadas}, líneas de tiempo simuladas: {trazabilidad_simulada}, '
            'interacciones simuladas: {interacciones_nuevas}, '
            'franjas vencidas archivadas: {archivadas}, '
            'solicitudes vencidas canceladas con nota: {canceladas}.'.format(**resumen)
        ))
        self.stdout.write(
            f'Estado final: {franjas} franjas futuras activas, {citas} citas. '
            'Credenciales locales: docs/demo/CUENTAS_DE_PRUEBA.md.'
        )
