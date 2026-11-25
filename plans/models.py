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
    products = models.ManyToManyField(
        'plans.Product',
        through='plans.PlanProduct',
        related_name='plans',
        blank=True,
        verbose_name='Productos recomendados',
    )

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


class Product(models.Model):
    """
    Catálogo de productos que recomienda el entrenador (suplementos, alimentos,
    material…), cada uno con el enlace a su página. Se añaden a los planes de
    alimentación y el cliente los abre desde la app.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('Nombre', max_length=120)
    brand = models.CharField('Marca', max_length=80, blank=True)
    description = models.CharField('Descripción', max_length=255, blank=True)
    url = models.URLField('Enlace', max_length=500)
    # Archivar en vez de borrar: un producto que ya está en planes de clientes
    # no debe desaparecer de ellos; solo deja de ofrecerse para planes nuevos.
    active = models.BooleanField('Activo', default=True)

    created_at = models.DateTimeField('Creado', auto_now_add=True)
    updated_at = models.DateTimeField('Actualizado', auto_now=True)

    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.brand})" if self.brand else self.name


class PlanProduct(models.Model):
    """Un producto dentro de un plan, con la pauta (cuánto y cuándo)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='plan_products')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='plan_products')
    note = models.CharField('Pauta', max_length=160, blank=True)
    order = models.PositiveIntegerField('Orden', default=0)

    class Meta:
        verbose_name = 'Producto del plan'
        verbose_name_plural = 'Productos del plan'
        ordering = ['order']
        constraints = [
            models.UniqueConstraint(fields=['plan', 'product'], name='unique_product_per_plan'),
        ]

    def __str__(self):
        return f"{self.plan} · {self.product}"
