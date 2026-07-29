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
