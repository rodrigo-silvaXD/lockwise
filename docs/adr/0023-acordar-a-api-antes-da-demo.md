# ADR 0023 — Acordar a API antes da demonstração

Data: 2026-09-22
Situação: aceita

## Contexto

O serviço no plano gratuito do Render hiberna depois de alguns minutos sem tráfego. A primeira requisição depois disso espera o contêiner subir: de dez a trinta segundos, às vezes mais.

O retry do gateway (ADR 0012) cobre falhas curtas: três tentativas com esperas de 0,5 s, 1 s e 2 s, e cinco segundos de tempo limite por tentativa — no pior caso, uns vinte e três segundos. Contra uma hibernação de trinta segundos, isso não basta. O primeiro acesso da demonstração cairia na fila e o operador precisaria digitar `fila` para reenviar. Funciona, mas é exatamente o tipo de hesitação que não se quer na frente do avaliador nos primeiros trinta segundos da apresentação.

## Decisão

O gateway ganhou um comando `acordar`, que chama `GET /health` a cada dois segundos até a API responder ou até esgotar o tempo (sessenta segundos por padrão). Quando o gateway inicia apontando para uma API — e não no modo eco —, ele faz isso automaticamente e avisa na tela: "acordando a API... no ar". Só depois processa a fila pendente e entrega o terminal ao operador.

O `--espera-acordar 0` desliga o comportamento, para quem estiver testando contra uma API local que já está de pé.

## Alternativas que consideramos

Aumentar o tempo limite dos POSTs para trinta segundos: resolveria a hibernação, mas atrasaria todo erro de rede legítimo. Um cabo solto passaria a travar o gateway por dois minutos antes de enfileirar.

Um serviço externo pingando a API de minuto em minuto para ela nunca dormir: funciona, mas é gambiarra contra o plano gratuito, gasta as horas mensais do serviço e continua deixando a demonstração dependente de um terceiro estar de pé.

Confiar na fila e explicar ao avaliador: honesto, mas a demonstração vale 35% e a primeira impressão importa. Custa quinze linhas evitar.

Um passo manual no roteiro de ensaio ("antes de começar, abra a URL no navegador"): é o que faríamos sem o comando. Automatizar é mais confiável do que lembrar.

## Consequências

Iniciar o gateway contra uma API hibernada leva até meio minuto antes de aceitar comandos. É meio minuto na preparação, não durante a apresentação, e a tela diz o que está acontecendo.

Se a API não responder no tempo, o gateway avisa e abre mesmo assim: os eventos vão para a fila e são reenviados quando ela voltar. Nada se perde, como antes.

O `/health` ganhou um segundo papel além da observabilidade: é o que o CI consulta depois do deploy (ADR 0022) e o que o gateway usa para acordar o serviço.
