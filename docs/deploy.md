# Deploy e pipeline

Como a API do LOCKWISE vai para o ar e como o pipeline decide publicar.

```
push na main
    │
    ▼
GitHub Actions — testes            gateway: 107 testes (inclui a prova contra o .circ)
    │                              backend: 69 testes (inclui a demo ponta a ponta)
    │ só se passar
    ▼
GitHub Actions — deploy            chama o deploy hook do Render
    │                              e espera /health responder ok (até 10 min)
    ▼
Render                             lockwise-api + lockwise-db (Postgres)
```

A infraestrutura está versionada em [`render.yaml`](../render.yaml) e os workflows em [`.github/workflows/`](../.github/workflows/).

---

## Primeira vez: criar a infraestrutura

Precisa ser feito uma vez, por quem tem a conta do Render.

**1. Criar o blueprint.** No painel do Render: **New → Blueprint**, escolha o repositório `lockwise`, confirme. O Render lê o `render.yaml` e cria dois recursos: o banco `lockwise-db` (Postgres 16, plano gratuito) e o serviço `lockwise-api`.

O primeiro build leva alguns minutos. Ele instala as dependências do `backend/pyproject.toml` e sobe o uvicorn. As tabelas e o usuário morador são criados no arranque, automaticamente — não há migração para rodar.

**2. Anotar a URL.** Algo como `https://lockwise-api.onrender.com`. Confirme que está no ar:

```bash
curl https://lockwise-api.onrender.com/health
```

Deve responder `{"status":"ok","banco":"ok",...}`. A documentação interativa fica em `/docs`.

**3. Copiar a chave da API.** No serviço `lockwise-api`, aba **Environment**, a variável `LOCKWISE_API_KEY` foi gerada pelo próprio Render. Copie o valor: é o que o gateway usa para escrever. Não coloque esse valor em nenhum arquivo do repositório.

**4. Pegar o deploy hook.** No serviço, **Settings → Deploy Hook**. É uma URL secreta que dispara um deploy quando chamada.

**5. Configurar os segredos no GitHub.** No repositório, **Settings → Secrets and variables → Actions → New repository secret**, dois segredos:

| Nome | Valor |
|---|---|
| `RENDER_DEPLOY_HOOK_URL` | a URL do passo 4 |
| `LOCKWISE_API_URL` | a URL do passo 2, sem barra no fim |

Sem eles o workflow de deploy não falha — avisa que faltam e termina. Com eles, todo push na `main` que passar nos testes publica sozinho.

---

## Apontar o gateway para a nuvem

```bash
cd gateway
export LOCKWISE_API_URL=https://lockwise-api.onrender.com
export LOCKWISE_API_KEY=<a chave do passo 3>
python -m lockwise_gateway.cli
```

No Windows, no PowerShell:

```powershell
$env:LOCKWISE_API_URL = "https://lockwise-api.onrender.com"
$env:LOCKWISE_API_KEY = "<a chave do passo 3>"
python -m lockwise_gateway.cli
```

O gateway acorda a API sozinho antes de aceitar comandos, porque o plano gratuito hiberna (ADR 0023). A tela mostra `acordando a API... no ar`.

---

## No dia da avaliação

Meia hora antes, na ordem:

1. Abrir `https://lockwise-api.onrender.com/health` no navegador. Se demorar, é a hibernação; espere responder.
2. Conferir que o pipeline está verde na aba Actions do GitHub.
3. Subir o gateway com as variáveis de ambiente. Ele acorda a API de novo, por garantia.
4. Abrir o Logisim com `circuito/lockwise_completo.circ`.
5. Ensaiar uma vez o `roteiros/demo.txt`, e depois limpar o que foi criado, se quiser começar do zero na frente do avaliador.

Durante a apresentação, três janelas: Logisim, gateway e o navegador em `/docs` ou `/fechadura`.

---

## Quando algo dá errado

**A API responde 503 ao escrever.** A variável `LOCKWISE_API_KEY` não está configurada no Render. É proposital: sem chave, a API não aceita escrita (ADR 0016). O gateway guarda os eventos na fila; corrija a variável e digite `fila`.

**O gateway mostra 401.** A chave do gateway e a do Render não são a mesma. Copie de novo do painel.

**O deploy falha no passo do `/health`.** Veja os logs do serviço no Render. A causa mais comum é `DATABASE_URL` ausente ou o banco expirado (ver abaixo).

**A API responde `{"status":"degradado"}`.** O processo está vivo mas o banco não responde. Confira se o banco ainda existe no painel.

**O banco expirou.** O Postgres gratuito do Render expira 90 dias depois de criado. Se isso acontecer antes de 28/11, crie um novo pelo blueprint e reaponte a `DATABASE_URL`. Os dados antigos se perdem — são eventos de teste, não há problema, mas vale gerar histórico novo antes da otimização (Fase G) rodar.

---

## O que fica em segredo, e onde

| Segredo | Onde vive | Quem usa |
|---|---|---|
| `LOCKWISE_API_KEY` | painel do Render (gerada lá) | a API para validar, o gateway para escrever |
| `DATABASE_URL` | painel do Render (ligada ao banco) | a API |
| `RENDER_DEPLOY_HOOK_URL` | segredos do GitHub | o workflow de deploy |

Nenhum deles está no repositório. O `.env.example` do backend mostra os nomes das variáveis, nunca os valores.
