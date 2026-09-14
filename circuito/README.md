# Circuito LOCKWISE

Arquivo principal: `lockwise_completo.circ`

## Requisitos

- Logisim-evolution 4.1.0 ou superior
- Java 21 (já embutido nos instaladores oficiais)

Download: https://github.com/logisim-evolution/logisim-evolution/releases

## Como abrir

1. Abra o Logisim-evolution
2. Arquivo → Abrir → selecione `lockwise_completo.circ`
3. No painel esquerdo, selecione o circuito `LOCKWISE`
4. Simular → Reiniciar Simulação

A luz AGUARDANDO deve estar acesa e todas as entradas em 0.

## Organização interna

O circuito usa **túneis nomeados** em vez de fiação longa. Componentes com o mesmo rótulo estão eletricamente conectados, o que mantém o diagrama legível e evita cruzamentos de fios.

Os blocos estão dispostos de cima para baixo: painel de entradas e saídas, comparador de senha, decodificação de estado, lógica de próximo estado, flip-flops da máquina de estados e, por último, o contador de tentativas.

## Verificação temporal

`Simular → Cronograma` permite observar as formas de onda. Os sinais relevantes são CLK, CONFIRMA, SENHA_OK, os quatro indicadores de estado e os dois bits do contador.

A evidência registrada em `docs/evidencias/fig14_diagrama.png` demonstra que todas as transições ocorrem nas bordas de subida do clock.
