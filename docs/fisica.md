# Física Aplicada — Memorial de Cálculos

Justificativa técnica do comportamento físico do circuito LOCKWISE: corrente, tensão, potência e sinal, com os cálculos aplicados.

Este documento responde ao requisito **Física para Sistemas Computacionais** do roteiro da categoria INTERFACE e cobre os três eixos listados no roteiro — eletrostática, eletrodinâmica e magnetismo — aplicados ao circuito descrito no [README](../README.md#o-circuito) e simulado em [`circuito/lockwise_completo.circ`](../circuito/lockwise_completo.circ).

---

## 1. Escopo e premissas

### 1.1 O que este memorial descreve

O Logisim simula a **lógica** do circuito: portas, flip-flops e os níveis 0 e 1. Ele não simula corrente, tensão, potência, capacitância nem indutância. Este memorial descreve a **implementação física de referência** — o que seria montado em bancada com componentes reais — e justifica, com cálculo, cada decisão que a lógica sozinha não explica:

- por que cada entrada tem um resistor de pull-down;
- por que o clock precisa de tratamento de sinal e as outras entradas não;
- por que cada LED tem um resistor em série e qual é o seu valor;
- por que a trava **não pode** ser ligada diretamente na saída de uma porta lógica;
- por que há um diodo em antiparalelo com a bobina da trava;
- quanto tempo a trava fica aberta e quanta energia isso consome.

O último item produz o número que atravessa todo o projeto: a **energia por liberação**, gravada pelo backend na coluna `energia_mj` de cada evento de acesso.

### 1.2 Correspondência entre a simulação e o hardware

| Pino no Logisim | Elemento físico | Seção |
|---|---|---|
| `S3 S2 S1 S0`, `CONFIRMA`, `RESET` | Chave + resistor de pull-down 10 kΩ | 2.2 |
| `CLK` | Botão + filtro RC + inversor Schmitt 74HC14 | 2.3 |
| `TIMEOUT` | Temporizador monoestável NE555 | 5 |
| `AGUARDANDO`, `VERIFICANDO`, `BLOQUEADO`, `SENHA_OK`, `ERROS_C1`, `ERROS_C0` | LED + resistor 220 Ω | 3 |
| `TRAVA_ABERTA` | LED + resistor 220 Ω **e** estágio de potência (BC337 + 1N4007 + solenoide 12 V) | 4 |
| Portas e flip-flops | Família CMOS 74HC alimentada em 5 V | 2.1 |

A composição do circuito simulado — 20 portas AND (15 de duas entradas, 5 de três), 5 OR (3 de duas, 2 de três), 6 NOT, 2 XOR e 4 flip-flops D — corresponde a 12 circuitos integrados da família 74HC: 4× 74HC08, 2× 74HC11, 1× 74HC32, 1× 74HC4075, 1× 74HC04, 1× 74HC86 e 2× 74HC74.

### 1.3 Parâmetros adotados

Valores típicos de folha de dados, à temperatura ambiente de 25 °C. Onde há faixa, adota-se o valor que produz o **pior caso** para o cálculo em questão.

| Símbolo | Grandeza | Valor | Fonte |
|---|---|---|---|
| V_CC | Alimentação da lógica | 5,0 V | regulador 7805 |
| V_TRAVA | Alimentação da trava | 12 V | fonte externa |
| V_IH / V_IL | Limiares de entrada 74HC | 3,5 V / 1,5 V | 0,7·V_CC / 0,3·V_CC |
| V_OH / V_OL | Níveis de saída 74HC garantidos a 4 mA | ≥ 4,4 V / ≤ 0,33 V | folha de dados 74HC |
| R_out | Resistência de saída típica 74HC | ≈ 50 Ω | estimado de V_OH × I_OH |
| I_O(máx) | Corrente máxima absoluta por saída 74HC | 25 mA | folha de dados 74HC |
| I_fuga | Corrente de fuga de entrada 74HC | ≤ 1 µA | folha de dados 74HC |
| t_pd | Atraso de propagação máximo por porta 74HC | ≈ 19–25 ns | folha de dados 74HC |
| V_F(LED) | Queda direta do LED vermelho 5 mm | 2,0 V | típico |
| I_F(LED) | Corrente nominal / máxima do LED | 15 mA / 20 mA | típico |
| R_BOB | Resistência da bobina do solenoide | 40 Ω | 12 V / 300 mA |
| L_BOB | Indutância da bobina do solenoide | 100 mH | premissa (ordem de grandeza de trava solenoide 12 V) |
| h_FE(mín) | Ganho mínimo do BC337-40 a I_C = 100 mA | 250 | folha de dados |
| V_CE(sat) | Tensão coletor-emissor saturado, adotada | 0,3 V | típico no ponto de operação |
| V_BE(sat) | Tensão base-emissor saturado | 0,7 V | típico |
| V_CEO | Tensão máxima coletor-emissor do BC337 | 45 V | folha de dados |
| P_tot | Dissipação máxima do BC337 (TO-92) | 625 mW | folha de dados |
| R_th(j-a) | Resistência térmica junção-ambiente TO-92 | 200 K/W | folha de dados |
| V_F(diodo) | Queda direta do 1N4007 a 0,3 A | ≈ 0,8 V | folha de dados |

---

## 2. Sinal: níveis lógicos, integridade e temporização

### 2.1 Níveis lógicos e margem de ruído

A família 74HC, alimentada em 5 V, reconhece como nível alto qualquer tensão acima de V_IH = 3,5 V e como nível baixo qualquer tensão abaixo de V_IL = 1,5 V. Entre esses valores a entrada é indefinida.

As saídas garantem V_OH ≥ 4,4 V e V_OL ≤ 0,33 V quando drenam ou fornecem até 4 mA. A **margem de ruído** — quanto uma interferência pode deslocar o sinal sem trocar o nível lógico — é a diferença entre o que uma saída garante e o que a entrada seguinte exige:

```
Margem no nível alto   = V_OH − V_IH = 4,4 − 3,5 = 0,9 V
Margem no nível baixo  = V_IL − V_OL = 1,5 − 0,33 ≈ 1,17 V
```

Ambas são amplas para um circuito de bancada com fiação curta. É essa margem que permite que os 132 túneis da simulação sejam, no hardware, fios comuns sem tratamento especial.

### 2.2 Entradas: por que toda chave tem um resistor de pull-down

Aqui entra a **eletrostática**. A entrada de uma porta CMOS é o terminal de porta (*gate*) de um transistor MOS: uma placa metálica separada do canal por uma camada de óxido isolante. Eletricamente, é um **capacitor** de poucos picofarads (C_in ≈ 5 pF), com impedância de entrada da ordem de 10¹² Ω.

Uma entrada CMOS deixada em aberto não vale 0 — vale **o que a carga acumulada nesse capacitor determinar**. Para levar 5 pF de 0 a 2,5 V (o meio da faixa indefinida) basta:

```
Q = C · V = 5 pF × 2,5 V = 12,5 pC   ≈  78 milhões de elétrons
```

Isso é menos carga do que um dedo aproximado, um fio vizinho comutando ou a umidade do ar transferem. A entrada flutuante oscila entre 0 e 1 de forma imprevisível, e a máquina de estados receberia comandos fantasmas.

O **resistor de pull-down** de R_PD = 10 kΩ resolve isso: oferece um caminho de baixa impedância para o terra, drenando qualquer carga parasita, e define o nível 0 quando a chave está aberta.

**Chave aberta.** A única corrente pelo resistor é a fuga da entrada, I_fuga ≤ 1 µA:

```
V_entrada = R_PD · I_fuga = 10 kΩ × 1 µA = 10 mV   ≪  V_IL = 1,5 V   ✓
```

**Chave fechada.** A entrada vai a 5 V e o resistor conduz:

```
I_PD = V_CC / R_PD = 5 V / 10 kΩ = 0,5 mA
P_PD = V_CC · I_PD = 5 V × 0,5 mA = 2,5 mW
```

Sete chaves (S3–S0, CONFIRMA, TIMEOUT, RESET) fechadas ao mesmo tempo somam 3,5 mA — desprezível, e cada resistor de 1/4 W trabalha a 1% de sua capacidade.

**Por que 10 kΩ e não outro valor.** Menor (1 kΩ) drenaria 5 mA por chave sem ganho de robustez. Maior (1 MΩ) tornaria V_entrada = 1 V com a fuga máxima, corroendo a margem de ruído. 10 kΩ é o compromisso padrão da indústria para CMOS a 5 V.

O mesmo raciocínio eletrostático explica a proteção contra **descarga eletrostática (ESD)**: o corpo humano carregado a alguns quilovolts, ao tocar um pino, descarrega em nanossegundos. Os CIs 74HC têm diodos internos de proteção que desviam esse pulso para V_CC ou GND, e o pull-down oferece caminho permanente para a carga escoar antes que ela se acumule.

### 2.3 Clock: por que só ele precisa de tratamento de sinal

A máquina de estados é **síncrona**: todos os flip-flops mudam apenas na borda de subida de CLK. Isso tem uma consequência prática que divide as entradas em duas classes.

**As entradas de dados** (S3–S0, CONFIRMA, TIMEOUT, RESET) são apenas *amostradas* na borda. Se a chave vibrar mecanicamente ao ser acionada, não importa: o valor só é lido quando o operador pulsa o CLK, milissegundos depois, com a chave já estável. Não precisam de filtro.

**O clock** é sensível à borda. Cada transição 0→1 que chega ao pino CLK é um ciclo da máquina. Uma chave mecânica, ao fechar, não produz uma transição — produz um trem de transições (*bounce*) durante 1 a 5 ms, às vezes até 20 ms, enquanto os contatos metálicos ricocheteiam. Sem tratamento, um único aperto poderia avançar a máquina de estados duas ou três vezes e o contador registraria erros que não aconteceram.

A solução combina um **filtro RC** com um **inversor Schmitt-trigger** (74HC14):

```
V_CC ──[ R1 = 10 kΩ ]──┬──────────── entrada do 74HC14 ──▷o── CLK
                        │
                    C = 1 µF
                        │
                       GND
                        │
    botão ─[ 100 Ω ]────┘  (fecha o nó ao terra)
```

Com o botão solto, C carrega através de R1 até 5 V e a saída do inversor é 0. Ao apertar, o nó vai a 0 quase instantaneamente (τ_descarga = 100 Ω × 1 µF = 0,1 ms) e a saída sobe: **essa é a borda que a máquina vê**. Se o contato abrir por um ricochete, C começa a recarregar com constante de tempo:

```
τ_carga = R1 · C = 10 kΩ × 1 µF = 10 ms
```

A tensão no capacitor segue a curva de carga do circuito RC:

```
v_C(t) = V_CC · (1 − e^(−t/τ))
```

O 74HC14 só volta a reconhecer nível alto quando v_C atinge o limiar superior V_T+ ≈ 2,7 V. O tempo necessário é:

```
t = τ · ln( V_CC / (V_CC − V_T+) ) = 10 ms × ln(5 / 2,3) = 10 ms × 0,777 ≈ 7,8 ms
```

Um ricochete de 1 a 5 ms fecha o contato de novo antes que C chegue a 2,7 V, e o inversor nunca muda. **Um aperto, uma borda.**

O Schmitt-trigger é indispensável aqui por um segundo motivo: a subida lenta de v_C (dezenas de milissegundos) atravessaria a faixa indefinida de uma porta comum e produziria oscilação. O Schmitt tem **histerese** — liga em V_T+ ≈ 2,7 V e só desliga em V_T− ≈ 1,6 V, uma janela de ≈ 1,1 V — e converte qualquer rampa em uma única transição limpa.

O diagrama temporal em [`evidencias/fig14_diagrama.png`](evidencias/fig14_diagrama.png) mostra o que esse tratamento garante: cada transição de estado alinhada a exatamente uma borda de CLK.

### 2.4 Temporização: caminho crítico e frequência máxima

Para que a máquina de estados funcione, o sinal em cada entrada D precisa estar estável um pouco antes da borda de clock (tempo de *setup*, t_su ≈ 20 ns). O sinal nasce na saída Q de um flip-flop, atravessa a lógica combinacional e chega à entrada D de outro. O período mínimo de clock é a soma dos atrasos do **caminho mais longo**.

O caminho mais longo do LOCKWISE passa pelo sinal de limiar E: a decodificação do estado alimenta ERRO, que alimenta E, que alimenta a entrada D0 pelo termo de bloqueio. Como o flip-flop já fornece Q̄ diretamente, não há inversor no início do caminho:

```
Q1,Q0 ─▷ AND (VERIFICANDO = Q̄1·Q0) ─▷ AND (ERRO = VER·ĪGUAL) ─▷ OR (C0 + ERRO)
      ─▷ AND (E = C1·…) ─▷ AND (NE = ĪGUAL·E) ─▷ AND3 (B2 = Q̄1·Q0·NE) ─▷ OR3 (D0)
```

Sete níveis de porta. Somando os atrasos máximos de folha de dados (19 ns por porta de duas entradas, 22 ns para AND de três, 25 ns para OR de três):

```
t_FF(CLK→Q)        =  31 ns
t_lógica           =  5 × 19 ns + 22 ns + 25 ns = 142 ns
t_su               =  20 ns
─────────────────────────────
T_mín              = 193 ns    →    f_máx = 1 / 193 ns ≈ 5,2 MHz
```

O caminho do contador (VERIFICANDO → ERRO → EN → G → X1 → DC1, seis níveis, 118 ns) é um pouco mais curto e não é o limitante.

O clock do LOCKWISE é acionado manualmente, a menos de 10 Hz. A margem é superior a **500 000 vezes**. Isso significa que:

1. o circuito pode ser montado com fiação longa, protoboard e componentes de qualquer lote, sem risco de violação de *setup*;
2. **glitches** na lógica combinacional — pulsos espúrios de nanossegundos que aparecem quando várias entradas de uma porta mudam quase ao mesmo tempo — são irrelevantes, porque se extinguem centenas de milhares de vezes antes da próxima borda. Esta é a razão física para a decisão de projeto síncrono registrada no README.

### 2.5 Desacoplamento da alimentação

Quando uma saída 74HC comuta, ela carrega ou descarrega a capacitância do que está ligado a ela (C_carga ≈ 50 pF entre pino, trilha e entrada seguinte) em cerca de 5 ns. A corrente instantânea é:

```
i = C · dV/dt = 50 pF × 5 V / 5 ns = 50 mA
```

Cinquenta miliamperes por 5 nanossegundos, por porta, várias portas ao mesmo tempo. A fonte de alimentação, a centímetros de distância e atrás da indutância dos fios, não responde nessa escala de tempo. Sem providência, V_CC afunda momentaneamente e a margem de ruído da seção 2.1 desaparece.

O **capacitor de desacoplamento** de 100 nF, soldado junto a cada CI entre V_CC e GND, funciona como reservatório local de carga. A carga que uma comutação exige é:

```
ΔQ = C_carga · ΔV = 50 pF × 5 V = 250 pC
```

Retirar 250 pC de um capacitor de 100 nF faz sua tensão cair:

```
ΔV = ΔQ / C = 250 pC / 100 nF = 2,5 mV
```

Contra 900 mV de margem de ruído. O capacitor cobre o transitório; a fonte o reabastece nos microssegundos seguintes.

---

## 3. Corrente e tensão: os indicadores luminosos

O circuito tem sete saídas indicadoras, cada uma acionando um LED. Um LED é um diodo: conduz a partir de sua tensão direta V_F e, acima dela, a corrente cresce exponencialmente com a tensão. Ligado diretamente em 5 V, um LED de V_F = 2,0 V tentaria absorver amperes e queimaria. **O resistor em série define a corrente.**

### 3.1 Dimensionamento

Pela lei de Kirchhoff das tensões, a queda no resistor é o que sobra da alimentação depois do LED:

```
V_R = V_CC − V_F = 5,0 − 2,0 = 3,0 V
```

Para a corrente nominal I_F = 15 mA, a lei de Ohm dá:

```
R = V_R / I_F = 3,0 V / 15 mA = 200 Ω
```

200 Ω não é valor comercial da série E12. Escolhe-se o valor **imediatamente acima**, 220 Ω, para que o arredondamento reduza a corrente em vez de aumentá-la:

```
I_F = 3,0 V / 220 Ω = 13,6 mA        (abaixo do máximo de 20 mA   ✓)
```

### 3.2 Potência

```
P_R   = I² · R  = (13,6 mA)² × 220 Ω = 40,9 mW    →  resistor de 1/4 W (250 mW), margem de 6×
P_LED = V_F · I = 2,0 V × 13,6 mA    = 27,3 mW
P_total por indicador = 68,2 mW
```

### 3.3 Verificação com a saída real

O cálculo acima supõe uma fonte ideal de 5 V. A saída de uma porta 74HC não é ideal: tem resistência interna R_out ≈ 50 Ω. O circuito real é 5 V em série com 50 Ω, 220 Ω e o LED:

```
I_F  = (5,0 − 2,0) / (50 + 220) = 3,0 / 270 = 11,1 mA
V_OH = 5,0 − 50 Ω × 11,1 mA = 4,44 V
```

O LED acende com 11 mA — perfeitamente visível. Essa corrente está acima dos 4 mA nos quais o fabricante *garante* V_OH ≥ 4,4 V, mas bem abaixo do máximo absoluto de 25 mA por pino. A queda em V_OH não causa problema porque **o pino alimenta apenas o LED**, e não outra entrada lógica: não há nível lógico a preservar naquele nó.

Se um mesmo pino precisasse acionar o LED **e** a próxima porta, seria obrigatório um *buffer*. É por isso que a saída `TRAVA_ABERTA`, que alimenta o LED e o transistor da trava, usa portas separadas do mesmo CI para cada carga.

### 3.4 Corrente simultânea

No pior caso, quatro LEDs acendem ao mesmo tempo: um indicador de estado, SENHA_OK e os dois bits do contador. Corrente total dos indicadores:

```
I_LEDs(máx) = 4 × 11,1 mA ≈ 44 mA
```

Como as quatro saídas pertencem a portas de decodificação diferentes, nenhum CI individual chega perto do limite de 50 mA no pino de alimentação.

---

## 4. Potência: o acionamento da trava

Esta é a seção central do memorial. O atuador do LOCKWISE é uma **trava solenoide de 12 V / 300 mA**: uma bobina que, ao ser energizada, gera um campo magnético que puxa um êmbolo de ferro e libera o ferrolho. Ela é acionada pela saída `TRAVA_ABERTA`, que no Logisim é apenas um pino que vale 1 no estado LIBERADO ([`evidencias/fig07_liberado.png`](evidencias/fig07_liberado.png)).

### 4.1 Por que a trava não pode ser ligada na saída da porta lógica

Duas incompatibilidades, cada uma suficiente para inviabilizar a ligação direta:

**Corrente.** A bobina exige 300 mA. Uma saída 74HC suporta no máximo 25 mA absolutos — **doze vezes menos**. A tentativa destruiria o estágio de saída da porta em milissegundos.

**Tensão.** A trava é de 12 V; a lógica opera em 5 V. Mesmo que a corrente fosse compatível, uma porta a 5 V entregaria à bobina de 40 Ω apenas 5/40 = 125 mA, e a força do solenoide — proporcional ao quadrado da corrente, como se verá na seção 4.6 — cairia para 17% da nominal. A trava não abriria.

A saída lógica precisa **comandar** um dispositivo que, por sua vez, **chaveia** a potência. Esse dispositivo é o transistor.

### 4.2 O estágio de potência

```
                              +12 V
                                │
                     ┌──────────┴──────────┐
                     │                     │
                     │   solenoide         ▲  D1  1N4007
                     │   40 Ω / 100 mH     │  (catodo no +12 V)
                     │                     │
                     └──────────┬──────────┘
                                │  coletor
                                │
TRAVA_ABERTA ──[ R_B = 1 kΩ ]───┤  BC337-40 (NPN)
 (saída 74HC, 5 V)              │
                                │  emissor
                               GND
```

O transistor NPN opera como chave. Com `TRAVA_ABERTA` = 0, a base está em 0 V, o transistor está em **corte**, nenhuma corrente flui pela bobina. Com `TRAVA_ABERTA` = 1, a corrente de base leva o transistor à **saturação**: ele se comporta como um contato fechado entre coletor e emissor, com uma pequena queda residual V_CE(sat).

### 4.3 Corrente de coletor

Com o transistor saturado, a tensão sobre a bobina é a alimentação menos a queda residual no transistor:

```
V_BOB = V_TRAVA − V_CE(sat) = 12 − 0,3 = 11,7 V
I_C   = V_BOB / R_BOB = 11,7 V / 40 Ω = 292,5 mA
```

O BC337 suporta I_C(máx) = 800 mA. Margem de 2,7×.

### 4.4 Corrente de base e o ganho forçado

Um transistor só satura se a base receber corrente suficiente para sustentar a corrente de coletor exigida. A folha de dados diz que o BC337-40 tem h_FE ≥ 250 — mas esse é o ganho na **região ativa**, medido a 100 mA. Na saturação, o ganho efetivo é bem menor, e projetar com o h_FE de folha de dados é o erro clássico que deixa o transistor semi-ligado, dissipando potência e sem entregar corrente.

A prática de engenharia é impor um **ganho forçado** β_F várias vezes menor que h_FE(mín), garantindo excesso de corrente de base (*overdrive*). Adotando fator 3:

```
β_F ≤ h_FE(mín) / 3 = 250 / 3 ≈ 83
I_B ≥ I_C / β_F = 292,5 mA / 83 ≈ 3,5 mA
```

O resistor de base é dimensionado no pior caso — saída da porta no mínimo garantido, V_OH = 4,4 V:

```
R_B = (V_OH − V_BE(sat)) / I_B = (4,4 − 0,7) / 3,5 mA ≈ 1,06 kΩ   →  1 kΩ (E12)
```

Verificação com R_B = 1 kΩ:

```
I_B (pior caso, V_OH = 4,4 V)  = (4,4 − 0,7) / 1 kΩ = 3,7 mA   →  β_F = 292,5 / 3,7 = 79   →  overdrive 3,2×  ✓
I_B (típico, V_OH = 5,0 V)     = (5,0 − 0,7) / 1 kΩ = 4,3 mA   →  β_F = 68                →  overdrive 3,7×  ✓
P_RB = I_B² · R_B = (4,3 mA)² × 1 kΩ = 18,5 mW                 →  resistor de 1/4 W
```

A corrente de base de 3,7 a 4,3 mA está **dentro dos 4 mA garantidos** pela saída 74HC. Foi essa restrição — e não o transistor — que determinou o fator de *overdrive*: um fator maior exigiria mais corrente do que a porta lógica fornece com nível garantido.

**O que aconteceria com R_B errado.** Se R_B fosse 10 kΩ, I_B cairia a 0,43 mA e o coletor sustentaria no máximo h_FE × I_B = 250 × 0,43 mA ≈ 107 mA. O transistor ficaria na região ativa, com:

```
V_CE = 12 − 40 Ω × 107 mA = 7,7 V
P_Q  = 7,7 V × 107 mA = 0,82 W   >  P_tot = 625 mW   →  transistor destruído
```

E a trava, com 36% da corrente nominal, teria 13% da força. Não abriria. O dimensionamento da base não é detalhe: é a diferença entre um atuador que funciona e um que queima.

### 4.5 Potência dissipada e temperatura

**Na bobina:**

```
P_BOB = V_BOB · I_C = 11,7 V × 292,5 mA = 3,42 W
```

Essa potência é dissipada como calor na resistência do fio da bobina (efeito Joule, P = I²R). Travas solenoide comerciais de 12 V são projetadas para isso em regime intermitente — e o LOCKWISE mantém a trava energizada por apenas ≈ 5 s por liberação (seção 5).

**No transistor:**

```
P_Q = V_CE(sat) · I_C + V_BE(sat) · I_B = 0,3 × 0,2925 + 0,7 × 0,0043 = 87,8 + 3,0 ≈ 91 mW
```

Isto é 15% de P_tot = 625 mW. A elevação de temperatura da junção, sem dissipador, é:

```
ΔT = P_Q · R_th(j-a) = 0,091 W × 200 K/W ≈ 18 K
T_j = 25 + 18 = 43 °C       (limite: 150 °C)   ✓
```

Compare com o caso de ligação direta ou base subdimensionada: o segredo da baixa dissipação é a saturação. Um transistor **bem saturado** dissipa pouco porque V_CE é pequena; um transistor **semi-ligado** dissipa muito porque V_CE é grande. A potência vai para a carga ou para o transistor — o projeto decide qual.

**Fornecido pela fonte de 12 V:**

```
P_12V = V_TRAVA · I_C = 12 V × 292,5 mA = 3,51 W
```

A diferença entre P_12V e P_BOB (≈ 88 mW) é exatamente o que o transistor absorve.

### 4.6 Magnetismo: a bobina, a força e o pico reverso

**A força do solenoide.** Uma bobina de N espiras percorrida por corrente I gera, no entreferro g entre o êmbolo e o núcleo, um campo magnético B ≈ μ₀·N·I / g. A força de atração sobre o êmbolo de seção A é a pressão magnética integrada na área:

```
F = B² · A / (2 μ₀)  =  μ₀ · N² · I² · A / (2 g²)
```

O que importa para o projeto é a dependência: **F ∝ I²**. Isso tem duas consequências mensuráveis:

1. A queda V_CE(sat) do transistor reduz a corrente de 300 para 292,5 mA e, portanto, a força para (292,5/300)² = **95%** da nominal. No pior caso de folha de dados (V_CE(sat) = 0,7 V), a corrente seria 282,5 mA e a força 89%. Fabricantes especificam força com margem para isso, mas um transistor mal saturado (V_CE de vários volts) faria a trava simplesmente não abrir.

2. A ligação direta na porta lógica a 5 V (seção 4.1), com 125 mA, daria (125/300)² = **17%** da força. Confirma-se por outro caminho que o estágio de potência é obrigatório.

**Transitório de acionamento.** Uma bobina resiste a variações de corrente. Ao saturar o transistor, a corrente não salta a 292,5 mA — sobe exponencialmente com constante de tempo:

```
τ = L_BOB / R_BOB = 100 mH / 40 Ω = 2,5 ms

i(t) = I_C · (1 − e^(−t/τ))
i(3τ = 7,5 ms)  = 95% de I_C
i(5τ = 12,5 ms) = 99% de I_C
```

A trava atinge força plena em cerca de 10 ms — instantâneo para o usuário, mas uma vantagem para a fonte: a demanda de corrente sobe suavemente, sem degrau, e a própria indutância da carga dispensa um capacitor de reserva grande no barramento de 12 V.

**O pico reverso e o diodo de roda livre.** O problema aparece no **desligamento**. Quando `TRAVA_ABERTA` volta a 0 e o transistor corta, a bobina se recusa a interromper a corrente instantaneamente. A lei de Faraday–Lenz dá a tensão que ela gera para tentar mantê-la:

```
v_L = − L · di/dt
```

Um BC337 corta em cerca de 1 µs. Se a corrente tivesse de cair de 292,5 mA a zero nesse intervalo:

```
|v_L| = 100 mH × 0,2925 A / 1 µs ≈ 29 000 V
```

Esse número é idealizado — na prática o transistor entra em avalanche muito antes —, mas o ponto é a ordem de grandeza: **centenas a milhares de volts** contra um V_CEO de 45 V. Sem proteção, o primeiro desligamento destrói o transistor. Esta é a pergunta que a seção de física precisa responder: *por que há um diodo em antiparalelo com a bobina?*

O **diodo de roda livre** D1 (1N4007), com o catodo no +12 V e o anodo no coletor, fica reversamente polarizado durante a operação normal e não conduz. No instante do corte, a bobina inverte a polaridade da tensão sobre si tentando manter a corrente — e agora o diodo está diretamente polarizado. A corrente encontra um caminho fechado: bobina → diodo → bobina. A tensão no coletor fica limitada a:

```
V_C(máx) = V_TRAVA + V_F(diodo) = 12 + 0,8 = 12,8 V   ≪  V_CEO = 45 V   ✓
```

A corrente circula pelo laço e decai, dissipando na resistência da bobina e no diodo a energia que estava armazenada no campo magnético:

```
E_L = ½ · L · I² = ½ × 100 mH × (0,2925 A)² ≈ 4,3 mJ
```

Quatro milijoules por desligamento — desprezível para o 1N4007 (que suporta 1 A contínuo e 30 A de surto), mas suficiente para destruir uma junção de transistor se concentrada em um pulso de alta tensão. O decaimento leva aproximadamente 3τ ≈ 7,5 ms, o que adiciona alguns milissegundos ao tempo de soltura do êmbolo — irrelevante para uma trava.

**Por que 1N4007.** Sua tensão reversa de 1000 V é muito superior aos 12,8 V exigidos; um 1N4001 (50 V) bastaria. A escolha é por disponibilidade e custo idênticos. A ressalva é que a família 1N400x tem recuperação reversa lenta (µs) — inadequada para PWM em dezenas de kHz, mas perfeitamente adequada a um chaveamento que ocorre uma vez a cada liberação.

---

## 5. TIMEOUT: o temporizador da trava aberta

No Logisim, `TIMEOUT` é uma chave que o operador aciona para devolver a máquina ao estado AGUARDANDO. No hardware, esse sinal vem de um **temporizador monoestável** disparado pela entrada no estado LIBERADO, que define por quanto tempo a trava permanece energizada.

O circuito é o NE555 (ou TLC555, versão CMOS) em configuração monoestável, e sua física é a carga de um capacitor por um resistor — o mesmo fenômeno da seção 2.3, agora usado para medir tempo.

Ao ser disparado, o 555 libera o capacitor C_T, que carrega por R_T a partir de 0 V:

```
v_C(t) = V_CC · (1 − e^(−t / R_T·C_T))
```

O ciclo termina quando v_C atinge 2/3 de V_CC (limiar interno do 555). Resolvendo:

```
1 − e^(−T/RC) = 2/3   →   e^(−T/RC) = 1/3   →   T = R_T · C_T · ln 3 ≈ 1,0986 · R_T · C_T
```

Esta é a origem do "1,1·RC" que aparece nas folhas de dados. Para T ≈ 5 s com valores comerciais:

```
R_T = 470 kΩ,  C_T = 10 µF   →   T = 470 kΩ × 10 µF × 1,0986 = 5,16 s
```

**Tolerância.** Capacitores eletrolíticos têm tolerância de ±20% e resistores de ±5%. O intervalo real fica entre 3,9 e 6,5 s. Para o LOCKWISE isso é aceitável; se a precisão importasse, um capacitor de tântalo ou filme (±10%) estreitaria a faixa para 4,4–5,9 s.

O sinal `TIMEOUT` é o único elemento **assíncrono** do sistema — o 555 não sabe do clock. Isso não é problema justamente pela arquitetura síncrona da seção 2.3: a máquina apenas amostra `TIMEOUT` na próxima borda de CLK. O temporizador pode ser lento e ruidoso; a máquina de estados o lê de forma limpa.

---

## 6. Energia por liberação — o número que atravessa o projeto

Com a potência de acionamento (seção 4.5) e a duração da abertura (seção 5), calcula-se a energia consumida por cada evento de liberação:

```
P_atuação = P_12V + P_base(5 V) = 12 V × 292,5 mA + 5 V × 4,3 mA = 3,510 + 0,022 = 3,53 W
T_aberta  = 5,16 s

E_liberação = P_atuação × T_aberta = 3,53 W × 5,16 s ≈ 18,2 J  =  18 200 mJ
```

Os 4,3 mJ de energia magnética da bobina (seção 4.6) e os 68 mW do LED `TRAVA_ABERTA` estão dentro do arredondamento.

**Onde esse número vai.** O gateway envia, a cada evento com resultado `LIBERADO`, o campo `energia_mj = 18200`. Eventos `NEGADO` e `BLOQUEADO` não acionam a trava e registram `energia_mj = 0`. O backend persiste o valor na tabela `acesso`, e o módulo de otimização pode somá-lo por faixa horária para compor o custo energético da operação junto ao custo de vigilância.

A frase para a sabatina: *"a energia registrada em cada acesso não é um número inventado — é 12 volts vezes 292 miliamperes vezes 5,16 segundos, e cada um desses três fatores tem um cálculo neste memorial."*

---

## 7. Alimentação: orçamento de consumo

Uma única fonte externa de 12 V alimenta a trava diretamente e a lógica através de um regulador linear 7805.

```
 fonte 12 V ──┬──────────────────────────▶ solenoide (via BC337)
              │
              └──[ 7805 ]──▶ 5 V ──┬──▶ CIs 74HC (≈ 12)
                                   ├──▶ LEDs (até 4 simultâneos)
                                   ├──▶ pull-downs das chaves
                                   ├──▶ NE555
                                   └──▶ base do BC337
```

### 7.1 Barramento de 5 V

| Carga | Corrente | Observação |
|---|---|---|
| LEDs, 4 simultâneos | 44,4 mA | seção 3.4 |
| Base do BC337 | 4,3 mA | seção 4.4, só no estado LIBERADO |
| Pull-downs, 7 chaves fechadas | 3,5 mA | seção 2.2, pior caso |
| NE555 em repouso | 3 mA | folha de dados (TLC555: < 1 mA) |
| 12 CIs 74HC, estáticos | 0,2 mA | ≤ 20 µA por CI; dinâmico desprezível a < 10 Hz |
| **Total** | **≈ 56 mA** | |

```
P_5V = 5 V × 56 mA = 0,28 W
```

### 7.2 Regulador 7805

Um regulador linear derruba a tensão excedente dissipando-a como calor. A corrente de entrada é praticamente igual à de saída, mais a corrente de repouso (≈ 5 mA):

```
P_7805 = (V_in − V_out) × I_out = (12 − 5) V × 56 mA = 0,39 W
```

Encapsulamento TO-220 sem dissipador, R_th(j-a) ≈ 65 K/W:

```
ΔT = 0,39 W × 65 K/W ≈ 25 K   →   T_j ≈ 50 °C   (limite: 125 °C)   ✓
```

Dispensa dissipador. A eficiência do 7805 aqui é 5/12 ≈ 42% — baixa, mas sobre uma potência de 0,28 W isso custa 0,39 W de calor. Um conversor chaveado economizaria 0,3 W e introduziria ruído de comutação junto à lógica; não vale a troca.

### 7.3 Barramento de 12 V e escolha da fonte

| Carga | Corrente | Quando |
|---|---|---|
| Solenoide via BC337 | 292,5 mA | estado LIBERADO |
| Entrada do 7805 | 61 mA | sempre |
| **Pico** | **≈ 354 mA** | |

```
P_pico = 12 V × 354 mA ≈ 4,2 W
```

Uma fonte de **12 V / 1 A** (12 W) oferece margem de 2,8× sobre o pico. Um capacitor eletrolítico de 100 µF no barramento de 12 V absorve o transitório de acionamento — que, como visto na seção 4.6, já é suavizado pela indutância da própria bobina.

---

## 8. Resumo dos valores de projeto

| Item | Valor | Justificativa |
|---|---|---|
| Pull-down de entrada | 10 kΩ | 10 mV com fuga máxima; 0,5 mA por chave fechada (2.2) |
| Filtro de clock | 10 kΩ + 1 µF + 74HC14 | τ = 10 ms; 7,8 ms até V_T+; filtra *bounce* de até 5 ms (2.3) |
| Desacoplamento | 100 nF por CI | queda de 2,5 mV por comutação (2.5) |
| Resistor de LED | 220 Ω, 1/4 W | 13,6 mA ideal / 11,1 mA real; 41 mW (3) |
| Resistor de base | 1 kΩ, 1/4 W | I_B = 3,7–4,3 mA; β_F ≈ 70–80; overdrive > 3× (4.4) |
| Transistor | BC337-40 | I_C = 292,5 mA de 800 mA; P_Q = 91 mW de 625 mW; T_j ≈ 43 °C (4.3–4.5) |
| Diodo de roda livre | 1N4007 | limita V_C a 12,8 V contra V_CEO = 45 V; absorve 4,3 mJ (4.6) |
| Temporizador | NE555, 470 kΩ + 10 µF | T = RC·ln 3 = 5,16 s (5) |
| Energia por liberação | **18 200 mJ** | 3,53 W × 5,16 s (6) |
| Regulador | 7805 sem dissipador | 0,39 W; T_j ≈ 50 °C (7.2) |
| Fonte | 12 V / 1 A | pico de 354 mA / 4,2 W (7.3) |

### Lista de componentes da implementação física

| Qtd | Componente | Função |
|---|---|---|
| 12 | CIs 74HC (4× 08, 2× 11, 32, 4075, 04, 86, 2× 74) | lógica do circuito simulado |
| 1 | 74HC14 | Schmitt-trigger do clock |
| 1 | NE555 ou TLC555 | temporizador TIMEOUT |
| 1 | BC337-40 | chave de potência da trava |
| 1 | 1N4007 | diodo de roda livre |
| 1 | 7805 | regulador 5 V |
| 1 | Solenoide 12 V / 300 mA | atuador (trava) |
| 7 | LED 5 mm vermelho | indicadores |
| 7 | Resistor 220 Ω 1/4 W | limitação dos LEDs |
| 7 | Resistor 10 kΩ 1/4 W | pull-down das entradas |
| 1 | Resistor 1 kΩ 1/4 W | base do BC337 |
| 1 | Resistor 100 Ω 1/4 W | descarga do filtro de clock |
| 1 | Resistor 470 kΩ 1/4 W | temporização do 555 |
| 1 | Capacitor 10 µF | temporização do 555 |
| 1 | Capacitor 1 µF | filtro de clock |
| ≈ 14 | Capacitor 100 nF cerâmico | desacoplamento |
| 1 | Capacitor 100 µF eletrolítico | barramento de 12 V |
| 8 | Chave / botão | entradas |

---

## 9. Perguntas prováveis na sabatina

**Por que você não ligou a trava direto na saída da porta lógica?**
Porque a bobina exige 300 mA e a porta fornece 25 mA no máximo absoluto — 12 vezes menos. E porque a trava é de 12 V e a lógica de 5 V; mesmo sem queimar, a força cairia a 17% e a trava não abriria. Seção 4.1.

**Para que serve o diodo em antiparalelo com a bobina?**
Quando o transistor corta, a bobina gera uma tensão reversa v = −L·di/dt para manter a corrente. Sem o diodo, essa tensão chega a centenas de volts e destrói o transistor, que suporta 45 V. O diodo oferece um caminho para a corrente decair, limitando a tensão a 12,8 V. Seção 4.6.

**Como você escolheu o resistor de base?**
Não pelo h_FE da folha de dados, que vale para a região ativa. Impus um ganho forçado três vezes menor que o h_FE mínimo para garantir saturação e calculei R_B no pior caso de tensão de saída da porta. O resultado de 1 kΩ dá 3,7 a 4,3 mA — dentro do que a porta 74HC fornece com nível garantido. Seção 4.4.

**O que acontece se o resistor de base for grande demais?**
O transistor fica na região ativa: V_CE sobe a 7,7 V, dissipa 0,82 W e queima, e a trava recebe um terço da corrente. Seção 4.4.

**Por que o transistor esquenta tão pouco?**
Porque está saturado. V_CE = 0,3 V vezes 292 mA dá 88 mW. A potência vai para a carga, não para a chave. Seção 4.5.

**Por que só o clock tem filtro e as outras chaves não?**
Porque o sistema é síncrono. As entradas de dados são amostradas na borda do clock, e o *bounce* já terminou quando o operador pulsa CLK. O clock é sensível à borda: cada ricochete seria um ciclo. Seção 2.3.

**Por que cada entrada tem um resistor para o terra?**
Porque a entrada CMOS é a porta de um transistor MOS — um capacitor de 5 pF. Deixada em aberto, ela assume o nível que 12 picocoulombs de carga parasita determinarem. O pull-down drena essa carga e define 0. Seção 2.2.

**220 Ω dá 13,6 mA, mas você disse que a porta garante 4 mA. Como?**
A porta *garante* V_OH ≥ 4,4 V até 4 mA; acima disso a tensão cai, mas ela ainda fornece corrente até 25 mA. Como o pino alimenta só o LED, não há nível lógico a preservar naquele nó. Se alimentasse outra porta, precisaria de buffer. Seção 3.3.

**De onde vem o "1,1·RC" do 555?**
Da carga do capacitor até 2/3 de V_CC: 1 − e^(−T/RC) = 2/3 dá T = RC·ln 3 = 1,0986·RC. Seção 5.

**O que é o número 18 200 no banco de dados?**
A energia em milijoules de uma liberação: 12 V × 292,5 mA de bobina, mais 5 V × 4,3 mA de base, vezes 5,16 s de trava aberta. Seção 6.

---

## 10. Referências

- Nexperia. *74HC/HCT04, 74HC/HCT08, 74HC/HCT74, 74HC/HCT14 — Product data sheets.* Níveis lógicos, correntes de saída, atrasos de propagação.
- onsemi. *BC337, BC337-25, BC337-40 — Amplifier Transistors, NPN Silicon.* h_FE, V_CE(sat), P_tot, R_th(j-a).
- Vishay. *1N4001 to 1N4007 — General Purpose Plastic Rectifier.*
- Texas Instruments. *NE555 / TLC555 — Precision Timers.* Configuração monoestável.
- STMicroelectronics. *L78xx — Positive voltage regulator ICs.* Dissipação e resistência térmica do 7805.
- Halliday, D.; Resnick, R.; Walker, J. *Fundamentos de Física, vol. 3 — Eletromagnetismo.* Capacitância, circuitos RC, indutância, lei de Faraday–Lenz.
- Sedra, A. S.; Smith, K. C. *Microeletrônica.* Operação do TBJ em saturação; portas CMOS.
- Horowitz, P.; Hill, W. *The Art of Electronics*, 3ª ed. Acionamento de cargas indutivas, diodo de roda livre, *debounce*.
