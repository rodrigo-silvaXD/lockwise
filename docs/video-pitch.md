# Vídeo pitch — roteiro

Três minutos, exigidos pelo regulamento geral da ExpoTech (não pelo roteiro da INTERFACE, e é por isso que costuma ser esquecido).

Três minutos é pouco. A escolha aqui é **mostrar o sistema funcionando** em vez de narrar o que ele faz: quem assiste precisa ver o dado nascer no circuito e chegar na nuvem. Slides explicativos consomem tempo e não provam nada.

---

## Estrutura

| Tempo | Bloco | O que aparece na tela |
|---|---|---|
| 0:00–0:20 | O problema | Fala, sobre a tela do circuito parado |
| 0:20–0:40 | O circuito | Logisim, senha correta, trava abre |
| 0:40–1:10 | O bloqueio | Três erros, contador subindo, BLOQUEADO |
| 1:10–1:50 | A ponte | Gateway ao lado, POSTs saindo, 201 |
| 1:50–2:20 | A nuvem | Navegador: `/fechadura`, `/acessos`, banco |
| 2:20–2:50 | A otimização | Relatório com os 26,6% |
| 2:50–3:00 | Fecho | Equipe e o repositório |

---

## Texto

### 0:00–0:20 · O problema

> Uma fechadura eletrônica precisa decidir sozinha quem entra. Mas a decisão dela, sozinha, não vale muito: quem administra um prédio quer saber **quando** as pessoas entram, **quantas** tentativas falharam, e **quantos vigilantes** precisa ter em cada turno.
>
> O LOCKWISE liga essas duas pontas. Um circuito digital decide o acesso, e o mesmo evento atravessa até virar uma escala de trabalho.

*Tela: o circuito no Logisim, parado, com AGUARDANDO aceso.*

---

### 0:20–0:40 · O circuito

> O circuito compara uma senha de quatro bits e governa uma máquina de estados de quatro estados. Tudo em portas lógicas e flip-flops — nenhum componente pronto.

*Tela: digitar `1011`, SENHA_OK acende. CONFIRMA, clock → VERIFICANDO. Clock → TRAVA_ABERTA.*

> Senha certa: a trava abre.

---

### 0:40–1:10 · O bloqueio

> Agora o contrário.

*Tela: três tentativas erradas, mostrando o contador `01` → `10` → `11`.*

> Um erro, dois erros. No terceiro, o contador satura e o sistema bloqueia. E repare: **o bloqueio acontece na terceira tentativa, não na quarta**. O sinal de limiar é calculado antes da borda de clock, porque o flip-flop só assume o valor novo depois dela.

*Tela: tentar `1011` com o sistema bloqueado — não adianta. RESET libera.*

> Nem a senha certa destrava. Só a intervenção administrativa.

---

### 1:10–1:50 · A ponte

> O Logisim não fala com a internet. Então o gateway é a mesma máquina de estados escrita em Python — e a equivalência não é promessa, é teste.

*Tela: rodar `pytest tests/test_netlist.py`, mostrar verde.*

> Esse teste lê o arquivo do circuito, reconstrói a netlist e compara com o Python em **todas** as combinações possíveis de estado e entrada.

*Tela: duas janelas lado a lado — Logisim e gateway. Repetir a senha correta nos dois.*

> Mesmo gesto dos dois lados. E aqui o evento sai para a nuvem.

*Tela: `POST /acessos → enviado HTTP 201`.*

---

### 1:50–2:20 · A nuvem

*Tela: navegador em `lockwise-api.onrender.com/fechadura`.*

> A API está no Render, com Postgres gerenciado na Neon. Ela reconstrói o estado da fechadura a partir dos eventos — é a mesma máquina de estados pela terceira vez, agora projetando o passado.

*Tela: `/acessos` mostrando o registro recém-criado, com o `energia_mj`.*

> E cada liberação carrega dezoito mil e duzentos milijoules. Esse número não é enfeite: é doze volts vezes duzentos e noventa e dois miliamperes vezes cinco vírgula dezesseis segundos — cada fator calculado no memorial de física.

---

### 2:20–2:50 · A otimização

*Tela: rodar o `resolver`, deixar o relatório aparecer.*

> O histórico de acessos vira a demanda de um modelo de programação linear inteira. Seis turnos de oito horas que se sobrepõem, e a pergunta: quantos vigilantes em cada um, ao menor custo, sem deixar hora descoberta?

*Tela: destacar o bloco da economia.*

> Nove vigilantes contra doze da escala ingênua. Vinte e seis por cento mais barato — vinte e dois mil reais por mês.

---

### 2:50–3:00 · Fecho

*Tela: página do repositório no GitHub.*

> Circuito, física, arquitetura, nuvem e otimização. Um evento atravessando as cinco.
>
> LOCKWISE. Código e decisões, abertos no GitHub.

---

## Antes de gravar

- [ ] Acordar a API (`/health` no navegador) — o plano gratuito hiberna
- [ ] Semear o histórico, se o banco estiver vazio
- [ ] Logisim com o circuito aberto e a simulação reiniciada
- [ ] Gateway já apontando para produção (`.\demo.ps1`) e **acordado**
- [ ] Fonte do terminal aumentada — texto pequeno não se lê em vídeo
- [ ] Ensaiar uma vez inteiro, cronometrando

## Erros que custam caro

**Falar sobre em vez de mostrar.** Cada segundo de slide é um segundo a menos de sistema funcionando.

**Estourar o tempo.** Três minutos é limite, não sugestão. Se faltar tempo, corte o bloco do bloqueio (0:40–1:10) — é o mais longo e o menos essencial.

**Gravar a tela pequena.** O que não se lê no celular não existe.

**Pressa no 1:50–2:20.** É o trecho que prova que o sistema é real. Se algo tiver que respirar, é esse.

## Divisão de falas

O regulamento avalia domínio individual. Vale cada integrante narrar o bloco da sua responsabilidade — e isso também ajuda no ensaio da sabatina, que cobra exatamente isso.

| Bloco | Quem narra |
|---|---|
| Problema e circuito | *(preencher)* |
| Bloqueio e física | *(preencher)* |
| Gateway e nuvem | *(preencher)* |
| Otimização e fecho | *(preencher)* |
