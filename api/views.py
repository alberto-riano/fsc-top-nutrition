from django.contrib.auth import authenticate
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from bonos.models import Bono
from metrics.models import BodyMeasurement, EnduranceTest, StrengthPR
from plans.models import Plan

from .permissions import ClientProfileMixin
from .serializers import (
    BodyMeasurementSerializer,
    BonoSerializer,
    ClientProfileSerializer,
    DeviceTokenSerializer,
    EnduranceTestSerializer,
    PlanSerializer,
    StrengthPRSerializer,
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
