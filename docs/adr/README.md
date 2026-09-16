# Registros de decisão de arquitetura

Cada arquivo desta pasta registra uma decisão que moldou o LOCKWISE: o que estava em jogo, o que escolhemos, o que descartamos e o que isso nos custa. Servem para a equipe lembrar o porquê das coisas e para a sabatina, onde "por que vocês fizeram assim?" é a pergunta mais provável.

Regras que seguimos:

- Uma decisão por arquivo, numerado na ordem em que foi tomada.
- Uma ADR não é reescrita depois de aceita. Se mudarmos de ideia, nasce uma nova que substitui a antiga, e a antiga recebe a situação "substituída pela NNNN".
- A ADR é escrita quando a decisão é tomada, ou logo depois, no mesmo commit do código que ela justifica.
- Situações possíveis: proposta, aceita, substituída.

## Índice

| Nº | Decisão | Fase | Situação |
|---|---|---|---|
| [0001](0001-tema-controle-de-acesso.md) | Tema: sistema de controle de acesso | inscrição | aceita |
| [0002](0002-logisim-evolution-em-vez-de-proteus.md) | Logisim-evolution desktop em vez de Proteus | eletrônica | aceita |
| [0003](0003-portas-e-flip-flops-discretos.md) | Circuito com portas e flip-flops discretos, sem componentes prontos | eletrônica | aceita |
| [0004](0004-bloqueio-antecipado-e-contador-saturado.md) | Bloqueio antecipado e contador saturado | eletrônica | aceita |
| [0005](0005-maquina-de-estados-sincrona.md) | Máquina de estados síncrona | eletrônica | aceita |
| [0006](0006-implementacao-fisica-de-referencia.md) | Implementação física de referência: 74HC, BC337, 1N4007, NE555 | física | aceita |
| [0007](0007-energia-por-liberacao-como-constante.md) | Energia por liberação como constante do sistema | física | aceita |
| [0008](0008-gateway-como-gemeo-digital.md) | Gateway como gêmeo digital, não integração com o Logisim | gateway | aceita |
| [0009](0009-equivalencia-provada-contra-o-circ.md) | Equivalência provada por teste, contra o arquivo .circ | gateway | aceita |
| [0010](0010-gateway-sem-dependencias.md) | Gateway sem dependências externas | gateway | aceita |
| [0011](0011-contrato-de-eventos.md) | Contrato de eventos: só transições, senhas não transmitidas | gateway | aceita |
| [0012](0012-entrega-resiliente.md) | Entrega resiliente: retry, fila offline, momento preservado | gateway | aceita |
| [0013](0013-render-como-provedor-de-nuvem.md) | Render como provedor de nuvem | nuvem | proposta |
| [0014](0014-fastapi-sqlalchemy-sqlite-postgres.md) | FastAPI e SQLAlchemy; SQLite local, Postgres em produção | backend | aceita |
| [0015](0015-tres-padroes-gof.md) | Três padrões GoF, cada um com um trabalho real | backend | aceita |
| [0016](0016-chave-na-escrita-leitura-aberta.md) | Chave só na escrita; leitura aberta; sem chave, 503 | backend | aceita |
| [0017](0017-eventos-inconsistentes-aceitos.md) | Eventos inconsistentes são aceitos e anotados | backend | aceita |
| [0018](0018-demanda-horaria-em-hora-local.md) | Demanda horária em hora local, agregada em Python | backend | aceita |
| [0019](0019-timestamps-em-utc-explicito.md) | Timestamps sempre em UTC explícito | backend | aceita |
| [0020](0020-teste-ponta-a-ponta-como-demo.md) | Teste ponta a ponta como demo automatizada | backend | aceita |
| [0021](0021-commit-por-passo-e-adrs.md) | Commit e push a cada passo; ADRs junto do código | processo | aceita |

## Modelo para uma ADR nova

```
# ADR NNNN — Título curto, no infinitivo ou como afirmação

Data: AAAA-MM-DD
Situação: proposta | aceita | substituída pela NNNN

## Contexto
O problema, as restrições, o que estava em jogo. Fatos, não opinião.

## Decisão
O que escolhemos, em uma ou duas frases. Depois o raciocínio.

## Alternativas que consideramos
Cada uma com o motivo de ter sido descartada.

## Consequências
O que ganhamos e o que passamos a carregar. As negativas também.
```
