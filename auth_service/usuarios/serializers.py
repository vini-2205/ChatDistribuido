from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


def nome_exibicao(user):
    return user.get_full_name() or user.username


class UsuarioSerializer(serializers.ModelSerializer):
    nome = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'nome', 'first_name', 'last_name', 'email']
        read_only_fields = ['id', 'username']

    def get_nome(self, obj):
        return nome_exibicao(obj)


class RegistroSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'password', 'first_name', 'last_name', 'email']

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(TokenObtainPairSerializer):
    """Login: além dos tokens, devolve os dados básicos do usuário."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Claims lidos pelo Serviço de Chat (que não acessa o banco de usuários)
        token['username'] = user.username
        token['nome'] = nome_exibicao(user)
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['id'] = self.user.id
        data['username'] = self.user.username
        data['nome'] = nome_exibicao(self.user)
        return data
