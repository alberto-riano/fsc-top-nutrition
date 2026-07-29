from django.urls import path

from . import views

app_name = 'bonos'

urlpatterns = [
    path('cliente/<uuid:client_pk>/nuevo/', views.bono_create, name='create'),
    path('<uuid:pk>/editar/', views.bono_edit, name='edit'),
    path('<uuid:pk>/archivar/', views.bono_archive, name='archive'),
    path('<uuid:pk>/borrar/', views.bono_delete, name='delete'),
    # Sesiones
    path('cliente/<uuid:client_pk>/sesion-hoy/', views.mark_session_today, name='mark_today'),
    path('cliente/<uuid:client_pk>/sesion/nueva/', views.session_create, name='session_create'),
    path('sesion/<uuid:pk>/borrar/', views.session_delete, name='session_delete'),
]
