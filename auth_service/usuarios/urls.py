from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='refresh'),
    path('registrar/', views.RegistroView.as_view(), name='registrar'),
    path('perfil/', views.PerfilView.as_view(), name='perfil'),
    path('usuarios/', views.UsuarioListView.as_view(), name='usuarios'),
    path('saude/', views.saude, name='saude'),
]
