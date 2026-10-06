from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid


class User(AbstractUser):
    """
    Usuario personalizado con login por email y dos roles: el entrenador
    (admin) y el cliente. App single-tenant: no hay pertenencia a ningún
    centro, solo el rol distingue el acceso.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Email como identidad de login (único, obligatorio). El username se conserva
    # (autogenerado en el alta) para no romper /admin ni createsuperuser.
    email = models.EmailField('Email', unique=True)

    ROLE_CHOICES = [
        ('admin', 'Entrenador'),
        ('cliente', 'Cliente'),
    ]
    role = models.CharField(
        'Rol',
        max_length=20,
        choices=ROLE_CHOICES,
        default='cliente',
    )

    phone = models.CharField('Teléfono', max_length=20, blank=True)
    avatar = models.ImageField('Foto', upload_to='avatars/', blank=True)

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def save(self, *args, **kwargs):
        # Normalizar email a minúsculas para que el login case-insensitive no
        # choque con duplicados que difieran solo en mayúsculas.
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_full_name() or self.email} ({self.get_role_display()})"

    @property
    def is_trainer(self):
        """Entrenador/administrador (acceso total)."""
        return self.role == 'admin' or self.is_superuser

    @property
    def is_client(self):
        return self.role == 'cliente' and not self.is_superuser

    @property
    def display_name(self):
        return self.get_full_name() or self.email


class DeviceToken(models.Model):
    """
    Push token (Expo) de un dispositivo donde el usuario tiene instalada la
    app móvil nativa. Un usuario puede tener varios dispositivos; un mismo
    token se reasigna si cambia de usuario (reinstalación, otra cuenta).
    """

    PLATFORM_IOS = 'ios'
    PLATFORM_ANDROID = 'android'
    PLATFORM_CHOICES = [
        (PLATFORM_IOS, 'iOS'),
        (PLATFORM_ANDROID, 'Android'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='device_tokens',
        verbose_name='Usuario',
    )
    token = models.CharField('Push token', max_length=255, unique=True)
    platform = models.CharField('Plataforma', max_length=20, choices=PLATFORM_CHOICES)

    created_at = models.DateTimeField('Creado', auto_now_add=True)
    updated_at = models.DateTimeField('Actualizado', auto_now=True)

    class Meta:
        verbose_name = 'Dispositivo (push)'
        verbose_name_plural = 'Dispositivos (push)'

    def __str__(self):
        return f"{self.user} · {self.platform}"
