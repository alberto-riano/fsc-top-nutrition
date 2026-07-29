from django.urls import path

from . import views

app_name = 'plans'

urlpatterns = [
    path('cliente/<uuid:client_pk>/nuevo/', views.plan_create, name='create'),
    path('<uuid:pk>/editar/', views.plan_edit, name='edit'),
    path('<uuid:pk>/archivar/', views.plan_archive, name='archive'),
    path('<uuid:pk>/borrar/', views.plan_delete, name='delete'),
    path('<uuid:pk>/descargar/', views.plan_download, name='download'),
]
