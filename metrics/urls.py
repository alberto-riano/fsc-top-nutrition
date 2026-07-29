from django.urls import path

from . import views

app_name = 'metrics'

urlpatterns = [
    path('cliente/<uuid:client_pk>/composicion/nueva/', views.body_create, name='body_create'),
    path('composicion/<uuid:pk>/borrar/', views.body_delete, name='body_delete'),
    path('cliente/<uuid:client_pk>/fuerza/nueva/', views.pr_create, name='pr_create'),
    path('fuerza/<uuid:pk>/borrar/', views.pr_delete, name='pr_delete'),
    path('cliente/<uuid:client_pk>/test/nuevo/', views.test_create, name='test_create'),
    path('test/<uuid:pk>/borrar/', views.test_delete, name='test_delete'),
]
