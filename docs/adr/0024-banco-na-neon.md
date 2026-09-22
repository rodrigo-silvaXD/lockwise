# ADR 0024 — Postgres na Neon, aplicação no Render

Data: 2026-09-22
Situação: aceita (substitui a parte de banco de dados da ADR 0013)

## Contexto

Ao criar o blueprint no Render, o provisionamento falhou:

```
Create database lockwise-db
(cannot have more than one active free tier database)
Create web service lockwise-api
(canceled: another action failed)
```

O Render permite um único Postgres gratuito por conta, e a conta já tinha um, de outro projeto. O web service foi cancelado em cascata porque dependia do banco.

Três saídas apareceram: apagar o banco antigo, dividir o banco antigo entre os dois projetos, ou buscar o Postgres em outro provedor.

## Decisão

O banco vai para a Neon; a aplicação continua no Render.

A Neon é Postgres gerenciado, com plano gratuito, e a equipe já a usa em outro projeto — não é uma ferramenta nova para aprender na véspera. O requisito de cloud pede "banco de dados gerenciado", sem exigir que seja do mesmo provedor da aplicação; separar aplicação e banco é, aliás, o arranjo comum em produção.

No `render.yaml`, o bloco `databases` deixou de existir e a `DATABASE_URL` virou uma variável com `sync: false`: o valor é colado uma vez no painel do Render e o blueprint não o sobrescreve nos deploys seguintes.

## Alternativas que consideramos

Apagar o Postgres gratuito antigo do Render: resolveria em dois cliques e manteria tudo num provedor só. Descartado porque apagar é irreversível e o banco pertence a outro projeto do autor; não vale arriscar dados alheios ao LOCKWISE para economizar uma configuração.

Reusar o banco do outro projeto, com as tabelas do LOCKWISE convivendo com as dele: funcionaria — os nomes `usuario`, `acesso` e `alerta` provavelmente não colidem —, mas mistura dois sistemas no mesmo banco, e um `create_all` distraído em qualquer um dos dois passa a ser um risco para o outro.

Supabase ou Aiven: também dão Postgres gratuito, mas seriam um provedor a mais para a equipe conhecer. A Neon já está na casa.

## Consequências

Um efeito colateral bom: o plano gratuito da Neon não expira em noventa dias, ao contrário do Postgres gratuito do Render. O risco registrado na ADR 0013 — o banco vencer entre a criação e o evento de 28/11 — deixa de existir. A Neon suspende o projeto por inatividade e o retoma na primeira conexão, com atraso de menos de um segundo.

A configuração ganhou um passo manual: colar a string de conexão no painel do Render. Está documentado em `docs/deploy.md`. É o preço de não ter o banco declarado no mesmo blueprint.

A string da Neon vem com `?sslmode=require`, e às vezes `channel_binding=require`. A normalização em `config.py` preserva a query ao trocar o prefixo para `postgresql+psycopg://`, e o psycopg entende os dois parâmetros. Verificado antes do deploy.

A ADR 0013 continua valendo para a escolha do Render como provedor da aplicação e para o raciocínio sobre AWS, GCP e Azure. Só a parte de banco foi substituída por esta.
