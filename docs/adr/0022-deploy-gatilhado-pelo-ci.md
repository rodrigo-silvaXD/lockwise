# ADR 0022 — Deploy disparado pelo CI, não pelo push

Data: 2026-09-22
Situação: aceita

## Contexto

O Render, quando conectado a um repositório, tem uma opção de deploy automático a cada commit na branch principal. É o caminho mais fácil: dois cliques e todo push vai para o ar.

O problema é que "todo push" inclui o push com o teste quebrado. Numa equipe de quatro pessoas mexendo em cinco disciplinas nas semanas que antecedem a avaliação, é questão de tempo até alguém enviar código que não passa. Se isso derrubar a API, e derrubar na véspera, perdemos o quesito que vale 35%.

O requisito de cloud também pede pipeline de CI/CD, e "o Render faz deploy sozinho" é uma resposta pobre para "me mostre seu pipeline".

## Decisão

O `autoDeployTrigger` fica desligado no `render.yaml`. Quem manda deployar é o GitHub Actions, depois que os testes passam.

São dois workflows. O primeiro (`ci.yml`) roda as duas suítes em jobs separados a cada push e pull request: o gateway, que inclui a prova de equivalência contra o arquivo `.circ`, e o backend, que inclui a demo ponta a ponta. O segundo (`deploy.yml`) é disparado pela conclusão do primeiro, verifica que ele terminou em sucesso, chama o deploy hook do Render e depois fica consultando `/health` até a API responder com status ok — por até dez minutos, porque o plano gratuito hiberna e o build leva alguns minutos.

Se os segredos não estiverem configurados, o workflow de deploy avisa e termina sem falhar. Isso permite que o pipeline fique verde antes de a infraestrutura existir, em vez de mostrar vermelho por um motivo que não é erro.

## Alternativas que consideramos

Deploy automático do Render a cada commit: simples, mas publica código quebrado. Descartado pelo motivo acima.

Deploy só por gatilho manual: seguro, mas depende de alguém lembrar. E na véspera da avaliação, "alguém lembrar" não é um plano.

Render Preview Environments por pull request: bom em projeto de produção, mas cada ambiente consome recursos do plano gratuito, e não temos fluxo de PR na equipe.

Uma action oficial do Render em vez de `curl` no deploy hook: a action existe, mas exige uma chave de API com permissão ampla. O deploy hook é uma URL secreta que só sabe fazer uma coisa — disparar um deploy daquele serviço. Menos permissão, menos dependência.

## Consequências

Entre o push e a API atualizada passam alguns minutos: os testes, mais o build, mais o arranque. É o preço de não publicar código quebrado.

Dois segredos precisam ser configurados no GitHub uma vez: `RENDER_DEPLOY_HOOK_URL` e `LOCKWISE_API_URL`. Estão documentados no README do backend e no próprio workflow.

O passo que espera o `/health` transforma o pipeline em verificação de verdade: não basta o Render aceitar o pedido de deploy, a API precisa responder que está viva e com o banco acessível. Se o deploy subir quebrado, o pipeline fica vermelho e alguém descobre na hora, não na avaliação.

## Atualização de 22/09 — o primeiro deploy automático mostrou um furo

Na primeira execução com os segredos configurados, o pipeline ficou verde e a API continuou na versão antiga. O passo de verificação procurava `"status":"ok"` na resposta do `/health`, e a versão anterior — que segue no ar enquanto a nova é construída — responde exatamente isso. O pipeline aprovou o deploy conferindo o serviço que já estava rodando.

Falso positivo é pior que verificação nenhuma: dá confiança sem base. Corrigido para comparar a versão. O job agora lê `__version__` de `backend/lockwise_api/__init__.py` no commit que está sendo publicado e só termina quando o `/health` responde aquela versão. De quebra, exige `"persistente":true`, para que um deploy sem `DATABASE_URL` — que sobe e responde ok em SQLite efêmero — também seja reprovado.

A lição vale além deste caso: uma verificação de deploy precisa checar algo que *muda* com o deploy. `status: ok` não muda; a versão muda.
