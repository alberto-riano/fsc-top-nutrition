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


def invite_expiry_days():
    """Días que vale el enlace (el mismo plazo que el de recuperar contraseña)."""
    return max(1, round(settings.PASSWORD_RESET_TIMEOUT / 86400))


def invite_message(user, invite_url):
    """
    El mensaje que el entrenador manda al cliente: qué es, el enlace para poner
    su contraseña y el usuario con el que entrará en la app. Con pasos
    numerados porque se lee en el móvil y de un vistazo.
    """
    centre = getattr(settings, 'SITE_TAGLINE', '') or settings.SITE_NAME
    name = (user.first_name or '').strip()
    steps = []
    if settings.APP_DOWNLOAD_URL:
        steps.append(f'Descarga la app:\n{settings.APP_DOWNLOAD_URL}')
    steps.append(f'Activa tu cuenta y elige tu contraseña:\n{invite_url}')
    steps.append(f'Entra en la app con tu usuario: {user.email}')
    numbered = '\n\n'.join(f'{i}. {step}' for i, step in enumerate(steps, start=1))
    days = invite_expiry_days()
    return (
        f'¡Hola{" " + name if name else ""}! 👋 Bienvenido/a a {centre}.\n\n'
        f'Ya tienes tu cuenta en {settings.SITE_NAME}, donde verás tus sesiones, tu progreso y tus planes.\n\n'
        f'{numbered}\n\n'
        f'El enlace vale {days} {"día" if days == 1 else "días"}.'
    )


def whatsapp_number(phone):
    """Teléfono en el formato de wa.me: solo dígitos y con prefijo de país."""
    digits = re.sub(r'\D', '', phone or '')
    if digits.startswith('00'):
        digits = digits[2:]
    # Números españoles guardados a 9 dígitos sin prefijo de país.
    if len(digits) == 9:
        digits = '34' + digits
    return digits


def whatsapp_invite_url(user, invite_url):
    """
    Enlace wa.me para compartir la invitación por WhatsApp con el mensaje y
    (si hay teléfono guardado) el destinatario ya rellenados.
    """
    message = invite_message(user, invite_url)
    return f'https://wa.me/{whatsapp_number(user.phone)}?text={quote(message)}'


def build_invite(request, user):
    """Todo lo que la app necesita para enviar la invitación."""
    url = invitation_url(request, user)
    return {
        'url': url,
        'message': invite_message(user, url),
        'whatsapp_url': whatsapp_invite_url(user, url),
        'username': user.email,
        'phone': user.phone,
        'expires_in_days': invite_expiry_days(),
    }


def suggest_username(base):
    """`base` si está libre; si no, base2, base3…"""
    base = (base or '').strip().lower() or 'cliente'
    candidate, n = base, 1
    while User.objects.filter(email__iexact=candidate).exists():
        n += 1
        candidate = f'{base}{n}'
    return candidate


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
