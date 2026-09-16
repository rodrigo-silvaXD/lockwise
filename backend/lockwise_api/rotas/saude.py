"""GET /health — observabilidade minima: o processo responde e o banco atende."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response, status
from sqlalchemy import text

from .. import __version__
from ..esquemas import Saude

router = APIRouter(tags=["saude"])


@router.get("/health", response_model=Saude, summary="Saude do servico e do banco")
def health(request: Request, response: Response):
    estado = request.app.state
    try:
        with estado.engine.connect() as conexao:
            conexao.execute(text("SELECT 1"))
        banco, situacao = "ok", "ok"
    except Exception as e:  # noqa: BLE001 - qualquer falha de banco e "degradado"
        banco, situacao = f"erro: {type(e).__name__}", "degradado"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return Saude(
        status=situacao,
        banco=banco,
        versao=__version__,
        politica=estado.politica.nome,
        observadores=estado.notificador.quantidade,
    )
