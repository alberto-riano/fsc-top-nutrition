import uuid
from datetime import date

from django.db import models

# Tipos de sesión / bono, compartidos por ambos modelos.
SESSION_TYPE_CHOICES = [
    ('individual', 'Individual'),
    ('grupo', 'Grupo pequeño'),
    ('futbol', 'Fútbol'),
]


class Bono(models.Model):
    """
    Bono de sesiones de un cliente (p. ej. bono de 10 sesiones individuales).
    Las sesiones consumidas se cuentan a partir de los registros `Session`
    asociados, de modo que borrar una sesión mal apuntada restaura el contador
    automáticamente.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(
        'clients.ClientProfile',
        on_delete=models.CASCADE,
        related_name='bonos',
        verbose_name='Cliente',
    )
    bono_type = models.CharField(
        'Tipo de bono', max_length=20, choices=SESSION_TYPE_CHOICES, default='individual')
    sessions_total = models.PositiveIntegerField('Sesiones totales', default=10)
    price = models.DecimalField('Precio', max_digits=8, decimal_places=2, null=True, blank=True)
    purchase_date = models.DateField('Fecha de compra', default=date.today)
    expiry_date = models.DateField('Fecha de caducidad', null=True, blank=True)
    archived = models.BooleanField('Archivado', default=False)
    notes = models.TextField('Notas', blank=True)

    created_at = models.DateTimeField('Creado', auto_now_add=True)
    updated_at = models.DateTimeField('Actualizado', auto_now=True)

    class Meta:
        verbose_name = 'Bono'
        verbose_name_plural = 'Bonos'
        ordering = ['-purchase_date', '-created_at']

    def __str__(self):
        return f"{self.get_bono_type_display()} · {self.sessions_used}/{self.sessions_total}"

    @property
    def sessions_used(self):
        return self.sessions.count()

    @property
    def sessions_left(self):
        return max(0, self.sessions_total - self.sessions_used)

    @property
    def progress_pct(self):
        if not self.sessions_total:
            return 0
        return round(100 * self.sessions_used / self.sessions_total)

    @property
    def is_expired(self):
        return bool(self.expiry_date) and self.expiry_date < date.today()

    @property
    def status(self):
        """Estado derivado: archivado / caducado / agotado / activo."""
        if self.archived:
            return 'archivado'
        if self.is_expired:
            return 'caducado'
        if self.sessions_used >= self.sessions_total:
            return 'agotado'
        return 'activo'

    @property
    def status_display(self):
        return {
            'archivado': 'Archivado',
            'caducado': 'Caducado',
            'agotado': 'Agotado',
            'activo': 'Activo',
        }[self.status]


class Session(models.Model):
    """Una sesión registrada, que consume una unidad del bono asociado."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bono = models.ForeignKey(
        'bonos.Bono',
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name='Bono',
    )
    date = models.DateTimeField('Fecha y hora')
    session_type = models.CharField(
        'Tipo de sesión', max_length=20, choices=SESSION_TYPE_CHOICES, default='individual')
    notes = models.TextField('Notas del entrenador', blank=True)

    created_at = models.DateTimeField('Registrada', auto_now_add=True)

    class Meta:
        verbose_name = 'Sesión'
        verbose_name_plural = 'Sesiones'
        ordering = ['-date']

    def __str__(self):
        return f"Sesión {self.get_session_type_display()} · {self.date:%d/%m/%Y %H:%M}"

    def save(self, *args, **kwargs):
        # Por defecto, hereda el tipo del bono al que pertenece.
        if not self.session_type and self.bono_id:
            self.session_type = self.bono.bono_type
        super().save(*args, **kwargs)
