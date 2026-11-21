from django.contrib.auth.models import User
from rest_framework import generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .middleware import NOME_REPLICA
from .serializers import LoginSerializer, RegistroSerializer, UsuarioSerializer


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


class RegistroView(generics.CreateAPIView):
    """POST /api/auth/registrar/ — cadastro aberto de novos usuários."""
    serializer_class = RegistroSerializer
    permission_classes = [AllowAny]


class PerfilView(generics.RetrieveUpdateAPIView):
    """GET/PATCH /api/auth/perfil/ — dados do próprio usuário logado."""
    serializer_class = UsuarioSerializer

    def get_object(self):
        return self.request.user


class UsuarioListView(generics.ListAPIView):
    """GET /api/auth/usuarios/?busca=ana — usuários para iniciar conversas e montar grupos."""
    serializer_class = UsuarioSerializer

    def get_queryset(self):
        qs = User.objects.filter(is_active=True).exclude(id=self.request.user.id).order_by('username')
        busca = self.request.query_params.get('busca')
        if busca:
            qs = qs.filter(username__icontains=busca)
        return qs[:50]


@api_view(['GET'])
@permission_classes([AllowAny])
def saude(request):
    """Health check usado pelo Docker/Nginx."""
    return Response({'servico': 'auth', 'replica': NOME_REPLICA, 'status': 'ok'})
