# ADR 0030 — A placa em WebGL, não no Tinkercad

Data: 2026-10-28
Situação: aceita

## Contexto

Faltava uma peça visual do circuito. O `.circ` do Logisim é fiel, mas só abre no Logisim; o simulador em `site/index.html` mostra o comportamento da máquina de estados, não as portas que a produzem. Numa categoria chamada INTERFACE, a banca vai querer ver as portas.

A primeira ideia foi refazer o circuito no Tinkercad Circuits, que todo mundo conhece e que mostra componentes num tampo de bancada. Fomos medir antes de montar.

O circuito tem 37 peças: 21 AND (cinco delas de três entradas), 7 NOT, 6 OR, 3 XOR e 4 flip-flops D. O Tinkercad não tem flip-flop D discreto. Um flip-flop ali só sai de NANDs com realimentação cruzada, e o simulador dele resolve mal esse laço. Sobraria o caminho que todo projeto de Tinkercad acaba tomando: um Arduino Uno rodando a máquina de estados em `if/else`.

Esse caminho custa o argumento inteiro. A decisão de abrir deixaria de ser tomada por portas e passaria a ser tomada por firmware — exatamente o que tiramos do projeto quando removemos a ponte em ESP32. Um sketch de Arduino bem apresentado seria uma resposta pior à pergunta que a banca vai fazer.

## Decisão

Descartamos o Tinkercad e desenhamos a placa em WebGL, com Three.js, em `site/circuito-3d.html`.

As 37 peças aparecem com as silhuetas que elas têm de verdade — o arco do AND, a curva do OR, o triângulo com bolinha do inversor, o corpo retangular dos flip-flops — distribuídas em quatro zonas que seguem o fluxo do sinal: comparador, decodificação de estado, próximo estado e contador. As trilhas acendem conforme o nível lógico, e a câmera gira com o mouse.

A lógica da página não foi escrita à mão. É o porte direto de `gateway/lockwise_gateway/circuito.py`, que já reproduz a netlist porta a porta. Cada peça na tela carrega a equação e a coordenada `loc` da porta correspondente no Logisim, para qualquer divergência entre a tela e o arquivo original ser localizável no mesmo lugar que as outras.

Antes de publicar, comparamos as duas implementações nas 128 combinações de pinos vezes os 16 estados de registrador — os mesmos 2048 casos que `tests/test_equivalencia.py` usa. Saída idêntica.

## Alternativas que consideramos

**Refazer no Tinkercad com Arduino.** Descrita acima: troca portas por firmware e derruba o argumento de INTERFACE. Também reabriria uma decisão que já tínhamos tomado.

**Montar os flip-flops com NANDs cruzados no Tinkercad.** Tecnicamente possível, mas são quatro laços de realimentação num simulador que não os trata bem, e o resultado seria uma placa visualmente mais confusa que o `.circ` — pior do que não ter.

**Só exportar imagens do Logisim.** Barato e fiel, e continuamos tendo essas imagens em `docs/evidencias/`. Mas é estático: não dá para girar, não dá para clicar numa porta e ler o que ela faz, e não acrescenta nada ao que o relatório já mostra.

**Pôr o circuito em 3D dentro do simulador que já existe.** Juntaria as duas coisas numa página só, mas o simulador tem um trabalho próprio — contar a travessia do evento pelas camadas — e a placa tem outro. Separados, cada um faz o seu.

## Consequências

Ganhamos uma página que responde à pergunta da categoria olhando para ela: as portas estão lá, nomeadas, com as equações, e quem estiver na banca pode girar a placa e clicar numa delas.

Passamos a carregar uma terceira implementação da mesma lógica — o `.circ`, o gêmeo em Python e agora o porte em JavaScript. Três cópias divergem sozinhas com o tempo. A defesa é a comparação dos 2048 casos, mas ela hoje é um comando que rodamos à mão, não um teste do CI. Enquanto não for, a página pode envelhecer em silêncio se alguém mexer nas equações. Fica registrado como dívida, com o lugar certo para resolver: um teste que leia as funções do HTML e as confronte com `circuito.py`, do mesmo jeito que o teste de AST confronta a arquitetura do backend.

A página depende do Three.js vindo de CDN e de WebGL no navegador da banca. Se a sala não tiver rede, ela não abre. O simulador em `site/index.html` e as imagens do Logisim continuam sendo o caminho que funciona offline.
