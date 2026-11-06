from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import CustomUser, PerfilEstudiante, Role, StudentType


@receiver(post_save, sender=CustomUser)
def crear_perfil_estudiante(sender, instance, created, **kwargs):
    if created and instance.role == Role.ESTUDIANTE:
        if not instance.student_type:
            instance.student_type = StudentType.CONSULTOR
            instance.save(update_fields=['student_type'], skip_validation=True)
        PerfilEstudiante.objects.get_or_create(
            usuario=instance,
            defaults={'creditos_aprobados': 0, 'promedio_general': 0},
        )
