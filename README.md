# Hermes Userbot

Sistema Python production-ready para controlar uma conta dedicada do Telegram ("conta suporte") via MTProto/User API, usando Kurigram (fork ativo do Pyrogram).

## Visão Geral

O Hermes Userbot permite que o Hermes-Agente opere no Telegram como uma conta comum, dentro dos limites técnicos e legais aplicáveis. O sistema foi projetado para:

- Automação **responsável** — rate limiting conservador, modos dry-run e read-only
- Operação **24/7** — reconexão automática, logging estruturado, healthchecks
- Arquitetura **modular** — plugins Kurigram, tools independentes, camada agentic
- Integração com o **backend do Hermes** via API FastAPI interna

## Decisão Técnica: Kurigram (fork do Pyrogram)

| Critério | Kurigram | Pyrogram original | Telethon |
|----------|----------|-------------------|----------|
| **Manutenção (2026)** | ✅ Ativo (v2.2.23, Mai 2026) | ❌ Arquivado (Dez 2024) | ✅ Ativo (v1.44.0) |
| **API Layer** | 225 (atualizada) | 158 (desatualizada) | atualizada |
| **Sistema de Plugins** | ✅ Smart Plugins nativo | ✅ Smart Plugins nativo | ❌ Não nativo |
| **Tipagem** | ✅ Type hints completos | ✅ Type hints | ⚠️ Parcial |
| **Drop-in Pyrogram** | ✅ Substitui imports | — | ❌ API diferente |
| **Python 3.11+** | ✅ | ⚠️ Até 3.11 | ✅ |
| **Licença** | LGPL-3.0 | LGPL-3.0 | MIT |

**Recomendação**: Kurigram como biblioteca principal. É o Pyrogram vivo — mesma API, mesmo sistema de plugins, mas com manutenção ativa e layer atualizada. A troca de imports é `from pyrogram import ...` (Kurigram é drop-in replacement).

> Se preferir Telethon, a arquitetura é a mesma. A diferença fica na camada `client.py` e nos handlers de plugin (Telethon usa decorators diferentes).

## Arquitetura

```
┌─────────────────────────────────────────────────────┐
│                    Hermes Backend                     │
│                  (envia comandos via API)              │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP (token interno)
                       ▼
┌─────────────────────────────────────────────────────┐
│                  FastAPI (porta 8000)                  │
│              /api/v1/commands/*                       │
│              /health · /status                        │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│              Camada Agentic (agent/)                   │
│  ┌─────────┐  ┌─────────┐  ┌──────────┐             │
│  │  Router  │→ │  Policy  │→ │ Decision │             │
│  └─────────┘  └─────────┘  └──────────┘             │
│       │              │            │                    │
│  classificar    aprovar/bloq   executar/aprovar       │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│              Tools (tools/)                            │
│  messaging · chats · history · bots · safety          │
│              (rate limited, auditado)                 │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│          Kurigram Client (MTProto)                     │
│       Plugins: private_msgs · groups · cmds · bots     │
│                    · lifecycle                         │
└──────────────────────────────────────────────────────┘
```

## Estrutura de Pastas

```
hermes-userbot/
├── app/
│   ├── main.py              # Ponto de entrada
│   ├── client.py            # Factory do cliente Kurigram
│   ├── bootstrap.py         # Inicialização de serviços
│   ├── config/
│   │   └── settings.py      # Pydantic Settings (.env)
│   ├── plugins/             # Handlers Kurigram (Smart Plugins)
│   │   ├── private_messages.py
│   │   ├── group_messages.py
│   │   ├── commands.py
│   │   ├── bot_interactions.py
│   │   └── lifecycle.py
│   ├── agent/               # Tomada de decisão
│   │   ├── schemas.py       # Modelos Pydantic
│   │   ├── policy.py        # Política de segurança
│   │   ├── router.py        # Roteamento de eventos
│   │   └── decision.py      # Decisor principal
│   ├── tools/               # Ferramentas assíncronas
│   │   ├── messaging.py     # send_message, reply, forward
│   │   ├── chats.py         # join_chat, leave_chat, get_chat_info
│   │   ├── history.py        # get_chat_history, mark_read
│   │   ├── bots.py           # send_bot_command, wait_for_bot_response
│   │   └── safety.py        # Deduplicação, verificação de chat
│   ├── api/                 # API FastAPI interna
│   │   ├── server.py
│   │   ├── routes.py
│   │   └── schemas.py
│   ├── services/            # Serviços transversais
│   │   ├── rate_limiter.py  # Rate limiting conservador
│   │   ├── audit_log.py     # Log de auditoria JSONL
│   │   ├── session_manager.py # Gerenciamento de sessão
│   │   └── command_queue.py # Fila de comandos da API
│   ├── utils/
│   │   ├── logging.py       # Structlog configurado
│   │   ├── errors.py        # Exceções e handlers
│   │   └── time.py          # Delays e backoff
│   └── types/
│       └── common.py        # Enums e tipos compartilhados
├── scripts/
│   ├── generate_session.py  # Gerar string session
│   └── run_dev.py           # Rodar em modo dev
├── sessions/                # Sessões do Telegram (.session)
├── logs/                    # Logs estruturados
├── tests/                   # Testes com pytest
├── .env.example             # Template de configuração
├── pyproject.toml           # Dependências e config
├── Dockerfile               # Container para VPS
├── docker-compose.yml       # Orquestração
├── Makefile                 # Comandos convenientes
└── README.md                # Este arquivo
```

## Requisitos

- Python 3.11+
- Conta do Telegram dedicada ("conta suporte")
- `api_id` e `api_hash` obtidos em https://my.telegram.org
- VPS ou máquina Linux/macOS para operação 24/7

## Instalação Local

```bash
# Clone o repositório
git clone https://github.com/prof-ramos/hermes-userbot.git
cd hermes-userbot

# Crie o .env a partir do template
cp .env.example .env

# Edite o .env com suas credenciais
# NUNCA commite o .env com dados reais!

# Instale com uv (recomendado)
uv pip install -e ".[dev]"

# Ou com pip
pip install -e ".[dev]"
```

## Instalação em VPS (Docker)

```bash
# Clone e configure
git clone https://github.com/prof-ramos/hermes-userbot.git
cd hermes-userbot
cp .env.example .env
# Edite o .env

# Build e deploy
docker compose build
docker compose up -d

# Verificar status
docker compose logs -f hermes-userbot

# Healthcheck
curl http://localhost:8000/health
```

## Como Obter api_id e api_hash

1. Acesse https://my.telegram.org
2. Faça login com o número da **conta suporte**
3. Vá em "API development tools"
4. Crie uma aplicação (preencha nome curto e título)
5. Copie o `api_id` (número) e `api_hash` (string hexadecimal)
6. Adicione ao `.env` como `API_ID` e `API_HASH`

## Como Gerar String Session

```bash
# Execute o script interativo
python scripts/generate_session.py

# Siga as instruções — você receberá um código no Telegram
# Copie a string session gerada e adicione ao .env:
# STRING_SESSION=sua_string_aqui
```

**IMPORTANTE**: A string session é equivalente à sua sessão logada. Nunca a compartilhe ou commite no Git.

## Como Configurar .env

```bash
cp .env.example .env
# Edite as variáveis obrigatórias:
# API_ID=33224854
# API_HASH=sua_api_hash
# STRING_SESSION=sua_string_session  # Gerada pelo script
# PHONE_NUMBER=+55_seu_numero
# INTERNAL_API_TOKEN=um_token_seguro_aleatorio
# OWNER_USER_ID=seu_user_id_no_telegram

# Para primeiro teste, ative dry-run:
# DRY_RUN=true
```

## Como Rodar em Modo Dev

```bash
# Modo dev com dry-run ativado (seguro — não executa ações)
python scripts/run_dev.py

# Ou diretamente
python -m app.main
```

## Como Rodar com Docker

```bash
# Build e start
docker compose up -d

# Logs
docker compose logs -f hermes-userbot

# Parar
docker compose down
```

## Como Ativar Modo Dry-Run

No `.env`:
```
DRY_RUN=true
```

No modo dry-run, **todas as ações de escrita são simuladas** — nada é enviado ao Telegram. Apenas registrado em logs. Ideal para testar sem risco.

## Como Ativar Modo Read-Only

No `.env`:
```
READ_ONLY=true
```

No modo read-only, o userbot apenas lê eventos. Qualquer ação de escrita é bloqueada com erro.

## Como Usar a API Interna

A API roda em `http://127.0.0.1:8000`. Todos os endpoints (exceto `/health`) requerem o header `X-Internal-Token`.

### Exemplos de curl

```bash
# Healthcheck (sem autenticação)
curl http://localhost:8000/health

# Status
curl -H "X-Internal-Token: seu_token" http://localhost:8000/api/v1/status

# Enviar mensagem
curl -X POST http://localhost:8000/api/v1/commands/send-message \
  -H "X-Internal-Token: seu_token" \
  -H "Content-Type: application/json" \
  -d '{"chat_id": 123456, "text": "Olá do Hermes Userbot!"}'

# Responder mensagem
curl -X POST http://localhost:8000/api/v1/commands/reply \
  -H "X-Internal-Token: seu_token" \
  -H "Content-Type: application/json" \
  -d '{"chat_id": 123456, "text": "Resposta", "reply_to_message_id": 789}'

# Entrar em um chat
curl -X POST http://localhost:8000/api/v1/commands/join-chat \
  -H "X-Internal-Token: seu_token" \
  -H "Content-Type: application/json" \
  -d '{"chat_id": "nome_do_grupo"}'

# Sair de um chat
curl -X POST http://localhost:8000/api/v1/commands/leave-chat \
  -H "X-Internal-Token: seu_token" \
  -H "Content-Type: application/json" \
  -d '{"chat_id": -100123456789}'

# Interagir com bot
curl -X POST http://localhost:8000/api/v1/commands/interact-with-bot \
  -H "X-Internal-Token: seu_token" \
  -H "Content-Type: application/json" \
  -d '{"bot_chat_id": 123456, "command": "start"}'
```

## Como Adicionar Novo Plugin

1. Crie um arquivo em `app/plugins/novo_plugin.py`
2. Use o decorator `@Client.on_message(filters.seu_filtro)` do Kurigram
3. O plugin é carregado automaticamente pelo sistema de Smart Plugins
4. Para excluir, adicione o nome em `PLUGINS_EXCLUDE` no `.env`

Exemplo:

```python
# app/plugins/novo_plugin.py
from pyrogram import Client, filters

@Client.on_message(filters.private & filters.command("novo"))
async def handle_novo(client: Client, message: Message):
    await message.reply("Novo plugin funcionando!")
```

## Como Adicionar Nova Tool

1. Crie o arquivo em `app/tools/nova_tool.py`
2. Implemente a função assíncrona com tipagem
3. Adicione rate limiting, audit log e tratamento de erros
4. Adicione um endpoint em `app/api/routes.py` se necessário

Exemplo:

```python
# app/tools/nova_tool.py
from app.client import get_client
from app.agent.schemas import ActionOutcome
from app.types.common import ActionResultStatus

async def nova_acao(param: str) -> ActionOutcome:
    """Nova tool assíncrona."""
    client = get_client()
    # ... lógica aqui ...
    return ActionOutcome(
        action_id="nova_acao",
        status=ActionResultStatus.SUCCESS,
        details={"param": param},
    )
```

## Como Rodar Testes

```bash
# Todos os testes
pytest -v

# Com cobertura
pytest --cov=app --cov-report=term-missing

# Apenas testes de rate_limiter
pytest tests/test_rate_limiter.py -v

# Lint
ruff check app/ scripts/ tests/

# Typecheck
mypy app/
```

## Checklist de Segurança

- [ ] `.env` está no `.gitignore` e não será commitado
- [ ] `sessions/*.session` está no `.gitignore`
- [ ] Logs não contêm API hash, string session, tokens ou senhas
- [ ] `INTERNAL_API_TOKEN` é um token forte e único
- [ ] `OWNER_USER_ID` está configurado (seu user ID do Telegram)
- [ ] Modo `DRY_RUN=true` está ativo para primeiros testes
- [ ] Rate limiting conservador está configurado
- [ ] Lista de chats permitidos/bloqueados está revisada
- [ ] API interna está bindada em `127.0.0.1` (não 0.0.0.0)
- [ ] Docker expõe a porta apenas em `127.0.0.1`

## Riscos de Banimento

**O uso de contas de usuário via MTProto para automação viola os Termos de Serviço do Telegram.** Riscos incluem:

- **Banimento temporário ou permanente** da conta suporte
- **Flood wait** (limite de requisições excedido)
- **Restrição de funcionalidades** (envio de mensagens, entrada em grupos)
- **Number ban** (banimento do número de telefone)

O sistema implementa medidas para **reduzir risco operacional** (rate limiting, delays, dry-run), mas **não pode eliminar o risco**.

## Observações sobre Termos do Telegram

- Automatizar uma conta de usuário é diferente de usar a Bot API (que é oficial)
- O Telegram **não proíbe** explicitamente o uso de MTProto, mas **pode banir contas** com comportamento automatizado
- Use sempre uma **conta dedicada**, nunca sua conta principal
- Mantenha o **rate limiting conservador** ativado
- **Não** envie mensagens em massa, não faça scraping abusivo, não evade restrições

## Cuidados com Logs

- Logs são estruturados (JSON via structlog)
- **Nunca** logar: API hash, string session, número de telefone completo, tokens, senhas 2FA
- Os valores sensíveis são **mascarados automaticamente** pelo processador de logging
- Arquivos de log vão para `logs/` (incluído no `.gitignore`)
- Audit log em `logs/audit.jsonl`

## Rotação de Sessão

Se a sessão for comprometida ou precisar ser renovada:

1. Pare o userbot
2. Delete o arquivo `sessions/hermes_userbot.session`
3. Gere uma nova string session com `python scripts/generate_session.py`
4. Atualize o `.env` com a nova `STRING_SESSION`
5. No Telegram, vá em Configurações → Dispositivos → e termine sessões antigas se necessário
6. Reinicie o userbot

## Troubleshooting

### Erro de autenticação
- Verifique `API_ID` e `API_HASH` no `.env`
- Regenerate a string session se necessário

### Flood wait
- O sistema trata flood wait automaticamente com backoff
- Se persistir, reduza os limites no `.env`

### Cliente não conecta
- Verifique a conexão com a internet
- Verifique se a sessão não foi revogada no Telegram
- Tente gerar uma nova string session

### Erro "String session inválida"
- Gere uma nova string session com `python scripts/generate_session.py`
- Atualize o `.env`

### API não responde
- Verifique se o userbot está rodando
- Verifique `INTERNAL_API_TOKEN` no `.env` e no header

## Stack Técnica

| Componente | Tecnologia |
|------------|-----------|
| MTProto | Kurigram 2.2+ (fork do Pyrogram) |
| Config | Pydantic Settings + .env |
| API | FastAPI + Uvicorn |
| Logging | Structlog (JSON) |
| Testes | pytest + pytest-asyncio |
| Lint | Ruff |
| Tipos | mypy |
| Container | Docker + docker-compose |

## Licença

MIT