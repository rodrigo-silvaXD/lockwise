# ADR 0005 — Máquina de estados síncrona

Data: 2026-09-14
Situação: aceita

## Contexto

A fechadura poderia reagir na hora: CONFIRMA ligado, senha comparada, trava aberta, sem clock. Seria um circuito assíncrono, com menos gestos na demonstração e sem o pino CLK.

## Decisão

Todas as transições acontecem na borda de subida de CLK. As entradas (senha, CONFIRMA, TIMEOUT, RESET) são apenas amostradas nessa borda; entre uma borda e outra, podem mudar à vontade sem efeito.

O motivo principal é previsibilidade. Num circuito assíncrono, a ordem em que os sinais se propagam pelas portas determina o resultado, e um pulso espúrio de nanossegundos numa entrada (um glitch de lógica combinacional, o ricochete de uma chave) pode avançar a máquina ou o contador. No projeto síncrono, nada disso importa: só o que está estável no instante da borda é lido.

## Alternativas que consideramos

Projeto assíncrono: menos um pino, demonstração mais fluida. Descartado porque o contador de tentativas seria a primeira vítima — cada ricochete mecânico do CONFIRMA contaria como uma tentativa, e o bloqueio viria sem motivo.

Clock automático (componente Clock do Logisim a alguns hertz): a máquina avançaria sozinha e o operador não teria controle do passo a passo. Para a demonstração e para as capturas de evidência, o clock manual é melhor: cada borda é um gesto deliberado, e cada figura mostra um estado estável.

## Consequências

A operação tem mais gestos: ligar CONFIRMA, pulsar CLK, desligar CONFIRMA, pulsar CLK. O README documenta a sequência e o gateway oferece macros que a reproduzem.

Três coisas ficaram mais simples por causa desta escolha. Na física, só o clock precisa de tratamento de sinal (debounce); as demais entradas dispensam filtro porque são amostradas com a chave já estável. Na análise de temporização, glitches na lógica combinacional são irrelevantes porque se extinguem centenas de milhares de vezes antes da próxima borda. E no gateway, uma borda de clock é uma chamada de função — próximo estado é função de (estado atual, entradas) — o que é o que torna possível varrer todas as combinações e provar equivalência com o circuito.
