# ADR 0012 — Entrega resiliente: retry, fila offline, momento preservado

Data: 2026-09-16
Situação: aceita

## Contexto

A demonstração acontece numa sala de aula, com o Wi-Fi que houver, contra uma API hospedada em um plano gratuito que hiberna quando fica sem tráfego e demora alguns segundos para acordar. Uma requisição perdida no meio da demonstração seria um acesso que o circuito registrou e a nuvem não — o pior cenário possível na frente do avaliador.

## Decisão

Quando um POST falha por erro de conexão ou resposta 5xx, o gateway tenta de novo três vezes, esperando 0,5 s, 1 s e 2 s. Se ainda assim falhar, o evento vai para um arquivo JSON Lines em disco e o operador vê "enfileirado" na tela. Na próxima vez que o gateway iniciar, ou quando o operador digitar `fila`, os eventos pendentes são reenviados. O `momento` de cada evento é o original — o instante em que a trava abriu —, não o instante do reenvio.

Respostas 4xx não são repetidas nem enfileiradas. Um 4xx significa que o gateway e a API discordam sobre o contrato; repetir não resolve, e enfileirar só adiaria o mesmo erro. O operador vê "rejeitado" e o código, e alguém precisa olhar.

## Alternativas que consideramos

Sem retry, só fila: cada soluço de rede geraria um evento enfileirado, e a demonstração ficaria cheia de "enfileirado" mesmo com a API no ar. As três tentativas cobrem a hibernação do plano gratuito, que é o caso mais comum.

Retry infinito: travaria o gateway numa API fora do ar. Três tentativas somam 3,5 s de espera, o suficiente para o operador perceber e continuar.

Enfileirar também os 4xx: um evento malformado ficaria na fila para sempre, falhando a cada reenvio. Melhor que ele apareça uma vez e seja descartado, com o erro visível.

Usar o momento do reenvio: mais simples, mas distorceria a demanda horária. Um acesso das 8h reenviado às 10h contaria na faixa errada, e a escala de vigilância calculada a partir disso estaria errada.

## Consequências

Nenhum acesso se perde por queda de rede. Testamos derrubando a API no meio de um roteiro, vendo o evento ir para a fila, religando a API e vendo o reenvio na inicialização com o timestamp original.

A fila é um arquivo local, sem lock. Se dois gateways rodassem na mesma pasta ao mesmo tempo poderiam corromper o arquivo. Não é um cenário do projeto: há um circuito e um gateway.

Um 4xx desaparece depois de mostrado. É deliberado, mas significa que o operador precisa estar olhando. A alternativa — guardar rejeitados num arquivo separado — pode ser adicionada se algum dia fizer falta.
