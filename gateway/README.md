# Gateway LOCKWISE

Gêmeo digital do circuito e ponte para a API na nuvem.

O Logisim não fala HTTP, não grava arquivo nem abre socket — não há caminho suportado para ler o estado da simulação de fora. O gateway resolve isso sendo **a mesma máquina de estados do circuito, escrita em Python**, e provando essa equivalência por teste. O operador aciona os mesmos pinos nos dois lados; a saída do gateway é o evento que vai para a nuvem.

```
Logisim (Poke Tool)        gateway (CLI)                API
  senha 1011  ─────────▶  senha 1011
  CONFIRMA, CLK ────────▶  confirma on, clk       VERIFICANDO
  CONFIRMA, CLK ────────▶  confirma off, clk      LIBERADO ──▶ POST /acessos {energia_mj: 18200}
```

Só biblioteca padrão. Python 3.11+.

---

## Dois gêmeos, uma prova

| Módulo | O que é | Para que serve |
|---|---|---|
| [`circuito.py`](lockwise_gateway/circuito.py) | As equações booleanas do `.circ`, porta a porta, com a coordenada de cada porta no comentário | Gêmeo da **netlist**. Não sabe o que é senha ou tentativa; sabe pinos, portas e flip-flops. |
| [`estados.py`](lockwise_gateway/estados.py) + [`maquina.py`](lockwise_gateway/maquina.py) | Padrão **State**: uma classe por estado, um contador com as regras do hardware, eventos nas transições | Gêmeo **semântico**. É o que o backend vai espelhar. |

[`tests/test_equivalencia.py`](tests/test_equivalencia.py) e [`tests/test_netlist.py`](tests/test_netlist.py) provam que os dois são a mesma máquina — e que ambos são o circuito — em quatro níveis:

1. **Exaustivo** — para os 16 estados possíveis dos flip-flops × 128 combinações de pinos, o próximo estado da netlist é idêntico ao do padrão State. 2048 casos, todo o espaço.
2. **Saídas** — os sete pinos de saída coincidem em todos os estados e entradas.
3. **Simulação** — as sequências de [`referencia/sequencias.json`](referencia/sequencias.json), extraídas das figuras de evidência, produzem nos dois modelos exatamente o estado e o contador que o Logisim mostra.
4. **O arquivo `.circ`** — [`tests/logisim.py`](tests/logisim.py) lê `circuito/lockwise_completo.circ`, reconstrói as conexões (fios, túneis, portas dos componentes) e simula o grafo de portas sem saber nada sobre o LOCKWISE. O próximo estado e as saídas coincidem com `circuito.py` nos 2048 casos.

Se alguém mover uma porta no Logisim e esquecer o Python, o nível 4 quebra. Se alterar o Python e esquecer o Logisim, os níveis 1 a 4 quebram.

### As equações, extraídas da netlist

Foram lidas diretamente do arquivo `.circ` por análise de conectividade, não copiadas da documentação. Duas diferem do que o README do projeto dizia originalmente e foram corrigidas lá:

```
IGUAL = (S3·S̄2)·(S1·S0)                            comparador, senha 1011
ERRO  = VERIFICANDO · ¬IGUAL
E     = C1 · (C0 + ERRO)                            limiar de bloqueio, antecipado

D1 = Q̄1·Q0·(IGUAL + E) + Q1·Q̄0·¬TIMEOUT + Q1·Q0·¬RESET
D0 = Q̄1·Q̄0·CONFIRMA + Q̄1·Q0·(¬IGUAL·E) + Q1·Q0·¬RESET

CLR = LIBERADO + RESET
EN  = ERRO · ¬(C1·C0)                               incrementa em erro, satura em 11
DC0 = (C0 ⊕ EN) · ¬CLR
DC1 = (C1 ⊕ (C0·EN)) · ¬CLR
```

---

## Eventos

Nascem apenas em transições — nunca por leitura periódica.

| Transição | Evento | Rota | Campos relevantes |
|---|---|---|---|
| VERIFICANDO → LIBERADO | `LIBERADO` | `POST /acessos` | `energia_mj: 18200`, `usuario_id: 1`, `tentativa: n` |
| VERIFICANDO → AGUARDANDO | `NEGADO` | `POST /acessos` | `energia_mj: 0`, `usuario_id: null`, `tentativa: 1 ou 2` |
| VERIFICANDO → BLOQUEADO | `BLOQUEADO` + alerta `BLOQUEIO` | `POST /acessos`, `POST /alertas` | `tentativa: 3` |
| BLOQUEADO → AGUARDANDO | alerta `DESBLOQUEIO_ADMIN` | `POST /alertas` | — |

`energia_mj = 18200` vem de [`docs/fisica.md`](../docs/fisica.md), seção 6: 3,53 W × 5,16 s. Senhas incorretas não são transmitidas — só o resultado.

Payload de `/acessos`:

```json
{"momento": "2026-09-16T11:37:23.010+00:00", "usuario_id": 1, "resultado": "LIBERADO", "tentativa": 2, "energia_mj": 18200}
```

`momento` é o instante da transição, em UTC. Se o evento ficar na fila offline, ele é reenviado com o `momento` original — a demanda horária da otimização não se distorce por uma queda de rede.

---

## Transporte

[`transporte.py`](lockwise_gateway/transporte.py):

- **Retry** em falha de conexão ou 5xx: 0,5 s → 1 s → 2 s. A API no free tier pode estar acordando.
- **Fila offline** (`fila_offline.jsonl`): esgotadas as tentativas, o evento vai para disco e é reenviado ao iniciar o gateway ou com o comando `fila`. Nenhum acesso se perde.
- **4xx não repete nem enfileira.** É defeito de contrato entre gateway e API; o operador precisa ver.
- Autenticação por `X-API-Key`, lida de variável de ambiente.

---

## Uso

```bash
cd gateway
python -m lockwise_gateway.cli                     # modo eco: imprime os POSTs, sem rede
```

```bash
export LOCKWISE_API_URL=https://lockwise-api.onrender.com
export LOCKWISE_API_KEY=...
python -m lockwise_gateway.cli --timeout-fisico   # TIMEOUT sozinho após 5,16 s, como o NE555
```

| Opção | Variável | Efeito |
|---|---|---|
| `--api-url` | `LOCKWISE_API_URL` | URL base da API. Sem ela, modo eco. |
| `--api-key` | `LOCKWISE_API_KEY` | Enviada em `X-API-Key` |
| `--fila` | `LOCKWISE_FILA` | Arquivo da fila offline (padrão `fila_offline.jsonl`) |
| `--roteiro arquivo` | — | Executa os comandos do arquivo em vez do teclado |
| `--timeout-fisico` | — | Dispara TIMEOUT automaticamente 5,16 s após LIBERADO |
| `--espera-acordar` | — | Segundos esperando a API acordar no arranque (padrão 60; `0` desliga) |

### Comandos

Cada um é um gesto na Poke Tool do Logisim:

```
senha 1011          define S3 S2 S1 S0
s3|s2|s1|s0 on|off  um bit de cada vez
confirma [on|off]   pino CONFIRMA (sem argumento: alterna)
timeout  [on|off]   pino TIMEOUT
reset    [on|off]   pino RESET
clk                 borda de subida do clock
```

Macros, para a demo andar no ritmo da conversa:

```
tentar 1011         senha + confirma on + clk + confirma off + clk
fechar              timeout on + clk + timeout off       LIBERADO -> AGUARDANDO
desbloquear         reset on + clk + reset off           BLOQUEADO -> AGUARDANDO
```

`estado` mostra pinos, estado, contador e saídas acesas; `fila` reenvia a fila offline; `acordar` chama `/health` até a API responder; `ajuda`; `sair`.

Apontando para uma API, o gateway acorda o serviço antes de aceitar comandos — o plano gratuito do Render hiberna e a primeira requisição pode levar 30 s (ADR 0023).

### Roteiro de ensaio

[`roteiros/demo.txt`](roteiros/demo.txt) percorre acesso liberado, três erros, bloqueio, tentativa com senha certa durante o bloqueio e desbloqueio administrativo:

```bash
python -m lockwise_gateway.cli --roteiro roteiros/demo.txt
```

---

## Testes

```bash
python -m pytest
```

| Arquivo | Cobre |
|---|---|
| `test_netlist.py` + `logisim.py` | o `.circ` lido e simulado ≡ `circuito.py` (2048 casos), estrutura do circuito |
| `test_equivalencia.py` | netlist ≡ State (2048 casos), saídas, sequências da simulação |
| `test_circuito.py` | comparador, bloqueio antecipado, saturação, reset |
| `test_maquina.py` | eventos por transição, energia, usuário, payloads |
| `test_transporte.py` | retry, backoff, fila, 4xx, reenvio, `ClienteEco` |
| `test_cli.py` | comandos, macros, roteiro, timeout físico, `main()` |

---

## Um caso de canto que o modelo revelou

Com RESET ligado **durante** a terceira tentativa incorreta, o circuito vai para BLOQUEADO com o contador em `00` (E é calculado sobre o contador *antes* da borda; CLR zera o contador *na* borda). É comportamento fiel ao hardware, coberto pela prova exaustiva, e sem efeito prático: RESET é um gesto administrativo que não ocorre no meio de uma tentativa. Fica registrado porque é o tipo de coisa que a sabatina pergunta.
