"""Os eventos que o gateway produz e as constantes que vêm das outras camadas.

Um evento nasce em uma transição da máquina de estados e morre em um POST.
Este módulo define o formato; `maquina.py` decide quando criar, `transporte.py`
decide como entregar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

# Senha gravada no comparador do circuito: P1 = S3·S̄2, P2 = S1·S0.
SENHA = 0b1011

# Energia de uma liberação, em milijoules. Vem de docs/fisica.md, seção 6:
# (12 V × 292,5 mA + 5 V × 4,3 mA) × 5,16 s = 3,53 W × 5,16 s ≈ 18,2 J.
ENERGIA_LIBERACAO_MJ = 18_200

# Duração da trava aberta, em segundos. NE555 monoestável, 470 kΩ × 10 µF × ln 3.
TEMPO_TRAVA_ABERTA_S = 5.16

# O circuito tem uma senha, logo um morador. Registro 1 da tabela `usuario`.
USUARIO_MORADOR = 1

# Tentativas incorretas que levam ao bloqueio (contador de 2 bits satura em 11).
LIMITE_TENTATIVAS = 3


def agora() -> str:
    """Timestamp ISO 8601 em UTC, com precisão de milissegundos."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class Resultado(str, Enum):
    """Coluna `acesso.resultado` do banco. Um valor por transição de saída de VERIFICANDO."""

    LIBERADO = "LIBERADO"
    NEGADO = "NEGADO"
    BLOQUEADO = "BLOQUEADO"


class TipoAlerta(str, Enum):
    """Coluna `alerta.tipo` do banco."""

    BLOQUEIO = "BLOQUEIO"
    DESBLOQUEIO_ADMIN = "DESBLOQUEIO_ADMIN"


@dataclass(frozen=True)
class EventoAcesso:
    """Uma linha da tabela `acesso`. Vai para POST /acessos."""

    resultado: Resultado
    tentativa: int
    energia_mj: int
    usuario_id: int | None
    momento: str = field(default_factory=agora)

    rota = "/acessos"

    def payload(self) -> dict:
        return {
            "momento": self.momento,
            "usuario_id": self.usuario_id,
            "resultado": self.resultado.value,
            "tentativa": self.tentativa,
            "energia_mj": self.energia_mj,
        }

    @classmethod
    def liberado(cls, tentativas_anteriores: int) -> EventoAcesso:
        return cls(
            resultado=Resultado.LIBERADO,
            tentativa=tentativas_anteriores + 1,
            energia_mj=ENERGIA_LIBERACAO_MJ,
            usuario_id=USUARIO_MORADOR,
        )

    @classmethod
    def negado(cls, tentativa: int) -> EventoAcesso:
        return cls(resultado=Resultado.NEGADO, tentativa=tentativa, energia_mj=0, usuario_id=None)

    @classmethod
    def bloqueado(cls) -> EventoAcesso:
        return cls(
            resultado=Resultado.BLOQUEADO,
            tentativa=LIMITE_TENTATIVAS,
            energia_mj=0,
            usuario_id=None,
        )


@dataclass(frozen=True)
class Alerta:
    """Uma linha da tabela `alerta`. Vai para POST /alertas."""

    tipo: TipoAlerta
    momento: str = field(default_factory=agora)

    rota = "/alertas"

    def payload(self) -> dict:
        return {"tipo": self.tipo.value, "momento": self.momento}


Evento = EventoAcesso | Alerta
