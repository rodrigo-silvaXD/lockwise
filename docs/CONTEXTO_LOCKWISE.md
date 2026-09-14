# LOCKWISE — Contexto do Projeto

Documento de continuidade. Contém tudo o que foi decidido e construído até 14 de setembro de 2026, para retomar o trabalho em qualquer ferramenta sem perder contexto.

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
E    = C1 · (C0 + ERRO)      sinal de limiar, antecipado
ERRO = VERIFICANDO · ĪGUAL
EN   = ERRO · Ē              habilitação com saturação
DC0  = (C0 ⊕ EN) · CLR
DC1  = (C1 ⊕ (C0 · EN)) · CLR
CLR  = LIBERADO + RESET
```

### As duas perguntas prováveis na sabatina

**Por que `E = C1·(C0 + ERRO)` e não simplesmente `C1·C0`?**
O contador só atinge `11` *depois* da borda de clock. Se o bloqueio dependesse apenas do valor armazenado, a FSM veria `E = 0` no instante do terceiro erro e bloquearia só no quarto. A expressão antecipa o limiar.

**Por que o contador satura em vez de transbordar?**
Com `EN = ERRO · Ē`, o próprio sinal de limiar desabilita a contagem. Sem isso, o quarto erro levaria `11` de volta a `00`, liberando novas tentativas indevidamente.

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
│   ├── fisica.md                  A FAZER
│   ├── arquitetura.md             A FAZER
│   └── otimizacao.md              A FAZER
├── gateway/                       A FAZER
├── backend/                       A FAZER
├── otimizacao/                    A FAZER
└── .github/workflows/             A FAZER
```

Pendência no README: preencher a tabela de Equipe.

---

## 7. Requisitos do roteiro — situação

| # | Requisito | Situação |
|---|---|---|
| 1 | Eletrônica digital e analógica: circuito funcional simulado, sensor ou atuador, lógica digital | **Cumprido** (entregue acima do mínimo: combinacional *e* sequencial) |
| 2 | Física: justificativa do comportamento físico com cálculos documentados | Não iniciado |
| 3 | Arquitetura: C4 ou UML, ≥2 padrões GoF, SOLID no backend | Não iniciado |
| 4 | Cloud: deploy real, banco gerenciado, variáveis seguras, CI/CD | Não iniciado |
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

### Fase A — Física (≈1 dia)
Memorial de cálculos em `docs/fisica.md`. Quatro itens:

1. **Resistor do LED indicador.** Vcc 5 V, Vf 2,0 V, If 15 mA → R = 200 Ω → comercial 220 Ω. Potência dissipada ≈ 41 mW.
2. **Estágio de potência da trava.** Solenoide 12 V / 300 mA = 3,6 W. Porta lógica 74HC entrega no máximo ~25 mA, logo é obrigatório transistor. BC337 com β ≈ 100 → Ib = 3 mA → Rb = (5 − 0,7)/0,003 ≈ 1,5 kΩ.
3. **Diodo de roda livre** (1N4007) contra o pico reverso da indutância: V = −L·di/dt.
4. **Energia por liberação.** 3,67 W × 5 s ≈ 18,4 J. *Este número reaparece na fase de otimização — guardar.*

Ponto de atenção: um LED com resistor sozinho não sustenta a seção. O transistor e o diodo sustentam. A pergunta provável é "por que você não ligou a trava direto na saída da porta lógica?".

### Fase B — Gateway (≈1 dia)
`gateway/gateway.py`. Replica a FSM do circuito em Python usando o padrão **State**. Lê o evento de acesso, monta o payload (momento, usuário, resultado, energia em mJ) e faz `POST /acessos` com retry.

Incluir teste de **equivalência**: roda as mesmas sequências no modelo Python e compara com a tabela de referência extraída da simulação. Isso vira uma seção do relatório e responde "como o circuito conversa com a nuvem?".

### Fase C — Backend (≈3 a 4 dias)
`backend/` em Python com FastAPI.

Padrões GoF obrigatórios (mínimo 2):
- **State** — espelha a FSM do circuito. A justificativa é técnica: o hardware *é* uma máquina de estados.
- **Strategy** — política de bloqueio intercambiável (três tentativas, bloqueio progressivo, horário restrito).
- *(opcional)* **Observer** — notificação ao administrador.

SOLID mapeado princípio a princípio, **apontando linha de código**. "Aplicamos SOLID" sem evidência não conta.

Rotas:

| Método | Rota |
|---|---|
| POST | `/acessos` |
| GET | `/acessos?de=&ate=` |
| GET | `/acessos/demanda-horaria` |
| POST | `/alertas` |
| GET | `/escala/otimizada` |

### Fase D — Banco (≈1 dia)

```sql
CREATE TABLE usuario (
    id           SERIAL PRIMARY KEY,
    nome         VARCHAR(100) NOT NULL,
    codigo_senha SMALLINT NOT NULL,
    ativo        BOOLEAN DEFAULT TRUE
);

CREATE TABLE acesso (
    id          SERIAL PRIMARY KEY,
    usuario_id  INTEGER REFERENCES usuario(id),
    momento     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resultado   VARCHAR(20) NOT NULL,   -- LIBERADO | NEGADO | BLOQUEADO
    energia_mj  INTEGER
);

CREATE TABLE alerta (
    id        SERIAL PRIMARY KEY,
    tipo      VARCHAR(30) NOT NULL,
    momento   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolvido BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_acesso_momento ON acesso(momento);
```

A coluna `energia_mj` é o que liga a fase de física à de otimização. Não é enfeite.

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
4. **A seção de física ficar rasa.** Sem transistor e diodo, não há "Física para Sistemas Computacionais".
5. **Vídeo pitch esquecido.** Não aparece no roteiro da INTERFACE, só no regulamento geral.

---

## 12. Prompt para retomar em outra ferramenta

> Estou desenvolvendo o LOCKWISE, um sistema de controle de acesso para a ExpoTech 2026.2 da UniFECAF (categoria INTERFACE, Engenharia da Computação). Leia o arquivo `docs/contexto.md` do repositório, que contém todo o histórico, decisões técnicas, equações do circuito e o plano das fases restantes.
>
> A eletrônica está concluída: circuito em Logisim-evolution com comparador de senha, máquina de estados de quatro estados e contador de tentativas, mais 14 figuras de evidência.
>
> Quero seguir pela Fase [X]. Antes de escrever código, confirme comigo as decisões de projeto que ainda estiverem em aberto.
