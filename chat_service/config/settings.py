"""
Configurações do Serviço de Mensagens/Chat.

- API REST (DRF): conversas privadas (1:1), grupos (1:N) e histórico de mensagens.
- WebSocket (Django Channels): entrega das mensagens em tempo real.
- Channel layer no Redis: permite que várias réplicas deste serviço troquem eventos,
  de modo que um usuário conectado à réplica A receba mensagens enviadas pela réplica B.

Este serviço não tem tabela de usuários: valida o JWT emitido pelo Serviço de
Autenticação com a chave compartilhada (JWT_SIGNING_KEY) e lê user_id/username do token.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR.parent / '.env')

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-chat-troque-esta-chave')
DEBUG = os.getenv('DJANGO_DEBUG', 'True') == 'True'
ALLOWED_HOSTS = [h.strip() for h in os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()]

INSTALLED_APPS = [
    'daphne',
    'django.contrib.auth',  # exigido pelo simplejwt; usuários ficam no Serviço de Autenticação
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'channels',
    'chat',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'chat.middleware.IdentificaReplicaMiddleware',
]

CORS_ALLOW_ALL_ORIGINS = True

ROOT_URLCONF = 'config.urls'

TEMPLATES = []

ASGI_APPLICATION = 'config.asgi.application'

if os.getenv('DB_HOST'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('CHAT_DB_NAME', 'chat_db'),
            'USER': os.getenv('DB_USER', 'chat'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST'),
            'PORT': os.getenv('DB_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Com Redis, as réplicas compartilham os grupos do Channels. Sem Redis (desenvolvimento local
# com uma única instância), usa a camada em memória.
REDIS_URL = os.getenv('REDIS_URL')
if REDIS_URL:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {'hosts': [REDIS_URL]},
        }
    }
else:
    CHANNEL_LAYERS = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}

REST_FRAMEWORK = {
    # Stateless: monta um TokenUser a partir das claims, sem consultar banco de usuários
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTStatelessUserAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'UNAUTHENTICATED_USER': None,
}

SIMPLE_JWT = {
    'SIGNING_KEY': os.getenv('JWT_SIGNING_KEY', 'jwt-chave-de-desenvolvimento-troque'),
}

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
