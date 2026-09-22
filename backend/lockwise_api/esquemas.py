"""Contratos HTTP (Pydantic). O que entra é validado aqui; o que sai é serializado aqui.

`AcessoEntrada` e `AlertaEntrada` são exatamente os payloads que
`gateway/lockwise_gateway/eventos.py` produz. Se um lado mudar, o teste
ponta a ponta quebra.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .dominio.eventos import LIMITE_TENTATIVAS_HARDWARE, Resultado, TipoAlerta, utc

Tentativa = Annotated[int, Field(ge=1, le=LIMITE_TENTATIVAS_HARDWARE)]


# ----------------------------------------------------------------- acessos


class AcessoEntrada(BaseModel):
    momento: datetime
    usuario_id: int | None = None
    resultado: Resultado
    tentativa: Tentativa
    energia_mj: int = Field(ge=0)

    @field_validator("momento")
    @classmethod
    def _em_utc(cls, v: datetime) -> datetime:
        return utc(v)


class AcessoSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    momento: datetime
    usuario_id: int | None
    resultado: Resultado
    tentativa: int
    energia_mj: int

    # O SQLite devolve datetimes sem fuso; a API sempre responde em UTC explícito.
    _em_utc = field_validator("momento")(lambda cls, v: utc(v))


class AlertaGeradoSaida(BaseModel):
    id: int
    tipo: TipoAlerta
    detalhe: str | None


class AcessoRegistradoSaida(BaseModel):
    """Resposta do POST /acessos: o acesso e os alertas que a política gerou."""

    acesso: AcessoSaida
    alertas_gerados: list[AlertaGeradoSaida]


class FaixaHoraria(BaseModel):
    hora: int = Field(ge=0, le=23)
    acessos: int
    liberados: int
    negados: int
    bloqueados: int
    energia_mj: int


class DemandaHoraria(BaseModel):
    """Entrada do modelo de otimização: 24 faixas, sempre presentes, em horário local."""

    de: datetime | None
    ate: datetime | None
    fuso: str
    total_acessos: int
    total_energia_mj: int
    faixas: list[FaixaHoraria]


# ----------------------------------------------------------------- alertas


class AlertaEntrada(BaseModel):
    tipo: TipoAlerta
    momento: datetime
    detalhe: str | None = Field(default=None, max_length=200)

    @field_validator("momento")
    @classmethod
    def _em_utc(cls, v: datetime) -> datetime:
        return utc(v)


class AlertaSaida(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: TipoAlerta
    momento: datetime
    resolvido: bool
    detalhe: str | None
    acesso_id: int | None

    _em_utc = field_validator("momento")(lambda cls, v: utc(v))


# --------------------------------------------------------------- fechadura


class UltimoEvento(BaseModel):
    tipo: str  # "acesso" | "alerta"
    momento: datetime
    descricao: str


class FechaduraSaida(BaseModel):
    estado: str  # AGUARDANDO | LIBERADO | BLOQUEADO
    tentativas: int
    desde: datetime | None
    trava_fecha_em: datetime | None  # só em LIBERADO
    ultimo_evento: UltimoEvento | None
    avisos: list[str]
    consultado_em: datetime


# ------------------------------------------------------------------- saúde


class Saude(BaseModel):
    status: str
    banco: str
    # Qual motor esta em uso: "postgresql" em producao, "sqlite" em
    # desenvolvimento. Sem DATABASE_URL o codigo cai no SQLite, que no Render
    # vive em disco efemero e some a cada reinicio — este campo denuncia isso
    # de fora, sem precisar abrir o painel.
    motor: str
    persistente: bool
    versao: str
    politica: str
    observadores: int
