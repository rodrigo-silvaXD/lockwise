"""GET /fechadura — o estado atual da fechadura, projetado a partir dos eventos."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..dependencias import obter_servico_da_fechadura
from ..esquemas import FechaduraSaida
from ..servicos import ServicoDaFechadura

router = APIRouter(prefix="/fechadura", tags=["fechadura"])


@router.get(
    "",
    response_model=FechaduraSaida,
    summary="Estado atual (AGUARDANDO | LIBERADO | BLOQUEADO), tentativas e ultimo evento",
)
def estado(servico: ServicoDaFechadura = Depends(obter_servico_da_fechadura)):
    return servico.estado()
