# LOCKWISE

Sistema de controle de acesso com circuito digital simulado, backend em nuvem e otimização da escala de segurança.

**ExpoTech 2026.2 — Missão 2050** · Categoria INTERFACE · Engenharia da Computação · UniFECAF

---

## Sobre o projeto

O LOCKWISE é uma fechadura eletrônica cujo circuito digital valida uma senha de 4 bits e bloqueia o sistema após três tentativas incorretas. Cada evento de acesso é enviado a um serviço em nuvem, e o histórico acumulado alimenta um modelo de otimização matemática que determina a escala de vigilância de menor custo.

O projeto atravessa cinco camadas, e o mesmo dado — o evento de acesso — percorre todas elas:

```
[CIRCUITO]      máquina de estados decide liberar ou bloquear
     ↓
[FÍSICA]        corrente e potência do acionamento da trava
     ↓
[GATEWAY]       transporta o evento via HTTP
     ↓
[NUVEM]         API e banco gerenciado persistem o histórico
     ↓
[OTIMIZAÇÃO]    demanda horária define a escala de segurança
```

---

## Estado atual

| Camada | Situação |
|---|---|
| Eletrônica digital | Concluída |
| Física aplicada | Concluída |
| Gateway | Concluído |
| Backend e banco | Concluído (local; deploy na Fase F) |
| Arquitetura e padrões | Código concluído (State, Strategy, Observer, SOLID); documentação C4 pendente |
| Nuvem e CI/CD | API no ar; falta ligar o deploy automático |
| Pesquisa operacional | Não iniciado |

---

## Estrutura do repositório

```
lockwise/
├── circuito/
│   ├── lockwise_completo.circ     circuito principal
│   └── README.md                  como abrir e operar
├── docs/
│   ├── eletronica.md              projeto do circuito
│   ├── fisica.md                  memorial de cálculos
│   ├── arquitetura.md             C4 e padrões de projeto
│   ├── otimizacao.md              modelo matemático
│   ├── adr/                       registros de decisão (por quê de cada escolha)
│   └── evidencias/                14 figuras da simulação
├── gateway/                       gêmeo digital do circuito + POST para a API
├── backend/                       API FastAPI: State, Strategy, Observer + Postgres
├── otimizacao/                    modelo PuLP
├── .github/workflows/             testes e deploy
└── render.yaml                    infraestrutura do Render, versionada
```

---

## O circuito

Desenvolvido em **Logisim-evolution 4.1.0**. Abra `circuito/lockwise_completo.circ` e selecione o circuito `LOCKWISE`.

**Senha gravada:** `1011`

### Blocos funcionais

**Comparador de senha (combinacional).** Implementado em dois estágios para reduzir o fan-in:

```
P1    = S3 · S̄2
P2    = S1 · S0
IGUAL = P1 · P2
```

**Máquina de estados (sequencial).** Quatro estados codificados em dois flip-flops D:

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

**Contador de tentativas (sequencial).** Dois flip-flops D com saturação:

```
ERRO = VERIFICANDO · ĪGUAL
E    = C1 · (C0 + ERRO)
EN   = ERRO · ¬(C1 · C0)
CLR  = LIBERADO + RESET
DC0  = (C0 ⊕ EN) · C̄LR
DC1  = (C1 ⊕ (C0 · EN)) · C̄LR
```

### Duas decisões de projeto

**Por que o bloqueio usa `E = C1·(C0 + ERRO)` e não o valor do contador.** O contador só atinge `11` após a borda de clock. Se o sinal de bloqueio dependesse apenas do valor armazenado, a máquina de estados veria `E = 0` no instante do terceiro erro e só bloquearia no quarto. A expressão antecipa a condição de limiar, garantindo o bloqueio na terceira tentativa.

**Por que o contador satura em vez de transbordar.** Com `EN = ERRO · ¬(C1·C0)`, o contador cheio desabilita a própria contagem. Sem isso, um novo erro levaria o contador de `11` de volta a `00`, liberando indevidamente novas tentativas. Na sequência normal o estado BLOQUEADO já impede novos erros (ERRO exige VERIFICANDO); a saturação garante o comportamento correto mesmo fora dela.

---

## A física

O Logisim simula a lógica; o memorial [`docs/fisica.md`](docs/fisica.md) descreve a implementação física de referência e justifica, com cálculo, o que a lógica sozinha não explica.

| Decisão | Número que a sustenta |
|---|---|
| Pull-down de 10 kΩ em cada entrada | entrada CMOS é um capacitor de ~5 pF: 12,5 pC bastam para levá-la ao nível indefinido |
| Filtro RC + Schmitt só no clock | τ = 10 ms filtra *bounce* de até 5 ms; as demais entradas são amostradas na borda |
| 220 Ω em série com cada LED | 13,6 mA ideal, 11,1 mA com a resistência de saída real da porta |
| Transistor BC337 acionando a trava | bobina exige 300 mA; porta 74HC fornece 25 mA no máximo absoluto |
| R_B = 1 kΩ na base | ganho forçado ≈ 80, três vezes abaixo do h_FE mínimo, garante saturação (V_CE = 0,3 V, P_Q = 91 mW) |
| Diodo 1N4007 em antiparalelo com a bobina | v = −L·di/dt chegaria a centenas de volts contra V_CEO = 45 V; o diodo limita a 12,8 V |
| Trava aberta por 5,16 s | NE555 monoestável: T = RC·ln 3 com 470 kΩ e 10 µF |
| **Energia por liberação: 18 200 mJ** | 3,53 W × 5,16 s — é o valor gravado em `energia_mj` a cada acesso liberado |

---

## No ar

A API está publicada em **https://lockwise-api.onrender.com** ([Swagger](https://lockwise-api.onrender.com/docs)), com Postgres gerenciado na Neon. Aplicação no Render, banco na Neon, testes no GitHub Actions — o porquê de cada escolha está em [`docs/adr/`](docs/adr/), e o passo a passo em [`docs/deploy.md`](docs/deploy.md).

```bash
curl https://lockwise-api.onrender.com/health
curl https://lockwise-api.onrender.com/fechadura
```

---

## O gateway

O Logisim não fala HTTP. O gateway ([`gateway/`](gateway/)) é **a mesma máquina de estados do circuito, escrita em Python** — e a equivalência é provada por teste, não por afirmação: um leitor de `.circ` simula o grafo de portas do arquivo real, e para os 16 estados possíveis dos flip-flops × 128 combinações de pinos ele, as equações transcritas e o padrão State produzem o mesmo próximo estado (2048 casos); as sequências das figuras de evidência reproduzem exatamente o que a simulação mostra.

Cada transição gera um evento: `LIBERADO` (com `energia_mj = 18200`), `NEGADO`, `BLOQUEADO` (+ alerta) ou `DESBLOQUEIO_ADMIN`. Retry com backoff, fila offline em disco e autenticação por `X-API-Key`. Zero dependências.

```bash
cd gateway && python -m pytest          # 103 testes
python -m lockwise_gateway.cli          # painel de pinos em modo eco
```

---

## O backend

[`backend/`](backend/) é a API que recebe os eventos do gateway, persiste o histórico e expõe a **demanda horária** (entrada da otimização) e o **estado da fechadura** (para o painel). FastAPI + SQLAlchemy; SQLite local, Postgres gerenciado em produção.

Três padrões GoF, cada um com trabalho real: **State** projeta o estado da fechadura a partir dos eventos (a mesma FSM do circuito, pela terceira vez); **Strategy** é a política de supervisão que decide quando avisar alguém — `limite`, `horario`, `composta` — trocada por variável de ambiente; **Observer** avisa log e webhook quando um alerta nasce. SOLID está mapeado princípio a princípio no README do backend.

```bash
cd backend && .venv/Scripts/python -m pytest      # 69 testes, inclusive a demo ponta a ponta
```

O teste `test_ponta_a_ponta.py` sobe a API real, roda o gateway real com `roteiros/demo.txt` e confere no banco: é a demo automatizada.

---

## Como operar o circuito

Selecione a ferramenta de mão (Poke Tool) e clique nos pinos. A máquina de estados é síncrona: as transições ocorrem apenas na borda de subida do CLK.

**Acesso liberado**

1. Ligue S3, S1 e S0 (senha `1011`) — SENHA_OK acende
2. Ligue CONFIRMA, pulse o CLK — VERIFICANDO acende
3. Desligue CONFIRMA, pulse o CLK — TRAVA_ABERTA acende
4. Ligue TIMEOUT, pulse o CLK — retorna a AGUARDANDO

**Bloqueio por tentativas**

Com senha incorreta, repita três vezes: CONFIRMA liga, pulse o CLK, CONFIRMA desliga, pulse o CLK. O contador evolui `00` → `01` → `10` e, na terceira tentativa, BLOQUEADO acende com o contador em `11`.

Para desbloquear: ligue RESET e pulse o CLK.

---

## Por que as coisas são assim

Cada decisão que moldou o projeto — do tema à política de autenticação — tem um registro em [`docs/adr/`](docs/adr/): o que estava em jogo, o que escolhemos, o que descartamos e o que isso custa. Se a pergunta é "por que vocês fizeram desse jeito?", a resposta está lá.

---

## Equipe

| Integrante | Responsabilidade |
|---|---|
| *(preencher)* | *(preencher)* |

Conforme o regulamento da ExpoTech, todos os integrantes devem ser capazes de explicar qualquer parte do projeto.

---

## Licença

Projeto acadêmico desenvolvido para a ExpoTech 2026.2 da UniFECAF.
