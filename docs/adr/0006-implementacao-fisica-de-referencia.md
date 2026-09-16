# ADR 0006 — Implementação física de referência: 74HC, BC337, 1N4007, NE555

Data: 2026-09-16
Situação: aceita

## Contexto

O requisito de física pede justificativa do comportamento do circuito em corrente, tensão, potência ou sinal, com os cálculos. O nosso circuito é simulado, e o Logisim não simula nenhuma dessas grandezas. Precisávamos decidir sobre o que exatamente a seção de física fala.

Um LED com resistor em série é o cálculo óbvio, mas sozinho não sustenta uma seção inteira nem responde à pergunta que qualquer avaliador faria: "e a trava, como você aciona?".

## Decisão

Documentar uma implementação física de referência — o que seria montado em bancada se o circuito lógico saísse do simulador — e justificar cada componente que a lógica sozinha não explica:

- Família 74HC a 5 V para as portas e flip-flops, com resistores de pull-down de 10 kΩ nas entradas (a entrada CMOS é um capacitor; flutuante, assume qualquer valor).
- Filtro RC de 10 ms mais um Schmitt-trigger 74HC14 só no clock, porque é a única entrada sensível à borda (ADR 0005).
- LEDs indicadores com 220 Ω, verificados contra a resistência de saída real da porta.
- Trava solenoide de 12 V / 300 mA acionada por um BC337 em saturação, com resistor de base de 1 kΩ dimensionado por ganho forçado, e um 1N4007 em antiparalelo com a bobina.
- TIMEOUT gerado por um NE555 monoestável com 470 kΩ e 10 µF, que dá 5,16 s.
- Alimentação única de 12 V, com 7805 para a lógica.

## Alternativas que consideramos

Um MOSFET de nível lógico (IRLZ44N) no lugar do BC337: dispensa corrente de base e dissipa menos. Preferimos o bipolar porque é o dispositivo que a disciplina de física cobre (regiões de operação, saturação, ganho), porque o dimensionamento do resistor de base é um cálculo que vale a pena mostrar — e porque a pergunta "por que não ligou a trava direto na porta lógica?" tem uma resposta mais completa quando a limitação de 25 mA da porta aparece contra os 300 mA da bobina e o ganho do transistor faz a ponte.

Um relé em vez do transistor: é outra bobina, com o mesmo pico reverso, mais lento e maior. Não resolve nada que o transistor não resolva.

Um 555 no gateway em vez de hardware para o TIMEOUT: o gateway tem a opção `--timeout-fisico` que reproduz os 5,16 s, mas a origem do número precisa estar na física, não no software.

## Consequências

A seção de física tem eletrostática (entrada CMOS, RC, desacoplamento), eletrodinâmica (LED, transistor, regulador, orçamento de potência) e magnetismo (força do solenoide, transitório L/R, pico reverso e diodo de roda livre). Cobre os três eixos que o roteiro cita.

A lista de componentes permite montar de fato o estágio de potência para a demonstração, se a equipe quiser algo além da simulação. Não é obrigatório, mas responderia bem ao risco de "protótipo fictício".

Uma premissa fica declarada: a indutância da bobina, 100 mH, é ordem de grandeza de trava solenoide de 12 V, não valor de folha de dados. Afeta só o transitório (2,5 ms) e a energia magnética (4,3 mJ). Se a equipe escolher um modelo específico de trava, esse número deve ser trocado.

O número de energia por liberação, que atravessa o resto do projeto, nasce aqui (ADR 0007).
