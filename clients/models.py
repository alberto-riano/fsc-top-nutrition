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


RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]


class PlayerQuestionnaire(models.Model):
    """
    Cuestionario inicial de futbolistas (niños y adolescentes). Se rellena una
    vez al dar de alta al jugador y se puede editar después. Solo visible para
    el entrenador (incluye datos sensibles de salud y notas de los padres).
    """

    FOOT_DERECHO = 'derecho'
    FOOT_IZQUIERDO = 'izquierdo'
    FOOT_AMBOS = 'ambos'
    FOOT_CHOICES = [
        (FOOT_DERECHO, 'Derecho'),
        (FOOT_IZQUIERDO, 'Izquierdo'),
        (FOOT_AMBOS, 'Ambos'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.OneToOneField(
        'clients.ClientProfile',
        on_delete=models.CASCADE,
        related_name='questionnaire',
        verbose_name='Cliente',
    )

    # -- Datos personales (complementan los ya recogidos en ClientProfile) ---
    team = models.CharField('Equipo actual', max_length=120, blank=True)
    category = models.CharField('Categoría', max_length=80, blank=True)
    dominant_foot = models.CharField('Pie dominante', max_length=20, choices=FOOT_CHOICES, blank=True)
    height_cm = models.PositiveSmallIntegerField('Altura (cm)', null=True, blank=True)
    weight_kg = models.DecimalField('Peso (kg)', max_digits=5, decimal_places=1, null=True, blank=True)
    guardian_email = models.EmailField('Email de los padres/tutor', blank=True)

    # -- Fútbol -----------------------------------------------------------
    years_playing = models.PositiveSmallIntegerField('Años jugando al fútbol', null=True, blank=True)
    weekly_trainings = models.PositiveSmallIntegerField('Entrenamientos/semana con el equipo', null=True, blank=True)
    weekly_matches = models.PositiveSmallIntegerField('Partidos habituales', null=True, blank=True)
    other_sports = models.CharField('Otros deportes que practica', max_length=255, blank=True)
    strengths = models.TextField('Puntos fuertes como futbolista', blank=True)
    areas_to_improve = models.TextField('Aspectos a mejorar', blank=True)
    season_goals = models.TextField('Objetivos de la temporada', blank=True)

    # -- Hábitos diarios ----------------------------------------------------
    wake_time = models.TimeField('Hora de levantarse', null=True, blank=True)
    sleep_time = models.TimeField('Hora de acostarse', null=True, blank=True)
    sleep_hours = models.DecimalField('Horas de sueño', max_digits=3, decimal_places=1, null=True, blank=True)
    daily_routine = models.TextField('Día normal (colegio, estudios, entrenos, descanso)', blank=True)
    screen_time = models.CharField('Tiempo diario de móvil/videojuegos/TV', max_length=100, blank=True)

    # -- Entrenamiento --------------------------------------------------------
    gym_experience = models.BooleanField('Ha entrenado antes en gimnasio/centro deportivo', default=False)
    trainer_experience = models.BooleanField('Ha trabajado con preparador físico/entrenador personal', default=False)
    trainer_experience_detail = models.TextField('Cómo fue esa experiencia', blank=True)
    weekly_availability_days = models.PositiveSmallIntegerField('Días/semana disponibles además del equipo', null=True, blank=True)
    session_duration_minutes = models.PositiveSmallIntegerField('Minutos disponibles por sesión', null=True, blank=True)

    # -- Valoración física (1-5) ----------------------------------------------
    rating_endurance = models.PositiveSmallIntegerField('Resistencia', choices=RATING_CHOICES, null=True, blank=True)
    rating_strength = models.PositiveSmallIntegerField('Fuerza', choices=RATING_CHOICES, null=True, blank=True)
    rating_speed = models.PositiveSmallIntegerField('Velocidad', choices=RATING_CHOICES, null=True, blank=True)
    rating_jump_power = models.PositiveSmallIntegerField('Potencia de salto', choices=RATING_CHOICES, null=True, blank=True)
    rating_agility = models.PositiveSmallIntegerField('Agilidad', choices=RATING_CHOICES, null=True, blank=True)
    rating_change_of_direction = models.PositiveSmallIntegerField('Cambios de dirección', choices=RATING_CHOICES, null=True, blank=True)
    rating_balance = models.PositiveSmallIntegerField('Equilibrio', choices=RATING_CHOICES, null=True, blank=True)
    rating_flexibility = models.PositiveSmallIntegerField('Flexibilidad', choices=RATING_CHOICES, null=True, blank=True)

    # -- Salud y lesiones -----------------------------------------------------
    had_major_injury = models.BooleanField('Ha tenido alguna lesión importante', default=False)
    injury_ankle_sprain = models.BooleanField('Esguince de tobillo', default=False)
    injury_knee = models.BooleanField('Lesión de rodilla', default=False)
    injury_muscle_tear = models.BooleanField('Rotura muscular', default=False)
    injury_hamstring = models.BooleanField('Lesión de isquiotibiales', default=False)
    injury_pubalgia = models.BooleanField('Pubalgia', default=False)
    injury_lower_back = models.BooleanField('Dolor lumbar', default=False)
    injury_fracture = models.BooleanField('Fractura', default=False)
    injury_other = models.BooleanField('Otra lesión', default=False)
    injury_other_detail = models.CharField('Cuál (otra lesión)', max_length=255, blank=True)
    current_pain = models.TextField('Molestia o dolor actual', blank=True)
    painful_movements = models.TextField('Movimientos/ejercicios que producen molestias', blank=True)
    physio_treatment = models.TextField('Tratamiento de fisioterapia/rehabilitación en curso', blank=True)
    medication = models.TextField('Medicación habitual', blank=True)
    medical_conditions = models.TextField('Enfermedades (asma, alergias, diabetes...)', blank=True)
    doctor_restricted_exercise = models.BooleanField('El médico le ha prohibido ejercicio intenso', default=False)

    # -- Alimentación ---------------------------------------------------------
    meals_per_day = models.PositiveSmallIntegerField('Comidas al día', null=True, blank=True)
    breakfast = models.TextField('Desayuno habitual', blank=True)
    pre_training_meal = models.TextField('Qué come antes de entrenar', blank=True)
    post_training_dinner = models.TextField('Qué cena después de entrenar', blank=True)
    water_intake = models.CharField('Agua al día (aprox.)', max_length=100, blank=True)
    liked_foods = models.TextField('Alimentos que le encantan', blank=True)
    disliked_foods = models.TextField('Alimentos que no le gustan', blank=True)
    junk_food_frequency = models.CharField('Frecuencia de bollería/refrescos/comida rápida', max_length=100, blank=True)
    supplements = models.TextField('Suplementos deportivos', blank=True)

    # -- Objetivos --------------------------------------------------------
    goal_faster = models.BooleanField('Ser más rápido', default=False)
    goal_more_strength = models.BooleanField('Tener más fuerza', default=False)
    goal_jump_higher = models.BooleanField('Saltar más', default=False)
    goal_better_acceleration = models.BooleanField('Mejorar la aceleración', default=False)
    goal_change_direction = models.BooleanField('Cambiar de dirección más rápido', default=False)
    goal_less_fatigue = models.BooleanField('Cansarse menos en los partidos', default=False)
    goal_prevent_injuries = models.BooleanField('Prevenir lesiones', default=False)
    goal_injury_recovery = models.BooleanField('Recuperarse de una lesión', default=False)
    goal_season_fitness = models.BooleanField('Llegar mejor físicamente a la temporada', default=False)
    goal_trials_prep = models.BooleanField('Preparar pruebas de acceso', default=False)
    goal_other = models.CharField('Otro objetivo', max_length=255, blank=True)

    # -- Disponibilidad ---------------------------------------------------
    available_days = models.CharField('Días disponibles', max_length=255, blank=True)
    available_schedule = models.CharField('Horario disponible', max_length=255, blank=True)
    important_dates = models.TextField('Fechas importantes de la temporada', blank=True)

    # -- Información para los padres -----------------------------------------
    parent_notes = models.TextField(
        'Algo importante que debamos saber (salud, hábitos, rendimiento, comportamiento, estudios...)',
        blank=True)

    created_at = models.DateTimeField('Creado', auto_now_add=True)
    updated_at = models.DateTimeField('Actualizado', auto_now=True)

    class Meta:
        verbose_name = 'Cuestionario de futbolista'
        verbose_name_plural = 'Cuestionarios de futbolista'

    def __str__(self):
        return f"Cuestionario de {self.client.full_name}"

    @property
    def injuries(self):
        """Lista de lesiones marcadas, para mostrar como badges."""
        mapping = [
            (self.injury_ankle_sprain, 'Esguince de tobillo'),
            (self.injury_knee, 'Lesión de rodilla'),
            (self.injury_muscle_tear, 'Rotura muscular'),
            (self.injury_hamstring, 'Lesión de isquiotibiales'),
            (self.injury_pubalgia, 'Pubalgia'),
            (self.injury_lower_back, 'Dolor lumbar'),
            (self.injury_fracture, 'Fractura'),
        ]
        labels = [label for checked, label in mapping if checked]
        if self.injury_other and self.injury_other_detail:
            labels.append(self.injury_other_detail)
        elif self.injury_other:
            labels.append('Otra')
        return labels

    @property
    def objectives(self):
        """Lista de objetivos marcados, para mostrar como badges."""
        mapping = [
            (self.goal_faster, 'Ser más rápido'),
            (self.goal_more_strength, 'Tener más fuerza'),
            (self.goal_jump_higher, 'Saltar más'),
            (self.goal_better_acceleration, 'Mejorar la aceleración'),
            (self.goal_change_direction, 'Cambiar de dirección más rápido'),
            (self.goal_less_fatigue, 'Cansarse menos en los partidos'),
            (self.goal_prevent_injuries, 'Prevenir lesiones'),
            (self.goal_injury_recovery, 'Recuperarse de una lesión'),
            (self.goal_season_fitness, 'Llegar mejor físicamente a la temporada'),
            (self.goal_trials_prep, 'Preparar pruebas de acceso'),
        ]
        labels = [label for checked, label in mapping if checked]
        if self.goal_other:
            labels.append(self.goal_other)
        return labels

    @property
    def ratings(self):
        """Pares (etiqueta, valor 1-5) para pintar la valoración física."""
        fields = [
            ('Resistencia', self.rating_endurance),
            ('Fuerza', self.rating_strength),
            ('Velocidad', self.rating_speed),
            ('Potencia de salto', self.rating_jump_power),
            ('Agilidad', self.rating_agility),
            ('Cambios de dirección', self.rating_change_of_direction),
            ('Equilibrio', self.rating_balance),
            ('Flexibilidad', self.rating_flexibility),
        ]
        return [(label, value) for label, value in fields if value]
