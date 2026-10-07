from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from clients.models import ClientProfile


class ClientProfileMixin:
    """
    Resuelve el `ClientProfile` del usuario autenticado. La app móvil (fase 1)
    es la vista del cliente: el entrenador sigue gestionando desde la web.
    """

    def get_client_profile(self):
        user = self.request.user
        profile = getattr(user, 'client_profile', None)
        if profile is None:
            raise PermissionDenied('Esta cuenta no tiene perfil de cliente.')
        return profile


class IsTrainer(BasePermission):
    """Solo el entrenador (o superusuario) puede usar los endpoints de gestión."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_trainer)


class TrainerClientMixin:
    """Resuelve el `ClientProfile` indicado en la URL para los endpoints de entrenador."""

    def get_client(self):
        return get_object_or_404(ClientProfile, pk=self.kwargs['client_pk'])
