"""Padrão Strategy — a política de supervisão da nuvem.

O hardware já decide bloquear após três erros; isso não se muda por software.
O que a nuvem decide é **quando avisar alguém**, e essa decisão varia com o
contexto de uso: uma residência quer saber de tentativas suspeitas antes do
bloqueio; um condomínio quer saber de acessos fora do horário. A política é
um objeto intercambiável, escolhido por variável de ambiente, e o serviço que
registra acessos não sabe qual está em uso.

Cada política recebe o acesso recém-registrado e devolve os alertas que ele
merece — possivelmente nenhum.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import ClassVar, Protocol
from zoneinfo import ZoneInfo

from .eventos import AcessoRegistrado, Resultado, TipoAlerta


@dataclass(frozen=True)
class AlertaGerado:
    tipo: TipoAlerta
    detalhe: str


class PoliticaDeSupervisao(Protocol):
    nome: ClassVar[str]

    def avaliar(self, acesso: AcessoRegistrado) -> list[AlertaGerado]: ...


@dataclass(frozen=True)
class LimiteDeTentativas:
    """Avisa quando o número de tentativas erradas seguidas atinge `limite`.

    Com limite=2 (padrão), o administrador é avisado na segunda tentativa —
    uma antes do hardware bloquear. É o aviso prévio que o circuito sozinho
    não consegue dar.
    """

    nome: ClassVar[str] = "limite"
    limite: int = 2

    def avaliar(self, acesso: AcessoRegistrado) -> list[AlertaGerado]:
        if acesso.resultado is Resultado.NEGADO and acesso.tentativa >= self.limite:
            return [AlertaGerado(
                TipoAlerta.TENTATIVAS_SUSPEITAS,
                f"{acesso.tentativa}ª tentativa incorreta seguida (limite de aviso: {self.limite})",
            )]
        return []


@dataclass(frozen=True)
class JanelaHoraria:
    """Avisa quando um acesso LIBERADO acontece fora da janela permitida.

    A janela é em horário local (`fuso`), porque "fora do horário" é um
    conceito humano, não de UTC. Janelas que cruzam a meia-noite (22:00–06:00)
    são aceitas.
    """

    nome: ClassVar[str] = "horario"
    inicio: time = time(6, 0)
    fim: time = time(23, 0)
    fuso: str = "America/Sao_Paulo"

    def dentro(self, hora_local: time) -> bool:
        if self.inicio <= self.fim:
            return self.inicio <= hora_local < self.fim
        return hora_local >= self.inicio or hora_local < self.fim  # cruza a meia-noite

    def avaliar(self, acesso: AcessoRegistrado) -> list[AlertaGerado]:
        if acesso.resultado is not Resultado.LIBERADO:
            return []
        local = acesso.momento.astimezone(ZoneInfo(self.fuso))
        if self.dentro(local.time()):
            return []
        return [AlertaGerado(
            TipoAlerta.ACESSO_FORA_DO_HORARIO,
            f"acesso liberado às {local.strftime('%H:%M')} ({self.fuso}); "
            f"janela permitida {self.inicio:%H:%M}–{self.fim:%H:%M}",
        )]


@dataclass(frozen=True)
class Composta:
    """Aplica várias políticas e reúne os alertas. Composição, não herança."""

    nome: ClassVar[str] = "composta"
    politicas: tuple[PoliticaDeSupervisao, ...] = ()

    def avaliar(self, acesso: AcessoRegistrado) -> list[AlertaGerado]:
        return [a for p in self.politicas for a in p.avaliar(acesso)]


@dataclass(frozen=True)
class SemSupervisao:
    """Nenhum alerta além dos que o gateway já envia. Útil em testes e demos."""

    nome: ClassVar[str] = "nenhuma"

    def avaliar(self, acesso: AcessoRegistrado) -> list[AlertaGerado]:
        return []


def politica_por_nome(
    nome: str,
    *,
    limite: int = 2,
    janela: tuple[time, time] = (time(6, 0), time(23, 0)),
    fuso: str = "America/Sao_Paulo",
) -> PoliticaDeSupervisao:
    """Fábrica usada pela configuração. Nomes: limite | horario | composta | nenhuma."""
    limite_pol = LimiteDeTentativas(limite=limite)
    horario_pol = JanelaHoraria(inicio=janela[0], fim=janela[1], fuso=fuso)
    opcoes: dict[str, PoliticaDeSupervisao] = {
        "limite": limite_pol,
        "horario": horario_pol,
        "composta": Composta((limite_pol, horario_pol)),
        "nenhuma": SemSupervisao(),
    }
    try:
        return opcoes[nome]
    except KeyError:
        raise ValueError(f"política desconhecida: {nome!r}; use uma de {sorted(opcoes)}") from None
