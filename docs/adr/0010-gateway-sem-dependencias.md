# ADR 0010 — Gateway sem dependências externas

Data: 2026-09-16
Situação: aceita

## Contexto

O plano inicial do gateway previa `requests` para o HTTP. Na hora de começar, a máquina não tinha o pacote instalado. Isso nos fez pensar na máquina da demonstração: será a de algum integrante, talvez com outro Python, talvez sem internet para um `pip install` de última hora.

## Decisão

O gateway usa só a biblioteca padrão: `urllib` para HTTP, `json`, `threading`, `argparse`, `dataclasses`. A única dependência é `pytest`, e só para os testes. Exige Python 3.11 ou mais novo.

## Alternativas que consideramos

`requests`: API mais agradável e retry pronto via `urllib3`. O custo é uma instalação que pode falhar na hora errada. O retry que precisávamos tem três esperas fixas; escrever à mão são vinte linhas.

`httpx`: mesmo caso, com a vantagem de async, que não usamos.

## Consequências

Retry, backoff e fila offline foram implementados no próprio `transporte.py` (cerca de sessenta linhas) e testados com um `urlopen` falso injetado, sem tocar na rede.

Copiar a pasta `gateway/` para qualquer máquina com Python 3.11+ e rodar `python -m lockwise_gateway.cli` funciona. Nada para instalar no dia.
