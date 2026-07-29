import uuid
from datetime import date

from django.db import models


class BodyMeasurement(models.Model):
    """Composición corporal en una fecha (datos de báscula)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(
        'clients.ClientProfile',
        on_delete=models.CASCADE,
        related_name='body_measurements',
        verbose_name='Cliente',
    )
    date = models.DateField('Fecha', default=date.today)

    weight_kg = models.DecimalField('Peso (kg)', max_digits=5, decimal_places=1)
    body_fat_pct = models.DecimalField(
        '% grasa corporal', max_digits=4, decimal_places=1, null=True, blank=True)
    muscle_mass_pct = models.DecimalField(
        '% masa muscular', max_digits=4, decimal_places=1, null=True, blank=True)
    water_pct = models.DecimalField(
        '% agua', max_digits=4, decimal_places=1, null=True, blank=True)
    # Campos opcionales que da la báscula.
    visceral_fat = models.DecimalField(
        'Grasa visceral', max_digits=4, decimal_places=1, null=True, blank=True)
    basal_metabolism = models.PositiveIntegerField(
        'Metabolismo basal (kcal)', null=True, blank=True)

    notes = models.CharField('Notas', max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Medición corporal'
        verbose_name_plural = 'Mediciones corporales'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.date:%d/%m/%Y} · {self.weight_kg} kg"


class Exercise(models.Model):
    """
    Catálogo de ejercicios de fuerza. Se siembra con los habituales y el
    entrenador puede añadir los suyos desde /admin/.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('Ejercicio', max_length=80, unique=True)
    order = models.PositiveIntegerField('Orden', default=0)

    class Meta:
        verbose_name = 'Ejercicio'
        verbose_name_plural = 'Ejercicios'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class StrengthPR(models.Model):
    """Récord/registro de fuerza de un cliente en un ejercicio."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(
        'clients.ClientProfile',
        on_delete=models.CASCADE,
        related_name='strength_prs',
        verbose_name='Cliente',
    )
    exercise = models.ForeignKey(
        'metrics.Exercise',
        on_delete=models.PROTECT,
        related_name='prs',
        verbose_name='Ejercicio',
    )
    date = models.DateField('Fecha', default=date.today)
    weight_kg = models.DecimalField('Peso (kg)', max_digits=6, decimal_places=1)
    reps = models.PositiveIntegerField('Repeticiones', default=1)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Récord de fuerza'
        verbose_name_plural = 'Récords de fuerza'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.exercise} · {self.weight_kg} kg × {self.reps}"


class EnduranceTestType(models.Model):
    """
    Catálogo de tests de resistencia / físicos. Se siembra con los habituales
    (incluidos los de fútbol) y es ampliable desde /admin/.
    """
    UNIT_SECONDS = 'segundos'
    UNIT_REPS = 'repeticiones'
    UNIT_METERS = 'metros'
    UNIT_CHOICES = [
        (UNIT_SECONDS, 'Segundos'),
        (UNIT_REPS, 'Repeticiones'),
        (UNIT_METERS, 'Metros'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField('Test', max_length=80, unique=True)
    unit = models.CharField('Unidad', max_length=20, choices=UNIT_CHOICES, default=UNIT_SECONDS)
    # Para segundos/metros/reps a veces "más" es mejor y a veces "menos" (sprint).
    lower_is_better = models.BooleanField('Menos es mejor', default=False)
    order = models.PositiveIntegerField('Orden', default=0)

    class Meta:
        verbose_name = 'Tipo de test'
        verbose_name_plural = 'Tipos de test'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    @property
    def unit_short(self):
        return {'segundos': 's', 'repeticiones': 'reps', 'metros': 'm'}.get(self.unit, self.unit)


class EnduranceTest(models.Model):
    """Registro de un test de resistencia / físico de un cliente."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(
        'clients.ClientProfile',
        on_delete=models.CASCADE,
        related_name='endurance_tests',
        verbose_name='Cliente',
    )
    test_type = models.ForeignKey(
        'metrics.EnduranceTestType',
        on_delete=models.PROTECT,
        related_name='results',
        verbose_name='Test',
    )
    date = models.DateField('Fecha', default=date.today)
    value = models.DecimalField('Valor', max_digits=8, decimal_places=1)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Test de resistencia'
        verbose_name_plural = 'Tests de resistencia'
        ordering = ['-date', '-created_at']

    def __str__(self):
        return f"{self.test_type} · {self.value} {self.test_type.unit_short}"
