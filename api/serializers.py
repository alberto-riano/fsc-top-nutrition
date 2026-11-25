from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from accounts.models import DeviceToken, User
from bonos.models import Bono, Session
from clients.models import ClientProfile
from metrics.body_map import FIELD_NAMES
from metrics.models import BodyMeasurement, CircumferenceMeasurement, EnduranceTest, StrengthPR
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

    class Meta:
        model = ClientProfile
        fields = (
            'id', 'profile_type', 'start_date', 'goal', 'active',
            'birth_date', 'position', 'full_name', 'initials', 'age',
            'sessions_left', 'low_sessions_alert', 'shows_body_composition',
            'shows_strength_prs', 'shows_endurance_tests', 'shows_plans',
            'shows_metrics',
        )


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

class ClientListItemSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    initials = serializers.ReadOnlyField()
    sessions_left = serializers.ReadOnlyField()
    low_sessions_alert = serializers.ReadOnlyField()

    class Meta:
        model = ClientProfile
        fields = (
            'id', 'full_name', 'initials', 'profile_type', 'active',
            'sessions_left', 'low_sessions_alert',
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
