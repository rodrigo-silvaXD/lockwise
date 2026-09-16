# ADR 0019 — Timestamps sempre em UTC explícito

Data: 2026-09-16
Situação: aceita

## Contexto

O gateway envia `momento` como ISO 8601 com fuso (`2026-09-16T11:37:23.010+00:00`). O SQLAlchemy grava. O SQLite, que não tem tipo de data com fuso, guarda a string sem o `+00:00`. Ao ler de volta, o datetime vem "ingênuo" — sem informação de fuso — e a API respondia `2026-09-16T11:37:23` em vez de `2026-09-16T11:37:23Z`.

Um teste que comparava o momento enviado com o recebido pegou isso. No Postgres, com `TIMESTAMPTZ`, o problema não existiria — mas os testes rodam em SQLite, e queríamos o mesmo comportamento nos dois.

## Decisão

Toda datetime que entra na API é normalizada para UTC na validação: se vier com fuso, é convertida; se vier sem, é tratada como UTC. Toda datetime que sai passa por um validador de saída que garante o fuso UTC. O resultado é que as respostas sempre terminam em `Z`, em qualquer banco.

Internamente, o domínio usa uma função `utc()` para o mesmo fim, de modo que a projeção de estado e as políticas nunca comparam um datetime com fuso contra um sem (o que em Python levanta exceção).

## Alternativas que consideramos

Confiar no Postgres e ignorar o SQLite: os testes não pegariam regressões, e o comportamento local seria diferente do de produção.

Armazenar como string ISO: resolve a serialização mas perde ordenação e filtro por período no banco.

Tratar datetime sem fuso como hora local: ambíguo; um cliente que enviasse sem fuso poderia ter qualquer intenção. UTC é a única convenção que não depende de onde o servidor está.

## Consequências

Clientes nunca precisam adivinhar o fuso de uma resposta. O fuso humano é aplicado só onde interessa: na demanda horária (ADR 0018) e na janela horária da política de supervisão.

A convenção "sem fuso significa UTC" está documentada no esquema de entrada e testada. Um cliente que enviar hora local sem fuso vai ter o evento registrado com três horas de diferença; é o preço de uma regra simples, e o gateway, que é o único cliente de escrita, sempre envia com fuso.
