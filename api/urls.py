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
    path('metrics/strength/', views.StrengthPRListView.as_view(), name='strength-prs'),
    path('metrics/endurance/', views.EnduranceTestListView.as_view(), name='endurance-tests'),
    path('plans/', views.PlanListView.as_view(), name='plans'),

    path('devices/register/', views.DeviceTokenRegisterView.as_view(), name='device-register'),

    # Entrenador
    path('trainer/clients/', views.TrainerClientListView.as_view(), name='trainer-clients'),
    path('trainer/clients/<uuid:client_pk>/', views.TrainerClientDetailView.as_view(), name='trainer-client-detail'),
    path('trainer/clients/<uuid:client_pk>/bonos/', views.TrainerBonoListView.as_view(), name='trainer-bonos'),
    path('trainer/clients/<uuid:client_pk>/sessions/mark/', views.TrainerMarkSessionView.as_view(), name='trainer-mark-session'),
    path('trainer/clients/<uuid:client_pk>/metrics/body/', views.TrainerBodyMeasurementListView.as_view(), name='trainer-body-measurements'),
    path('trainer/clients/<uuid:client_pk>/metrics/strength/', views.TrainerStrengthPRListView.as_view(), name='trainer-strength-prs'),
    path('trainer/clients/<uuid:client_pk>/metrics/endurance/', views.TrainerEnduranceTestListView.as_view(), name='trainer-endurance-tests'),
    path('trainer/clients/<uuid:client_pk>/plans/', views.TrainerPlanListCreateView.as_view(), name='trainer-plans'),
]
