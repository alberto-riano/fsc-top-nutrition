from datetime import date

from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from accounts.models import DeviceToken, User
from bonos.models import Bono, Session
from clients.models import ClientProfile
from metrics.body_map import FIELD_NAMES
from clients.services import create_client_user
from metrics.models import (
    BodyMeasurement, CircumferenceMeasurement, EnduranceTest, EnduranceTestType, Exercise, StrengthPR,
)
from plans.models import Plan, PlanProduct, Product


class UserSerializer(serializers.ModelSerializer):
    display_name = serializers.ReadOnlyField()
    is_trainer = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'phone', 'role',
                  'display_name', 'is_trainer')


class ClientProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    initials = serializers.ReadOnlyField()
    age = serializers.ReadOnlyField()
    sessions_left = serializers.ReadOnlyField()
    low_sessions_alert = serializers.ReadOnlyField()
    shows_body_composition = serializers.ReadOnlyField()
    shows_strength_prs = serializers.ReadOnlyField()
    shows_endurance_tests = serializers.ReadOnlyField()
    shows_plans = serializers.ReadOnlyField()
    shows_metrics = serializers.ReadOnlyField()
    queued_sessions = serializers.ReadOnlyField()
    active_bono_id = serializers.SerializerMethodField()
    username = serializers.CharField(source='user.email', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    access_pending = serializers.SerializerMethodField()

    class Meta:
        model = ClientProfile
        fields = (
            'id', 'profile_type', 'sex', 'start_date', 'goal', 'active',
            'birth_date', 'position', 'full_name', 'initials', 'age',
            'sessions_left', 'queued_sessions', 'active_bono_id', 'low_sessions_alert',
            'shows_body_composition', 'shows_strength_prs', 'shows_endurance_tests',
            'shows_plans', 'shows_metrics', 'username', 'phone', 'access_pending',
        )

    def get_active_bono_id(self, obj):
        bono = obj.active_bono
        return str(bono.id) if bono else None

    def get_access_pending(self, obj):
        return access_pending(obj.user)


def access_pending(user):
    """Todavía no ha puesto su contraseña (se le dio de alta con invitación)."""
    return not user.is_active or not user.has_usable_password()


class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Session
        fields = ('id', 'date', 'session_type', 'notes')


class BonoSerializer(serializers.ModelSerializer):
    sessions = SessionSerializer(many=True, read_only=True)
    sessions_used = serializers.ReadOnlyField()
    sessions_left = serializers.ReadOnlyField()
    progress_pct = serializers.ReadOnlyField()
    status = serializers.ReadOnlyField()
    status_display = serializers.ReadOnlyField()

    class Meta:
        model = Bono
        fields = (
            'id', 'bono_type', 'sessions_total', 'purchase_date', 'expiry_date',
            'archived', 'sessions', 'sessions_used', 'sessions_left',
            'progress_pct', 'status', 'status_display',
        )


class BodyMeasurementSerializer(serializers.ModelSerializer):
    class Meta:
        model = BodyMeasurement
        fields = (
            'id', 'date', 'weight_kg', 'body_fat_pct', 'muscle_mass_pct',
            'water_pct', 'visceral_fat', 'basal_metabolism', 'notes',
        )

    def validate_weight_kg(self, value):
        if value is None or value <= 0 or value > 400:
            raise serializers.ValidationError('Indica un peso válido en kg.')
        return value

    def validate(self, attrs):
        labels = {'body_fat_pct': 'grasa', 'muscle_mass_pct': 'músculo', 'water_pct': 'agua'}
        for field, label in labels.items():
            value = attrs.get(field)
            if value is not None and not (0 < value < 100):
                raise serializers.ValidationError({field: f'El % de {label} debe estar entre 0 y 100.'})
        fat, muscle = attrs.get('body_fat_pct'), attrs.get('muscle_mass_pct')
        if fat is not None and muscle is not None and fat + muscle > 100:
            raise serializers.ValidationError('La grasa y el músculo juntos no pueden pasar del 100 %.')
        return attrs


class CircumferenceMeasurementSerializer(serializers.ModelSerializer):
    class Meta:
        model = CircumferenceMeasurement
        fields = ('id', 'date', *FIELD_NAMES, 'notes')

    def validate(self, attrs):
        if not any(attrs.get(f) is not None for f in FIELD_NAMES):
            raise serializers.ValidationError('Indica al menos una medida.')
        return attrs


class TrainerBonoReadSerializer(BonoSerializer):
    """El bono visto por el entrenador: con precio y notas, que el cliente no ve."""

    class Meta(BonoSerializer.Meta):
        fields = BonoSerializer.Meta.fields + ('price', 'notes')


class TrainerBonoSerializer(serializers.ModelSerializer):
    """Alta de un bono desde la app del entrenador."""

    class Meta:
        model = Bono
        fields = ('bono_type', 'sessions_total', 'price', 'purchase_date', 'expiry_date', 'notes')

    def validate_sessions_total(self, value):
        if not 1 <= value <= 200:
            raise serializers.ValidationError('Indica entre 1 y 200 sesiones.')
        return value

    def validate_price(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError('El precio no puede ser negativo.')
        return value

    def validate(self, attrs):
        purchase = attrs.get('purchase_date') or date.today()
        expiry = attrs.get('expiry_date')
        if expiry and expiry < purchase:
            raise serializers.ValidationError({'expiry_date': 'La caducidad no puede ser anterior a la compra.'})
        return attrs


class ExerciseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = ('id', 'name')


class EnduranceTestTypeSerializer(serializers.ModelSerializer):
    unit_short = serializers.ReadOnlyField()

    class Meta:
        model = EnduranceTestType
        fields = ('id', 'name', 'unit', 'unit_short', 'lower_is_better')


def _not_in_future(value):
    if value and value > date.today():
        raise serializers.ValidationError('La fecha no puede ser futura.')
    return value


def one_rep_max(weight, reps):
    """1RM estimado (Epley), para comparar 100×5 con 110×2."""
    weight = float(weight)
    return weight if reps <= 1 else weight * (1 + reps / 30)


class TrainerStrengthPRCreateSerializer(serializers.ModelSerializer):
    """Marca de fuerza. El ejercicio va por id o, si es nuevo, por nombre."""

    exercise = serializers.PrimaryKeyRelatedField(queryset=Exercise.objects.all(), required=False)
    exercise_name = serializers.CharField(max_length=80, required=False, allow_blank=True, write_only=True)

    class Meta:
        model = StrengthPR
        fields = ('exercise', 'exercise_name', 'weight_kg', 'reps', 'date')

    validate_date = staticmethod(_not_in_future)

    def validate_weight_kg(self, value):
        if not 0 < value <= 600:
            raise serializers.ValidationError('Indica un peso entre 0 y 600 kg.')
        return value

    def validate_reps(self, value):
        if not 1 <= value <= 100:
            raise serializers.ValidationError('Indica entre 1 y 100 repeticiones.')
        return value

    def validate(self, attrs):
        name = (attrs.pop('exercise_name', '') or '').strip()
        if not attrs.get('exercise'):
            if not name:
                raise serializers.ValidationError({'exercise': 'Elige un ejercicio.'})
            existing = Exercise.objects.filter(name__iexact=name).first()
            attrs['exercise'] = existing or Exercise(name=name[:1].upper() + name[1:], order=999)
        return attrs

    def create(self, validated_data):
        exercise = validated_data['exercise']
        if exercise._state.adding:
            exercise.save()
        return super().create(validated_data)


class TrainerEnduranceTestCreateSerializer(serializers.ModelSerializer):
    test_type = serializers.PrimaryKeyRelatedField(queryset=EnduranceTestType.objects.all())

    class Meta:
        model = EnduranceTest
        fields = ('test_type', 'value', 'date')

    validate_date = staticmethod(_not_in_future)

    def validate_value(self, value):
        if value <= 0:
            raise serializers.ValidationError('Indica un valor mayor que 0.')
        return value


class StrengthPRSerializer(serializers.ModelSerializer):
    exercise_name = serializers.CharField(source='exercise.name', read_only=True)

    class Meta:
        model = StrengthPR
        fields = ('id', 'date', 'exercise_name', 'weight_kg', 'reps')


class EnduranceTestSerializer(serializers.ModelSerializer):
    test_name = serializers.CharField(source='test_type.name', read_only=True)
    unit_short = serializers.CharField(source='test_type.unit_short', read_only=True)

    class Meta:
        model = EnduranceTest
        fields = ('id', 'date', 'test_name', 'unit_short', 'value')


class ProductSerializer(serializers.ModelSerializer):
    plans_count = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ('id', 'name', 'brand', 'description', 'url', 'active', 'plans_count')

    def get_plans_count(self, obj):
        count = getattr(obj, 'plans_count', None)
        return count if count is not None else obj.plan_products.count()

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Ponle un nombre al producto.')
        return value

    def validate_url(self, value):
        if not value.lower().startswith(('http://', 'https://')):
            raise serializers.ValidationError('El enlace debe empezar por http:// o https://')
        return value


class PlanProductSerializer(serializers.ModelSerializer):
    """El producto tal y como lo ve el cliente dentro de su plan."""

    id = serializers.UUIDField(source='product.id', read_only=True)
    name = serializers.CharField(source='product.name', read_only=True)
    brand = serializers.CharField(source='product.brand', read_only=True)
    description = serializers.CharField(source='product.description', read_only=True)
    url = serializers.CharField(source='product.url', read_only=True)

    class Meta:
        model = PlanProduct
        fields = ('id', 'name', 'brand', 'description', 'url', 'note')


class PlanSerializer(serializers.ModelSerializer):
    pdf_url = serializers.SerializerMethodField()
    is_routine = serializers.ReadOnlyField()
    is_nutrition = serializers.ReadOnlyField()
    products = PlanProductSerializer(source='plan_products', many=True, read_only=True)

    class Meta:
        model = Plan
        fields = (
            'id', 'plan_type', 'title', 'content', 'pdf_url', 'date',
            'archived', 'is_routine', 'is_nutrition', 'products',
        )

    def get_pdf_url(self, obj):
        if not obj.pdf:
            return None
        request = self.context.get('request')
        url = obj.pdf.url
        return request.build_absolute_uri(url) if request else url


class DeviceTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceToken
        fields = ('token', 'platform')

    def create(self, validated_data):
        user = self.context['request'].user
        device, _ = DeviceToken.objects.update_or_create(
            token=validated_data['token'],
            defaults={'user': user, 'platform': validated_data['platform']},
        )
        return device


# -- Entrenador ---------------------------------------------------------------

class ClientSexSerializer(serializers.ModelSerializer):
    """Lo único que el entrenador cambia de la ficha desde la app: el sexo (silueta)."""

    class Meta:
        model = ClientProfile
        fields = ('sex',)


class ClientListItemSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    initials = serializers.ReadOnlyField()
    sessions_left = serializers.ReadOnlyField()
    low_sessions_alert = serializers.ReadOnlyField()
    access_pending = serializers.SerializerMethodField()

    class Meta:
        model = ClientProfile
        fields = (
            'id', 'full_name', 'initials', 'profile_type', 'active',
            'sessions_left', 'low_sessions_alert', 'access_pending',
        )

    def get_access_pending(self, obj):
        return access_pending(obj.user)


class TrainerClientCreateSerializer(serializers.Serializer):
    """
    Alta de cliente desde la app. Mismas reglas que la ficha web: el usuario es
    único (sin distinguir mayúsculas), la contraseña es opcional (sin ella se
    entra por invitación) y un futbolista necesita fecha de nacimiento y tutor.
    """

    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default='')
    username = serializers.CharField(max_length=150, validators=[UnicodeUsernameValidator()])
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')
    password = serializers.CharField(required=False, allow_blank=True, write_only=True, default='')
    profile_type = serializers.ChoiceField(ClientProfile.PROFILE_CHOICES, default=ClientProfile.PROFILE_COMPLETO)
    sex = serializers.ChoiceField(ClientProfile.SEX_CHOICES, required=False, allow_blank=True, default='')
    goal = serializers.CharField(required=False, allow_blank=True, default='')
    birth_date = serializers.DateField(required=False, allow_null=True, default=None)
    position = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    guardian_name = serializers.CharField(max_length=150, required=False, allow_blank=True, default='')
    guardian_phone = serializers.CharField(max_length=20, required=False, allow_blank=True, default='')

    def validate_first_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('Indica el nombre.')
        return value

    def validate_username(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Ya hay una cuenta con este usuario.')
        return value

    def validate_password(self, value):
        if value:
            validate_password(value)
        return value

    def validate_birth_date(self, value):
        if value and value > date.today():
            raise serializers.ValidationError('La fecha de nacimiento no puede ser futura.')
        return value

    def validate(self, attrs):
        if attrs['profile_type'] == ClientProfile.PROFILE_FUTBOLISTA:
            errors = {}
            if not attrs.get('birth_date'):
                errors['birth_date'] = 'Obligatoria para un futbolista.'
            if not attrs.get('guardian_name', '').strip():
                errors['guardian_name'] = 'Indica el nombre del tutor (es menor).'
            if errors:
                raise serializers.ValidationError(errors)
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        user = create_client_user(
            email=validated_data['username'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'].strip(),
            phone=validated_data['phone'].strip(),
            password=validated_data['password'] or None,
        )
        return ClientProfile.objects.create(
            user=user,
            profile_type=validated_data['profile_type'],
            sex=validated_data['sex'],
            goal=validated_data['goal'].strip(),
            birth_date=validated_data['birth_date'],
            position=validated_data['position'].strip(),
            guardian_name=validated_data['guardian_name'].strip(),
            guardian_phone=validated_data['guardian_phone'].strip(),
        )


class MarkSessionSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True, default='')

    def save(self, **kwargs):
        client = self.context['client']
        bono = client.active_bono
        if bono is None:
            raise serializers.ValidationError('No hay ningún bono activo con sesiones disponibles.')
        return Session.objects.create(
            bono=bono,
            date=timezone.now(),
            session_type=bono.bono_type,
            notes=self.validated_data.get('notes', ''),
        )


class TrainerPlanSerializer(serializers.ModelSerializer):
    archive_previous = serializers.BooleanField(write_only=True, required=False, default=True)
    pdf_url = serializers.SerializerMethodField()
    # Llega como texto JSON dentro del multipart: [{"product": "<uuid>", "note": "…"}].
    products = serializers.JSONField(write_only=True, required=False)

    class Meta:
        model = Plan
        fields = (
            'id', 'plan_type', 'title', 'content', 'pdf', 'pdf_url', 'date',
            'archived', 'archive_previous', 'products',
        )
        extra_kwargs = {'pdf': {'write_only': True, 'required': False}}

    def validate_products(self, value):
        if value in (None, ''):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError('Formato de productos no válido.')
        items, seen = [], set()
        for raw in value:
            if not isinstance(raw, dict) or not raw.get('product'):
                raise serializers.ValidationError('Formato de productos no válido.')
            pid = str(raw['product'])
            if pid in seen:
                continue
            seen.add(pid)
            note = str(raw.get('note') or '').strip()[:160]
            items.append((pid, note))
        found = {str(p.id): p for p in Product.objects.filter(pk__in=[pid for pid, _ in items], active=True)}
        missing = [pid for pid, _ in items if pid not in found]
        if missing:
            raise serializers.ValidationError('Algún producto ya no está en el catálogo. Vuelve a elegirlos.')
        return [(found[pid], note) for pid, note in items]

    def validate(self, attrs):
        content = attrs.get('content', getattr(self.instance, 'content', ''))
        pdf = attrs.get('pdf', getattr(self.instance, 'pdf', None))
        has_products = bool(attrs.get('products'))
        if not content and not pdf and not has_products:
            raise serializers.ValidationError('Añade contenido de texto, un PDF o algún producto.')
        if has_products and attrs.get('plan_type') != Plan.TYPE_NUTRITION:
            raise serializers.ValidationError('Los productos solo se añaden a planes de alimentación.')
        return attrs

    def get_pdf_url(self, obj):
        if not obj.pdf:
            return None
        request = self.context.get('request')
        url = obj.pdf.url
        return request.build_absolute_uri(url) if request else url

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['products'] = PlanProductSerializer(instance.plan_products.select_related('product'), many=True).data
        return data

    @transaction.atomic
    def create(self, validated_data):
        archive_previous = validated_data.pop('archive_previous', True)
        products = validated_data.pop('products', [])
        client = self.context['client']
        if archive_previous:
            client.plans.filter(plan_type=validated_data['plan_type'], archived=False).update(archived=True)
        plan = Plan.objects.create(client=client, **validated_data)
        PlanProduct.objects.bulk_create([
            PlanProduct(plan=plan, product=product, note=note, order=i)
            for i, (product, note) in enumerate(products)
        ])
        return plan
