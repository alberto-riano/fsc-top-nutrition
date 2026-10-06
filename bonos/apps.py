from django.apps import AppConfig


class BonosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bonos'
    verbose_name = 'Bonos y sesiones'

    def ready(self):
        from . import signals  # noqa: F401
