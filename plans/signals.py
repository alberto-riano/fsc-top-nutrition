from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.services import send_push_to_user

from .models import Plan


@receiver(post_save, sender=Plan)
def notify_new_plan(sender, instance, created, **kwargs):
    if not created:
        return
    send_push_to_user(
        instance.client.user,
        title='Nuevo plan disponible',
        body=f'Tu entrenador ha subido: {instance.title}',
        data={'type': 'new_plan', 'plan_id': str(instance.id)},
    )
