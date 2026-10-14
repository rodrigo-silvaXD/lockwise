# ADR 0029 — Teto na versão maior do PuLP

Data: 2026-10-14
Situação: aceita

## Contexto

O `pyproject.toml` do módulo de otimização pedia `pulp>=2.8`, sem teto. Em 29 de setembro o PuLP 4.0 foi publicado, a instalação limpa do CI resolveu para ele, e o pipeline quebrou:

```
AttributeError: module 'pulp' has no attribute 'PULP_CBC_CMD'
```

Três coisas mudaram na versão 4. O `PULP_CBC_CMD` foi removido em favor do `COIN_CMD`; o solver passou a depender do extra `pulp[cbc]`, que não estava declarado; e o pacote importa `numpy` sem declarar essa dependência, então mesmo instalando o extra o import falha numa máquina limpa.

A função que escolhe o solver já previa a troca de nome, mas com a lógica invertida: tentava o `COIN_CMD` e **caía** no `PULP_CBC_CMD` por acesso direto ao atributo. Quando o nome deixou de existir, o fallback levantou exceção em vez de ser pulado — o caminho de recuperação virou o caminho da falha.

O efeito foi pior do que um teste vermelho. O pipeline barra o deploy, então a remoção da ponte em ESP32, enviada em 29 de setembro, nunca chegou à produção: a API ficou duas semanas rodando um commit anterior sem que ninguém percebesse.

## Decisão

Fixamos `pulp>=2.8,<4`.

Nada no modelo precisa do que a versão 4 trouxe. O que ela trouxe de concreto, para este projeto, foi uma dependência não declarada e um solver que exige configuração extra — a quatro semanas da avaliação.

A escolha do solver também foi corrigida: os dois nomes são procurados com `getattr`, nunca por acesso direto, e quando nenhum funciona o erro diz qual versão do PuLP está instalada e qual comando instala a faixa suportada. Dois testes removem cada nome por vez e exigem que o resultado seja ou uma escala válida ou `SemSolucao` — nunca `AttributeError`.

## Alternativas que consideramos

Migrar para o PuLP 4: declarar `pulp[cbc]`, adicionar `numpy` e adaptar ao `COIN_CMD`. É o caminho certo em outro momento. Hoje significaria depender de uma release de duas semanas, com um defeito de empacotamento confirmado, numa parte do projeto que já está pronta e verificada.

Deixar sem teto e corrigir quando quebrar: foi o que estava em vigor, e o custo apareceu — duas semanas de produção desatualizada. Uma dependência sem teto é uma aposta de que ninguém vai publicar uma versão incompatível antes da entrega.

Fixar a versão exata (`==3.3.2`): protege mais e impede correções de bugs dentro da faixa 3.x. O teto na versão maior é o equilíbrio usual.

## Consequências

A instalação limpa volta a resolver para a 3.3.2, que é a versão com que todo o modelo foi desenvolvido e verificado — incluindo o teste que confere por força bruta que o solver achou o ótimo.

Em algum momento a faixa 3.x deixará de receber correções e a migração para a 4 será necessária. Quando for, o caminho está descrito aqui: declarar o extra `[cbc]`, acrescentar `numpy`, e confirmar que `COIN_CMD` fica disponível no runner do CI, que é onde isso importa.

A lição de processo é mais ampla que o PuLP: **enviar o commit não é o mesmo que entregar**. Rodar os testes na máquina local e empurrar não garante nada enquanto o pipeline não fecha o ciclo. Passamos a conferir o CI depois de cada push, e não só a suíte local.
