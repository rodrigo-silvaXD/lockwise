# ADR 0018 — Demanda horária em hora local, agregada em Python

Data: 2026-09-16
Situação: aceita

## Contexto

O modelo de otimização (Fase G) precisa da demanda por hora do dia: quantos acessos acontecem entre 8h e 9h, entre 9h e 10h, e assim por diante, para dimensionar a escala de vigilância. Vigilante trabalha em horário de gente, não em UTC. Às 22h30 em São Paulo são 01h30 UTC do dia seguinte; se agregássemos em UTC, a demanda das 22h apareceria na faixa da 1h da madrugada e a escala sairia errada.

Os timestamps são guardados em UTC (ADR 0019). A conversão precisa acontecer na hora de agregar.

## Decisão

`GET /acessos/demanda-horaria` devolve 24 faixas, sempre presentes (a otimização quer um vetor completo, com zeros onde não há demanda), em hora local do fuso configurado em `LOCKWISE_FUSO`, padrão `America/Sao_Paulo`. Cada faixa traz acessos, liberados, negados, bloqueados e a soma de `energia_mj`.

A agregação é feita em Python: o repositório devolve os acessos do período e o serviço os distribui nas faixas usando `zoneinfo`.

## Alternativas que consideramos

`GROUP BY EXTRACT(HOUR FROM momento)` em SQL: o SQLite não tem fuso; o Postgres tem `AT TIME ZONE`. O SQL seria diferente nos dois bancos, e os testes (em SQLite) não testariam o que roda em produção (Postgres). Uma função Python é a mesma nos dois.

Agregar em UTC e deixar o cliente converter: empurra a complexidade para quem consome, e cada consumidor faria diferente.

Guardar o momento já em hora local: perde a referência absoluta, e o horário de verão (se voltar) tornaria alguns instantes ambíguos.

## Consequências

Os acessos do período consultado são carregados em memória. Para o volume deste projeto — algumas centenas de eventos numa semana de testes, talvez alguns milhares até novembro — é irrelevante. Se um dia fosse um condomínio com milhões de eventos, a agregação migraria para SQL no Postgres, e esta ADR seria substituída.

O fuso é configurável para que o mesmo backend sirva outro lugar. A janela horária da política de supervisão (ADR 0015) usa o mesmo fuso, pelo mesmo motivo.
