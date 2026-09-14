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
| Física aplicada | Em andamento |
| Gateway | Não iniciado |
| Backend e banco | Não iniciado |
| Arquitetura e padrões | Não iniciado |
| Nuvem e CI/CD | Não iniciado |
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
│   └── evidencias/                14 figuras da simulação
├── gateway/                       ponte entre circuito e nuvem
├── backend/                       API e banco
├── otimizacao/                    modelo PuLP
└── .github/workflows/             pipeline de CI/CD
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
E    = C1 · (C0 + ERRO)
EN   = ERRO · Ē
DC0  = (C0 ⊕ EN) · CLR
DC1  = (C1 ⊕ (C0 · EN)) · CLR
CLR  = LIBERADO + RESET
```

### Duas decisões de projeto

**Por que o bloqueio usa `E = C1·(C0 + ERRO)` e não o valor do contador.** O contador só atinge `11` após a borda de clock. Se o sinal de bloqueio dependesse apenas do valor armazenado, a máquina de estados veria `E = 0` no instante do terceiro erro e só bloquearia no quarto. A expressão antecipa a condição de limiar, garantindo o bloqueio na terceira tentativa.

**Por que o contador satura em vez de transbordar.** Com `EN = ERRO · Ē`, o próprio sinal de limiar desabilita a contagem. Sem isso, o quarto erro levaria o contador de `11` de volta a `00`, liberando indevidamente novas tentativas.

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

## Equipe

| Integrante | Responsabilidade |
|---|---|
| *(preencher)* | *(preencher)* |

Conforme o regulamento da ExpoTech, todos os integrantes devem ser capazes de explicar qualquer parte do projeto.

---

## Licença

Projeto acadêmico desenvolvido para a ExpoTech 2026.2 da UniFECAF.
