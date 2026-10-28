# Passagem de contexto — LOCKWISE

Cole este arquivo inteiro no primeiro prompt de um chat novo. Ele substitui o
histórico da conversa anterior.

---

## O projeto

LOCKWISE — ExpoTech 2026.2, UniFECAF, Engenharia da Computação, categoria
INTERFACE. Avaliação 09–13/11/2026, evento 28/11/2026.
Repo: https://github.com/rodrigo-silvaXD/lockwise
Local: `C:\Users\rg601\Documents\lockwise`

Equipe: Rodrigo Gonçalves da Silva (RA 98550), Carlos Henrique Barreto
(RA 113749), Fabrício Conceição Silva (RA 114204).

Uma fechadura digital feita em portas lógicas decide o acesso; o mesmo evento
atravessa gateway → nuvem → modelo de otimização e volta como escala de
vigilância. O fio condutor é um dado só: o acesso que carrega 18 200 mJ.

## Como está dividido

| Pasta | O que é | Estado |
|---|---|---|
| `eletronica/` | `.circ` do Logisim-evolution: comparador + FSM de 4 estados + contador saturado, em portas e flip-flops discretos | pronto |
| `docs/fisica.md` | memorial de física, 635 linhas, BOM completa, tudo dimensionado (não montado) | pronto |
| `gateway/` | gêmeo digital em Python puro, equivalência provada contra o `.circ` em 2048 casos | pronto |
| `backend/` | FastAPI + SQLAlchemy 2, três padrões GoF, Clean Architecture verificada por teste de AST | pronto |
| `otimizacao/` | PuLP/CBC, cobertura com 6 turnos de 8 h sobrepostos | pronto |
| `site/index.html` | simulador interativo, publicado no GitHub Pages | pronto |
| `docs/adr/` | 29 ADRs + índice, na voz da equipe ("fizemos", "escolhemos") | pronto |
| `docs/arquitetura.md` | C4 em Mermaid, 5 diagramas validados | pronto |
| `docs/video-pitch.md` | roteiro de 3 min; divisão de falas ainda `*(definir)*` | parcial |
| Fase I | ensaio da sabatina | **nada escrito** |

Nuvem: API no Render (`lockwise-api.onrender.com`), Postgres na Neon,
GitHub Actions com CI que barra o deploy e confere a SHA do commit em `/health`.

## Regras de trabalho que o usuário pediu

1. Commit e push a cada passo — nada fica só local.
2. Toda decisão vira ADR em `docs/adr/`, na primeira pessoa do plural, sem cara
   de IA. Nunca reescrever ADR aceita: nasce uma nova que substitui.
3. Avisar quando uma matéria/fase fecha e outra abre.
4. Nada de ESP32, Wokwi ou Tinkered — foi removido por decisão dele, sem ADR
   nova. Não ressuscitar.
5. No GitHub só o nome dele como autor. Sem "Rodrigo and Claude", sem trailer
   de co-autoria.

## O que falta, em ordem de peso

1. **`git push --force origin main`** — o histórico local foi reescrito
   (31 commits, autor único, sem trailers). `origin/main` ainda está em
   `b9d508e`; o local está em `2872aaa`. Backup do original:
   `refs/original/refs/heads/main`. O comando precisa ser rodado por ele.
2. **Fase I — sabatina.** O regulamento diz que resposta vaga elimina a
   elegibilidade do grupo inteiro. É o maior risco aberto.
3. **Trocar a chave da API** — parte dela apareceu num log colado no chat.
4. **Gravar o vídeo** e preencher quem narra cada bloco.

## Fragilidades conhecidas, para não serem redescobertas

- O hardware está dimensionado mas **não montado**. Declarado em `fisica.md`
  §1.1 e no `relatorio.md` §7. O roteiro aceita circuito simulado.
- O Logisim **não se comunica** com nada. Nunca se comunicou. O gateway é um
  gêmeo digital, e a equivalência é provada por teste, não por cabo.
- A economia da otimização dá R$ 84 480/mês para 50 unidades — irreal, porque
  K=4 (15 min por acesso) é conservador demais. Duas saídas oferecidas e não
  decididas: recalibrar K para ~8, ou reposicionar o cenário para uma
  instalação maior.

## Erros já cometidos, para não repetir

- As equações do README estavam erradas e o circuito certo: o `.circ` tem
  `EN = ERRO·¬(C1·C0)` e `·¬CLR`. Sempre extrair da netlist, nunca copiar doc.
- O deploy ficou verde com a versão antiga no ar, porque checava
  `"status":"ok"`. Hoje compara a SHA do commit.
- O PuLP 4.0 derrubou o CI por duas semanas e, como o CI barra o deploy, um
  commit não chegou à produção por 14 dias. Causa de processo: rodar teste
  local, dizer "verde" e não olhar o CI. Resolvido com `pulp<4` + `getattr`.
