# ADR 0027 — Histórico sintético gerado pela máquina de estados e enviado pela API real

Data: 2026-09-22
Situação: aceita

## Contexto

O modelo de escala precisa de demanda nas 24 horas do dia. O banco, na véspera desta fase, tinha quatro acessos — todos gravados às 11h de um mesmo dia, durante os testes do deploy. Com esse histórico, o modelo responderia "um vigilante às 11h e ninguém no resto do dia", o que não demonstra nada.

Havia três caminhos: operar o circuito e o gateway diariamente até novembro acumulando dados reais; escrever a demanda como uma tabela de 24 números dentro do módulo de otimização; ou gerar histórico sintético.

## Decisão

Gerar histórico sintético, com duas regras que separam isso de inventar números.

A primeira: os eventos nascem da **máquina de estados do gateway**, importada do módulo vizinho. O gerador aciona os mesmos pinos — liga CONFIRMA, pulsa o clock, desliga, pulsa de novo — e os eventos saem da mesma função que os produz na operação real. Por isso o campo `tentativa` conta certo, o `energia_mj` traz os 18 200 mJ só nas liberações, o bloqueio acontece no terceiro erro e o desbloqueio administrativo aparece depois dele. Nada disso precisou ser reproduzido à mão, porque quem produz é o circuito replicado.

A segunda: os eventos são entregues pela **API de produção**, com a mesma chave e o mesmo cliente HTTP que o gateway usa, passando pelas mesmas validações e pela mesma política de supervisão. O modelo depois lê a demanda de `GET /acessos/demanda-horaria` sem saber de onde os dados vieram.

A única coisa que difere da operação real é o relógio: em vez de esperar sete dias, os eventos são carimbados com datas passadas.

O perfil é o de uma portaria de condomínio de cerca de cinquenta unidades — pico ao sair de manhã e ao voltar à noite, madrugada parada, fim de semana mais espalhado —, com a quantidade de acessos de cada hora sorteada de uma distribuição de Poisson. A semente é fixa, então o resultado é reprodutível.

## Alternativas que consideramos

Esperar dados reais: seria o ideal, e é o que uma equipe faria com meses disponíveis. Exigiria alguém operando circuito e gateway todo dia até novembro, e ainda assim não cobriria madrugadas nem fins de semana. Continua valendo como complemento — os acessos reais que forem acontecendo entram no mesmo banco e no mesmo modelo.

Tabela fixa de 24 números no código: mais simples, e quebraria o fio condutor do projeto. O modelo deixaria de consumir o histórico e viraria um exercício isolado, exatamente o tipo de coisa que o regulamento chama de protótipo fictício.

Gerar os eventos escrevendo JSON direto no banco: rápido, e perderia as duas garantias acima. Um `tentativa` errado ou uma sequência impossível passariam despercebidos.

## Consequências

A resposta honesta para "esses dados são reais?" é: não, são simulados, e o relatório diz isso. Mas eles atravessam o mesmo caminho que um acesso real percorre — mesma máquina de estados, mesma API, mesmo banco — e o modelo não distingue uns dos outros.

O banco de produção passa a conter cerca de mil eventos sintéticos misturados com os poucos reais. Para este projeto isso é desejável; num sistema de verdade, dados semeados em produção precisariam de marcação.

O cenário passou a ser explicitamente o de uma portaria de condomínio, e não de uma porta residencial. Uma residência gera poucas passagens por dia, e ninguém escala seis turnos de vigilância para ela. O circuito demonstra o controle de um ponto de acesso com uma senha; a tabela `usuario` do banco já modela vários moradores.
