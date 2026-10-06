"""
Envío de notificaciones push nativas vía Expo Push API.

Expo retransmite el mensaje a APNs (iOS) o FCM (Android) según el token, así
que el backend no necesita gestionar certificados APNs ni credenciales
Firebase directamente: solo hace un POST HTTPS al endpoint de Expo.
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def send_push_to_user(user, title, body, data=None):
    """Envía una notificación a todos los dispositivos registrados del usuario."""
    tokens = list(user.device_tokens.values_list('token', flat=True))
    if not tokens:
        return

    messages = [
        {
            'to': token,
            'title': title,
            'body': body,
            'data': data or {},
            'sound': 'default',
        }
        for token in tokens
    ]
    try:
        response = requests.post(
            settings.EXPO_PUSH_URL,
            json=messages,
            headers={'Accept': 'application/json', 'Content-Type': 'application/json'},
            timeout=5,
        )
        response.raise_for_status()
    except requests.RequestException:
        # Un fallo de push nunca debe romper el flujo de negocio (crear sesión, etc.).
        logger.warning('No se pudo enviar la notificación push a %s', user, exc_info=True)
