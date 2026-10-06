from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.services import send_push_to_user

from .models import Session


@receiver(post_save, sender=Session)
def notify_low_sessions(sender, instance, created, **kwargs):
    """Avisa por push al cliente cuando le quedan pocas sesiones en el bono."""
    if not created:
        return
    bono = instance.bono
    client = bono.client
    if not client.low_sessions_alert:
        return
    send_push_to_user(
        client.user,
        title='Pocas sesiones restantes',
        body=f'Te quedan {bono.sessions_left} sesiones en tu bono.',
        data={'type': 'low_sessions', 'bono_id': str(bono.id)},
    )
