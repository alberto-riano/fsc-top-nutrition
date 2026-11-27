from django.contrib.auth import authenticate
from django.db.models import Count
from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.deletion import delete_account, is_last_trainer
from bonos.models import Bono
from clients.models import ClientProfile
from clients.services import build_invite, suggest_username
from metrics.models import (
    BodyMeasurement, CircumferenceMeasurement, EnduranceTest, EnduranceTestType, Exercise, StrengthPR,
)
from plans.models import Plan, Product

from .permissions import ClientProfileMixin, IsTrainer, TrainerClientMixin
from .serializers import (
    BodyMeasurementSerializer,
    BonoSerializer,
    CircumferenceMeasurementSerializer,
    ClientListItemSerializer,
    ClientProfileSerializer,
    ClientSexSerializer,
    DeviceTokenSerializer,
    EnduranceTestSerializer,
    EnduranceTestTypeSerializer,
    ExerciseSerializer,
    TrainerBonoReadSerializer,
    TrainerBonoSerializer,
    TrainerClientCreateSerializer,
    TrainerEnduranceTestCreateSerializer,
    TrainerStrengthPRCreateSerializer,
    one_rep_max,
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


class AccountDeleteView(APIView):
    """
    Eliminar la propia cuenta desde la app (requisito de Apple).

    GET dice qué se pierde (o por qué no se puede) antes de pedir nada; POST
    con la contraseña la borra para siempre junto con todos sus datos.
    """

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'
    LAST_TRAINER = ('Eres el único entrenador del centro: si eliminas tu cuenta, nadie podrá '
                    'gestionar a los clientes. Da de alta a otro entrenador antes desde el panel web.')

    def get(self, request):
        user = request.user
        profile = getattr(user, 'client_profile', None)
        blocked = is_last_trainer(user)
        return Response({
            'can_delete': not blocked,
            'reason': self.LAST_TRAINER if blocked else '',
            'sessions_left': profile.sessions_left if profile else 0,
        })

    def post(self, request):
        user = request.user
        if not user.check_password(request.data.get('password') or ''):
            return Response({'password': ['La contraseña no es correcta.']}, status=status.HTTP_400_BAD_REQUEST)
        if is_last_trainer(user):
            return Response({'detail': self.LAST_TRAINER}, status=status.HTTP_400_BAD_REQUEST)
        delete_account(user)
        return Response(status=status.HTTP_204_NO_CONTENT)


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

class TrainerClientListView(generics.ListCreateAPIView):
    """Clientes del entrenador. POST da de alta uno y devuelve su invitación."""

    permission_classes = [IsTrainer]
    serializer_class = ClientListItemSerializer
    queryset = ClientProfile.objects.select_related('user').prefetch_related('bonos__sessions')

    def get_serializer_class(self):
        return TrainerClientCreateSerializer if self.request.method == 'POST' else ClientListItemSerializer

    def create(self, request, *args, **kwargs):
        serializer = TrainerClientCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        data = ClientProfileSerializer(profile, context={'request': request}).data
        data['invite'] = None if profile.user.has_usable_password() else build_invite(request, profile.user)
        return Response(data, status=status.HTTP_201_CREATED)


class TrainerClientDetailView(TrainerClientMixin, generics.RetrieveUpdateAPIView):
    """Ficha del cliente. PATCH solo admite `sex` (la silueta del mapa corporal)."""

    permission_classes = [IsTrainer]
    serializer_class = ClientProfileSerializer
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_serializer_class(self):
        return ClientSexSerializer if self.request.method == 'PATCH' else ClientProfileSerializer

    def update(self, request, *args, **kwargs):
        super().update(request, *args, **kwargs)
        return Response(ClientProfileSerializer(self.get_object(), context=self.get_serializer_context()).data)

    def get_object(self):
        return self.get_client()


class TrainerBonoListView(TrainerClientMixin, generics.ListCreateAPIView):
    permission_classes = [IsTrainer]
    serializer_class = TrainerBonoReadSerializer

    def get_queryset(self):
        return Bono.objects.filter(client=self.get_client()).prefetch_related('sessions')

    def create(self, request, *args, **kwargs):
        client = self.get_client()
        serializer = TrainerBonoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        bono = serializer.save(client=client)
        return Response({
            'bono': TrainerBonoReadSerializer(bono).data,
            'sessions_left': client.sessions_left,
            'queued_sessions': client.queued_sessions,
        }, status=status.HTTP_201_CREATED)


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


class TrainerStrengthPRListView(TrainerClientMixin, generics.ListCreateAPIView):
    permission_classes = [IsTrainer]
    serializer_class = StrengthPRSerializer

    def get_queryset(self):
        return StrengthPR.objects.filter(client=self.get_client()).select_related('exercise')

    def create(self, request, *args, **kwargs):
        client = self.get_client()
        serializer = TrainerStrengthPRCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pr = serializer.save(client=client)
        previous = StrengthPR.objects.filter(client=client, exercise=pr.exercise).exclude(pk=pr.pk)
        best = max((one_rep_max(p.weight_kg, p.reps) for p in previous), default=None)
        data = StrengthPRSerializer(pr).data
        data['is_first'] = best is None
        data['is_record'] = best is not None and one_rep_max(pr.weight_kg, pr.reps) > best + 0.01
        return Response(data, status=status.HTTP_201_CREATED)


class TrainerEnduranceTestListView(TrainerClientMixin, generics.ListCreateAPIView):
    permission_classes = [IsTrainer]
    serializer_class = EnduranceTestSerializer

    def get_queryset(self):
        return EnduranceTest.objects.filter(client=self.get_client()).select_related('test_type')

    def create(self, request, *args, **kwargs):
        client = self.get_client()
        serializer = TrainerEnduranceTestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        test = serializer.save(client=client)
        values = list(EnduranceTest.objects.filter(client=client, test_type=test.test_type)
                      .exclude(pk=test.pk).values_list('value', flat=True))
        lower = test.test_type.lower_is_better
        best = (min(values) if lower else max(values)) if values else None
        data = EnduranceTestSerializer(test).data
        data['is_first'] = best is None
        data['is_record'] = best is not None and (test.value < best if lower else test.value > best)
        return Response(data, status=status.HTTP_201_CREATED)


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
            'sessions_left': client.sessions_left,
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


class TrainerClientInviteView(TrainerClientMixin, APIView):
    """
    Enlace para que el cliente ponga su contraseña, con el mensaje listo para
    WhatsApp. Sirve para la primera vez y para quien la ha olvidado.
    """

    permission_classes = [IsTrainer]

    def post(self, request, client_pk):
        client = self.get_client()
        data = build_invite(request, client.user)
        data['first_name'] = client.user.first_name
        data['full_name'] = client.full_name
        data['access_pending'] = not client.user.is_active or not client.user.has_usable_password()
        return Response(data)


class TrainerUsernameCheckView(APIView):
    """¿Está libre este usuario? Si no, propone el siguiente libre."""

    permission_classes = [IsTrainer]

    def get(self, request):
        username = (request.query_params.get('username') or '').strip().lower()
        if not username:
            return Response({'available': False, 'suggestion': ''})
        suggestion = suggest_username(username)
        return Response({'available': suggestion == username, 'suggestion': suggestion})


class TrainerCatalogView(APIView):
    """Ejercicios de fuerza y tipos de test, para registrar marcas."""

    permission_classes = [IsTrainer]

    def get(self, request):
        return Response({
            'exercises': ExerciseSerializer(Exercise.objects.all(), many=True).data,
            'test_types': EnduranceTestTypeSerializer(EnduranceTestType.objects.all(), many=True).data,
        })
