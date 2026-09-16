# LOCKWISE — Contexto do Projeto

Documento de continuidade. Contém tudo o que foi decidido e construído até 16 de setembro de 2026, para retomar o trabalho em qualquer ferramenta sem perder contexto.

---

## 1. O que é o projeto

**LOCKWISE** — sistema de controle de acesso com circuito digital simulado, backend em nuvem e otimização da escala de segurança.

**Evento:** ExpoTech 2026.2 "Missão 2050: Smart Home & Tecnologias do Futuro"
**Categoria:** INTERFACE (4º e 5º semestre, Engenharia da Computação)
**Instituição:** UniFECAF, Campus Conceito
**Inscrição:** concluída (prazo era 11/09/2026, já encerrado — tema e equipe não podem mais mudar)

### Descrição oficial inscrita

Sistema de controle de acesso residencial inteligente, desenvolvido integralmente em ambiente simulado. O circuito é implementado no Logisim e combina um bloco combinacional de comparação de senha de 4 bits com um bloco sequencial formado por uma máquina de estados finitos de quatro estados e um contador de tentativas que bloqueia o sistema após três erros consecutivos. Cada evento de acesso é registrado por um backend em Python hospedado em nuvem pública, com banco de dados gerenciado, variáveis de ambiente seguras e pipeline de CI/CD. O histórico de acessos alimenta um modelo de otimização matemática que determina a escala de vigilância de menor custo capaz de cobrir a demanda real de cada faixa horária.

---

## 2. O fio condutor

O projeto não é cinco trabalhos separados. Um único dado — o **evento de acesso** — atravessa todas as camadas:

```
[CIRCUITO LOGISIM]   FSM decide liberar ou bloquear
        ↓            justificado por...
[FÍSICA]             corrente e potência do acionamento da trava
        ↓            transportado por...
[GATEWAY.PY]         POST /acessos
        ↓            persistido em...
[NUVEM + BANCO]      tabela `acesso`
        ↓            agregado por hora, alimenta...
[OPERATIONS RESEARCH]  modelo de escala de segurança
```

**Frase para a sabatina:** "A demanda do modelo de otimização não é inventada — vem do histórico de acessos que o próprio circuito gerou."

---

## 3. Decisões técnicas tomadas

| Decisão | Motivo |
|---|---|
| **Logisim em vez de Proteus** | O `.circ` é XML e pode ser gerado/editado por IA. O `.pdsprj` do Proteus é binário proprietário, Windows-only e pago. O roteiro aceita ambos. |
| **Logisim-evolution 4.1.0 desktop** | Tem cronograma (diagrama de tempo), essencial para evidenciar o comportamento síncrono. A versão web (logisim.app, 2.7.2) ficou como plano B. |
| **Túneis em vez de fiação longa** | Elimina erro de conexão por coordenada e mantém o diagrama legível. |
| **Contador feito com flip-flops D, não com o componente Counter pronto** | Permite explicar cada porta na avaliação individual. |
| **Comparador em dois estágios (P1, P2)** | Reduz fan-in e evita AND de 4 entradas. |
| **Tema "controle de acesso" e não "estação ambiental"** | É o único dos três sugeridos que é 100% digital. Os outros partem de grandezas analógicas que o Logisim não simula. |
| **Render como provedor de nuvem (recomendado)** | Deploy direto do GitHub, Postgres gerenciado no free tier, sem cartão. AWS custaria dias de configuração de IAM. |
| **Gateway em Python como ponte** | O Logisim não faz HTTP. O gateway replica a FSM e prova equivalência com a simulação. |

---

## 4. O circuito (CONCLUÍDO)

Arquivo: `circuito/lockwise_completo.circ` · Senha gravada: **1011**

### Entradas
`S3 S2 S1 S0` (senha), `CONFIRMA`, `TIMEOUT`, `RESET`, `CLK`

### Saídas
`AGUARDANDO`, `VERIFICANDO`, `TRAVA_ABERTA`, `BLOQUEADO`, `SENHA_OK`, `ERROS_C1`, `ERROS_C0`

### Comparador (combinacional)
```
P1    = S3 · S̄2
P2    = S1 · S0
IGUAL = P1 · P2
```

### Máquina de estados (sequencial, 2 flip-flops D)

| Estado | Q1 Q0 |
|---|:---:|
| AGUARDANDO | 00 |
| VERIFICANDO | 01 |
| LIBERADO | 10 |
| BLOQUEADO | 11 |

```
D1 = Q̄1·Q0·(IGUAL + E) + Q1·Q̄0·T̄ + Q1·Q0·R̄
D0 = Q̄1·Q̄0·C + Q̄1·Q0·ĪGUAL·E + Q1·Q0·R̄
```

### Contador de tentativas (sequencial, 2 flip-flops D)
```
ERRO = VERIFICANDO · ĪGUAL
E    = C1 · (C0 + ERRO)      sinal de limiar, antecipado
EN   = ERRO · ¬(C1 · C0)     habilitação com saturação (contador cheio desabilita)
CLR  = LIBERADO + RESET
DC0  = (C0 ⊕ EN) · C̄LR
DC1  = (C1 ⊕ (C0 · EN)) · C̄LR
```

> Equações extraídas da netlist do `.circ` em 16/09/2026 (análise de conectividade feita para o gateway). A versão anterior deste documento e do README trazia `EN = ERRO·Ē` e `·CLR` — com essas, o contador ficaria em `10` no bloqueio, contradizendo a fig. 11. O circuito estava certo; a documentação, não.

### As duas perguntas prováveis na sabatina

**Por que `E = C1·(C0 + ERRO)` e não simplesmente `C1·C0`?**
O contador só atinge `11` *depois* da borda de clock. Se o bloqueio dependesse apenas do valor armazenado, a FSM veria `E = 0` no instante do terceiro erro e bloquearia só no quarto. A expressão antecipa o limiar.

**Por que o contador satura em vez de transbordar?**
Com `EN = ERRO · ¬(C1·C0)`, o contador cheio desabilita a própria contagem. Sem isso, um erro a mais levaria `11` de volta a `00`, liberando novas tentativas indevidamente.

### Geometria do Logisim-evolution 4.1.0 (para gerar novos `.circ`)

Flip-Flop D, deslocamentos em relação ao `loc`:

| Porta | Offset |
|---|---|
| D | −10, +10 |
| Clock | −10, +50 |
| S (topo) | +20, 0 |
| R (base) | +20, +60 |
| Q | +50, +10 |
| Q̄ | +50, +50 |

Portas lógicas, `size=50`, entradas em `loc.x − 50`:
- 2 entradas: `loc.y ± 20`
- 3 entradas: `loc.y − 20`, `loc.y`, `loc.y + 20`
- 4 entradas: `loc.y − 20, −10, +10, +20`

NOT gate: entrada em `loc.x − 30`.
Bibliotecas: `lib 0` = Wiring, `lib 1` = Gates, `lib 5` = Memory, `lib 9` = Base.
Pino de saída usa `<a name="type" val="output"/>` e `facing="west"`.
Rótulos **não podem ter espaço** — o Logisim renomeia para um hash aleatório.

---

## 5. Evidências (CONCLUÍDO)

14 figuras capturadas em `docs/evidencias/`:

| Figura | Conteúdo |
|---|---|
| 01 | Visão geral do circuito |
| 02 | Painel de entradas e saídas |
| 03 | Comparador rejeitando senha incorreta |
| 04 | Comparador reconhecendo 1011 |
| 05–08 | Os quatro estados e o retorno por timeout |
| 09–11 | Contador em 01, 10 e o bloqueio em 11 |
| 12 | Saturação do contador |
| 13 | Desbloqueio por RESET |
| 14 | Diagrama temporal (cronograma) |

---

## 6. Repositório

Estrutura montada, pronta para push:

```
lockwise/
├── README.md                      completo, com equações e decisões
├── .gitignore
├── circuito/
│   ├── lockwise_completo.circ
│   └── README.md
├── docs/
│   ├── evidencias/                14 figuras + índice
│   ├── eletronica.md              A FAZER
│   ├── fisica.md                  CONCLUÍDO
│   ├── arquitetura.md             A FAZER
│   └── otimizacao.md              A FAZER
├── gateway/                       CONCLUÍDO
├── backend/                       CONCLUÍDO (local)
├── otimizacao/                    A FAZER
└── .github/workflows/             A FAZER
```

Pendência no README: preencher a tabela de Equipe.

---

## 7. Requisitos do roteiro — situação

| # | Requisito | Situação |
|---|---|---|
| 1 | Eletrônica digital e analógica: circuito funcional simulado, sensor ou atuador, lógica digital | **Cumprido** (entregue acima do mínimo: combinacional *e* sequencial) |
| 2 | Física: justificativa do comportamento físico com cálculos documentados | **Cumprido** (`docs/fisica.md`) |
| 3 | Arquitetura: C4 ou UML, ≥2 padrões GoF, SOLID no backend | **Código cumprido** (3 padrões + SOLID em `backend/`); C4 pendente (Fase E) |
| 4 | Cloud: deploy real, banco gerenciado, variáveis seguras, CI/CD | Backend pronto para deploy; nuvem e pipeline pendentes (Fase F) |
| 5 | Operations Research: problema de otimização modelado e resolvido | Não iniciado |

---

## 8. Regulamento geral — o que ele acrescenta

**Entregas obrigatórias que o roteiro da INTERFACE omite:**
- Vídeo pitch de até 3 minutos
- Repositório GitHub **público** com código documentado

**Pesos da avaliação:**

| Pilar | Peso | Observação |
|---|:--:|---|
| Funcionalidade real e validação | 35% | Tem que funcionar **ao vivo**. Só slides ou protótipo fictício zera o quesito. |
| Profundidade e rigor técnico | 30% | Projetos triviais são desclassificados. |
| Documentação e GitHub | 20% | Repositório organizado, código comentado, vídeo pitch. |
| Domínio individual e sabatina | 15% | Respostas vagas **eliminam a elegibilidade do grupo inteiro**. |

**Risco principal identificado:** o circuito é simulado e a ponte é software. Se na avaliação isso virar "Logisim numa tela e print da API na outra", cheira a protótipo fictício. A demo precisa ser encadeada ao vivo: digitar a senha no Logisim → gateway dispara → registro aparece no banco na nuvem, na frente do professor.

**Regras adicionais:** equipe de 3 a 5 pessoas da mesma turma; nota individual; falta na avaliação atribui 0 ao integrante; projeto não pode ser alterado após a avaliação; até 30% dos grupos são convocados para o evento.

---

## 9. Cronograma

| Data | Etapa |
|---|---|
| 11/09/2026 | Inscrição encerrada ✅ |
| 09 a 13/11/2026 | **Avaliação individual em sala** |
| 16 a 20/11/2026 | Divulgação dos convocados |
| 28/11/2026 | ExpoTech, dia do evento |

Restam cerca de **8 semanas** até a avaliação.

---

## 10. O que falta fazer

### Fase A — Física ✅ CONCLUÍDA (16/09/2026)
Memorial em `docs/fisica.md`, organizado por grandeza (sinal, corrente/tensão, potência, magnetismo) e cobrindo os três eixos do roteiro — eletrostática, eletrodinâmica, magnetismo. Valores de projeto:

| Item | Valor |
|---|---|
| Pull-down das entradas | 10 kΩ |
| Filtro de clock | 10 kΩ + 1 µF + 74HC14 (τ = 10 ms) |
| Resistor de LED | 220 Ω → 11,1 mA real |
| Estágio de potência | BC337-40, R_B = 1 kΩ, I_C = 292,5 mA, V_CE(sat) = 0,3 V, P_Q = 91 mW |
| Diodo de roda livre | 1N4007, limita coletor a 12,8 V |
| TIMEOUT | NE555 monoestável, 470 kΩ + 10 µF → T = 5,16 s |
| **Energia por liberação** | **18 200 mJ** (3,53 W × 5,16 s) — constante `energia_mj` do gateway/backend; eventos NEGADO/BLOQUEADO gravam 0 |
| Fonte | 12 V / 1 A; pico 354 mA |

Seção 9 do memorial tem as respostas prontas para a sabatina ("por que não ligou a trava direto na porta?", "para que serve o diodo?", "como escolheu o resistor de base?").

### Fase B — Gateway ✅ CONCLUÍDA (16/09/2026)
`gateway/lockwise_gateway/`, Python 3.11+, zero dependências (só `pytest` para testes). 103 testes.

Decisões tomadas:
- **Gêmeo digital**, não integração com o Logisim (não existe caminho suportado). Dois modelos: `circuito.py` (equações da netlist, porta a porta) e `estados.py`+`maquina.py` (padrão **State**). `test_equivalencia.py` prova netlist ≡ State em todos os 2048 casos (16 estados × 128 entradas) e reproduz as sequências das figuras 05–13 (`referencia/sequencias.json`). `test_netlist.py` + `tests/logisim.py` leem o `.circ` real, simulam o grafo de portas e provam que ele ≡ `circuito.py` nos 2048 casos — a transcrição manual deixou de ser um ponto de confiança.
- Eventos só em transição: `LIBERADO` (energia_mj 18200, usuario_id 1), `NEGADO` (energia 0, usuario null), `BLOQUEADO` + alerta `BLOQUEIO`, RESET → alerta `DESBLOQUEIO_ADMIN`. Campo extra `tentativa` (1–3) no payload de `/acessos`. Senhas erradas não são transmitidas.
- Transporte: `urllib`, retry 0,5/1/2 s em conexão/5xx, fila offline JSONL reenviada no início e no comando `fila`, 4xx não repete. `X-API-Key` por variável de ambiente. `momento` preservado no reenvio.
- CLI (`python -m lockwise_gateway.cli`): comandos por pino (`senha`, `confirma`, `clk`…) e macros (`tentar`, `fechar`, `desbloquear`); `--roteiro`, `--timeout-fisico` (TIMEOUT sozinho após 5,16 s), modo eco sem API.
- `roteiros/demo.txt` é o ensaio da demo.

**Contrato que o backend precisa honrar** (Fase C): `POST /acessos` com `{momento, usuario_id, resultado, tentativa, energia_mj}` e `POST /alertas` com `{tipo, momento}`; responder 201; aceitar `X-API-Key`; `tipo ∈ {BLOQUEIO, DESBLOQUEIO_ADMIN}`. A coluna `tentativa SMALLINT` deve entrar na tabela `acesso`.

### Fase C — Backend ✅ CONCLUÍDA (16/09/2026) · Fase D — Banco ✅ CONCLUÍDA (local)
`backend/lockwise_api/`, FastAPI + SQLAlchemy 2 + Pydantic 2, venv em `backend/.venv`. 69 testes.

Decisões tomadas:
- **Três padrões GoF com trabalho real**: State (`dominio/estados.py`) = projeção do estado da fechadura a partir dos eventos, LIBERADO expira sozinho após 5,16 s; Strategy (`dominio/politicas.py`) = política de supervisão `limite` | `horario` | `composta` | `nenhuma`, por `LOCKWISE_POLITICA`; Observer (`dominio/notificacao.py`) = `LogObservador` + `WebhookObservador` opcional.
- Camadas: rotas → `dependencias.py` (composição) → `servicos.py` → `repositorios.py` (Protocols) → domínio. SOLID mapeado no `backend/README.md`.
- **Escrita exige `X-API-Key`, leitura aberta.** Sem chave configurada, escrita responde **503** (falha fechada; 5xx faz o gateway enfileirar).
- **Evento inconsistente é aceito e anotado** em `/fechadura.avisos`, nunca rejeitado com 4xx.
- **Demanda horária em hora local** (`LOCKWISE_FUSO`, padrão America/Sao_Paulo), 24 faixas sempre presentes, com `energia_mj` somada — é a d_h da Fase G.
- Respostas sempre em UTC explícito (`Z`), mesmo com SQLite.
- Banco: `schema.sql` de referência; `create_all` + semente `usuario(1, 'Morador', 1011)` idempotente no arranque. Colunas novas: `acesso.tentativa`, `alerta.detalhe`, `alerta.acesso_id`. Tipos de alerta da nuvem: `TENTATIVAS_SUSPEITAS`, `ACESSO_FORA_DO_HORARIO`.
- `DATABASE_URL` `postgres://` (Render) é normalizada para `postgresql+psycopg://`; `psycopg[binary]` já está nas dependências.
- **`tests/test_ponta_a_ponta.py`** sobe uvicorn real, roda o gateway real com `roteiros/demo.txt` e confere: 4 acessos, 3 alertas, 18 200 mJ na hora certa, fechadura em AGUARDANDO. É a demo automatizada.

Rotas: `POST/GET /acessos`, `GET /acessos/demanda-horaria`, `POST/GET /alertas`, `PATCH /alertas/{id}/resolver`, `GET /fechadura`, `GET /health`, `/docs`. `GET /escala/otimizada` fica para a Fase G.

Rodar: `LOCKWISE_API_KEY=dev .venv/Scripts/python -m uvicorn lockwise_api.asgi:app --reload` e o gateway com `--api-url http://127.0.0.1:8000`.

**Pendente da Fase D em produção**: criar o Postgres no Render (Fase F) e apontar `DATABASE_URL`. Nenhuma migração é necessária — `create_all` cria tudo no primeiro arranque.

### Fase E — Arquitetura (≈1 dia)
`docs/arquitetura.md` com C4 níveis 1 a 3 em Mermaid ou PlantUML, versionado no repositório. Diagrama feito em ferramenta gráfica externa e não versionado se perde.

- **Contexto:** Morador / Administrador → LOCKWISE → Notificação
- **Contêiner:** Circuito → Gateway → API → Banco → Módulo de otimização
- **Componente:** `AcessoController`, `AcessoService`, `PoliticaBloqueio`, `AcessoRepository`, `NotificadorObserver`

### Fase F — Nuvem e CI/CD (≈2 dias)
Deploy no free tier (Render recomendado). Variáveis de ambiente em secrets, nunca no repositório. `.github/workflows/deploy.yml` com pytest → build → deploy. Precisa estar **verde** no dia da avaliação.

### Fase G — Operations Research (≈2 dias)
`otimizacao/` com modelo em PuLP, solver CBC. Set covering para escala de vigilância.

**Conjuntos:** `T` = seis turnos de 4 h; `H` = 24 horas; `a(t,h) = 1` se o turno cobre a hora.
**Parâmetros:** `c_t` custo do turno (noturno +20%); `d_h = ⌈acessos_h / K⌉` derivado do histórico real.
**Variável:** `x_t ∈ ℤ⁺`, vigilantes por turno.

```
minimizar  Σ c_t · x_t
sujeito a  Σ a(t,h) · x_t ≥ d_h   ∀h    (cobertura)
           Σ x_t ≤ N_max                 (equipe disponível)
           x_t ≥ 1               ∀t      (nenhum turno vazio)
```

Comparar com a escala ingênua (mesmo número em todos os turnos) e apresentar a economia percentual. Um número concreto vale mais que a explicação do modelo.

### Fase H — Documentação e vídeo (≈3 dias)
Relatório técnico, vídeo pitch de até 3 minutos, README finalizado.

Estrutura sugerida da seção de eletrônica:
- 3.1 Visão geral → Fig. 01, 02
- 3.2 Comparador → tabela-verdade, Karnaugh, expressão simplificada, Fig. 03, 04
- 3.3 Máquina de estados → tabela de transição, equações D1/D0, Fig. 05–08
- 3.4 Contador → equações, Fig. 09–13
- 3.5 Verificação temporal → Fig. 14

Regra: teoria antes, evidência depois.

### Fase I — Ensaio da sabatina (≈1 semana)
Cada integrante sendo arguido pelos outros. É a fase mais ignorada e a que o regulamento trata com mais dureza: respostas vagas eliminam a elegibilidade do **grupo inteiro**.

---

## 11. Riscos conhecidos

1. **Demo ao vivo vale 35%.** Precisa ser encadeada de ponta a ponta, não telas separadas. Ensaiar.
2. **Conhecimento concentrado.** Hoje uma pessoa opera o circuito. O regulamento não aceita divisão em que só um entende o projeto.
3. **Deploy quebra na véspera.** Subir cedo, mesmo incompleto, e manter o pipeline verde.
4. ~~**A seção de física ficar rasa.**~~ Resolvido: `docs/fisica.md` cobre transistor, diodo, RC, temporização e orçamento de potência.
5. **Vídeo pitch esquecido.** Não aparece no roteiro da INTERFACE, só no regulamento geral.

---

## 12. Prompt para retomar em outra ferramenta

> Estou desenvolvendo o LOCKWISE, um sistema de controle de acesso para a ExpoTech 2026.2 da UniFECAF (categoria INTERFACE, Engenharia da Computação). Leia o arquivo `docs/CONTEXTO_LOCKWISE.md` do repositório, que contém todo o histórico, decisões técnicas, equações do circuito e o plano das fases restantes.
>
> A eletrônica está concluída (circuito Logisim + 14 evidências), a física também (`docs/fisica.md`, energia por liberação 18 200 mJ) o gateway também (`gateway/`, gêmeo digital com prova de equivalência contra o .circ real, 103 testes) e o backend também (`backend/`, FastAPI com State/Strategy/Observer, 69 testes, demo ponta a ponta automatizada). Próximas: E (C4), F (Render + CI/CD), G (PuLP).
>
> Quero seguir pela Fase [X]. Antes de escrever código, confirme comigo as decisões de projeto que ainda estiverem em aberto.
