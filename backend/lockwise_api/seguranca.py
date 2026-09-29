"""Autenticação das rotas de escrita por chave em `X-API-Key`.

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
    esperada: str | None = request.app.state.config.api_key
    if not esperada:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "LOCKWISE_API_KEY não configurada no servidor; escrita desabilitada",
        )
    if not x_api_key or not secrets.compare_digest(x_api_key.encode(), esperada.encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "X-API-Key ausente ou inválida")
