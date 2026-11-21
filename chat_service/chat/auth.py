"""
Autenticação do WebSocket: o navegador não envia cabeçalho Authorization no handshake,
então o JWT vai na query string (ws/chat/?token=<access>).
"""
from urllib.parse import parse_qs

from channels.middleware import BaseMiddleware
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken


def usuario_do_token(token):
    try:
        claims = AccessToken(token)
    except TokenError:
        return None
    return {'id': int(claims['user_id']), 'username': claims.get('username', '')}


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        params = parse_qs(scope.get('query_string', b'').decode())
        token = (params.get('token') or [None])[0]
        scope['usuario'] = usuario_do_token(token) if token else None
        return await super().__call__(scope, receive, send)
