# Vídeo pitch — roteiro

Três minutos, exigidos pelo regulamento geral da ExpoTech (não pelo roteiro da INTERFACE, e é por isso que costuma ser esquecido).

Três minutos é pouco. A escolha aqui é **mostrar o sistema funcionando** em vez de narrar o que ele faz: quem assiste precisa ver o dado nascer no circuito e chegar na nuvem. Slides explicativos consomem tempo e não provam nada.

## Formato

**Captura de tela com narração em voz. Ninguém aparece.** Sem webcam, sem
câmera, sem foto da equipe — a tela é a única imagem do vídeo inteiro. Isso
combina com a escolha acima: os três minutos ficam todos para o sistema.

**Narram o Carlos e o Fabrício.** O Rodrigo não participa da gravação. Isso
não tem efeito na nota individual: o regulamento avalia domínio individual na
sabatina, em sala, não no vídeo. Mas tem um efeito prático — como nenhum
rosto aparece, **cada um se identifica pela voz na primeira fala**, senão
quem assiste não sabe quem é quem.

A equipe inteira, com os três nomes e RAs, aparece escrita na tela do fecho.

---

## Estrutura

| Tempo | Bloco | Narra | O que aparece na tela |
|---|---|---|---|
| 0:00–0:20 | O problema | Carlos | Fala, sobre a tela do circuito parado |
| 0:20–0:40 | O circuito | Carlos | Logisim, senha correta, trava abre |
| 0:40–1:10 | O bloqueio | Carlos | Três erros, contador subindo, BLOQUEADO |
| 1:10–1:50 | A ponte | Fabrício | Gateway ao lado, POSTs saindo, 201 |
| 1:50–2:20 | A nuvem | Fabrício | Navegador: `/fechadura`, `/acessos`, banco |
| 2:20–2:50 | A otimização | Fabrício | Relatório com os 26,6% |
| 2:50–3:00 | Fecho | Carlos | Equipe e o repositório |

A divisão segue o assunto, não o cronômetro: o **Carlos** fica com o hardware
— o circuito, o bloqueio e a física que os sustenta — e o **Fabrício** com o
software e a matemática — a ponte, a nuvem e a otimização. Dá 80 segundos de
fala para um e 100 para o outro, e cada um narra o que estudou mais a fundo.

Essa divisão vale **só para o vídeo**. Na sabatina cada um responde sobre
qualquer parte; ver `docs/sabatina.md`.

---

## Texto

### 0:00–0:20 · O problema — **Carlos**

> Aqui é o Carlos, do projeto LOCKWISE.
>
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

### 1:10–1:50 · A ponte — **Fabrício**

> Aqui é o Fabrício.
>
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

### 2:50–3:00 · Fecho — **Carlos**

*Tela: página do repositório no GitHub, com os três nomes e RAs sobrepostos —
Rodrigo Gonçalves da Silva (98550), Carlos Henrique Barreto (113749),
Fabrício Conceição Silva (114204).*

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

| Blocos | Quem narra | Tempo |
|---|---|:--:|
| O problema · O circuito · O bloqueio · Fecho | **Carlos** | 80 s |
| A ponte · A nuvem · A otimização | **Fabrício** | 100 s |

O Rodrigo não narra. Os três nomes aparecem na tela do fecho.

## Gravar sem aparecer

Como ninguém aparece, tudo depende do que se lê na tela e do que se ouve.

**Captura.** Gravar a tela em 1920×1080, 30 fps. No Windows serve a Game Bar
(`Win+G`) ou o OBS, que é melhor porque permite marcar a região e trocar de
cena sem cortar. **Desligar qualquer sobreposição de webcam** — é o erro mais
fácil de cometer e o único que invalida a escolha de formato.

**Antes de gravar a tela:** fechar notificações (modo foco), limpar a barra de
tarefas, sair de contas pessoais visíveis no navegador, e aumentar a fonte do
terminal e do editor. O que não se lê no celular não existe.

**Voz.** Gravar numa sala sem eco, com o microfone perto. Se as duas falas
forem gravadas em lugares diferentes, deixar o volume parecido — corte com
mudança brusca de som chama mais atenção que corte de imagem.

**Montagem.** Cada um grava seus blocos separado e junta depois. A troca de
narrador cai sempre numa troca de tela (0:00→1:10 Carlos, 1:10→2:50 Fabrício,
2:50 Carlos), então a emenda fica escondida.

**Nomear o arquivo:** `lockwise-pitch.mp4`, até 3:00 cravados.
