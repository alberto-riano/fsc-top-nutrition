import uuid
from datetime import date

from django.conf import settings
from django.db import models


class ClientProfile(models.Model):
    """
    Perfil de un cliente de FSC Top Nutrition. Relación 1:1 con el usuario que
    inicia sesión. El `profile_type` condiciona qué secciones se muestran tanto
    en el panel del cliente como en la ficha del entrenador.
    """

    PROFILE_COMPLETO = 'completo'
    PROFILE_BASICO = 'basico'
    PROFILE_FUTBOLISTA = 'futbolista'
    PROFILE_CHOICES = [
        (PROFILE_COMPLETO, 'Completo'),
        (PROFILE_BASICO, 'Básico'),
        (PROFILE_FUTBOLISTA, 'Futbolista'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='client_profile',
        verbose_name='Usuario',
    )
    profile_type = models.CharField(
        'Tipo de perfil', max_length=20, choices=PROFILE_CHOICES, default=PROFILE_COMPLETO)

    start_date = models.DateField('Fecha de alta', default=date.today)
    goal = models.TextField('Objetivo', blank=True)
    internal_notes = models.TextField(
        'Notas internas', blank=True,
        help_text='Solo visibles para el entrenador, nunca para el cliente.')
    active = models.BooleanField('Activo', default=True)

    # Campos específicos de futbolista (menores de edad)
    birth_date = models.DateField('Fecha de nacimiento', null=True, blank=True)
    position = models.CharField('Posición', max_length=50, blank=True)
    guardian_name = models.CharField('Nombre del tutor', max_length=150, blank=True)
    guardian_phone = models.CharField('Teléfono del tutor', max_length=20, blank=True)

    created_at = models.DateTimeField('Creado', auto_now_add=True)
    updated_at = models.DateTimeField('Actualizado', auto_now=True)

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['user__first_name', 'user__last_name']

    def __str__(self):
        return self.full_name

    # -- Identidad -----------------------------------------------------------
    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.email

    @property
    def initials(self):
        first = (self.user.first_name or self.user.email)[:1]
        last = (self.user.last_name or '')[:1]
        return (first + last).upper()

    @property
    def age(self):
        if not self.birth_date:
            return None
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day))

    # -- Visibilidad de secciones por tipo de perfil -------------------------
    @property
    def is_football(self):
        return self.profile_type == self.PROFILE_FUTBOLISTA

    @property
    def shows_body_composition(self):
        return self.profile_type in (self.PROFILE_COMPLETO, self.PROFILE_BASICO)

    @property
    def shows_strength_prs(self):
        return self.profile_type == self.PROFILE_COMPLETO

    @property
    def shows_endurance_tests(self):
        return self.profile_type in (self.PROFILE_COMPLETO, self.PROFILE_FUTBOLISTA)

    @property
    def shows_plans(self):
        return self.profile_type == self.PROFILE_COMPLETO

    @property
    def shows_metrics(self):
        return (self.shows_body_composition or self.shows_strength_prs
                or self.shows_endurance_tests)

    # -- Bonos ---------------------------------------------------------------
    @property
    def active_bono(self):
        """Bono con sesiones disponibles y no caducado, si lo hay."""
        for bono in self.bonos.filter(archived=False).order_by('purchase_date', 'created_at'):
            if bono.status == 'activo':
                return bono
        return None

    @property
    def sessions_left(self):
        bono = self.active_bono
        return bono.sessions_left if bono else 0

    @property
    def low_sessions_alert(self):
        """True si al cliente le quedan pocas (<=2) sesiones en su bono activo."""
        bono = self.active_bono
        return bool(bono) and bono.sessions_left <= 2
