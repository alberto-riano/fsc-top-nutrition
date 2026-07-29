from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """
    Autentica por email (case-insensitive) en vez de por username.

    Django llama a authenticate() pasando el valor del formulario en `username`;
    aquí lo tratamos como email. Se mantiene ModelBackend en AUTHENTICATION_BACKENDS
    como fallback para que el superadmin siga entrando a /admin/ por username.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        email = kwargs.get('email', username)
        if email is None or password is None:
            return None
        try:
            user = UserModel.objects.get(email__iexact=email)
        except UserModel.DoesNotExist:
            # Ejecuta el hasher para no revelar por tiempo si el email existe.
            UserModel().set_password(password)
            return None
        except UserModel.MultipleObjectsReturned:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
