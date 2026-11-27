# Chat Distribuído — Trabalho Final de Sistemas Distribuídos

Projeto desenvolvido para a disciplina de Sistemas Distribuídos do CEFET-MG. Consiste em uma aplicação de chat em tempo real, com mensagens privadas e em grupo, organizada em microsserviços replicados, balanceamento de carga e persistência híbrida de dados.

## Funcionalidades

- Cadastro, login e autenticação por JWT.
- Conversas privadas (1:1) e grupos (1:N).
- Envio e recebimento de mensagens via WebSocket.
- Histórico de mensagens persistido no MongoDB.
- Listagem de conversas com a última mensagem.
- Replicação dos serviços de autenticação e chat.
- Distribuição de eventos entre réplicas por meio do Redis.
- Balanceamento de carga com Nginx.
- Reconexão automática do WebSocket e recuperação do histórico.
- Execução conteinerizada com Docker Compose.

## Tecnologias

| Componente | Tecnologia |
|---|---|
| Autenticação | Python, Django 4.2, Django REST Framework, SimpleJWT, Gunicorn |
| Chat | Django 4.2, Django REST Framework, Django Channels, Daphne |
| Frontend | React 19 (Create React App) |
| Banco relacional | PostgreSQL 16 |
| Banco não relacional | MongoDB 7, PyMongo |
| Comunicação entre réplicas | Redis 7 |
| Balanceamento | Nginx |
| Conteinerização | Docker e Docker Compose |

## Arquitetura

```mermaid
flowchart TD
    U[Usuários / Navegador] -->|HTTP e WebSocket| N[Nginx :8080]
    N --> F[Frontend React]
    N -->|Round-robin| A1[Auth 1]
    N -->|Round-robin| A2[Auth 2]
    N -->|Least connections| C1[Chat 1]
    N -->|Least connections| C2[Chat 2]
    A1 --> P[(PostgreSQL)]
    A2 --> P
    C1 --> P
    C2 --> P
    C1 --> M[(MongoDB)]
    C2 --> M
    C1 <--> R[(Redis)]
    C2 <--> R
```

O Nginx encaminha as requisições de autenticação usando round-robin e as conexões do chat usando least connections. Por padrão, são executadas duas réplicas de cada microsserviço.

### Responsabilidades dos serviços

**Serviço de autenticação:** administra os usuários e emite tokens JWT. O serviço de chat verifica a assinatura dos tokens utilizando a mesma chave, sem depender de uma consulta remota ao serviço de autenticação a cada mensagem.

**Serviço de chat:** valida o acesso às conversas, processa mensagens e recupera o histórico. As réplicas compartilham os bancos de dados e utilizam o Redis como channel layer do Django Channels.

**Frontend:** interface para autenticação, gerenciamento de conversas e comunicação em tempo real. Possui mecanismo de reconexão do WebSocket com backoff exponencial.

### Fluxo de uma mensagem

1. O usuário autenticado envia uma mensagem pelo WebSocket ou pela API REST.
2. O Nginx direciona a conexão para uma réplica do chat.
3. A aplicação verifica o token, a participação na conversa e o conteúdo da mensagem.
4. A mensagem é gravada no MongoDB.
5. O serviço publica o evento no Redis para os grupos de canais dos participantes (`usuario_<id>`).
6. As réplicas responsáveis pelas conexões dos destinatários encaminham a mensagem pelo WebSocket.
7. O histórico permanece disponível para consultas posteriores.

### Persistência de dados

| Tecnologia | Responsabilidade |
|---|---|
| PostgreSQL — `auth_db` | Cadastro, credenciais e dados dos usuários |
| PostgreSQL — `chat_db` | Conversas, grupos e participantes |
| MongoDB — `chat_messages` | Conteúdo, remetente, conversa e data de envio das mensagens |
| Redis | Propagação de eventos em tempo real entre as réplicas; não é a fonte persistente do histórico |

A persistência híbrida mantém os relacionamentos estruturados no PostgreSQL e armazena as mensagens em documentos independentes no MongoDB. A coleção `mensagens` utiliza um índice composto por `conversa_id`, `enviada_em` e `_id` para auxiliar as consultas de histórico e paginação.

Exemplo de documento, em representação JSON estendida do BSON:

```json
{
  "_id": {"$oid": "6745af023c189482ac12ff01"},
  "conversa_id": 1,
  "remetente_id": 2,
  "remetente_username": "usuario1",
  "conteudo": "Olá, tudo bem?",
  "enviada_em": {"$date": "2026-11-27T18:00:00Z"}
}
```

A API converte o ObjectId para uma string e a data para ISO 8601. O identificador da conversa continua sendo numérico.

> Compatibilidade: mensagens gravadas no PostgreSQL antes da integração não aparecem automaticamente no MongoDB. A migração desse histórico deve ser realizada separadamente caso seja necessária. O model relacional antigo pode permanecer temporariamente para preservar esses dados.

## Instalação e execução

### Pré-requisitos

- Git.
- Docker com Docker Compose v2.
- No Windows, Docker Desktop com WSL 2 e virtualização habilitada.

Não é necessário instalar Python, Node.js, PostgreSQL, MongoDB ou Redis diretamente na máquina para executar o ambiente Docker.

### 1. Clonar o repositório

```bash
git clone https://github.com/vini-2205/ChatDistribuido.git
cd ChatDistribuido
```

Utilize a branch que contém a integração com MongoDB, caso as alterações ainda não tenham sido incorporadas à branch principal.

### 2. Configurar o ambiente

Windows (PowerShell):

```powershell
Copy-Item .env.example .env
```

Linux/macOS:

```bash
cp .env.example .env
```

Caso já exista um `.env`, preserve suas configurações. Exemplo para desenvolvimento local:

```dotenv
# Django
DJANGO_DEBUG=True
DJANGO_SECRET_KEY=troque-por-uma-chave-propria
JWT_SIGNING_KEY=troque-por-outra-chave-longa

# PostgreSQL
DB_USER=chat
DB_PASSWORD=SenhaLocalExemplo123
DB_PORT_HOST=5433

# MongoDB
MONGO_USER=chat_admin
MONGO_PASSWORD=MongoSenhaExemplo123
MONGO_URL=mongodb://chat_admin:MongoSenhaExemplo123@mongo:27017/?authSource=admin
MONGO_DB_NAME=chat_messages

# Docker
WEB_PORT=8080
AUTH_REPLICAS=2
CHAT_REPLICAS=2
```

Substitua as senhas e chaves de exemplo. A URL do MongoDB deve conter as mesmas credenciais configuradas nas variáveis `MONGO_USER` e `MONGO_PASSWORD`; caracteres reservados na senha precisam ser codificados na URI. A chave JWT deve ser compartilhada pelos dois microsserviços. Não publique o `.env` no GitHub.

| Variável | Finalidade |
|---|---|
| `DJANGO_DEBUG` | Modo de depuração |
| `DJANGO_SECRET_KEY` | Chave de segurança do Django |
| `JWT_SIGNING_KEY` | Assinatura e validação dos tokens |
| `DB_USER`, `DB_PASSWORD` | Credenciais PostgreSQL |
| `DB_PORT_HOST` | Porta PostgreSQL exposta no host |
| `MONGO_USER`, `MONGO_PASSWORD` | Credenciais iniciais do MongoDB |
| `MONGO_URL` | URI utilizada pelo PyMongo |
| `MONGO_DB_NAME` | Banco de mensagens |
| `WEB_PORT` | Porta de acesso ao frontend |
| `AUTH_REPLICAS` | Número de réplicas de autenticação |
| `CHAT_REPLICAS` | Número de réplicas de chat |

### 3. Iniciar os containers

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps -a
```

Os serviços de banco de dados, Redis, autenticação, chat e web devem permanecer ativos. Os containers de migrations podem terminar com `Exited (0)` após concluir sua execução.

### 4. Acessar a aplicação

Abra <http://localhost:8080>. Cadastre dois ou mais usuários e utilize perfis ou sessões independentes do navegador para testar conversas simultâneas.

### Comandos úteis

| Comando | Finalidade |
|---|---|
| `docker compose ps -a` | Inspecionar os containers |
| `docker compose logs -f chat` | Acompanhar os logs do chat |
| `docker compose logs -f auth` | Acompanhar os logs da autenticação |
| `docker compose logs -f mongo` | Acompanhar os logs do MongoDB |
| `docker compose up -d --build` | Reconstruir e iniciar os serviços |
| `docker compose down` | Encerrar o ambiente preservando os volumes |

**Atenção:** `docker compose down -v` remove os volumes e pode apagar os dados persistidos.

## Verificando o MongoDB

Após enviar mensagens pela interface, execute:

```bash
docker compose exec mongo mongosh -u chat_admin --authenticationDatabase admin -p
```

Informe a senha definida no `.env`. No shell do MongoDB:

```javascript
use chat_messages
show collections
db.mensagens.find().pretty()
db.mensagens.countDocuments()
db.mensagens.getIndexes()
```

Para consultar mensagens de uma conversa específica:

```javascript
db.mensagens.find({ conversa_id: 1 }).sort({ enviada_em: 1, _id: 1 })
```

Para validar a persistência, encerre e reinicie os containers sem remover os volumes e consulte novamente o histórico.

## Escalabilidade e balanceamento de carga

O número de instâncias pode ser configurado em `AUTH_REPLICAS` e `CHAT_REPLICAS`. Para aumentar temporariamente o número de réplicas do chat:

```bash
docker compose up -d --scale chat=4 --no-recreate
docker compose restart web
docker compose ps chat
```

O reinício do Nginx permite atualizar a lista de servidores upstream e pode interromper conexões existentes momentaneamente.

### Verificar a distribuição das requisições

PowerShell:

```powershell
1..10 | ForEach-Object {
    curl.exe -s http://localhost:8080/api/chat/saude/
    Write-Host ""
}
```

Linux/macOS:

```bash
for i in $(seq 1 10); do curl -s http://localhost:8080/api/chat/saude/; echo; done
```

Repita com `/api/auth/saude/` para verificar a autenticação. Os cabeçalhos `X-Servidor` e `X-Upstream` ajudam a identificar a instância que processou a requisição. O indicador Online da interface também informa a réplica associada à conexão WebSocket.

## Tolerância a falhas

Com duas ou mais réplicas de chat ativas, mantenha usuários conectados e trocando mensagens. No PowerShell:

```powershell
$replicas = @(docker compose ps -q chat)
if ($replicas.Count -ge 2) { docker stop $replicas[0] }
```

Verifique se a conexão afetada se restabelece em outra instância e se o histórico continua acessível. Para restaurar a instância interrompida:

```powershell
docker start $replicas[0]
```

A arquitetura oferece redundância no nível dos microsserviços. Entretanto, as instâncias únicas de Nginx, PostgreSQL, MongoDB e Redis continuam sendo pontos únicos de falha. A configuração atual não garante disponibilidade diante da falha de qualquer componente, nem entrega exatamente uma vez das mensagens.

## API

### Autenticação

| Método | Endpoint | Finalidade |
|---|---|---|
| POST | `/api/auth/registrar/` | Cadastro de usuário |
| POST | `/api/auth/login/` | Obtenção dos tokens JWT |
| POST | `/api/auth/refresh/` | Renovação do access token |
| GET/PATCH | `/api/auth/perfil/` | Consulta e atualização do perfil |
| GET | `/api/auth/usuarios/?busca=` | Pesquisa de usuários |
| GET | `/api/auth/saude/` | Identificação da réplica |

### Chat

| Método | Endpoint | Finalidade |
|---|---|---|
| GET | `/api/chat/conversas/` | Listagem de conversas |
| POST | `/api/chat/conversas/` | Criação de conversa privada ou grupo |
| GET | `/api/chat/conversas/<id>/mensagens/?antes=<id>` | Histórico paginado |
| POST | `/api/chat/conversas/<id>/mensagens/` | Envio por HTTP |
| GET | `/api/chat/saude/` | Identificação da réplica |
| WS | `/ws/chat/?token=<access>` | Conexão para eventos em tempo real |

As rotas protegidas por JWT utilizam o cabeçalho `Authorization: Bearer <access>` nas requisições HTTP. O parâmetro `antes` do histórico recebe o identificador textual de uma mensagem do MongoDB. O tamanho padrão da página é de 50 mensagens.

Exemplo de criação de grupo:

```json
{
  "tipo": "GRUPO",
  "nome": "Sistemas Distribuídos",
  "participantes": [{"id": 2, "username": "usuario2"}]
}
```

### Eventos WebSocket

Envio pelo cliente:

```json
{"tipo": "mensagem", "conversa_id": 1, "conteudo": "Olá!", "temp_id": "abc"}
```

Exemplo de resposta do servidor:

```json
{
  "tipo": "mensagem",
  "mensagem": {
    "id": "6745af023c189482ac12ff01",
    "conversa_id": 1,
    "remetente_id": 2,
    "remetente_username": "usuario1",
    "conteudo": "Olá!",
    "enviada_em": "2026-11-27T18:00:00+00:00"
  },
  "temp_id": "abc"
}
```

Outros eventos previstos são `conectado`, `nova_conversa` e `erro`.

## Desenvolvimento sem Docker

O modo local original utiliza SQLite e channel layer em memória quando `DB_HOST` e `REDIS_URL` não estão definidos. Após a integração, também é necessário disponibilizar um MongoDB acessível e configurar `MONGO_URL` e `MONGO_DB_NAME` no ambiente do processo de chat. O hostname `mongo` é interno à rede Docker e não deve ser utilizado por processos executados diretamente no host.

Para desenvolvimento distribuído e validação dos requisitos, recomenda-se o ambiente Docker descrito acima.

## Testes

### Testes unitários existentes

Com o ambiente Docker em execução, é possível iniciar as suítes existentes pelos comandos abaixo:

```bash
docker compose exec auth python manage.py test
docker compose exec -e MONGO_DB_NAME=chat_messages_test chat python manage.py test
```

Os testes do chat que utilizavam o model relacional `Mensagem` precisam ser revisados para utilizar o MongoDB. O banco `chat_messages_test` deve ser exclusivo para testes; a suíte deve controlar a preparação e limpeza dos documentos, pois o Django não faz isso automaticamente no MongoDB.

Para os testes do frontend, em um ambiente com Node.js instalado:

```bash
cd frontend
npm install
npm test -- --watchAll=false
```

### Plano de validação

| Categoria | Objetivo | Situação |
|---|---|---|
| Teste funcional | Cadastro, login, mensagens privadas e grupos | Validar e registrar evidências |
| Persistência | Recuperação do histórico no MongoDB após reinicialização | Integração funcional relatada; registrar evidências |
| Unitário | Credenciais, autorização e persistência | Revisar e executar suítes |
| Integração | JWT, frontend, APIs, WebSocket e comunicação entre réplicas | Pendente de comprovação automatizada |
| Carga | Pelo menos 100 usuários simultâneos e 20 grupos | Pendente de execução documentada |
| Tolerância a falhas | Interrupção e recuperação de uma réplica | Pendente de execução documentada |

### Teste de carga e escalabilidade

Cenários propostos para comparação, mantendo a mesma carga de trabalho:

| Cenário | Usuários simultâneos | Grupos | Réplicas de chat |
|---|---:|---:|---:|
| A | 100 | 20 | 1 |
| B | 100 | 20 | 2 |
| C | 100 | 20 | 4 |

Os usuários simulados devem realizar login, estabelecer conexões WebSocket e trocar mensagens. Registrar latência média e p95, throughput, erros, utilização de recursos e distribuição entre instâncias. A automação poderá ser implementada com Locust e um cliente WebSocket.

Não há resultados quantitativos de carga registrados nesta versão da documentação.

## Estrutura do projeto

```text
ChatDistribuido/
├── auth_service/            Microsserviço de autenticação
│   ├── config/
│   └── usuarios/
├── chat_service/            Microsserviço de mensagens
│   ├── config/
│   ├── chat/
│   │   ├── models.py        Conversas e participantes
│   │   ├── mongo.py         Acesso ao MongoDB
│   │   ├── servico.py       Regras de negócio
│   │   ├── views.py         API REST
│   │   ├── serializers.py   Serialização
│   │   ├── consumers.py     WebSocket
│   │   └── tests.py         Testes do chat
│   └── requirements.txt
├── frontend/                Interface React
├── deploy/                  Dockerfiles e configuração Nginx/SQL
├── enunciado/               Especificação acadêmica
├── .env.example             Modelo de configuração
├── docker-compose.yml       Orquestração dos containers
└── README.md
```

## Contexto acadêmico

Trabalho final da disciplina de Sistemas Distribuídos — CEFET-MG, 2026/1, professora Michelle Hanne.

O objetivo é aplicar conceitos de microsserviços, comunicação assíncrona, persistência distribuída entre serviços, replicação da aplicação, escalabilidade horizontal e disponibilidade. O relatório final deve apresentar as decisões de projeto e os resultados dos testes, incluindo a carga mínima prevista no enunciado, respeitando o limite de 10 páginas.

Repositório: <https://github.com/vini-2205/ChatDistribuido>
