"""Vocabulário compartilhado do domínio: o que chega do gateway, o que a nuvem produz.

Os valores de `Resultado` e os dois primeiros `TipoAlerta` são o contrato com
`gateway/lockwise_gateway/eventos.py`. Os demais tipos de alerta nascem aqui,
nas políticas de supervisão.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

# Duração da trava aberta (docs/fisica.md, seção 5): NE555, 470 kΩ × 10 µF × ln 3.
# A nuvem não recebe evento de TIMEOUT — ela sabe que a trava fechou porque
# conhece a física do temporizador.
TEMPO_TRAVA_ABERTA_S = 5.16

# Tentativas incorretas que levam ao bloqueio no hardware.
LIMITE_TENTATIVAS_HARDWARE = 3


class Resultado(str, Enum):
    LIBERADO = "LIBERADO"
    NEGADO = "NEGADO"
    BLOQUEADO = "BLOQUEADO"


class TipoAlerta(str, Enum):
    # emitidos pelo gateway, espelhando o circuito
    BLOQUEIO = "BLOQUEIO"
    DESBLOQUEIO_ADMIN = "DESBLOQUEIO_ADMIN"
    # emitidos pela nuvem, pelas políticas de supervisão
    TENTATIVAS_SUSPEITAS = "TENTATIVAS_SUSPEITAS"
    ACESSO_FORA_DO_HORARIO = "ACESSO_FORA_DO_HORARIO"


def utc(momento: datetime) -> datetime:
    """Normaliza para UTC. Datetimes sem fuso são tratados como UTC (é o que o SQLite devolve)."""
    if momento.tzinfo is None:
        return momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(timezone.utc)


@dataclass(frozen=True)
class AcessoRegistrado:
    """Um evento de acesso já aceito pela API."""

    momento: datetime
    resultado: Resultado
    tentativa: int
    energia_mj: int
    usuario_id: int | None


@dataclass(frozen=True)
class AlertaRegistrado:
    """Um alerta já aceito pela API."""

    momento: datetime
    tipo: TipoAlerta


Evento = AcessoRegistrado | AlertaRegistrado
