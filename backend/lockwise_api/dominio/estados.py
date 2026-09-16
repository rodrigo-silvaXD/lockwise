"""Padrão State — a fechadura vista pela nuvem.

O circuito é uma máquina de estados. O gateway a espelha em Python. Aqui ela
aparece pela terceira vez, com um trabalho diferente: **projeção**. A nuvem
não vê os pinos; vê a sequência de eventos que o gateway enviou. Cada classe
de estado sabe o que cada evento significa para ela e para onde leva.

Duas diferenças em relação ao circuito, ambas deliberadas:

- Não existe VERIFICANDO. É um estado transitório de uma borda de clock; a
  nuvem só recebe o resultado da verificação.
- LIBERADO expira sozinho. O hardware volta a AGUARDANDO por TIMEOUT, mas o
  gateway não envia esse evento. A nuvem sabe que a trava fechou porque
  conhece a duração do temporizador (docs/fisica.md, seção 5).

Transições que o hardware não produziria (um NEGADO durante BLOQUEADO, por
exemplo) não são rejeitadas — o evento é registrado e a projeção anota um
aviso. Rejeitar faria o gateway descartar o evento, e um acesso se perderia.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import ClassVar, Iterable

from .eventos import (
    TEMPO_TRAVA_ABERTA_S,
    AcessoRegistrado,
    AlertaRegistrado,
    Evento,
    Resultado,
    TipoAlerta,
    utc,
)


@dataclass(frozen=True)
class EstadoFechadura(ABC):
    """Um estado da fechadura. Imutável: aplicar um evento devolve um estado novo."""

    nome: ClassVar[str]
    tentativas: int = 0
    desde: datetime | None = None

    @abstractmethod
    def aplicar(self, evento: Evento) -> EstadoFechadura:
        """O estado após este evento."""

    def vigente(self, agora: datetime) -> EstadoFechadura:
        """O estado que vale neste instante. Só LIBERADO muda com o tempo."""
        return self

    # Reações comuns a todos os estados. Cada estado sobrescreve o que difere.

    def _acesso(self, a: AcessoRegistrado) -> EstadoFechadura:
        if a.resultado is Resultado.LIBERADO:
            return Liberado(tentativas=0, desde=utc(a.momento))
        if a.resultado is Resultado.BLOQUEADO:
            return Bloqueado(tentativas=a.tentativa, desde=utc(a.momento))
        return Aguardando(tentativas=a.tentativa, desde=utc(a.momento))

    def _alerta(self, al: AlertaRegistrado) -> EstadoFechadura:
        if al.tipo is TipoAlerta.DESBLOQUEIO_ADMIN:
            return Aguardando(tentativas=0, desde=utc(al.momento))
        return self  # BLOQUEIO chega junto do acesso BLOQUEADO; os demais não mudam estado


class Aguardando(EstadoFechadura):
    """Repouso. `tentativas` guarda quantos NEGADO seguidos já houve (0 a 2)."""

    nome = "AGUARDANDO"

    def aplicar(self, evento: Evento) -> EstadoFechadura:
        return self._acesso(evento) if isinstance(evento, AcessoRegistrado) else self._alerta(evento)


class Liberado(EstadoFechadura):
    """Trava acionada. Vale por TEMPO_TRAVA_ABERTA_S a partir de `desde`."""

    nome = "LIBERADO"

    @property
    def ate(self) -> datetime:
        assert self.desde is not None
        return self.desde + timedelta(seconds=TEMPO_TRAVA_ABERTA_S)

    def vigente(self, agora: datetime) -> EstadoFechadura:
        if utc(agora) >= self.ate:
            return Aguardando(tentativas=0, desde=self.ate)
        return self

    def aplicar(self, evento: Evento) -> EstadoFechadura:
        # Qualquer evento posterior já encontra a trava fechada: o hardware não
        # aceita CONFIRMA em LIBERADO, então o próximo acesso veio depois do TIMEOUT.
        return Aguardando(tentativas=0, desde=self.ate).aplicar(evento)


class Bloqueado(EstadoFechadura):
    """Sistema travado. Só DESBLOQUEIO_ADMIN sai daqui."""

    nome = "BLOQUEADO"

    def aplicar(self, evento: Evento) -> EstadoFechadura:
        if isinstance(evento, AlertaRegistrado):
            return self._alerta(evento)
        # Um acesso durante o bloqueio é impossível no hardware. A Projeção anota
        # o aviso (ver `Projecao.aplicar`); o estado permanece BLOQUEADO.
        return self


@dataclass
class Projecao:
    """Reconstrói o estado da fechadura a partir da sequência de eventos."""

    estado: EstadoFechadura = field(default_factory=Aguardando)
    ultimo_evento: Evento | None = None
    avisos: list[str] = field(default_factory=list)

    def aplicar(self, evento: Evento) -> EstadoFechadura:
        anterior = self.estado
        if isinstance(anterior, Bloqueado) and isinstance(evento, AcessoRegistrado):
            self.avisos.append(
                f"{evento.resultado.value} em {utc(evento.momento).isoformat()} "
                f"recebido com a fechadura BLOQUEADA — impossível no hardware"
            )
        self.estado = anterior.aplicar(evento)
        self.ultimo_evento = evento
        return self.estado

    @classmethod
    def reconstruir(cls, eventos: Iterable[Evento]) -> Projecao:
        """Aplica os eventos em ordem cronológica."""
        p = cls()
        for ev in sorted(eventos, key=lambda e: utc(e.momento)):
            p.aplicar(ev)
        return p

    def vigente(self, agora: datetime) -> EstadoFechadura:
        return self.estado.vigente(agora)
