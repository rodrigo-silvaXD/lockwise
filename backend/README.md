# API LOCKWISE

Backend do sistema de controle de acesso. Recebe os eventos que o gateway produz a partir do circuito, persiste o histórico e expõe a **demanda horária** (entrada do modelo de otimização) e o **estado atual da fechadura** (para o painel).

```
gateway ──POST /acessos, /alertas──▶  API  ──▶  Postgres (Render)
                                       │
       otimização ◀── GET /acessos/demanda-horaria
       painel     ◀── GET /fechadura, /alertas, /acessos
```

FastAPI · SQLAlchemy 2 · Pydantic 2 · Python 3.11+. SQLite em desenvolvimento e testes; Postgres gerenciado (Neon) em produção — o mesmo código, sem ramificação.

---

## Arquitetura

Camadas com dependências apontando para dentro. Nenhuma regra de negócio conhece HTTP ou SQL.

```
rotas/          FastAPI: valida entrada, chama um serviço, serializa saída
   │ Depends
dependencias.py composição: monta sessão, repositórios, serviços
   │
servicos.py     casos de uso: registrar acesso, projetar fechadura, agregar demanda
   │ Protocols
repositorios.py acesso a dados por trás de interfaces; implementação SQLAlchemy
   │
dominio/        State · Strategy · Observer — sem FastAPI, sem SQLAlchemy
```

### Padrões GoF — cada um com um trabalho concreto

| Padrão | Onde | O que faz | Por que aqui |
|---|---|---|---|
| **State** | [`dominio/estados.py`](lockwise_api/dominio/estados.py) | **Projeção.** Reconstrói o estado da fechadura (AGUARDANDO · LIBERADO · BLOQUEADO) a partir da sequência de eventos. Cada classe sabe o que cada evento significa para ela. LIBERADO expira sozinho após 5,16 s — a nuvem não recebe TIMEOUT, mas conhece o NE555. | O hardware *é* uma máquina de estados. É a terceira encarnação da mesma FSM: circuito → gateway → nuvem. |
| **Strategy** | [`dominio/politicas.py`](lockwise_api/dominio/politicas.py) | **Política de supervisão.** Decide quando um acesso merece alerta na nuvem: `LimiteDeTentativas` (avisa na 2ª, uma antes do hardware bloquear), `JanelaHoraria` (acesso fora do horário), `Composta`, `SemSupervisao`. Escolhida por `LOCKWISE_POLITICA`. | O hardware decide bloquear; a nuvem decide *avisar*, e isso muda com o contexto de uso sem tocar em código. |
| **Observer** | [`dominio/notificacao.py`](lockwise_api/dominio/notificacao.py) | **Notificação.** Quem cria o alerta não sabe quem se interessa. `LogObservador` (sempre) e `WebhookObservador` (se `LOCKWISE_WEBHOOK_URL`). Um observador que falha nunca derruba o registro do acesso. | Amanhã e-mail ou SMS entram sem mexer em quem cria alertas. |

### SOLID, com o dedo na linha

| Princípio | Onde ver |
|---|---|
| **S** — responsabilidade única | `ServicoDeAcessos`, `ServicoDeAlertas`, `ServicoDaFechadura` são três classes em [`servicos.py`](lockwise_api/servicos.py), não uma. `seguranca.py` só autentica. `config.py` só lê ambiente. |
| **O** — aberto/fechado | Nova política de supervisão = nova classe em `politicas.py` + uma entrada na fábrica. Novo observador = nova classe + `notificador.assinar()`. Nenhum `if` novo em `servicos.py`. |
| **L** — substituição | Qualquer `EstadoFechadura` é usado por `Projecao` sem saber qual é. Qualquer `PoliticaDeSupervisao` é usada por `ServicoDeAcessos` idem. |
| **I** — interfaces segregadas | `RepositorioDeAcessos`, `RepositorioDeAlertas`, `RepositorioDeUsuarios` são três Protocols em [`repositorios.py`](lockwise_api/repositorios.py). `ServicoDaFechadura` recebe só os dois que usa. |
| **D** — inversão de dependência | Serviços dependem de Protocols; as classes SQLAlchemy são injetadas em [`dependencias.py`](lockwise_api/dependencias.py). O domínio não importa `sqlalchemy` nem `fastapi`. |

A documentação C4 (Fase E) aponta linhas exatas.

---

## Rotas

| Método | Rota | Auth | Resposta |
|---|---|---|---|
| `POST` | `/acessos` | `X-API-Key` | **201** — o acesso e os alertas que a política gerou |
| `GET` | `/acessos?de=&ate=&limite=` | aberta | histórico, mais recente primeiro |
| `GET` | `/acessos/demanda-horaria?de=&ate=` | aberta | 24 faixas em **hora local** com acessos, liberados, negados, bloqueados e `energia_mj` |
| `POST` | `/alertas` | `X-API-Key` | **201** |
| `GET` | `/alertas?resolvido=` | aberta | |
| `PATCH` | `/alertas/{id}/resolver` | `X-API-Key` | 404 se não existe |
| `GET` | `/fechadura` | aberta | estado, tentativas, `trava_fecha_em`, último evento, avisos |
| `GET` | `/health` | aberta | `{status, banco, motor, persistente, versao, politica, observadores}`; 503 se o banco não responde. `persistente: false` denuncia que está rodando em SQLite — em produção, disco efêmero |
| `GET` | `/docs` | aberta | Swagger |

**Contrato com o gateway** — é exatamente o que `gateway/lockwise_gateway/eventos.py` produz:

```json
POST /acessos   {"momento": "2026-09-16T11:37:23.010+00:00", "usuario_id": 1, "resultado": "LIBERADO", "tentativa": 2, "energia_mj": 18200}
POST /alertas   {"tipo": "BLOQUEIO", "momento": "2026-09-16T11:37:23.010+00:00"}
```

Respostas sempre em UTC explícito (`…Z`), mesmo com SQLite, que descarta o fuso ao gravar.

### Decisões

- **Escrita exige chave; leitura é aberta.** O painel lê sem chave no navegador.
- **Sem chave configurada, escrita responde 503** — falha fechada. E 5xx, não 4xx, para o gateway enfileirar em vez de descartar.
- **Evento inconsistente é aceito e anotado, nunca rejeitado.** Um NEGADO durante BLOQUEADO é impossível no hardware; a projeção registra um aviso em `/fechadura`, mas o acesso fica no banco. Rejeitar com 4xx faria o gateway descartá-lo.
- **Demanda horária em hora local**, agregada em Python. 22:30 em São Paulo é 01:30 UTC; a escala de vigilância é em horário de gente.
- **`usuario.codigo_senha` em texto claro.** É um código de 4 bits com 16 valores; não é segredo criptográfico e existe para exibição, não para autenticar.

---

## Banco

Esquema em [`schema.sql`](schema.sql) (DDL de referência para Postgres). O código cria as tabelas com `create_all` e garante a semente `usuario(id=1, 'Morador', 1011)` no arranque — idempotente.

```
usuario  id · nome · codigo_senha · ativo
acesso   id · usuario_id → usuario · momento · resultado · tentativa · energia_mj      idx(momento)
alerta   id · tipo · momento · resolvido · detalhe · acesso_id → acesso                idx(momento)
```

`energia_mj` liga a física (`docs/fisica.md` §6) à otimização (`/demanda-horaria`). `tentativa` é o que o gateway informa (1–3). `alerta.acesso_id` liga um alerta da política ao acesso que o gerou.

---

## Configuração

Tudo por variável de ambiente; nada no código. Copie `.env.example`.

| Variável | Padrão | Uso |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./lockwise.db` | Render entrega `postgres://…`; é normalizada para `postgresql+psycopg://` |
| `LOCKWISE_API_KEY` | — | obrigatória para escrever |
| `LOCKWISE_POLITICA` | `limite` | `limite` · `horario` · `composta` · `nenhuma` |
| `LOCKWISE_LIMITE_TENTATIVAS` | `2` | política `limite` |
| `LOCKWISE_JANELA` | `06:00-23:00` | política `horario`; pode cruzar a meia-noite |
| `LOCKWISE_FUSO` | `America/Sao_Paulo` | janela e demanda horária |
| `LOCKWISE_WEBHOOK_URL` | — | Observer: POST JSON de cada alerta (Discord-compatível) |
| `LOCKWISE_CORS_ORIGINS` | `*` | o painel, depois |

---

## Rodar localmente

```bash
cd backend
python -m venv .venv
.venv/Scripts/pip install -e ".[dev,postgres]"        # Windows; em Linux/mac: .venv/bin/pip
LOCKWISE_API_KEY=dev .venv/Scripts/python -m uvicorn lockwise_api.asgi:app --reload
```

Swagger em http://127.0.0.1:8000/docs. Em outro terminal, o gateway contra ela:

```bash
cd gateway
LOCKWISE_API_KEY=dev python -m lockwise_gateway.cli --api-url http://127.0.0.1:8000 --roteiro roteiros/demo.txt
```

---

## Deploy

A infraestrutura está em [`render.yaml`](../render.yaml) e o passo a passo em [`docs/deploy.md`](../docs/deploy.md). Em resumo: os testes rodam no GitHub Actions a cada push, e só se passarem o deploy é disparado no Render; o pipeline então espera `/health` responder ok antes de se declarar verde (ADR 0022).

## Testes

```bash
.venv/Scripts/python -m pytest
```

| Arquivo | Cobre |
|---|---|
| `test_estados.py` | State: projeção, expiração do LIBERADO, bloqueio, desbloqueio, avisos |
| `test_politicas.py` | Strategy: limite, janela horária (fuso local, meia-noite), composta, fábrica |
| `test_notificacao.py` | Observer: assinantes, observador que falha, webhook |
| `test_acessos.py` | contrato do gateway, validações, histórico, período, alerta ligado ao acesso |
| `test_alertas_fechadura.py` | alertas do gateway, resolver, `/fechadura` via HTTP |
| `test_demanda.py` | 24 faixas, hora local vs UTC, soma de energia, período, fuso configurável |
| `test_seguranca_saude.py` | 401, 503 falha fechada, leitura aberta, `/health` 200/503, OpenAPI |
| **`test_ponta_a_ponta.py`** | **a demo:** uvicorn real + gateway real + `roteiros/demo.txt` → 4 acessos, 3 alertas, energia na hora certa, fechadura em AGUARDANDO |

O último é a demo ao vivo sem o Logisim na tela. Se ele passa, a apresentação funciona.
