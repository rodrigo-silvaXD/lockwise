# LOCKWISE — Relatório técnico

**Sistema de controle de acesso com circuito digital simulado, backend em nuvem e otimização da escala de vigilância**

ExpoTech 2026.2 — Missão 2050 · Categoria INTERFACE · Engenharia da Computação · UniFECAF

---

## Resumo

O LOCKWISE é uma fechadura eletrônica cujo circuito digital valida uma senha de 4 bits e bloqueia o sistema após três tentativas incorretas. Cada evento de acesso é enviado a uma API hospedada em nuvem pública, persistido em banco gerenciado, e o histórico acumulado alimenta um modelo de programação linear inteira que determina a escala de vigilância de menor custo.

O projeto atravessa cinco disciplinas, e o que as une não é o tema: é **um único dado**. O evento de acesso nasce numa transição da máquina de estados, carrega a energia calculada no memorial de física, viaja por HTTPS, é persistido em PostgreSQL e reaparece agregado por hora como a demanda de um modelo de otimização.

```
[CIRCUITO]      a máquina de estados decide liberar ou bloquear
     ↓          justificado por
[FÍSICA]        corrente e potência do acionamento da trava → 18 200 mJ
     ↓          transportado por
[GATEWAY]       gêmeo digital, equivalência provada contra o .circ
     ↓          persistido em
[NUVEM]         API no Render + PostgreSQL gerenciado na Neon
     ↓          agregado por hora, alimenta
[OTIMIZAÇÃO]    escala de vigilância: 26,6% mais barata que a ingênua
```

Resultados verificáveis: **238 testes automatizados**, pipeline de CI/CD verde, API pública em <https://lockwise-api.onrender.com>, e 28 registros de decisão documentando o porquê de cada escolha.

---

## 1. Eletrônica digital

**Documento completo:** [`eletronica.md`](eletronica.md)

O circuito foi desenvolvido em Logisim-evolution 4.1.0 e combina um bloco **combinacional** com dois blocos **sequenciais** — o roteiro pedia um *ou* outro.

### 1.1 Comparador (combinacional)

A tabela-verdade de quatro variáveis tem um único mintermo, m₁₁. O mapa de Karnaugh confirma que não há adjacência para agrupar: a expressão é irredutível.

```
IGUAL = S3 · S̄2 · S1 · S0
```

A implementação usa dois estágios — `P1 = S3·S̄2`, `P2 = S1·S0`, `IGUAL = P1·P2` — por associatividade. Não é simplificação lógica; é redução de *fan-in* de quatro para duas entradas, que é o que os CIs da família 74HC oferecem.

### 1.2 Máquina de estados (sequencial)

Quatro estados em dois flip-flops D, codificação binária, sem estados inválidos.

| Estado | Q1 Q0 | Sai quando |
|---|:---:|---|
| AGUARDANDO | 00 | CONFIRMA = 1 |
| VERIFICANDO | 01 | compara a senha |
| LIBERADO | 10 | TIMEOUT = 1 |
| BLOQUEADO | 11 | RESET = 1 |

```
D1 = Q̄1·Q0·(IGUAL + E) + Q1·Q̄0·T̄ + Q1·Q0·R̄
D0 = Q̄1·Q̄0·C + Q̄1·Q0·(ĪGUAL·E) + Q1·Q0·R̄
```

### 1.3 Contador de tentativas (sequencial)

```
ERRO = VERIFICANDO · ĪGUAL       E   = C1 · (C0 + ERRO)
CLR  = LIBERADO + RESET          EN  = ERRO · ¬(C1·C0)
DC0  = (C0 ⊕ EN) · C̄LR           DC1 = (C1 ⊕ (C0·EN)) · C̄LR
```

### 1.4 As duas decisões que sustentam o bloco sequencial

**O limiar é antecipado.** `E = C1·(C0 + ERRO)` em vez de `C1·C0`, porque o flip-flop só assume o valor novo *depois* da borda. Com `C1·C0`, a máquina leria `E = 0` no terceiro erro e bloquearia só no quarto.

**O contador satura.** `EN = ERRO·¬(C1·C0)` impede que um contador cheio transborde para `00` e desfaça o bloqueio.

### 1.5 Verificação

Caminho crítico de sete níveis de porta: 193 ns, ou f_máx ≈ 5,2 MHz. O clock é manual, abaixo de 10 Hz — margem de mais de 500 000 vezes, o que torna *glitches* combinacionais irrelevantes.

Quatorze figuras registram a simulação ([`evidencias/`](evidencias/)), incluindo o cronograma que evidencia o comportamento síncrono.

---

## 2. Física aplicada

**Documento completo:** [`fisica.md`](fisica.md)

O Logisim simula lógica, não grandezas físicas. O memorial descreve a **implementação física de referência** e justifica, com cálculo, cada decisão que a lógica não explica. Cobre os três eixos que o roteiro cita.

### 2.1 Eletrostática — por que toda entrada tem pull-down

A entrada CMOS é o terminal de porta de um MOSFET: um capacitor de ~5 pF. Para levá-la ao meio da faixa indefinida bastam 12,5 pC — menos do que um dedo aproximado transfere. O resistor de 10 kΩ drena essa carga e define o nível 0.

O mesmo raciocínio explica o tratamento do clock: filtro RC de τ = 10 ms mais Schmitt-trigger, porque é a **única** entrada sensível à borda. As demais são amostradas com a chave já estável.

### 2.2 Eletrodinâmica — o acionamento

A bobina exige 300 mA; uma saída 74HC entrega 25 mA no máximo absoluto. Doze vezes menos. Daí o transistor.

```
V_BOB = 12 − 0,3 = 11,7 V        I_C = 11,7 / 40 = 292,5 mA
β_F   ≤ h_FE(mín)/3 ≈ 83         I_B ≥ 292,5/83 ≈ 3,5 mA
R_B   = (4,4 − 0,7)/3,5 mA ≈ 1 kΩ
```

O resistor de base foi dimensionado por **ganho forçado**, não pelo h_FE de folha de dados — este vale para a região ativa. Com R_B de 10 kΩ, o transistor ficaria semi-ligado, dissipando 0,82 W contra os 625 mW que suporta.

Saturado, dissipa 91 mW e a junção fica a 43 °C.

### 2.3 Magnetismo — a força e o pico reverso

A força do solenoide é proporcional ao **quadrado** da corrente. A queda de 0,3 V no transistor reduz a força a 95% da nominal; ligar direto na porta lógica a 5 V daria 17%.

No desligamento, a bobina resiste à variação de corrente:

```
v_L = −L·di/dt ≈ 100 mH × 0,2925 A / 1 µs ≈ 29 000 V
```

Contra um V_CEO de 45 V. O diodo 1N4007 em antiparalelo limita o coletor a 12,8 V e dissipa os 4,3 mJ armazenados no campo.

### 2.4 O número que atravessa o projeto

```
P = 12 V × 292,5 mA + 5 V × 4,3 mA = 3,53 W
T = 470 kΩ × 10 µF × ln 3 = 5,16 s          (NE555 monoestável)
E = 3,53 × 5,16 ≈ 18,2 J = 18 200 mJ
```

Cada acesso liberado grava esse valor no banco. É a assinatura física de uma abertura.

---

## 3. Arquitetura e padrões de projeto

**Documento completo:** [`arquitetura.md`](arquitetura.md) — C4 níveis 1 a 4 em Mermaid versionado

### 3.1 Estilo

Camadas com dependências apontando para dentro: `rotas → dependências → serviços → repositórios → domínio`. O domínio não importa FastAPI nem SQLAlchemy, e é isso que permite testá-lo em 0,15 s sem banco nem rede.

### 3.2 Padrões GoF

O roteiro pede dois. São três, e o critério foi **o que neste sistema varia**:

| Padrão | Trabalho | Se não existisse |
|---|---|---|
| **State** | Projeta o estado da fechadura a partir da sequência de eventos | `if estado == …` repetido em cada método |
| **Strategy** | Política de supervisão trocável por variável de ambiente | A regra de alerta presa dentro do serviço |
| **Observer** | Quem é avisado quando um alerta nasce | O serviço dependeria de rede para registrar um acesso |

Factory, Command e Singleton foram considerados e descartados — o documento de arquitetura diz por quê.

### 3.3 SOLID

Cada princípio aponta arquivo e linha em [`arquitetura.md`](arquitetura.md). O exemplo mais direto é o **D**: os serviços recebem `Protocols` no construtor, e quem injeta a implementação concreta é `dependencias.py`.

### 3.4 A arquitetura como restrição executável

`backend/tests/test_arquitetura.py` lê a árvore sintática dos módulos e falha o CI se o domínio importar `fastapi`, `sqlalchemy` ou `pydantic`, se importar de fora do pacote, ou se uma rota falar com o banco sem passar por um serviço.

O desenho não é uma afirmação que envelhece em silêncio: é um teste.

---

## 4. Computação em nuvem

**Documento completo:** [`deploy.md`](deploy.md)

| Exigência | Como foi atendida |
|---|---|
| Deploy real em nuvem pública | <https://lockwise-api.onrender.com> |
| Banco de dados gerenciado | PostgreSQL na Neon |
| Variáveis de ambiente seguras | Chave e string de conexão só nos painéis; nenhum segredo versionado |
| Pipeline de CI/CD | GitHub Actions: testes → deploy → verificação |
| Observabilidade | `/health` com motor, persistência e commit; log estruturado |

### 4.1 O pipeline

Push na `main` → três suítes em paralelo → se passarem, chama o *deploy hook* do Render → o job consulta `/health` até ver **a SHA do commit publicado**.

Esse último passo nasceu de um erro real: a primeira versão verificava apenas `status: ok`, e a versão antiga — que continua respondendo enquanto a nova é construída — satisfazia a condição. O pipeline ficou verde sem ter publicado nada. Falso positivo é pior que verificação nenhuma, porque dá confiança sem base.

A lição generalizada: **uma verificação de deploy precisa checar algo que muda com o deploy**.

### 4.2 Segurança

Escrita exige `X-API-Key` comparada em tempo constante. Leitura é aberta, para o painel não precisar de chave no navegador.

Sem a chave configurada no servidor, a escrita responde **503** — falha fechada. E 5xx de propósito: o gateway trata 5xx como temporário e guarda o evento na fila, enquanto trataria 4xx como definitivo e o descartaria.

---

## 5. Pesquisa operacional

**Documento completo:** [`../otimizacao/README.md`](../otimizacao/README.md)

### 5.1 O problema

Uma portaria precisa de gente nas 24 horas, mas o movimento não é constante. Escalar o mesmo efetivo o dia inteiro cobre a demanda e paga gente parada.

### 5.2 Formulação

```
Conjuntos   H = {0..23} horas         T = {0..5} turnos de 8 h a cada 4 h
Parâmetros  a(t,h) ∈ {0,1}    d_h ∈ ℤ⁺    c_t ∈ ℝ⁺    N_max
Variável    x_t ∈ ℤ⁺

minimizar   Σ_t c_t · x_t
sujeito a   Σ_t a(t,h) · x_t ≥ d_h    ∀h      (cobertura)
            Σ_t x_t ≤ N_max                    (equipe)
```

**Turnos sobrepostos são a decisão que faz o problema existir.** Seis turnos de 4 h sem sobreposição cobririam cada hora uma única vez, e a solução sairia por inspeção. Com 8 h a cada 4 h, cada hora é coberta por dois turnos e a escolha vira combinatória.

### 5.3 Da demanda real ao modelo

```
d_h = max(presença mínima, ⌈ (acessos_h ÷ dias) ÷ K ⌉)
```

A divisão pelos dias é essencial: a rota devolve o acumulado do período. K = 4 vem de estimar quinze minutos de atenção por acesso.

### 5.4 Resultado

| | vigilantes | custo/dia |
|---|---:|---:|
| escala ingênua | 12 | R$ 2.816,00 |
| **escala otimizada** | **9** | **R$ 2.068,00** |
| economia | 3 | **R$ 748,00 — 26,6%** |

Duas leituras do resultado: o modelo **não abre dois dos seis turnos** — o que a restrição proíbe é hora descoberta, não turno vazio — e sobram vigilantes entre 4h e 6h, porque com blocos de 8 h não existe contratar alguém para duas horas. É o custo da granularidade, e aparece explicitamente na tabela de cobertura.

### 5.5 Por que a energia não entra no objetivo

O acionamento consome 0,6 Wh por dia, ou R$ 0,0005 — **cinco ordens de grandeza** abaixo do custo de um turno. Incluí-la no objetivo não mudaria uma única decisão do modelo. Ela entra no relatório como verificação física do histórico.

### 5.6 Verificação do ótimo

Um teste enumera por força bruta todas as escalas viáveis e confirma que nenhuma custa menos que a devolvida pelo CBC. A resposta para "como vocês sabem que é o ótimo?" não é "o solver disse".

---

## 6. Verificação e qualidade

### 6.1 Cobertura de testes

| Módulo | Testes | O que garante |
|---|---:|---|
| Gateway | 107 | Equivalência com o `.circ` em 2048 casos, transporte, CLI |
| Backend | 102 | Domínio, contrato, segurança, arquitetura, demo ponta a ponta |
| Otimização | 29 | Cobertura, sensibilidade, ótimo por força bruta |
| **Total** | **238** | |

### 6.2 Os três testes que sustentam as afirmações centrais

| Afirmação | Teste |
|---|---|
| "O gateway é a mesma máquina do circuito" | `test_netlist.py` lê o `.circ`, simula o grafo de portas e compara nos 2048 casos |
| "O domínio não conhece infraestrutura" | `test_arquitetura.py` lê a AST e falha se houver import proibido |
| "A demo funciona de ponta a ponta" | `test_ponta_a_ponta.py` sobe a API real e roda o gateway real contra ela |

### 6.3 Decisões documentadas

Vinte e oito ADRs em [`adr/`](adr/), uma decisão por arquivo, com contexto, alternativas descartadas e consequências — incluindo as negativas. Uma ADR aceita não é reescrita: se a decisão muda, nasce outra que substitui a anterior.

---

## 7. Limitações

Registradas por honestidade, e porque um avaliador as encontraria de qualquer forma.

**O circuito é digital; a eletrônica analógica é de papel.** O estágio de potência está integralmente dimensionado, com cálculo térmico e de saturação, mas não foi montado em bancada. Montá-lo custaria cerca de R$ 30 em componentes e é o caminho mais direto para fechar essa lacuna.

**O histórico de acessos é sintético.** Os eventos nascem da mesma máquina de estados do gateway e são enviados pela mesma API — o `tentativa`, o `energia_mj` e a ordem dos estados saem corretos porque quem os produz é o circuito replicado. O que difere da operação real é apenas o relógio. Dados reais acumulados até novembro entram no mesmo banco e no mesmo modelo.

**O circuito tem uma senha.** O comparador de 4 bits valida um único código. A tabela `usuario` do banco já modela vários moradores, e o cenário de otimização assume uma portaria de condomínio — o circuito demonstra o controle de um ponto de acesso, não o sistema completo de credenciais.

**A ponte circuito↔gateway é operada por pessoa.** O Logisim não expõe o estado da simulação para fora, e não há caminho suportado para isso. O que garante que os dois lados concordam é a prova de equivalência por teste. Um ESP32 lendo os pinos do circuito montado eliminaria esse passo manual, e o gateway já tem a abstração para receber essa fonte.

---

## 8. Conclusão

Os cinco requisitos do roteiro estão atendidos, e o que os liga é a rastreabilidade de um único dado: os 18 200 mJ que aparecem no banco de dados são doze volts vezes 292,5 miliamperes vezes 5,16 segundos, e cada um desses três fatores tem um cálculo no memorial de física. A demanda que o modelo de otimização consome é o histórico que o circuito gerou.

O que consideramos o diferencial técnico não é nenhuma das cinco partes isoladas, e sim o que as conecta com garantias verificáveis: a equivalência entre o hardware simulado e o software é provada contra o arquivo do circuito, não afirmada; a arquitetura documentada é imposta por teste, não descrita; o ótimo da otimização é conferido por força bruta, não aceito do solver; e o deploy é verificado pela SHA do commit que chegou ao ar.

---

## Referências

- Roteiro da categoria INTERFACE — ExpoTech 2026.2, Núcleo de Tecnologias e Engenharias, UniFECAF
- Regulamento Geral da ExpoTech 2026.2
- Nexperia. *74HC/HCT Family — Product data sheets*
- onsemi. *BC337 — Amplifier Transistors, NPN Silicon*
- Texas Instruments. *NE555 / TLC555 — Precision Timers*
- Halliday, Resnick, Walker. *Fundamentos de Física, vol. 3 — Eletromagnetismo*
- Sedra, A. S.; Smith, K. C. *Microeletrônica*
- Tocci, R.; Widmer, N.; Moss, G. *Sistemas Digitais: Princípios e Aplicações*
- Gamma, E.; Helm, R.; Johnson, R.; Vlissides, J. *Design Patterns: Elements of Reusable Object-Oriented Software*
- Martin, R. C. *Clean Architecture: A Craftsman's Guide to Software Structure and Design*
- Brown, S. *The C4 model for visualising software architecture* — <https://c4model.com>
- Hillier, F.; Lieberman, G. *Introduction to Operations Research*
- Mitchell, S.; O'Sullivan, M.; Dunning, I. *PuLP: A Linear Programming Toolkit for Python*

---

**Repositório:** <https://github.com/rodrigo-silvaXD/lockwise>
**API:** <https://lockwise-api.onrender.com>
