from rest_framework.exceptions import PermissionDenied


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
