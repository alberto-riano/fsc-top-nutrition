from django.contrib.auth import authenticate
from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from bonos.models import Bono
from clients.models import ClientProfile
from metrics.models import BodyMeasurement, EnduranceTest, StrengthPR
from plans.models import Plan

from .permissions import ClientProfileMixin, IsTrainer, TrainerClientMixin
from .serializers import (
    BodyMeasurementSerializer,
    BonoSerializer,
    ClientListItemSerializer,
    ClientProfileSerializer,
    DeviceTokenSerializer,
    EnduranceTestSerializer,
    MarkSessionSerializer,
    PlanSerializer,
    StrengthPRSerializer,
    TrainerPlanSerializer,
    UserSerializer,
)


class LoginView(APIView):
    """Login por email+contraseña -> par de tokens JWT (access/refresh)."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'

    def post(self, request):
        email = (request.data.get('email') or '').strip()
        password = request.data.get('password') or ''
        if not email or not password:
            return Response(
                {'detail': 'Email y contraseña son obligatorios.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = authenticate(request, username=email, password=password)
        if user is None or not user.is_active:
            return Response(
                {'detail': 'Credenciales inválidas.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        })


class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class MyClientProfileView(ClientProfileMixin, generics.RetrieveAPIView):
    serializer_class = ClientProfileSerializer

    def get_object(self):
        return self.get_client_profile()


class BonoListView(ClientProfileMixin, generics.ListAPIView):
    serializer_class = BonoSerializer

    def get_queryset(self):
        return (
            Bono.objects.filter(client=self.get_client_profile())
            .prefetch_related('sessions')
        )


class BodyMeasurementListView(ClientProfileMixin, generics.ListAPIView):
    serializer_class = BodyMeasurementSerializer

    def get_queryset(self):
        return BodyMeasurement.objects.filter(client=self.get_client_profile())


class StrengthPRListView(ClientProfileMixin, generics.ListAPIView):
    serializer_class = StrengthPRSerializer

    def get_queryset(self):
        return (
            StrengthPR.objects.filter(client=self.get_client_profile())
            .select_related('exercise')
        )


class EnduranceTestListView(ClientProfileMixin, generics.ListAPIView):
    serializer_class = EnduranceTestSerializer

    def get_queryset(self):
        return (
            EnduranceTest.objects.filter(client=self.get_client_profile())
            .select_related('test_type')
        )


class PlanListView(ClientProfileMixin, generics.ListAPIView):
    serializer_class = PlanSerializer

    def get_queryset(self):
        return Plan.objects.filter(client=self.get_client_profile(), archived=False)


class DeviceTokenRegisterView(generics.CreateAPIView):
    serializer_class = DeviceTokenSerializer


# -- Entrenador ---------------------------------------------------------------

class TrainerClientListView(generics.ListAPIView):
    permission_classes = [IsTrainer]
    serializer_class = ClientListItemSerializer
    queryset = ClientProfile.objects.select_related('user').all()


class TrainerClientDetailView(TrainerClientMixin, generics.RetrieveAPIView):
    permission_classes = [IsTrainer]
    serializer_class = ClientProfileSerializer

    def get_object(self):
        return self.get_client()


class TrainerBonoListView(TrainerClientMixin, generics.ListAPIView):
    permission_classes = [IsTrainer]
    serializer_class = BonoSerializer

    def get_queryset(self):
        return Bono.objects.filter(client=self.get_client()).prefetch_related('sessions')


class TrainerBodyMeasurementListView(TrainerClientMixin, generics.ListAPIView):
    permission_classes = [IsTrainer]
    serializer_class = BodyMeasurementSerializer

    def get_queryset(self):
        return BodyMeasurement.objects.filter(client=self.get_client())


class TrainerStrengthPRListView(TrainerClientMixin, generics.ListAPIView):
    permission_classes = [IsTrainer]
    serializer_class = StrengthPRSerializer

    def get_queryset(self):
        return StrengthPR.objects.filter(client=self.get_client()).select_related('exercise')


class TrainerEnduranceTestListView(TrainerClientMixin, generics.ListAPIView):
    permission_classes = [IsTrainer]
    serializer_class = EnduranceTestSerializer

    def get_queryset(self):
        return EnduranceTest.objects.filter(client=self.get_client()).select_related('test_type')


class TrainerMarkSessionView(TrainerClientMixin, APIView):
    """Registra una sesión de hoy en el bono activo del cliente (2 taps desde la app)."""

    permission_classes = [IsTrainer]

    def post(self, request, client_pk):
        client = self.get_client()
        serializer = MarkSessionSerializer(data=request.data, context={'client': client})
        serializer.is_valid(raise_exception=True)
        session = serializer.save()
        bono = session.bono
        return Response({
            'sessions_left': bono.sessions_left,
            'bono_status': bono.status,
        }, status=status.HTTP_201_CREATED)


class TrainerPlanListCreateView(TrainerClientMixin, generics.ListCreateAPIView):
    permission_classes = [IsTrainer]
    serializer_class = TrainerPlanSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return Plan.objects.filter(client=self.get_client())

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['client'] = self.get_client()
        return context
