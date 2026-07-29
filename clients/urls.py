from django.urls import path

from . import views

app_name = 'clients'

urlpatterns = [
    path('', views.client_list, name='list'),
    path('nuevo/', views.client_create, name='create'),
    path('<uuid:pk>/', views.client_detail, name='detail'),
    path('<uuid:pk>/editar/', views.client_edit, name='edit'),
    path('<uuid:pk>/invitacion/', views.client_invite_link, name='invite_link'),
]
