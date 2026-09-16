"""POST /alertas · GET /alertas · PATCH /alertas/{id}/resolver"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..dependencias import obter_servico_de_alertas
from ..esquemas import AlertaEntrada, AlertaSaida
from ..seguranca import exigir_chave
from ..servicos import ServicoDeAlertas

router = APIRouter(prefix="/alertas", tags=["alertas"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=AlertaSaida,
    dependencies=[Depends(exigir_chave)],
    summary="Registra um alerta vindo do gateway (BLOQUEIO, DESBLOQUEIO_ADMIN)",
)
def registrar(entrada: AlertaEntrada, servico: ServicoDeAlertas = Depends(obter_servico_de_alertas)):
    return servico.registrar(entrada)


@router.get("", response_model=list[AlertaSaida], summary="Alertas, do mais recente ao mais antigo")
def listar(
    resolvido: bool | None = Query(default=None, description="filtra por situação; omitido devolve todos"),
    limite: int = Query(default=100, ge=1, le=1000),
    servico: ServicoDeAlertas = Depends(obter_servico_de_alertas),
):
    return servico.listar(resolvido, limite)


@router.patch(
    "/{id}/resolver",
    response_model=AlertaSaida,
    dependencies=[Depends(exigir_chave)],
    summary="Marca um alerta como resolvido",
)
def resolver(id: int, servico: ServicoDeAlertas = Depends(obter_servico_de_alertas)):
    alerta = servico.resolver(id)
    if alerta is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"alerta {id} não existe")
    return alerta
