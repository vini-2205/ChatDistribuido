import jwt
from django.conf import settings
from django.contrib.auth.models import User
from rest_framework.test import APITestCase


class AutenticacaoTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='ana', password='senha123')

    def test_login_valido_retorna_tokens_e_dados(self):
        r = self.client.post('/api/auth/login/', {'username': 'ana', 'password': 'senha123'})
        self.assertEqual(r.status_code, 200)
        self.assertIn('access', r.data)
        self.assertEqual(r.data['username'], 'ana')

    def test_login_senha_errada_e_rejeitado(self):
        r = self.client.post('/api/auth/login/', {'username': 'ana', 'password': 'errada'})
        self.assertEqual(r.status_code, 401)

    def test_token_carrega_username_para_o_servico_de_chat(self):
        r = self.client.post('/api/auth/login/', {'username': 'ana', 'password': 'senha123'})
        claims = jwt.decode(r.data['access'], settings.SIMPLE_JWT['SIGNING_KEY'], algorithms=['HS256'])
        self.assertEqual(claims['user_id'], str(self.user.id))
        self.assertEqual(claims['username'], 'ana')

    def test_registro_cria_usuario(self):
        r = self.client.post('/api/auth/registrar/', {'username': 'bruno', 'password': 'senha123'})
        self.assertEqual(r.status_code, 201)
        self.assertTrue(User.objects.filter(username='bruno').exists())
        self.assertNotIn('password', r.data)

    def test_registro_username_duplicado(self):
        r = self.client.post('/api/auth/registrar/', {'username': 'ana', 'password': 'senha123'})
        self.assertEqual(r.status_code, 400)

    def test_perfil_exige_autenticacao(self):
        self.assertEqual(self.client.get('/api/auth/perfil/').status_code, 401)

    def test_lista_usuarios_exclui_o_proprio(self):
        User.objects.create_user(username='carla', password='senha123')
        self.client.force_authenticate(self.user)
        r = self.client.get('/api/auth/usuarios/')
        self.assertEqual([u['username'] for u in r.data], ['carla'])
