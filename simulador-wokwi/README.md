# Ponte de hardware — ESP32 no Wokwi

Um ESP32 simulado que **lê os pinos de saída do circuito** e envia cada evento de acesso para a API por HTTPS.

É o que fecha a limitação registrada no [relatório](../docs/relatorio.md) e na [ADR 0008](../docs/adr/0008-gateway-como-gemeo-digital.md): *"a ponte circuito↔gateway é operada por pessoa"*. Com isso, ninguém precisa replicar gestos — o circuito conversa com a nuvem sozinho.

## O que este programa não faz

**Ele não decide nada.** O comparador de senha, a máquina de estados e o contador de tentativas continuam sendo portas lógicas e flip-flops.

Isso não é detalhe de implementação: é o requisito. O roteiro pede *"lógica digital: portas lógicas, circuitos combinacionais ou sequenciais"*. Se a lógica migrasse para dentro do microcontrolador, sumiriam o mapa de Karnaugh, a tabela de transição e os flip-flops — tudo que [`docs/eletronica.md`](../docs/eletronica.md) documenta. O projeto trocaria eletrônica digital por programação.

O ESP32 aqui é instrumentação, não cérebro.

## Por que Wokwi

Das três plataformas avaliadas, é a única que dá **acesso real à internet** a um microcontrolador simulado: o ESP32 conecta numa rede virtual (`Wokwi-GUEST`) que passa por um gateway ligado à internet de verdade, com suporte a HTTPS.

| | Rede real | Lógica discreta | Analógico medível |
|---|---|---|---|
| **Wokwi** | sim, HTTPS | portas + flip-flop D | não |
| Tinkered | rede interna só | portas, sem flip-flop D pronto | sim (SPICE) |
| Tinkercad | não tem Wi-Fi | portas + 74HC74 | sim |

Para medir corrente no estágio de potência — o transistor, o diodo, a bobina — use Tinkercad ou Tinkered num circuito separado. O Wokwi não simula analógico.

## Ligações

| GPIO | Sinal do circuito |
|---|---|
| 16 | `AGUARDANDO` |
| 17 | `VERIFICANDO` |
| 18 | `TRAVA_ABERTA` |
| 19 | `BLOQUEADO` |
| 21 | `ERROS_C1` |
| 22 | `ERROS_C0` |

## Antes de rodar

**1. Crie uma chave só para o simulador.** No plano gratuito do Wokwi o projeto é público, então a chave no código fica visível para qualquer pessoa.

A API aceita várias chaves separadas por vírgula. No painel do Render, em `LOCKWISE_API_KEY`:

```
chave-do-gateway,chave-do-simulador
```

Assim a do simulador pode ser revogada sozinha — basta removê-la da lista — sem derrubar o gateway. Nunca use a mesma chave nos dois.

**2. Cole a chave do simulador** em `API_KEY`, no topo de `lockwise.ino`.

**3. Sem o circuito montado**, deixe `MODO_ENSAIO` em `1`. O programa percorre sozinho a sequência da demonstração — acesso liberado, três erros, bloqueio e desbloqueio — o que serve para provar a rede antes de existir hardware para ler. Com o circuito pronto, mude para `0`.

## O que esperar no monitor serial

```
LOCKWISE — ponte de hardware
conectando na rede virtual... conectado, IP 10.13.37.2
sincronizando o relógio 2026-09-29T14:32:11Z
acordando a API no ar
{"status":"ok","banco":"ok","motor":"postgresql",...}
estado inicial: AGUARDANDO, contador 0
AGUARDANDO -> VERIFICANDO (contador 0)
VERIFICANDO -> LIBERADO (contador 0)
evento LIBERADO tentativa=1 energia_mj=18200
  POST /acessos -> 201
```

Confirme do outro lado:

```bash
curl https://lockwise-api.onrender.com/acessos?limite=3
```

## Detalhes que custaram para acertar

**O certificado.** `setCACert()` precisa da raiz certa. O certificado do Render é assinado pelo **Google Trust Services**, raiz **GTS Root R4** — descoberto com `openssl s_client`, não chutado. Fixamos a raiz e não o certificado do servidor: o Render renova o dele a cada três meses, a raiz vale até janeiro de 2028.

Está embutida no sketch e guardada em [`gts_root_r4.pem`](gts_root_r4.pem). Para conferir se ainda é essa:

```bash
openssl s_client -showcerts -connect lockwise-api.onrender.com:443 -servername lockwise-api.onrender.com </dev/null 2>/dev/null | openssl x509 -noout -issuer
```

**O relógio.** O ESP32 acorda achando que é 1970, e a API exige `momento` em cada evento — sem NTP, todo acesso cairia na madrugada de 1º de janeiro de 1970 e a agregação por hora do modelo de otimização ficaria sem sentido. Daí o `configTime()`.

**A lentidão.** O gateway público do Wokwi é lento e o plano gratuito do Render hiberna. O sketch acorda a API antes de começar e usa timeout de 20 s.

## Se o HTTPS falhar

Troque `tls.setCACert(RAIZ_GTS_R4)` por `tls.setInsecure()` e rode de novo:

- **Funcionou sem validação** → o problema é o certificado. Extraia a raiz de novo com o comando acima.
- **Falhou dos dois jeitos** → o problema é a rede. Confira se o SSID é exatamente `Wokwi-GUEST` e se o Wokwi ainda oferece gateway no plano gratuito.

Não deixe `setInsecure()` na versão final: o gateway público do Wokwi é monitorado, e sem validação de certificado a chave trafega sem garantia de estar indo para o servidor certo.
