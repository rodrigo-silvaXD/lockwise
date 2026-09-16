# ADR 0011 — Contrato de eventos: só transições, senhas não transmitidas, um morador

Data: 2026-09-16
Situação: aceita

## Contexto

Definir o que o gateway envia para a nuvem, quando, e com quais campos. Isso é o contrato entre as duas metades do projeto, e as duas equipes (ou os dois módulos) precisam concordar antes de escrever código de cada lado.

## Decisão

Um evento nasce apenas quando a máquina de estados muda de estado. Nunca por leitura periódica.

| Transição | O que vai para a nuvem |
|---|---|
| VERIFICANDO → LIBERADO | acesso `LIBERADO`, `energia_mj = 18200`, `usuario_id = 1`, número da tentativa |
| VERIFICANDO → AGUARDANDO | acesso `NEGADO`, energia zero, sem usuário, tentativa 1 ou 2 |
| VERIFICANDO → BLOQUEADO | acesso `BLOQUEADO` (tentativa 3) e, junto, alerta `BLOQUEIO` |
| BLOQUEADO → AGUARDANDO (RESET) | alerta `DESBLOQUEIO_ADMIN` |

A senha digitada nunca sai do gateway. Só o resultado. O `momento` é o instante da transição, em UTC. O `usuario_id` é sempre 1: o circuito tem uma senha gravada, logo um morador.

O campo `tentativa` não estava no esquema original do banco e foi adicionado, porque o gateway sabe em qual tentativa o acesso aconteceu e essa informação é útil para a política de supervisão da nuvem.

## Alternativas que consideramos

Enviar o estado a cada borda de clock: gera ruído (a maioria das bordas não muda nada de interessante) e empurra para a nuvem a responsabilidade de descobrir o que aconteceu. A transição já é a informação.

Enviar a senha errada digitada: não ajuda em nada — a nuvem não faz nada com ela — e é o tipo de dado que não se transmite. Um atacante que erra por um bit não deve ter isso registrado em lugar nenhum.

Ignorar o RESET: perde o registro de que houve intervenção administrativa, que é justamente o que um administrador quer ver. Modelar o desbloqueio como um `resultado` na tabela de acesso: não é um acesso; é um alerta que se resolve.

Enviar TIMEOUT (LIBERADO → AGUARDANDO): não é informação nova — a duração é fixa por construção (ADR 0006). A nuvem sabe quando a trava fechou porque conhece o temporizador.

## Consequências

A tabela `acesso` ganhou a coluna `tentativa`. A tabela `alerta` é compartilhada: recebe alertas do gateway (`BLOQUEIO`, `DESBLOQUEIO_ADMIN`) e da própria nuvem (ADR 0015).

O backend precisa aceitar exatamente estes payloads. Um teste do backend copia a saída real do gateway e verifica que é aceita; se o contrato mudar de um lado só, ele quebra.
