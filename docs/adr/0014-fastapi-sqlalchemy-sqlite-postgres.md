# ADR 0014 — FastAPI e SQLAlchemy; SQLite local, Postgres em produção

Data: 2026-09-16
Situação: aceita

## Contexto

O roteiro pede backend em Python ou Java, com banco gerenciado na nuvem. A equipe programa em Python. O backend tem seis rotas, precisa validar o contrato do gateway (ADR 0011), e a documentação da API precisa existir sem que alguém a escreva à mão.

Ninguém da equipe tem Postgres instalado na máquina, e não queríamos que isso fosse pré-requisito para rodar os testes.

## Decisão

FastAPI com Pydantic para as rotas e validação, SQLAlchemy 2 para o banco. Em desenvolvimento e nos testes, SQLite — em memória nos testes, em arquivo no uso local. Em produção, o Postgres gerenciado do Render. O mesmo código roda nos dois; a diferença é a `DATABASE_URL`.

As tabelas são criadas com `create_all` no arranque, e a semente do morador é inserida se não existir. Sem Alembic por enquanto.

## Alternativas que consideramos

Flask: mais manual em validação e documentação. O Pydantic do FastAPI valida o payload do gateway e gera o Swagger de graça; com Flask seriam duas bibliotecas a mais.

Django: um framework inteiro (admin, ORM próprio, sessões) para seis rotas. Desproporcional.

Java com Spring Boot: nenhum integrante usa Java no dia a dia; o custo de aprendizado comeria o prazo.

Alembic desde o início: é o padrão para migrações, mas o esquema tem três tabelas e ainda está nascendo. `create_all` mais uma semente idempotente resolve enquanto as mudanças forem só adição de coluna. Se aparecer uma migração incompatível (renomear, mudar tipo), adotamos Alembic naquele momento, com uma ADR nova.

Postgres local via Docker: funciona, mas adiciona Docker como pré-requisito para rodar os testes. SQLite roda em qualquer lugar em milissegundos.

## Consequências

Rodar os testes é `pytest`, sem serviço nenhum de pé. A suíte inteira, incluindo o teste ponta a ponta que sobe um servidor de verdade, leva menos de três segundos.

As diferenças entre SQLite e Postgres precisam ser tratadas no código, não escondidas. Duas apareceram: o SQLite descarta o fuso horário ao gravar datetimes (ADR 0019), e a agregação por hora com fuso não tem SQL portável entre os dois (ADR 0018).

`DATABASE_URL` do Render vem como `postgres://…`; o SQLAlchemy 2 exige `postgresql+psycopg://…`. A normalização está em `config.py`. O driver `psycopg[binary]` já está nas dependências, para que o primeiro deploy não falhe por falta dele.
