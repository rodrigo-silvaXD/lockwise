# ADR 0032 — Trava comandada pelo temporizador, com TLC555

Data: 2026-11-15
Situação: aceita (revê o temporizador e o comando da trava da ADR 0006)

## Contexto

A ADR 0006 definiu a implementação física de referência com um NE555 gerando o TIMEOUT e com a saída `TRAVA_ABERTA` ligada direto à base do BC337. Ao desenhar o circuito completo, peça por peça, encontramos três problemas.

O primeiro é o tempo de abertura. A bobina ficava energizada enquanto a máquina estivesse em LIBERADO, e a máquina só sai de LIBERADO no pulso de clock seguinte ao TIMEOUT. Como o clock é acionado à mão, a trava podia ficar ligada por segundos ou minutos além dos 5,16 s. Esse tempo entra na energia por liberação que gravamos em cada acesso (ADR 0007), então o número dependia de quando alguém apertasse o botão.

O segundo é o nível de sinal. A saída alta do NE555 bipolar, alimentado em 5 V, fica entre 3,3 e 3,6 V, no limite dos 3,5 V que uma entrada 74HC exige para ler 1.

O terceiro é que o memorial não dizia como o 555 é disparado, e a contagem de chaves com pull-down incluía o TIMEOUT, que no hardware não é chave.

## Decisão

Ligamos a base do transistor à porta AND de três entradas que sobra no segundo 74HC11, com Q1, Q̄0 e a saída do temporizador: a bobina recebe corrente só em LIBERADO **e** enquanto o temporizador conta. A trava fica energizada exatamente 5,16 s, qualquer que seja o momento do próximo pulso de clock.

Trocamos o NE555 pelo TLC555, a versão CMOS do mesmo circuito, cuja saída chega praticamente a 5 V. A equação T = RC·ln 3 não muda.

Disparamos o 555 com o inverso de LIBERADO · CLK, usando a AND de duas entradas que sobra no quarto 74HC08 e um inversor do 74HC14. O pulso de clock que leva a máquina a LIBERADO ainda está alto quando o estado muda, e isso basta para o disparo. Outro inversor do 74HC14 entrega o TIMEOUT. Um capacitor de 10 nF no pino 5 protege a referência interna de 2/3·V_CC.

O memorial de física (seções 1.2, 2.2, 4.2, 5 e 7) passa a descrever esse arranjo.

## Alternativas que consideramos

Manter o NE555 e ler a saída através de um Schmitt-trigger 74HC14: resolve o nível de sinal, mas não resolve o tempo de abertura, e o NE555 consome cerca de 3 mA em repouso contra 0,2 mA do TLC555.

Disparar o 555 por um derivador RC a partir de `TRAVA_ABERTA`: cria um pulso curto na entrada em LIBERADO, mas na saída de LIBERADO empurra o pino de disparo para cerca de 10 V, acima da alimentação, e exigiria um diodo de grampo e um resistor em série. As portas que sobram nos CIs fazem o mesmo trabalho sem componentes novos.

Gerar o clock automaticamente: faria a máquina sair de LIBERADO sozinha, mas mudaria a operação manual do circuito, que é o que a simulação no Logisim reproduz (ADR 0005).

## Consequências

A energia por liberação da ADR 0007, 18 200 mJ, passa a valer por construção: o tempo de bobina ligada é o do temporizador, e não o do operador.

Nenhum CI de lógica é acrescentado. Usamos duas portas que já sobravam e dois dos seis inversores do 74HC14.

O TIMEOUT deixa de contar como chave: são 6 chaves com pull-down, que consomem 3,0 mA quando fechadas, e o barramento de 5 V cai de 56 para 52 mA no pior caso.

O LED de TRAVA_ABERTA continua mostrando o estado LIBERADO até o próximo pulso de clock, mesmo com a bobina já desligada. Se o botão de clock ficar apertado por mais de 5,16 s na entrada em LIBERADO, a trava só fecha quando ele for solto.
