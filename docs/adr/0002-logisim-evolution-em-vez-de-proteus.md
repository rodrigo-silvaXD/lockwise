# ADR 0002 — Logisim-evolution desktop em vez de Proteus

Data: 2026-09-14
Situação: aceita

## Contexto

O roteiro aceita Proteus ou Logisim para o circuito simulado. Precisávamos de uma ferramenta que a equipe inteira conseguisse abrir, que produzisse evidências (capturas e diagrama de tempo) e que não dependesse de licença.

## Decisão

Logisim-evolution 4.1.0, versão desktop.

Três motivos. O arquivo `.circ` é XML legível: dá para revisar em diff, gerar por script e, como descobrimos depois, analisar por programa para extrair as equações do circuito. A versão desktop tem o cronograma (diagrama de tempo), que é o que evidencia que a máquina de estados é síncrona — sem ele, a fig. 14 não existiria. E é gratuito e multiplataforma; ninguém precisa de licença nem de Windows.

## Alternativas que consideramos

Proteus: o `.pdsprj` é binário e proprietário, só abre no Windows, e a licença é paga. Ninguém da equipe tinha uma. Simula analógico, o que seria uma vantagem para outro tema, mas para o nosso (ADR 0001) não faz diferença.

logisim.app, a versão web (2.7.2): abre em qualquer navegador, mas não tem cronograma e é uma versão antiga do Logisim original, com outra geometria de componentes. Ficou como plano B caso o desktop falhasse na máquina de alguém.

## Consequências

Não temos simulação analógica de nenhum tipo; aceito, porque o circuito é digital por escolha.

O formato aberto foi o que permitiu, mais tarde, escrever um leitor de `.circ` que reconstrói a netlist e compara com o gateway em todos os estados possíveis (ADR 0009). Com o Proteus isso seria impossível.

A geometria dos componentes é específica desta versão (offsets das portas do flip-flop, posição das entradas das portas lógicas). Está documentada no contexto do projeto para quem precisar gerar ou editar o arquivo à mão, e o leitor de netlist depende dela.
