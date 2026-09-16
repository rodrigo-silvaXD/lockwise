# ADR 0021 — Commit e push a cada passo; ADRs junto do código

Data: 2026-09-16
Situação: aceita

## Contexto

Dois riscos de projeto, não de código. O primeiro é perder trabalho: uma máquina que quebra, um disco que falha, uma pasta apagada sem querer, com semanas de trabalho só locais. O segundo é perder o porquê: em novembro, na sabatina, alguém vai perguntar "por que o gateway não lê o Logisim diretamente?" ou "por que a leitura da API é aberta?", e a resposta precisa existir por escrito, na voz de quem decidiu, não reconstruída de memória.

O regulamento pesa 20% em "documentação e GitHub" e avisa que o repositório precisa estar organizado e o código documentado.

## Decisão

Todo bloco de trabalho concluído vira um commit com mensagem que diz o que mudou e por quê, e é enviado ao GitHub na hora. Não existe trabalho "só local" no fim de uma sessão.

Toda decisão que molda a arquitetura — escolha de ferramenta, de padrão, de contrato, de comportamento em caso de erro — vira um registro em `docs/adr/`, numerado, com contexto, decisão, alternativas descartadas e consequências, incluindo as negativas. A ADR é escrita quando a decisão é tomada, no mesmo commit do código que ela justifica. Uma ADR aceita não é reescrita: se a decisão mudar, nasce outra que substitui a anterior, e a anterior recebe a marca de substituída.

As ADRs são escritas em prosa, como notas de um engenheiro para o colega que vai continuar o trabalho. Datas, nomes de arquivo, números. Sem floreio.

## Alternativas que consideramos

Um único documento de contexto crescendo: é o que `docs/CONTEXTO_LOCKWISE.md` faz, e ele continua útil como visão geral e plano de fases. Mas um documento único vira um lugar onde decisões antigas são sobrescritas pelas novas, e o histórico de "por que mudamos" se perde. As ADRs são imutáveis por definição.

Registrar decisões só nas mensagens de commit: as mensagens têm o quê e um pouco do porquê, mas não as alternativas descartadas nem as consequências. E ninguém lê `git log` na sabatina.

Commits grandes no fim de cada fase: menos ruído no histórico, mais risco. Um commit por bloco de trabalho é o compromisso.

## Consequências

O histórico do repositório conta a história do projeto na ordem em que aconteceu. O índice em `docs/adr/README.md` é a lista de decisões; qualquer integrante consegue responder "por quê" apontando um arquivo.

Custo: cada decisão pede alguns minutos de escrita a mais. Vinte e uma ADRs foram escritas retroativamente em 16/09 para cobrir tudo desde a inscrição; daqui em diante, são escritas na hora.
