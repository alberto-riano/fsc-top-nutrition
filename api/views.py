from django.contrib.auth import authenticate
from django.db.models import Count
from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from bonos.models import Bono
from clients.models import ClientProfile
from metrics.models import BodyMeasurement, CircumferenceMeasurement, EnduranceTest, StrengthPR
from plans.models import Plan, Product

from .permissions import ClientProfileMixin, IsTrainer, TrainerClientMixin
from .serializers import (
    BodyMeasurementSerializer,
    BonoSerializer,
    CircumferenceMeasurementSerializer,
    ClientListItemSerializer,
    ClientProfileSerializer,
    DeviceTokenSerializer,
    EnduranceTestSerializer,
    MarkSessionSerializer,
    PlanSerializer,
    ProductSerializer,
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


class CircumferenceListView(ClientProfileMixin, generics.ListAPIView):
    serializer_class = CircumferenceMeasurementSerializer

    def get_queryset(self):
        return CircumferenceMeasurement.objects.filter(client=self.get_client_profile())


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
        return (
            Plan.objects.filter(client=self.get_client_profile(), archived=False)
            .prefetch_related('plan_products__product')
        )


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


class TrainerBodyMeasurementListView(TrainerClientMixin, generics.ListCreateAPIView):
    permission_classes = [IsTrainer]
    serializer_class = BodyMeasurementSerializer

    def get_queryset(self):
        return BodyMeasurement.objects.filter(client=self.get_client())

    def perform_create(self, serializer):
        serializer.save(client=self.get_client())


class TrainerCircumferenceListCreateView(TrainerClientMixin, generics.ListCreateAPIView):
    permission_classes = [IsTrainer]
    serializer_class = CircumferenceMeasurementSerializer

    def get_queryset(self):
        return CircumferenceMeasurement.objects.filter(client=self.get_client())

    def perform_create(self, serializer):
        serializer.save(client=self.get_client())


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
        return Plan.objects.filter(client=self.get_client()).prefetch_related('plan_products__product')

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['client'] = self.get_client()
        return context


class TrainerProductListCreateView(generics.ListCreateAPIView):
    """Catálogo de productos. `?all=1` incluye los archivados."""

    permission_classes = [IsTrainer]
    serializer_class = ProductSerializer
    pagination_class = None

    def get_queryset(self):
        qs = Product.objects.annotate(plans_count=Count('plan_products'))
        if self.request.query_params.get('all') != '1':
            qs = qs.filter(active=True)
        return qs


class TrainerProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Editar o quitar un producto. Si ya está en algún plan no se borra: se
    archiva, para que los clientes que lo tienen lo sigan viendo.
    """

    permission_classes = [IsTrainer]
    serializer_class = ProductSerializer
    queryset = Product.objects.annotate(plans_count=Count('plan_products'))

    def destroy(self, request, *args, **kwargs):
        product = self.get_object()
        if product.plan_products.exists():
            product.active = False
            product.save(update_fields=['active', 'updated_at'])
            return Response({'archived': True}, status=status.HTTP_200_OK)
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
