# Simulador interativo

`index.html` é o circuito do LOCKWISE rodando no navegador: a pessoa clica nos pinos e vê a máquina de estados decidir, sem instalar Logisim.

Serve para quem não lê esquemático entender o projeto em trinta segundos — e para a apresentação, porque funciona sem depender da API estar acordada.

## O que ele é, e o que não é

**É** a mesma lógica do circuito. Cada linha de `combinacional()` corresponde a uma porta de `circuito/lockwise_completo.circ`, transcrita do mesmo jeito que `gateway/lockwise_gateway/circuito.py`.

**Não é** um vídeo nem uma animação roteirizada. Você pode ligar os pinos em qualquer ordem e o resultado sai da lógica, não de um script.

A fidelidade foi verificada contra `gateway/referencia/sequencias.json` — as mesmas sequências que as figuras de evidência registram. Os 34 passos das cinco sequências conferem, estado e contador, sem divergência.

## Como abrir

Abra `index.html` no navegador. Não precisa de servidor, não tem dependência, não faz requisição nenhuma.

## O que tem na página

- **Painel de entrada** — os quatro bits da senha, CONFIRMA, TIMEOUT, RESET e o pulso de clock
- **A fechadura** — porta que abre, os sete LEDs do circuito e o contador de tentativas
- **Narração** — uma frase em português explicando o que cada clique fez e o que fazer em seguida
- **O caminho do sinal** — diagrama do circuito onde o pulso percorre os fios de verdade: entradas → comparador → máquina de estados → saída. Quando a senha não confere, o pulso **para no comparador**, uma marca vermelha aparece, e o sinal desvia para o contador de erros. É o comportamento real: `IGUAL = 0` não chega na entrada D do flip-flop.
- **Lógica acendendo** — as equações reais do circuito, acesas quando valem 1
- **Roteiros** — "acesso liberado" e "três erros e bloqueio" rodam sozinhos, passo a passo
- **No mundo real** — o que cada parte seria numa montagem física, com os números de `docs/fisica.md`
- **A corrente** — os cinco elos do projeto, que se acendem em sequência quando a trava abre

Uma escolha de temporização que vale notar: o estado só muda **depois** que o pulso termina de percorrer os fios, não no instante do clique. É mais lento que o necessário, e é de propósito — deixa visível que o circuito tem um caminho a percorrer antes de decidir.

## Se as equações do circuito mudarem

Altere `combinacional()` em `index.html` junto com `gateway/lockwise_gateway/circuito.py`. O teste `gateway/tests/test_netlist.py` protege o gateway contra divergência com o `.circ`; o simulador é verificado contra as sequências de referência.
