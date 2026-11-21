# Chat Distribuído — Trabalho Final de Sistemas Distribuídos

Plataforma de mensagens em tempo real com conversas privadas (1:1) e grupos (1:N), construída como microsserviços replicados atrás de um balanceador de carga.

| Parte | Tecnologia | Pasta |
|---|---|---|
| Serviço de Autenticação/Usuário | Python, Django 4.2, Django REST Framework, JWT (SimpleJWT), Gunicorn | `auth_service/` |
| Serviço de Mensagens/Chat | Django 4.2, DRF, Django Channels (WebSocket), Daphne | `chat_service/` |
| Frontend | React 19 (Create React App) | `frontend/` |
| Banco de dados | PostgreSQL 16 (um banco por serviço: `auth_db` e `chat_db`) | — |
| Mensageria entre réplicas | Redis 7 (channel layer do Channels) | — |
| Balanceador de carga | Nginx | `deploy/nginx.conf` |

---

## Arquitetura

```
                    ┌──────────────────────────── Nginx (web) :8080 ────────────────────────────┐
 Navegador ───────► │  /            → React compilado                                           │
 (HTTP + WebSocket) │  /api/auth/*  → auth  (round-robin)                                       │
                    │  /api/chat/*  → chat  (least_conn)                                        │
                    │  /ws/chat/    → chat  (WebSocket, least_conn)                             │
                    └───────────────┬───────────────────────────────┬───────────────────────────┘
                                    │                               │
                         ┌──────────▼──────────┐         ┌──────────▼──────────┐
                         │ auth-1 … auth-N     │         │ chat-1 … chat-N     │◄──► Redis (pub/sub
                         │ (Gunicorn, WSGI)    │         │ (Daphne, ASGI)      │     entre réplicas)
                         └──────────┬──────────┘         └──────────┬──────────┘
                                    │                               │
                                    └──────────► PostgreSQL ◄───────┘
                                              auth_db     chat_db
```

**Como os serviços se comunicam**

- O Serviço de Autenticação emite o JWT (com as claims `user_id` e `username`) assinado com `JWT_SIGNING_KEY`.
- O Serviço de Chat valida o mesmo JWT com a mesma chave, **sem chamar o serviço de autenticação** a cada requisição (autenticação stateless). Por isso o chat continua funcionando mesmo se o serviço de autenticação estiver fora do ar, para quem já está logado.
- Cada conexão WebSocket entra no grupo `usuario_<id>`. Ao receber uma mensagem, a réplica salva no banco e publica no Redis para o grupo de cada participante; a réplica onde o destinatário está conectado a entrega. Assim, usuários em réplicas diferentes conversam normalmente.
- Se uma réplica de chat cair, o frontend reconecta (backoff exponencial), o Nginx direciona para outra réplica e o histórico é recarregado pela API REST.

---

## Instalação rápida (Docker — sistema completo e distribuído)

```bash
cp .env.example .env        # troque DJANGO_SECRET_KEY, JWT_SIGNING_KEY e DB_PASSWORD
docker compose up -d --build
```

Acesse **http://localhost:8080**, clique em **Cadastre-se** e crie dois ou mais usuários (use janelas anônimas para logar com usuários diferentes ao mesmo tempo).

Por padrão sobem 2 réplicas de cada serviço (`AUTH_REPLICAS` e `CHAT_REPLICAS` no `.env`). Para escalar em tempo de execução:

```bash
docker compose up -d --scale chat=4 --no-recreate
docker compose restart web   # o Nginx recarrega a lista de réplicas
```

### Verificando o balanceamento

Os endpoints de saúde informam qual réplica respondeu:

```bash
for i in $(seq 1 10); do curl -s localhost:8080/api/chat/saude/; echo; done
```

Toda resposta da API também traz os cabeçalhos `X-Servidor` (hostname da réplica) e `X-Upstream` (IP escolhido pelo Nginx). No frontend, passe o mouse sobre o indicador **Online** para ver em qual réplica o seu WebSocket está.

### Simulando falha de uma réplica

```bash
docker compose stop chat --timeout 0   # derruba todas, ou:
docker stop trabalhofinal-chat-1       # derruba só uma
```

Os usuários conectados à réplica derrubada reconectam automaticamente em outra.

---

## Desenvolvimento local (sem Docker)

Sem `DB_HOST` e `REDIS_URL` no `.env`, cada serviço usa SQLite e o channel layer em memória (uma instância de cada serviço).

```bash
cp .env.example .env

# Backend (um venv para os dois serviços)
python3 -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -r auth_service/requirements.txt -r chat_service/requirements.txt

cd auth_service && python manage.py migrate && python manage.py runserver 8001   # terminal 1
cd chat_service && python manage.py migrate && python manage.py runserver 8002   # terminal 2

# Frontend (terminal 3)
cd frontend
npm install
npm start                               # http://localhost:3000
```

O `frontend/src/setupProxy.js` encaminha `/api/auth` → 8001 e `/api/chat` e `/ws/chat` → 8002, fazendo o papel do Nginx.

---

## API

### Serviço de Autenticação (`/api/auth/`)

| Método | Rota | Descrição |
|---|---|---|
| POST | `/api/auth/registrar/` | Cadastro (`username`, `password`, `first_name`, `email`) |
| POST | `/api/auth/login/` | Login: retorna `access`, `refresh`, `id`, `username`, `nome` |
| POST | `/api/auth/refresh/` | Renova o access token |
| GET/PATCH | `/api/auth/perfil/` | Dados do usuário logado |
| GET | `/api/auth/usuarios/?busca=` | Lista usuários (para iniciar conversas/grupos) |
| GET | `/api/auth/saude/` | Health check (mostra a réplica) |

### Serviço de Chat (`/api/chat/` e `/ws/chat/`)

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/chat/conversas/` | Conversas do usuário, com a última mensagem |
| POST | `/api/chat/conversas/` | Cria conversa: `{"tipo": "PRIVADA"\|"GRUPO", "nome": "...", "participantes": [{"id": 2, "username": "bruno"}]}` |
| GET | `/api/chat/conversas/<id>/mensagens/?antes=<id>` | Histórico (50 por página) |
| POST | `/api/chat/conversas/<id>/mensagens/` | Envia mensagem por HTTP (alternativa ao WebSocket) |
| GET | `/api/chat/saude/` | Health check |
| WS | `/ws/chat/?token=<access>` | Canal em tempo real |

Eventos do WebSocket (JSON):

```jsonc
// cliente → servidor
{"tipo": "mensagem", "conversa_id": 1, "conteudo": "oi", "temp_id": "abc"}
// servidor → cliente
{"tipo": "conectado", "replica": "a1b2c3"}
{"tipo": "mensagem", "mensagem": {"id": 10, "conversa_id": 1, "remetente_id": 1, "remetente_username": "ana", "conteudo": "oi", "enviada_em": "..."}, "temp_id": "abc"}
{"tipo": "nova_conversa", "conversa": {...}}
{"tipo": "erro", "detalhe": "...", "temp_id": "abc"}
```

---

## Testes

```bash
cd auth_service && python manage.py test     # login válido/inválido, claims do JWT, cadastro, perfil
cd chat_service && python manage.py test     # persistência, regras de conversa, API, entrega via WebSocket
cd frontend && CI=true npm test
```

**Pendente (plano de testes do enunciado):** teste de carga com 100 usuários simultâneos e 20 grupos, comparando 1 réplica × N réplicas, e testes de integração contra o ambiente Docker.

---

## Estrutura

```
auth_service/          Serviço de Autenticação/Usuário
  config/              settings, urls, wsgi
  usuarios/            views, serializers, testes
chat_service/          Serviço de Mensagens/Chat
  config/              settings, urls, asgi (HTTP + WebSocket)
  chat/                models, servico (regras), views, consumers (WebSocket), auth (JWT no WS), testes
frontend/              React
  src/services/        api.js (axios + renovação de token), chatSocket.js (WebSocket com reconexão)
  src/context/         AuthContext
  src/pages/           Login (login + cadastro), Chat (lista de conversas + mensagens)
  src/components/      PrivateRoute, NovaConversaModal
deploy/                Dockerfiles, nginx.conf, init-db.sql
docker-compose.yml     PostgreSQL, Redis, réplicas dos serviços e Nginx
```
