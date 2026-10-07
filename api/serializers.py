from django.utils import timezone
from rest_framework import serializers

from accounts.models import DeviceToken, User
from bonos.models import Bono, Session
from clients.models import ClientProfile
from metrics.models import BodyMeasurement, EnduranceTest, StrengthPR
from plans.models import Plan


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


class PlanSerializer(serializers.ModelSerializer):
    pdf_url = serializers.SerializerMethodField()
    is_routine = serializers.ReadOnlyField()
    is_nutrition = serializers.ReadOnlyField()

    class Meta:
        model = Plan
        fields = (
            'id', 'plan_type', 'title', 'content', 'pdf_url', 'date',
            'archived', 'is_routine', 'is_nutrition',
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

    class Meta:
        model = Plan
        fields = (
            'id', 'plan_type', 'title', 'content', 'pdf', 'pdf_url', 'date',
            'archived', 'archive_previous',
        )
        extra_kwargs = {'pdf': {'write_only': True, 'required': False}}

    def validate(self, attrs):
        content = attrs.get('content', getattr(self.instance, 'content', ''))
        pdf = attrs.get('pdf', getattr(self.instance, 'pdf', None))
        if not content and not pdf:
            raise serializers.ValidationError('Añade contenido de texto o un PDF (al menos uno).')
        return attrs

    def get_pdf_url(self, obj):
        if not obj.pdf:
            return None
        request = self.context.get('request')
        url = obj.pdf.url
        return request.build_absolute_uri(url) if request else url

    def create(self, validated_data):
        archive_previous = validated_data.pop('archive_previous', True)
        client = self.context['client']
        if archive_previous:
            client.plans.filter(plan_type=validated_data['plan_type'], archived=False).update(archived=True)
        return Plan.objects.create(client=client, **validated_data)
