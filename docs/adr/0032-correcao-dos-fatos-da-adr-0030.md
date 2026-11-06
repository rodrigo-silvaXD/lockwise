# ADR 0032 — Correção dos fatos da ADR 0030

Data: 2026-11-06
Situação: aceita (corrige o contexto e as alternativas da ADR 0030)

## Contexto

Ao revisar o material da sabatina, conferimos a ADR 0030 contra o arquivo do circuito e contra fontes públicas. Duas partes dela não se sustentaram.

A contagem de peças estava errada. A ADR diz 21 AND, 7 NOT, 6 OR e 3 XOR, números que somam 41 com os flip-flops, no mesmo parágrafo que fala em 37 peças. O erro veio de contar os nomes no XML do `.circ`, onde cada tipo de porta aparece uma vez a mais fora do circuito. Contando só os componentes, são 20 AND, 6 NOT, 5 OR, 2 XOR e 4 flip-flops D: 37 peças.

As afirmações sobre o Tinkercad não tinham verificação. Dissemos que ele não tem flip-flop D e que o simulador resolve mal a realimentação entre portas NAND. Há projetos públicos que montam flip-flop D com NAND no próprio Tinkercad, e não confirmamos se a biblioteca atual traz flip-flop pronto. A lista de 15 peças que consultamos era a do conector usado na tentativa, não a biblioteca do Tinkercad. Portanto, a conclusão de que sobraria apenas o caminho do Arduino não se segue.

## Decisão

Mantemos a placa em WebGL, pelo que ela entrega: uma página no próprio site, que gira com o mouse, em que cada peça mostra a equação e a coordenada do Logisim, e que o simulador abre na zona certa.

Deixamos de afirmar que o circuito não pode ser montado no Tinkercad. Montar em portas é um caminho possível que não testamos. O caminho com Arduino continua descartado, porque troca as portas por firmware.

## Alternativas que consideramos

Reescrever a ADR 0030: nossa regra não permite. Ela recebe a marca de situação e esta ADR registra os fatos corretos.

Montar o circuito em portas no Tinkercad: não avaliamos. Se o fizermos, será um complemento à placa, com ADR própria.

## Consequências

Se a banca perguntar por que não usamos o Tinkercad, a resposta é o que a placa entrega, e não uma limitação da ferramenta que não comprovamos.

A contagem correta das peças é a que está na placa em 3D e na sabatina: 33 portas e 4 flip-flops D.
