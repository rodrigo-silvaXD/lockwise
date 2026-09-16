# ADR 0013 — Render como provedor de nuvem

Data: 2026-09-14 (proposta), a confirmar no deploy
Situação: proposta

## Contexto

O requisito de cloud pede deploy real em nuvem pública, banco de dados gerenciado, variáveis de ambiente seguras e pipeline de CI/CD. O roteiro cita AWS, GCP e Azure em camada gratuita, mas "camada gratuita" nesses três exige cartão de crédito no cadastro e uma configuração inicial (IAM, VPC, grupos de segurança) que consome dias. A equipe não tem cartão corporativo e tem oito semanas para cinco disciplinas.

## Decisão (proposta)

Render: um web service Python conectado ao repositório do GitHub, com deploy automático a cada push na `main`, e um Postgres gerenciado no plano gratuito. Segredos (chave da API, URL do banco) ficam no painel do Render, nunca no repositório.

O GitHub Actions roda os testes a cada push; o deploy só acontece se os testes passarem.

## Alternativas que consideramos

AWS, GCP, Azure: exigem cartão e a curva de configuração é incompatível com o prazo. Seriam a escolha se o projeto fosse continuar depois da ExpoTech.

Railway: já foi gratuito sem cartão; hoje o plano gratuito é um crédito limitado que pode acabar antes de novembro.

Fly.io: pede cartão para sair do modo de avaliação.

Heroku: não tem plano gratuito desde 2022.

Vercel: bom para front, mas o backend seria serverless — o SQLAlchemy com pool de conexões e o `create_all` no arranque não combinam com funções efêmeras.

## Consequências

O plano gratuito hiberna o serviço após alguns minutos sem tráfego, e a primeira requisição depois disso demora de dez a trinta segundos. O retry do gateway (ADR 0012) cobre isso; mesmo assim, vale acordar a API antes da demonstração começar.

O Postgres gratuito do Render expira 90 dias depois de criado. A avaliação é de 09 a 13/11 e o evento em 28/11; criando o banco em meados de setembro, ele vale até meados de dezembro. Se for criado antes disso, é preciso recriar e reapontar.

A situação desta ADR muda para "aceita" quando a API estiver no ar e o pipeline verde.
