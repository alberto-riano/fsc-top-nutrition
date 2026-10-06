"""
URL configuration para TopTrack.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from .health import healthz

urlpatterns = [
    path('healthz/', healthz, name='healthz'),
    path('admin/', admin.site.urls),
    path('api/v1/', include('api.urls')),
    path('', include('dashboard.urls')),
    path('accounts/', include('accounts.urls')),
    path('clientes/', include('clients.urls')),
    path('bonos/', include('bonos.urls')),
    path('metricas/', include('metrics.urls')),
    path('planes/', include('plans.urls')),

    # Páginas legales (públicas)
    path('legal/privacidad/', TemplateView.as_view(
        template_name='legal/privacy.html', extra_context={'updated': 'julio de 2026'}), name='privacy'),
    path('legal/terminos/', TemplateView.as_view(
        template_name='legal/terms.html', extra_context={'updated': 'julio de 2026'}), name='terms'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
