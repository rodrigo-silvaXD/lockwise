# ADR 0009 — Equivalência provada por teste, contra o arquivo .circ

Data: 2026-09-16
Situação: aceita

## Contexto

Um gêmeo digital (ADR 0008) só vale se for de fato a mesma máquina que o circuito. "Confiem em mim, é igual" não sobrevive a uma sabatina. Precisávamos de uma prova, e ela precisava ser reproduzível por qualquer integrante em qualquer máquina.

## Decisão

Três camadas, construídas nesta ordem.

Primeiro, dois modelos em Python. `circuito.py` transcreve as equações da netlist, porta a porta, com a coordenada de cada porta no comentário; não sabe o que é senha ou tentativa. `estados.py` e `maquina.py` implementam a mesma máquina com o padrão State, em termos semânticos. Um teste varre os 16 estados possíveis dos quatro flip-flops contra as 128 combinações dos sete pinos de entrada e exige que os dois modelos produzam o mesmo próximo estado — 2048 casos, todo o espaço. Outro teste exige as mesmas saídas. Um terceiro reproduz as sequências das figuras de evidência e confere estado e contador a cada borda.

Depois, ao revisar, percebemos que a transcrição manual das equações continuava sendo um ponto de confiança: se alguém mexesse no `.circ`, nada perceberia. Escrevemos então um leitor de `.circ` (`tests/logisim.py`) que reconstrói as conexões — fios, túneis, portas dos componentes — e simula o grafo de portas sem saber nada sobre o LOCKWISE. O teste exige que o arquivo real e `circuito.py` coincidam nos 2048 casos.

## Alternativas que consideramos

Testar só as sequências das figuras: cobre o caminho feliz e o bloqueio, mas não os cantos. Foi exatamente num canto (RESET durante o terceiro erro) que a varredura exaustiva encontrou comportamento que ninguém tinha previsto.

Exportar VHDL do Logisim e comparar: o Logisim-evolution exporta, mas comparar VHDL com Python é outro problema tão difícil quanto o original.

Confiar na transcrição manual: foi o que fizemos por algumas horas. Não é aceitável como estado final porque a documentação já tinha se mostrado divergente do circuito.

## O que a extração da netlist revelou

Ao ler o `.circ` por conectividade, duas equações do README não batiam com o circuito: o texto dizia `EN = ERRO·Ē` e `DC = (...)·CLR`; o arquivo tem `EN = ERRO·¬(C1·C0)` e `DC = (...)·¬CLR`. Com as equações do texto, o contador ficaria em `10` no bloqueio; a fig. 11 mostra `11`. O circuito estava certo e a documentação errada (ADR 0004, nota de correção).

Também percebemos que a contagem inicial de componentes, feita com `grep` no XML, incluía as entradas da barra de ferramentas: são 20 portas AND, não 21; 4 flip-flops, não 5. O teste estrutural pegou isso.

## Consequências

Mover uma porta no Logisim sem atualizar o Python quebra o teste. Alterar o Python sem alterar o Logisim quebra o teste. É o comportamento que queríamos.

O leitor de `.circ` depende da geometria dos componentes do Logisim-evolution 4.1.0 (posição das entradas em relação à saída, offsets do flip-flop). Uma versão futura que mude a geometria exige ajuste no leitor. O teste estrutural, que conta portas e pinos, avisa cedo se isso acontecer.

Na sabatina, a resposta para "como você garante que o software faz o que o hardware faz?" é: o teste lê o arquivo do circuito e compara com o gateway em todos os estados possíveis. Não é uma afirmação; é um comando que qualquer um roda.
