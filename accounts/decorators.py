from functools import wraps

from django.core.exceptions import PermissionDenied


def trainer_required(view_func):
    """Solo el entrenador (admin) o un superusuario pueden acceder."""
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            raise PermissionDenied
        if user.is_trainer:
            return view_func(request, *args, **kwargs)
        raise PermissionDenied

    return wrapped


def client_required(view_func):
    """Solo un cliente con perfil asociado puede acceder a las vistas de portal."""
    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            raise PermissionDenied
        if user.is_client and hasattr(user, 'client_profile'):
            return view_func(request, *args, **kwargs)
        raise PermissionDenied

    return wrapped
