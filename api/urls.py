from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

app_name = 'api'

urlpatterns = [
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    path('me/', views.MeView.as_view(), name='me'),
    path('me/profile/', views.MyClientProfileView.as_view(), name='my-profile'),

    path('bonos/', views.BonoListView.as_view(), name='bonos'),
    path('metrics/body/', views.BodyMeasurementListView.as_view(), name='body-measurements'),
    path('metrics/circumference/', views.CircumferenceListView.as_view(), name='circumference'),
    path('metrics/strength/', views.StrengthPRListView.as_view(), name='strength-prs'),
    path('metrics/endurance/', views.EnduranceTestListView.as_view(), name='endurance-tests'),
    path('plans/', views.PlanListView.as_view(), name='plans'),

    path('devices/register/', views.DeviceTokenRegisterView.as_view(), name='device-register'),

    # Entrenador
    path('trainer/clients/', views.TrainerClientListView.as_view(), name='trainer-clients'),
    path('trainer/clients/<uuid:client_pk>/', views.TrainerClientDetailView.as_view(), name='trainer-client-detail'),
    path('trainer/clients/<uuid:client_pk>/invite/', views.TrainerClientInviteView.as_view(), name='trainer-client-invite'),
    path('trainer/usernames/check/', views.TrainerUsernameCheckView.as_view(), name='trainer-username-check'),
    path('trainer/catalog/', views.TrainerCatalogView.as_view(), name='trainer-catalog'),
    path('trainer/clients/<uuid:client_pk>/bonos/', views.TrainerBonoListView.as_view(), name='trainer-bonos'),
    path('trainer/clients/<uuid:client_pk>/sessions/mark/', views.TrainerMarkSessionView.as_view(), name='trainer-mark-session'),
    path('trainer/clients/<uuid:client_pk>/metrics/body/', views.TrainerBodyMeasurementListView.as_view(), name='trainer-body-measurements'),
    path('trainer/clients/<uuid:client_pk>/metrics/circumference/', views.TrainerCircumferenceListCreateView.as_view(), name='trainer-circumference'),
    path('trainer/clients/<uuid:client_pk>/metrics/strength/', views.TrainerStrengthPRListView.as_view(), name='trainer-strength-prs'),
    path('trainer/clients/<uuid:client_pk>/metrics/endurance/', views.TrainerEnduranceTestListView.as_view(), name='trainer-endurance-tests'),
    path('trainer/products/', views.TrainerProductListCreateView.as_view(), name='trainer-products'),
    path('trainer/products/<uuid:pk>/', views.TrainerProductDetailView.as_view(), name='trainer-product-detail'),
    path('trainer/clients/<uuid:client_pk>/plans/', views.TrainerPlanListCreateView.as_view(), name='trainer-plans'),
]
