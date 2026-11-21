from channels.testing import WebsocketCommunicator
from django.test import TransactionTestCase, override_settings
from rest_framework.test import APIClient, APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from config.asgi import application

from . import servico
from .models import Conversa, Mensagem

CAMADA_MEMORIA = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}


def token_para(uid, username):
    """Simula um access token emitido pelo Serviço de Autenticação (mesma chave)."""
    token = AccessToken()
    token['user_id'] = str(uid)
    token['username'] = username
    return str(token)


def cliente(uid, username):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f'Bearer {token_para(uid, username)}')
    return c


ANA = {'id': 1, 'username': 'ana'}
BRUNO = {'id': 2, 'username': 'bruno'}
CARLA = {'id': 3, 'username': 'carla'}


@override_settings(CHANNEL_LAYERS=CAMADA_MEMORIA)
class ServicoTests(APITestCase):
    def test_conversa_privada_e_reaproveitada(self):
        c1, criada1 = servico.criar_conversa(ANA, Conversa.PRIVADA, [BRUNO])
        c2, criada2 = servico.criar_conversa(BRUNO, Conversa.PRIVADA, [ANA])
        self.assertTrue(criada1)
        self.assertFalse(criada2)
        self.assertEqual(c1.pk, c2.pk)

    def test_grupo_exige_nome(self):
        with self.assertRaises(servico.ErroChat):
            servico.criar_conversa(ANA, Conversa.GRUPO, [BRUNO, CARLA], nome='  ')

    def test_mensagem_persistida(self):
        conversa, _ = servico.criar_conversa(ANA, Conversa.GRUPO, [BRUNO, CARLA], nome='SD')
        mensagem, destinatarios = servico.salvar_mensagem(conversa.pk, ANA, '  olá  ')
        self.assertEqual(Mensagem.objects.get(pk=mensagem.pk).conteudo, 'olá')
        self.assertCountEqual(destinatarios, [1, 2, 3])

    def test_nao_participante_nao_envia(self):
        conversa, _ = servico.criar_conversa(ANA, Conversa.PRIVADA, [BRUNO])
        with self.assertRaises(servico.ErroChat):
            servico.salvar_mensagem(conversa.pk, CARLA, 'intrusa')


@override_settings(CHANNEL_LAYERS=CAMADA_MEMORIA)
class ApiTests(APITestCase):
    def test_sem_token_e_rejeitado(self):
        self.assertEqual(APIClient().get('/api/chat/conversas/').status_code, 401)

    def test_fluxo_criar_grupo_enviar_e_ler_historico(self):
        ana = cliente(1, 'ana')
        r = ana.post('/api/chat/conversas/', {
            'tipo': 'GRUPO', 'nome': 'Turma SD',
            'participantes': [{'id': 2, 'username': 'bruno'}, {'id': 3, 'username': 'carla'}],
        }, format='json')
        self.assertEqual(r.status_code, 201)
        conversa_id = r.data['id']

        r = ana.post(f'/api/chat/conversas/{conversa_id}/mensagens/', {'conteudo': 'Oi, turma'}, format='json')
        self.assertEqual(r.status_code, 201)

        r = cliente(3, 'carla').get(f'/api/chat/conversas/{conversa_id}/mensagens/')
        self.assertEqual([m['conteudo'] for m in r.data], ['Oi, turma'])

        r = cliente(4, 'davi').get(f'/api/chat/conversas/{conversa_id}/mensagens/')
        self.assertEqual(r.status_code, 404)


@override_settings(CHANNEL_LAYERS=CAMADA_MEMORIA)
class WebSocketTests(TransactionTestCase):
    async def test_token_invalido_fecha_conexao(self):
        ws = WebsocketCommunicator(application, '/ws/chat/?token=invalido')
        conectado, _ = await ws.connect()
        self.assertFalse(conectado)

    async def test_mensagem_entregue_em_tempo_real(self):
        from channels.db import database_sync_to_async
        conversa, _ = await database_sync_to_async(servico.criar_conversa)(ANA, Conversa.PRIVADA, [BRUNO])

        ws_ana = WebsocketCommunicator(application, f'/ws/chat/?token={token_para(1, "ana")}')
        ws_bruno = WebsocketCommunicator(application, f'/ws/chat/?token={token_para(2, "bruno")}')
        self.assertTrue((await ws_ana.connect())[0])
        self.assertTrue((await ws_bruno.connect())[0])
        self.assertEqual((await ws_ana.receive_json_from())['tipo'], 'conectado')
        self.assertEqual((await ws_bruno.receive_json_from())['tipo'], 'conectado')

        await ws_ana.send_json_to({'tipo': 'mensagem', 'conversa_id': conversa.pk, 'conteudo': 'oi', 'temp_id': 't1'})

        recebido = await ws_bruno.receive_json_from(timeout=2)
        self.assertEqual(recebido['tipo'], 'mensagem')
        self.assertEqual(recebido['mensagem']['conteudo'], 'oi')
        confirmacao = await ws_ana.receive_json_from(timeout=2)
        self.assertEqual(confirmacao['temp_id'], 't1')

        await ws_ana.disconnect()
        await ws_bruno.disconnect()
