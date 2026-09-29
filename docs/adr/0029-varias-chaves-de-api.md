# ADR 0029 — A API aceita várias chaves de escrita

Data: 2026-09-29
Situação: aceita

## Contexto

A ADR 0016 estabeleceu uma chave única para as rotas de escrita, guardada no painel do Render e conhecida apenas pelo gateway. Isso funcionou enquanto o gateway era o único cliente que escrevia.

Ao avaliar um ESP32 simulado no Wokwi como ponte de hardware, apareceu um problema. No plano gratuito do Wokwi, todo projeto é público: a chave escrita no código do sketch fica visível para qualquer pessoa que abra o link. Com uma chave só, expor a do simulador é entregar acesso de escrita ao banco inteiro — inclusive ao histórico que alimenta o modelo de otimização.

Trocar a chave depois da demonstração resolveria, mas obrigaria a reconfigurar o gateway e qualquer outro cliente ao mesmo tempo, e deixaria a janela aberta enquanto o projeto estivesse publicado.

## Decisão

`LOCKWISE_API_KEY` passa a aceitar uma chave ou várias, separadas por vírgula. Qualquer uma delas autentica uma escrita.

Cada origem ganha a sua: o gateway tem uma, o simulador público tem outra. Revogar a do simulador é apagar aquele trecho da variável no painel — o gateway continua funcionando, e não há momento em que o sistema fique sem autenticação.

A comparação percorre todas as chaves configuradas **sem interromper na primeira que confere**. Sair do laço ao encontrar a chave certa faria o tempo de resposta depender de qual chave foi usada, e é exatamente esse vazamento que `secrets.compare_digest` existe para evitar.

## Alternativas que consideramos

Manter uma chave e trocá-la depois da demonstração: deixa a janela aberta enquanto o projeto está público, e obriga a reconfigurar todos os clientes de uma vez. O risco não é hipotético — a URL da API é pública e as rotas estão documentadas no Swagger.

Pagar o gateway privado do Wokwi, que permite projeto privado: resolve, custa dinheiro, e não ajuda em nenhum outro cliente que venha a existir.

Chaves com escopo — uma que só pode criar acessos, outra que também resolve alertas: seria o próximo passo natural, e é complexidade que o projeto ainda não precisa. Hoje todas as chaves têm o mesmo poder; o que muda é poder revogar uma sem tocar nas outras.

Tokens assinados com validade, tipo JWT: pelo mesmo motivo da ADR 0016 — um punhado de clientes com credencial fixa não justifica um fluxo de tokens.

## Consequências

Uma origem comprometida se revoga sozinha, em um campo de texto, sem parar o resto.

`Configuracao.api_key` continua existindo e devolve a primeira chave da lista, para quem só precisa saber se há alguma configurada — é o que o log de arranque usa. A configuração com chave única continua funcionando sem mudança nenhuma.

Passa a existir um cuidado operacional: uma chave esquecida na lista é uma porta aberta que ninguém lembra de ter deixado. Quando o projeto do Wokwi sair do ar, a chave dele deve sair da variável.
