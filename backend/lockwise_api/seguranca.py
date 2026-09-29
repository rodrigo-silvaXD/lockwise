"""Autenticação das rotas de escrita por chave em `X-API-Key`.

`LOCKWISE_API_KEY` aceita uma chave ou várias separadas por vírgula. Várias
existem para que uma fonte que exponha a chave — o sketch de um simulador num
projeto público, por exemplo — use a sua própria, revogável sozinha.

Leitura é aberta (o painel lê sem chave no navegador); escrita exige a chave
que o gateway envia. A comparação é em tempo constante. Sem chave configurada
o servidor **recusa** escrever (503) em vez de aceitar tudo: falhar fechado.
O 503 é proposital — o gateway trata 5xx como temporário e guarda o evento na
fila, então nada se perde enquanto a configuração é corrigida.
"""

from __future__ import annotations

import secrets

from fastapi import Header, HTTPException, Request, status


def exigir_chave(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    aceitas: tuple[str, ...] = request.app.state.config.api_keys
    if not aceitas:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "LOCKWISE_API_KEY não configurada no servidor; escrita desabilitada",
        )
    if not x_api_key or not _confere(x_api_key, aceitas):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "X-API-Key ausente ou inválida")


def _confere(recebida: str, aceitas: tuple[str, ...]) -> bool:
    """Compara contra todas as chaves, sem interromper na primeira que bater.

    Sair do laço assim que uma confere faria o tempo de resposta depender de
    qual chave foi usada, e é justamente esse tipo de vazamento que
    `compare_digest` existe para evitar.
    """
    bruta = recebida.encode()
    valida = False
    for chave in aceitas:
        if secrets.compare_digest(bruta, chave.encode()):
            valida = True
    return valida
