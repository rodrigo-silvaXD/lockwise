# ADR 0020 — Teste ponta a ponta como demonstração automatizada

Data: 2026-09-16
Situação: aceita

## Contexto

Funcionar ao vivo vale 35% da nota. A demonstração envolve três programas (Logisim, gateway, API), uma rede e um banco. Ensaiar tudo à mão a cada mudança de código é lento e as pessoas param de fazer. E o contrato entre gateway e backend (ADR 0011) é o tipo de coisa que quebra em silêncio quando alguém muda um nome de campo de um lado só.

Os testes unitários do gateway e do backend usam clientes HTTP falsos. Provam que cada lado faz o que promete, mas não que os dois conversam de verdade.

## Decisão

Um teste no backend, `tests/test_ponta_a_ponta.py`, sobe a API real com uvicorn num porto livre e SQLite em arquivo, importa o gateway real de `../gateway`, executa o roteiro de ensaio da demonstração (`roteiros/demo.txt`) contra a API pela rede, e depois verifica pelas rotas de leitura que tudo o que o circuito faria está no banco: quatro acessos com os resultados e tentativas certos, três alertas (dois do gateway e um da política de supervisão, ligado ao acesso que o gerou), a energia da física na faixa horária certa, e a fechadura de volta a AGUARDANDO depois do desbloqueio.

## Alternativas que consideramos

Testar o contrato com um esquema compartilhado (JSON Schema, OpenAPI) validado dos dois lados: verifica a forma do payload, não o comportamento — não pegaria, por exemplo, o gateway enviando o momento errado ou a API contando a energia duas vezes.

Ensaio manual com checklist: continua existindo (é o `roteiros/demo.txt` rodado por uma pessoa com o Logisim ao lado), mas não substitui uma verificação que roda em dois segundos a cada commit.

Mocks nos dois lados: é o que os testes unitários já fazem. O ponta a ponta existe justamente para não ter mock em lugar nenhum.

## Consequências

Qualquer mudança que quebre o contrato, de qualquer lado, aparece no mesmo `pytest`. O teste leva cerca de dois segundos.

Ele depende da pasta `gateway/` estar ao lado de `backend/` no repositório; se não estiver, é pulado com aviso, não falha. No CI, os dois estão.

A demonstração ganhou um ensaio reproduzível: se o teste passa, o que falta para a apresentação é o Logisim na tela ao lado. Se algum dia falhar, é o primeiro lugar para olhar antes da avaliação.
