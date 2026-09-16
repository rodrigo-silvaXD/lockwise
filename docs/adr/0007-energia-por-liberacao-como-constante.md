# ADR 0007 — Energia por liberação como constante do sistema

Data: 2026-09-16
Situação: aceita

## Contexto

O projeto cruza cinco disciplinas com um único dado, o evento de acesso. Queríamos que a física deixasse uma marca concreta nesse dado — um número que nascesse de um cálculo e chegasse até a otimização — em vez de ficar num documento à parte que ninguém consulta.

O documento de contexto trazia "≈ 18,4 J" como estimativa, sem cálculo.

## Decisão

Cada acesso com resultado LIBERADO carrega `energia_mj = 18200`. Os demais (NEGADO, BLOQUEADO) carregam zero, porque a trava não é acionada.

O valor vem do memorial de física: a fonte de 12 V entrega 292,5 mA à bobina (com 0,3 V perdidos no transistor saturado) e a fonte de 5 V entrega 4,3 mA à base; somados, 3,53 W. A trava fica aberta pelo tempo do NE555, 5,16 s. O produto é 18,2 J. Os 4,3 mJ de energia magnética da bobina e o LED de TRAVA_ABERTA cabem no arredondamento.

A constante mora no gateway (`lockwise_gateway/eventos.py`), com o comentário apontando a seção do memorial. O backend não recalcula: guarda o que recebe.

## Alternativas que consideramos

Calcular a energia no backend a partir de uma duração medida: o backend não sabe quanto tempo a trava ficou aberta, porque o gateway não envia TIMEOUT (ADR 0011). E a duração é fixa por construção — é um monoestável.

Não registrar energia e deixar a física só no documento: perde o fio condutor. A frase "a energia registrada em cada acesso é 12 volts vezes 292 miliamperes vezes 5,16 segundos, e cada fator tem um cálculo" vale mais na sabatina do que qualquer tabela.

## Consequências

`GET /acessos/demanda-horaria` soma a energia por faixa horária, e o modelo de otimização pode incluir custo energético além do custo de vigilância.

Se a física mudar — outra trava, outro tempo de abertura — a constante muda em um único lugar. Os eventos já gravados continuam com o valor da época, o que é o comportamento certo para um histórico.

O 18,4 J antigo foi substituído em todos os documentos.
