# ADR 0004 — Bloqueio antecipado e contador saturado

Data: 2026-09-14
Situação: aceita

## Contexto

O contador de tentativas tem dois bits e o sistema deve bloquear na terceira tentativa incorreta. Duas armadilhas apareceram ao projetar a lógica.

A primeira: o contador só assume o valor `11` depois da borda de clock que registra o terceiro erro. Se o sinal de bloqueio fosse simplesmente `C1·C0`, a máquina de estados olharia para o contador no instante do terceiro erro, veria `10`, e só bloquearia no quarto. O circuito aceitaria uma tentativa a mais do que a especificação.

A segunda: um contador binário de dois bits, ao receber um erro estando em `11`, voltaria a `00`. Se qualquer caminho levasse a isso, o bloqueio se desfaria sozinho e o sistema liberaria três novas tentativas.

## Decisão

O sinal de bloqueio antecipa o limiar: `E = C1·(C0 + ERRO)`. Com o contador em `10` e um erro acontecendo agora, `E` vale 1 nesta mesma borda, e a máquina vai para BLOQUEADO junto com o contador indo para `11`. A fig. 11 mostra exatamente isso.

O contador satura: `EN = ERRO·¬(C1·C0)`. Quando os dois bits estão em 1, a habilitação de contagem é cortada, e nenhum erro adicional o faz transbordar.

## Alternativas que consideramos

Um terceiro bit no contador, para ter folga: resolve o transbordo mas não o atraso de uma borda, e adiciona um flip-flop sem necessidade.

Um contador de três estados sem saturação, confiando que o estado BLOQUEADO impede novos erros (ERRO exige VERIFICANDO, e de BLOQUEADO não se chega a VERIFICANDO): funciona na sequência normal, mas deixa o comportamento correto dependendo de uma propriedade indireta. A saturação explícita custa duas portas e torna a garantia local.

## Consequências

O bloqueio ocorre na borda certa e o contador mostra `11` enquanto bloqueado, como as evidências registram.

Existe um caso de canto que só apareceu quando o gateway varreu todas as combinações: se RESET estiver ligado durante a borda do terceiro erro, o estado vai para BLOQUEADO e o contador para `00` ao mesmo tempo, porque `E` usa o contador antes da borda e CLR o zera na borda. É fiel ao hardware, não tem efeito prático (RESET é gesto administrativo, não acontece no meio de uma tentativa) e está documentado no README do gateway porque é o tipo de pergunta que aparece em sabatina.

Nota de correção. Entre 14 e 16/09 o README e o documento de contexto traziam `EN = ERRO·Ē` e `DC = (...)·CLR`. Ao extrair as equações da netlist para o gateway (ADR 0009), vimos que o circuito usa `EN = ERRO·¬(C1·C0)` e `·¬CLR`. Com as equações do texto, o contador ficaria em `10` no bloqueio, contradizendo a fig. 11. O circuito estava certo; a documentação, não. Corrigimos os dois documentos.
