import uuid
from datetime import date

from django.db import models


class Plan(models.Model):
    """
    Rutina de entrenamiento o plan de alimentación de un cliente. El contenido
    puede ser texto y/o un PDF adjunto. Al subir uno nuevo, el entrenador puede
    archivar el anterior para conservar el histórico.
    """

    TYPE_ROUTINE = 'rutina'
    TYPE_NUTRITION = 'alimentacion'
    TYPE_CHOICES = [
        (TYPE_ROUTINE, 'Rutina de entrenamiento'),
        (TYPE_NUTRITION, 'Plan de alimentación'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(
        'clients.ClientProfile',
        on_delete=models.CASCADE,
        related_name='plans',
        verbose_name='Cliente',
    )
    plan_type = models.CharField('Tipo', max_length=20, choices=TYPE_CHOICES)
    title = models.CharField('Título', max_length=150)
    content = models.TextField('Contenido', blank=True)
    pdf = models.FileField('PDF', upload_to='plans/', blank=True)
    date = models.DateField('Fecha', default=date.today)
    archived = models.BooleanField('Archivado', default=False)

    created_at = models.DateTimeField('Creado', auto_now_add=True)
    updated_at = models.DateTimeField('Actualizado', auto_now=True)

    class Meta:
        verbose_name = 'Plan'
        verbose_name_plural = 'Planes'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.get_plan_type_display()} · {self.title}"

    @property
    def is_routine(self):
        return self.plan_type == self.TYPE_ROUTINE

    @property
    def is_nutrition(self):
        return self.plan_type == self.TYPE_NUTRITION
