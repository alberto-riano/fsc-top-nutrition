"""Lógica de negocio de clientes (invitaciones y alta de cuenta)."""
import re
import uuid
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

User = get_user_model()


def invitation_url(request, user):
    """URL absoluta para que el cliente establezca su contraseña por primera vez."""
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    path = reverse('accounts:accept_invite', kwargs={'uidb64': uid, 'token': token})
    return request.build_absolute_uri(path)


def whatsapp_invite_url(user, invite_url):
    """
    Enlace wa.me para compartir la invitación por WhatsApp con el mensaje y
    (si hay teléfono guardado) el destinatario ya rellenados.
    """
    message = (
        f'Hola {user.first_name or ""}, soy tu entrenador/a de {settings.SITE_NAME}. '
        f'Aquí tienes tu enlace para activar tu cuenta: {invite_url}'
    ).strip()
    digits = re.sub(r'\D', '', user.phone or '')
    # Números españoles guardados a 9 dígitos sin prefijo de país.
    if len(digits) == 9:
        digits = '34' + digits
    return f'https://wa.me/{digits}?text={quote(message)}'


def create_client_user(*, email, first_name, last_name, phone, password=None):
    """
    Crea el usuario (rol cliente) de un nuevo cliente. Si no se da contraseña,
    la cuenta queda inactiva hasta que el cliente la establezca por invitación.
    """
    user = User(
        username=f'cliente-{uuid.uuid4().hex[:12]}',
        email=email,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        role='cliente',
        is_active=bool(password),
    )
    if password:
        user.set_password(password)
    else:
        user.set_unusable_password()
    user.save()
    return user
