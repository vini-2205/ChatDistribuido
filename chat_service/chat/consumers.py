"""
WebSocket do chat. Cada usuário conectado entra no grupo "usuario_<id>"; as mensagens
são publicadas nos grupos dos participantes da conversa. Com o channel layer no Redis,
isso funciona entre réplicas diferentes do serviço.

Protocolo (JSON):
  cliente → servidor: {"tipo": "mensagem", "conversa_id": 1, "conteudo": "oi", "temp_id": "abc"}
  servidor → cliente: {"tipo": "conectado", "replica": "..."}
                      {"tipo": "mensagem", "mensagem": {...}, "temp_id": "abc"}
                      {"tipo": "nova_conversa", "conversa": {...}}
                      {"tipo": "erro", "detalhe": "...", "temp_id": "abc"}
"""
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from . import servico
from .middleware import NOME_REPLICA


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.usuario = self.scope.get('usuario')
        if not self.usuario:
            await self.close(code=4401)
            return
        self.grupo = servico.grupo_usuario(self.usuario['id'])
        await self.channel_layer.group_add(self.grupo, self.channel_name)
        await self.accept()
        await self.send_json({'tipo': 'conectado', 'replica': NOME_REPLICA})

    async def disconnect(self, code):
        if getattr(self, 'grupo', None):
            await self.channel_layer.group_discard(self.grupo, self.channel_name)

    async def receive_json(self, content, **kwargs):
        if content.get('tipo') != 'mensagem':
            await self.send_json({'tipo': 'erro', 'detalhe': 'Tipo de evento desconhecido.'})
            return
        temp_id = content.get('temp_id')
        try:
            dados, destinatarios = await self._salvar(content.get('conversa_id'), content.get('conteudo'))
        except (servico.ErroChat, TypeError, ValueError) as e:
            await self.send_json({'tipo': 'erro', 'detalhe': str(e), 'temp_id': temp_id})
            return
        # temp_id permite ao remetente trocar a mensagem "enviando..." pela confirmada
        await servico.publicar_async(destinatarios, {'tipo': 'mensagem', 'mensagem': dados, 'temp_id': temp_id})

    @database_sync_to_async
    def _salvar(self, conversa_id, conteudo):
        mensagem, destinatarios = servico.salvar_mensagem(int(conversa_id), self.usuario, conteudo)
        return servico.mensagem_para_dict(mensagem), destinatarios

    async def chat_evento(self, event):
        await self.send_json(event['evento'])
