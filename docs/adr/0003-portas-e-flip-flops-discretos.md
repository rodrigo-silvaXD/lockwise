# ADR 0003 — Circuito com portas e flip-flops discretos, sem componentes prontos

Data: 2026-09-14
Situação: aceita

## Contexto

O Logisim oferece componentes prontos que resolveriam boa parte do circuito em um clique: um `Counter` para as tentativas, um `Comparator` para a senha, um `Register` para o estado. Seria mais rápido e o diagrama ficaria menor.

Mas a avaliação é individual e o regulamento é explícito: qualquer integrante pode ser questionado sobre qualquer parte do projeto, e resposta vaga elimina a elegibilidade do grupo inteiro. "É um contador pronto do Logisim" não é uma resposta que sobrevive a "e como ele funciona por dentro?".

## Decisão

Tudo em portas lógicas e flip-flops D.

O contador de tentativas são dois flip-flops D com a lógica de incremento em XOR e AND, e a saturação em uma porta. O comparador são três ANDs em dois estágios (P1 = S3·S̄2, P2 = S1·S0, IGUAL = P1·P2), em vez de um AND de quatro entradas, para reduzir o fan-in e deixar cada etapa explicável. A máquina de estados são dois flip-flops D com as equações de D1 e D0 escritas porta a porta.

As conexões entre blocos usam túneis nomeados em vez de fios longos. Cada sinal tem nome (Q1, Q0N, ERR, E, EN, CLRN...), o que mantém o diagrama legível e evita erros de fiação por coordenada.

## Alternativas que consideramos

Componentes prontos do Logisim: rápidos, mas opacos na sabatina. Descartado pelo motivo acima.

Fiação explícita entre blocos: mais fiel a um esquemático tradicional, mas o circuito tem mais de 130 conexões e os cruzamentos tornariam o diagrama ilegível nas capturas de evidência.

## Consequências

O circuito ficou maior: 20 portas AND, 5 OR, 6 NOT, 2 XOR e 4 flip-flops. Numa montagem física, são 12 circuitos integrados da família 74HC.

Em troca, cada equação do README corresponde a uma porta com coordenada no arquivo, cada integrante consegue seguir um sinal do pino de entrada ao flip-flop, e o gateway pôde transcrever a netlist para Python linha a linha, com o comentário apontando a porta de origem. Sem esta decisão, a prova de equivalência da ADR 0009 não teria a mesma força.
