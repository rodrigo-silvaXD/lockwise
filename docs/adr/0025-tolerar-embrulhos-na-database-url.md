# ADR 0025 — Tolerar os embrulhos que os painéis põem na string de conexão

Data: 2026-09-22
Situação: aceita

## Contexto

O primeiro deploy com o banco na Neon morreu no arranque:

```
sqlalchemy.exc.ArgumentError: Could not parse SQLAlchemy URL from given URL string
==> Exited with status 1
```

A causa é que o painel da Neon oferece a mesma string de conexão em vários formatos, e só um deles é uma URL pura. O formato `psql` vem como `psql 'postgresql://...'`. O formato `.env` vem como `DATABASE_URL='postgresql://...'`. Selecionar o texto com o mouse em vez de usar o botão de copiar traz a senha como `********`, porque o painel a esconde. Nenhum dos três é uma URL, e todos são o que uma pessoa apressada copia.

O erro que isso produzia não ajudava: um traceback de dentro do SQLAlchemy, sem mencionar qual variável estava errada nem o que fazer. Numa noite de véspera, é o tipo de coisa que custa uma hora.

## Decisão

`normalizar_url_banco` passa a limpar o embrulho antes de olhar o prefixo: remove um `psql ` inicial, remove um `DATABASE_URL=` inicial, remove aspas simples ou duplas em volta, e apara espaços e quebras de linha. Só então faz a troca de `postgres://` ou `postgresql://` para `postgresql+psycopg://`.

Se, depois disso, o texto não tiver `://`, o arranque falha com uma exceção própria que nomeia a variável, mostra o formato esperado, mostra os primeiros caracteres do que foi recebido — mascarando o resto, para não imprimir senha no log — e diz onde copiar a string certa.

## Alternativas que consideramos

Deixar o erro como estava e documentar no `docs/deploy.md`: a documentação já dizia para usar o botão de copiar, e mesmo assim erramos. Documentação não substitui uma mensagem de erro que aparece no momento em que a pessoa está olhando o log.

Aceitar apenas a URL pura e falhar rápido, mas com mensagem boa: era a opção mínima. Preferimos também aceitar os embrulhos, porque não há ambiguidade nenhuma no que a pessoa quis dizer ao colar `psql 'postgresql://...'` — rejeitar isso é rigor sem propósito.

Validar a URL montando o engine na hora, para pegar erros mais sutis (host errado, banco inexistente): isso transformaria uma falha de rede numa falha de arranque, e o serviço deixaria de subir por causa de um banco temporariamente fora do ar. O `/health` já reporta banco inacessível como `degradado` e devolve 503, que é o lugar certo para esse tipo de problema.

## Consequências

Três formatos do painel da Neon, mais os equivalentes do Render e do Heroku, passam a funcionar sem edição manual. Dezoito testes cobrem os casos, incluindo o de a mensagem de erro não vazar a senha inteira.

A função ficou mais longa do que "trocar um prefixo", e é código que existe por causa da interface de um fornecedor, não por causa do domínio do problema. É uma troca consciente: o custo é uma dúzia de linhas num lugar só; o benefício é não perder tempo com isso de novo em novembro.
