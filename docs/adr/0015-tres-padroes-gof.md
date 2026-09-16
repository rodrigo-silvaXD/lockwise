# ADR 0015 — Três padrões GoF, cada um com um trabalho real

Data: 2026-09-16
Situação: aceita

## Contexto

O requisito de arquitetura pede ao menos dois padrões GoF e princípios SOLID no backend. O risco conhecido desse tipo de requisito é o padrão de enfeite: uma classe `Singleton` que ninguém precisava, um `Factory` que constrói uma coisa só. Numa sabatina, "por que esse padrão está aqui?" precisa ter uma resposta que não seja "porque o roteiro pediu".

O backend recebe eventos, guarda e responde consultas. O que nele varia, e portanto justifica um padrão?

## Decisão

Três padrões, escolhidos pelo trabalho que fazem.

State (`dominio/estados.py`). A nuvem não vê os pinos do circuito; vê a sequência de eventos que o gateway enviou. Para responder "a fechadura está aberta agora?", precisa reconstruir o estado a partir dessa sequência. Cada classe de estado (Aguardando, Liberado, Bloqueado) sabe o que cada evento significa para ela e para onde leva. É a mesma máquina de estados do circuito e do gateway, pela terceira vez, com um trabalho diferente: projeção. Duas adaptações deliberadas: não há VERIFICANDO, porque a nuvem só recebe o resultado da verificação; e LIBERADO expira sozinho após 5,16 s, porque o gateway não envia TIMEOUT e a nuvem conhece o temporizador (ADR 0006).

Strategy (`dominio/politicas.py`). O hardware decide bloquear após três erros; isso não se muda por software. O que a nuvem decide é quando avisar alguém, e essa decisão depende do contexto de uso: uma casa quer saber de tentativas suspeitas antes do bloqueio; um condomínio quer saber de acesso fora do horário. A política é um objeto trocado por variável de ambiente — `limite`, `horario`, `composta`, `nenhuma` — e o serviço que registra acessos não sabe qual está em uso.

Observer (`dominio/notificacao.py`). Quando um alerta nasce, alguém precisa saber. Hoje é o log; opcionalmente um webhook do Discord da equipe. Quem cria o alerta não conhece os interessados; eles se inscrevem. Um observador que falha (webhook fora do ar) é isolado e registrado, nunca derruba o registro do acesso.

## Alternativas que consideramos

Só os dois obrigatórios (State e Strategy): o Observer custou quarenta linhas e resolve um problema real — sem ele, o webhook seria uma chamada dentro do serviço, e o serviço passaria a depender de rede.

Factory como terceiro padrão: existe uma fábrica (`politica_por_nome`), mas é uma função com um dicionário; chamá-la de "padrão Factory" seria inflar. Está lá porque é útil, não porque conta ponto.

Command para os eventos: não há desfazer, não há fila de comandos, não há macro. Não teria trabalho.

Singleton para o notificador: a instância única é garantida pela composição em `main.py`, sem a classe precisar saber disso. Singleton como padrão dificulta teste e não acrescenta nada.

## Consequências

O domínio (`dominio/`) não importa FastAPI nem SQLAlchemy. Os trinta testes dele rodam em 0,15 s e não precisam de banco.

O SOLID emerge da estrutura em vez de ser aplicado depois: responsabilidade única porque cada serviço faz uma coisa, aberto/fechado porque uma política nova é uma classe nova sem tocar no serviço, substituição porque qualquer estado ou política é usado pelo mesmo código, interfaces segregadas porque cada serviço recebe só os repositórios que usa, inversão de dependência porque os serviços dependem de Protocols e a composição (`dependencias.py`) injeta as implementações. O README do backend mapeia cada princípio ao arquivo.

Três encarnações da mesma FSM (circuito, gateway, nuvem) é redundância deliberada. A do circuito e a do gateway são provadas equivalentes (ADR 0009). A da nuvem tem um propósito diferente — projetar a partir de eventos, com tolerância a sequências impossíveis (ADR 0017) — e é testada separadamente.
