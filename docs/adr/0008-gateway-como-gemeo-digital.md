# ADR 0008 — Gateway como gêmeo digital, não integração com o Logisim

Data: 2026-09-16
Situação: aceita

## Contexto

O circuito roda no Logisim e a nuvem precisa receber cada evento de acesso, ao vivo, na frente do avaliador. O Logisim não fala HTTP, não grava arquivo com o estado da simulação e não tem API. Procuramos um caminho e não existe nenhum suportado.

Ao mesmo tempo, o regulamento dá 35% da nota para "funcionar ao vivo" e avisa que "só slides ou protótipo fictício zera o quesito". Uma demonstração com o Logisim numa tela e um print da API na outra, sem nada que as ligue, corre esse risco.

## Decisão

O gateway é a mesma máquina de estados do circuito, escrita em Python. O operador aciona os mesmos pinos nos dois lados — no Logisim com a Poke Tool, no gateway com comandos que têm o mesmo nome — e o gateway, ao transitar de estado, envia o evento para a nuvem.

O que faz isso não ser "duas telas separadas" é a prova de equivalência (ADR 0009): antes de começar a demonstração, mostra-se o teste verde que diz que o Python e o circuito são a mesma máquina em todos os estados possíveis. A partir daí, o que o gateway envia é o que o circuito decidiu.

## Alternativas que consideramos

Componentes TTY e Keyboard do Logisim: escrevem e leem só na própria janela do simulador, não em arquivo nem em socket. Exigiriam alterar o circuito e ainda assim não chegariam à rede.

Modo headless (`logisim-evolution -tty`): roda uma simulação e imprime uma tabela, mas não é interativo — não serve para uma demonstração conduzida por pessoa.

Biblioteca TCL do Logisim-evolution: existe um componente que conversa com um interpretador Tcl por socket. Obscuro, mal documentado e frágil; não confiaríamos nele no dia.

Captura de tela com reconhecimento de LEDs: funciona até funcionar. Indefensável numa sabatina.

ESP32 lendo os pinos de estado do circuito montado fisicamente e escrevendo na serial: é a solução de verdade, e o roteiro lista Arduino/ESP32 como opcional. Exige montar o hardware. Não prometemos isso para novembro, mas o gateway tem uma abstração de fonte de comandos (`fontes.py`) para que uma classe `Serial` entre sem tocar no resto.

## Consequências

A demonstração tem duas janelas que o operador precisa manter em sincronia. Um erro de digitação num lado e não no outro é possível; o comando `estado` mostra o que o gateway acha que está acontecendo, para conferir contra o Logisim.

O gateway é testável sem Logisim, roda em CI, e tem um roteiro de ensaio (`roteiros/demo.txt`) que a equipe pode repetir quantas vezes quiser.

O gateway é também a segunda encarnação da máquina de estados; o backend será a terceira (ADR 0015). Três implementações da mesma FSM é uma redundância deliberada: cada uma tem um trabalho diferente, e a equivalência entre a primeira e a segunda é provada.
