"""POST /acessos · GET /acessos · GET /acessos/demanda-horaria"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..dependencias import obter_servico_de_acessos
from ..esquemas import AcessoEntrada, AcessoRegistradoSaida, AcessoSaida, AlertaGeradoSaida, DemandaHoraria
from ..seguranca import exigir_chave
from ..servicos import ServicoDeAcessos, UsuarioDesconhecido

router = APIRouter(prefix="/acessos", tags=["acessos"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=AcessoRegistradoSaida,
    dependencies=[Depends(exigir_chave)],
    summary="Registra um evento de acesso vindo do gateway",
)
def registrar(entrada: AcessoEntrada, servico: ServicoDeAcessos = Depends(obter_servico_de_acessos)):
    try:
        acesso, gerados = servico.registrar(entrada)
    except UsuarioDesconhecido as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e)) from e
    return AcessoRegistradoSaida(
        acesso=AcessoSaida.model_validate(acesso),
        alertas_gerados=[AlertaGeradoSaida(id=a.id, tipo=a.tipo, detalhe=a.detalhe) for a in gerados],
    )


@router.get("", response_model=list[AcessoSaida], summary="Histórico, do mais recente ao mais antigo")
def listar(
    de: datetime | None = Query(default=None, description="início do período (inclusivo), ISO 8601"),
    ate: datetime | None = Query(default=None, description="fim do período (exclusivo), ISO 8601"),
    limite: int = Query(default=100, ge=1, le=1000),
    servico: ServicoDeAcessos = Depends(obter_servico_de_acessos),
):
    return servico.listar(de, ate, limite)


@router.get(
    "/demanda-horaria",
    response_model=DemandaHoraria,
    summary="Acessos e energia por hora local — a demanda do modelo de otimização",
)
def demanda_horaria(
    de: datetime | None = Query(default=None),
    ate: datetime | None = Query(default=None),
    servico: ServicoDeAcessos = Depends(obter_servico_de_acessos),
):
    return servico.demanda_horaria(de, ate)
