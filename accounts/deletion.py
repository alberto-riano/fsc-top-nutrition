"""
Eliminación de cuentas desde la app.

Apple exige que quien tiene cuenta pueda borrarla desde la propia app, y que
se borre de verdad (no basta con desactivarla). Al borrar el usuario caen en
cascada su ficha de cliente, bonos y sesiones, medidas, marcas, planes y
dispositivos. Los archivos (foto y PDFs de planes) no se borran solos con la
fila, así que se quitan del almacenamiento cuando la transacción se confirma.
"""
import logging

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q

from .services import send_push_to_user

logger = logging.getLogger(__name__)


def other_trainers(user):
    """Entrenadores activos distintos de `user`."""
    User = get_user_model()
    return (
        User.objects.filter(is_active=True)
        .filter(Q(role='admin') | Q(is_superuser=True))
        .exclude(pk=user.pk)
    )


def is_last_trainer(user):
    """Si es el único entrenador, borrarlo dejaría el centro sin nadie que lo gestione."""
    return user.is_trainer and not other_trainers(user).exists()


def delete_account(user):
    """Borra el usuario y todos sus datos. Avisa a los entrenadores si era un cliente."""
    files = []
    if user.avatar:
        files.append((user.avatar.storage, user.avatar.name))

    profile = getattr(user, 'client_profile', None)
    notice = None
    if profile is not None:
        files += [(p.pdf.storage, p.pdf.name) for p in profile.plans.all() if p.pdf]
        name = profile.full_name
        left = profile.sessions_left
        notice = f'{name} ha eliminado su cuenta y sus datos de la app.'
        if left:
            notice += f' Le {"quedaba 1 sesión" if left == 1 else f"quedaban {left} sesiones"} de su bono.'

    trainers = list(other_trainers(user)) if notice else []
    user_id = user.pk

    def after_commit():
        for storage, name in files:
            try:
                storage.delete(name)
            except Exception:  # noqa: BLE001 - un archivo huérfano no debe romper el borrado
                logger.warning('No se pudo borrar el archivo %s', name, exc_info=True)
        for trainer in trainers:
            send_push_to_user(trainer, 'Cuenta eliminada', notice)

    with transaction.atomic():
        user.delete()
        transaction.on_commit(after_commit)

    logger.info('Cuenta %s eliminada desde la app', user_id)
