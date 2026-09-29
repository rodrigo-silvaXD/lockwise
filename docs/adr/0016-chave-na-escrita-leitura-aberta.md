# ADR 0016 — Chave só na escrita; leitura aberta; sem chave, 503

Data: 2026-09-16
Situação: aceita

## Contexto

Quem escreve na API é o gateway, e só ele. Quem lê é o painel (que virá depois, no navegador), o módulo de otimização e, na avaliação, o professor olhando o Swagger. O requisito de cloud fala em "variáveis de ambiente seguras", o que inclui não deixar segredo no código.

## Decisão

As rotas de escrita (`POST /acessos`, `POST /alertas`, `PATCH /alertas/{id}/resolver`) exigem o cabeçalho `X-API-Key` com o valor de `LOCKWISE_API_KEY`. A comparação é em tempo constante. As rotas de leitura são abertas.

Se a variável não estiver configurada no servidor, a escrita responde 503, não 401 e não 201. Falha fechada: sem chave, não se aceita nada. E é um 5xx de propósito — o gateway trata 5xx como temporário e guarda o evento na fila (ADR 0012). Se a chave sumir do painel do Render por engano, os eventos ficam esperando em disco em vez de serem descartados.

## Alternativas que consideramos

JWT ou OAuth: um único cliente com uma única credencial não justifica um fluxo de tokens. Seria complexidade para a sabatina explicar sem ganho.

Chave em tudo, leitura inclusive: o painel roda no navegador, e uma chave no JavaScript é uma chave pública. Ou teríamos duas chaves (uma de leitura, uma de escrita), o que é a mesma coisa que leitura aberta com mais passos.

Sem chave configurada, aceitar tudo (modo desenvolvimento): conveniente localmente, perigoso em produção — um esquecimento na configuração e a API vira um endpoint público de escrita. Preferimos exigir `LOCKWISE_API_KEY=dev` até para rodar local.

HTTP Basic: funciona, mas o gateway teria usuário e senha para uma coisa só. `X-API-Key` é mais direto e é o que a ferramenta Swagger espera.

## Consequências

Os dados de acesso — horários de entrada de um morador fictício — são legíveis por quem tiver a URL. Para o projeto acadêmico, com um usuário inventado e a URL conhecida só pela equipe e pelo avaliador, é aceitável. Se isso virasse produto, a leitura precisaria de autenticação, e essa ADR seria substituída.

A chave do gateway e a chave da API são a mesma string, configurada dos dois lados por variável de ambiente. Não está em nenhum arquivo versionado; `.env.example` mostra o nome, não o valor.
