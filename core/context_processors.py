"""
Context processors propios.

`branding` expone la identidad del producto a todas las plantillas para no
tenerla escrita a mano por el código. Reutilizar este repositorio para otro
negocio es cambiar variables de entorno (SITE_NAME, ...) en vez de tocar HTML.
"""
from django.conf import settings
from .version import VERSION


def branding(request):
    return {
        'SITE_NAME': getattr(settings, 'SITE_NAME', 'TopTrack'),
        'SITE_TAGLINE': getattr(settings, 'SITE_TAGLINE', ''),
        'APP_VERSION': VERSION,
        'APP_BUILD': getattr(settings, 'APP_BUILD', ''),
        'SUPPORT_EMAIL': getattr(settings, 'SUPPORT_EMAIL', ''),
    }
