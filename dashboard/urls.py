from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    # Portal del cliente (solo lectura de sus propios datos)
    path('mi/progreso/', views.my_progress, name='my_progress'),
    path('mi/bonos/', views.my_bonos, name='my_bonos'),
    path('mi/planes/', views.my_plans, name='my_plans'),
]
