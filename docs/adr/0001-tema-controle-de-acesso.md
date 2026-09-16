# ADR 0001 — Tema: sistema de controle de acesso

Data: 2026-09-11 (inscrição), registrada em 2026-09-14
Situação: aceita

## Contexto

O roteiro da categoria INTERFACE sugere três temas dentro de "Smart Home 2050": estação de monitoramento ambiental com otimização do intervalo de leitura, sistema de controle de acesso com backend em nuvem e otimização de escala de segurança, e painel de energia residencial com circuito de leitura de consumo. A inscrição fechou em 11/09 e, a partir daí, tema e equipe não mudam mais.

O requisito de eletrônica aceita circuito simulado. Isso pesou na escolha, porque a equipe não tinha bancada nem componentes garantidos para o dia da avaliação.

## Decisão

Controle de acesso.

Dos três, é o único que é inteiramente digital. Senha, comparação, máquina de estados, contador de tentativas: tudo isso se descreve com portas lógicas e flip-flops e se simula por completo no Logisim. Os outros dois temas partem de uma grandeza analógica (temperatura, corrente elétrica) que precisa de um sensor real ou de um simulador analógico. Sem isso, o "sensor" vira um número digitado, e a demonstração ao vivo fica com cara de protótipo fictício, que o regulamento pune com zero no quesito de funcionalidade.

## Alternativas que consideramos

Estação ambiental: exigiria Proteus para simular o sensor analógico, ou um Arduino físico com sensor de verdade. Nenhuma das duas era garantida.

Painel de energia: a "leitura de consumo" é uma medição de corrente; mesmo problema, e ainda mais difícil de mostrar funcionando de forma convincente numa tela.

## Consequências

O circuito lógico não tem nenhum componente analógico. A parte de "eletrônica analógica" do requisito e toda a disciplina de física precisam ser cobertas pelo que está em volta do circuito lógico — o acionamento da trava, os indicadores, o temporizador. Isso deu origem à implementação física de referência (ADR 0006).

O fio condutor do projeto ficou natural: um evento de acesso nasce no circuito, atravessa o gateway, é guardado na nuvem e alimenta a otimização da escala de vigilância. Os outros temas exigiriam mais esforço para encadear as cinco disciplinas com um único dado.
