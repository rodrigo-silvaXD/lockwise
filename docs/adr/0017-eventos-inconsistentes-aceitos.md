# ADR 0017 — Eventos inconsistentes são aceitos e anotados, não rejeitados

Data: 2026-09-16
Situação: aceita

## Contexto

A projeção do estado da fechadura (ADR 0015) sabe o que é possível no hardware. Um acesso NEGADO com a fechadura BLOQUEADA, por exemplo, não pode acontecer: de BLOQUEADO só se sai com RESET, e sem passar por VERIFICANDO não há NEGADO. Se um evento assim chegar, o que a API faz?

A resposta intuitiva é rejeitar com 422: o evento viola as regras. Mas o gateway não repete 4xx (ADR 0012) — descarta o evento e avisa o operador. Um acesso que aconteceu de verdade no circuito sumiria por causa de um bug de sequência, ou de um evento perdido antes dele.

## Decisão

O evento é aceito (201) e guardado como qualquer outro. A projeção, ao encontrá-lo, mantém o estado que tinha e anota um aviso, que aparece em `GET /fechadura` no campo `avisos`. O histórico fica íntegro; a inconsistência fica visível.

A validação de contrato continua estrita: campo faltando, `resultado` fora do enum, `tentativa` fora de 1–3, `usuario_id` inexistente — tudo isso é 422, porque aí o problema é o payload, não a sequência.

## Alternativas que consideramos

Rejeitar com 422: perde o evento, como descrito. A única vantagem seria um banco "limpo", e um banco limpo com buracos é pior que um banco completo com avisos.

Rejeitar com 409 (conflito): mesmo problema — o gateway trata 4xx como definitivo.

Aceitar silenciosamente, sem aviso: o banco ficaria certo, mas ninguém saberia que a sequência estranhou. O aviso custa uma lista de strings e serve de diagnóstico.

Corrigir o estado da projeção para "fazer sentido" com o evento (por exemplo, assumir que houve um RESET não registrado): inventaria história. A projeção deve refletir o que foi recebido, não o que deveria ter sido.

## Consequências

O banco pode conter sequências impossíveis no hardware. Quem consultar a projeção vê o aviso e pode investigar — na prática, seria um sinal de que o gateway e o circuito saíram de sincronia durante a operação, ou de que um evento se perdeu antes da fila entrar em ação.

A projeção precisa ser tolerante: nunca levanta exceção por causa de um evento, só anota. Isso está testado com a sequência BLOQUEADO seguido de NEGADO.
