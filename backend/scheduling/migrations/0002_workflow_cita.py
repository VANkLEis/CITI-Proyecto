from django.conf import settings
from django.db import migrations, models
from django.db.models import Q
import django.core.validators
import django.db.models.deletion


def migrar_estados(apps, schema_editor):
    CitaAsesoria = apps.get_model('scheduling', 'CitaAsesoria')
    CitaAsesoria.objects.filter(estado='reservada').update(estado='solicitada')
    CitaAsesoria.objects.filter(estado='completada').update(estado='finalizada')


class Migration(migrations.Migration):

    dependencies = [
        ('scheduling', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='citaasesoria',
            name='unique_cita_activa_por_cliente_franja',
        ),
        migrations.AddField(
            model_name='citaasesoria',
            name='actualizada_en',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='citaasesoria',
            name='calificacion',
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(5),
                ],
            ),
        ),
        migrations.AddField(
            model_name='citaasesoria',
            name='comentario_cliente',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='citaasesoria',
            name='docente_asignado',
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={'role': 'docente'},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='citas_docente',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='citaasesoria',
            name='estudiante_apoyo',
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={'role': 'estudiante'},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='citas_apoyo_estudiante',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='citaasesoria',
            name='resumen_cierre',
            field=models.TextField(blank=True, help_text='Notas finales del docente al cerrar el caso.'),
        ),
        migrations.AddField(
            model_name='citaasesoria',
            name='subespecialidad',
            field=models.CharField(blank=True, max_length=30),
        ),
        migrations.AlterField(
            model_name='citaasesoria',
            name='estado',
            field=models.CharField(
                choices=[
                    ('solicitada', 'Solicitada'),
                    ('asignada', 'Asignada'),
                    ('en_proceso', 'En proceso'),
                    ('finalizada', 'Finalizada'),
                    ('cancelada', 'Cancelada'),
                ],
                default='solicitada',
                max_length=20,
            ),
        ),
        migrations.RunPython(migrar_estados, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='citaasesoria',
            constraint=models.UniqueConstraint(
                condition=Q(estado__in=['solicitada', 'asignada', 'en_proceso']),
                fields=('franja', 'cliente'),
                name='unique_cita_activa_por_cliente_franja',
            ),
        ),
        migrations.CreateModel(
            name='NotaBitacora',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('texto', models.TextField()),
                ('creada_en', models.DateTimeField(auto_now_add=True)),
                ('autor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notas_bitacora', to=settings.AUTH_USER_MODEL)),
                ('cita', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notas', to='scheduling.citaasesoria')),
            ],
            options={
                'verbose_name': 'Nota de bitácora',
                'verbose_name_plural': 'Notas de bitácora',
                'ordering': ['-creada_en'],
            },
        ),
    ]
