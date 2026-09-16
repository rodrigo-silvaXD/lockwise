"""Padrão Observer — quem é avisado quando um alerta nasce.

Quem cria o alerta (o serviço) não sabe quem se interessa por ele. Os
interessados se inscrevem no `Notificador`; hoje são o log estruturado e,
opcionalmente, um webhook (Discord, Telegram, Slack da equipe). Amanhã pode
ser e-mail ou SMS — sem tocar em quem cria alertas.

Um observador que falha não pode derrubar o registro do acesso: o webhook
fora do ar é problema do webhook, não do morador tentando entrar. Por isso
`publicar` isola cada observador e registra a falha em vez de propagá-la.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Protocol

from .eventos import TipoAlerta

log = logging.getLogger("lockwise.alertas")


@dataclass(frozen=True)
class AlertaPublicado:
    """O que os observadores recebem: o alerta já persistido, com id."""

    id: int
    tipo: TipoAlerta
    momento: datetime
    detalhe: str | None
    acesso_id: int | None


class Observador(Protocol):
    def notificar(self, alerta: AlertaPublicado) -> None: ...


class Notificador:
    def __init__(self) -> None:
        self._observadores: list[Observador] = []

    def assinar(self, observador: Observador) -> None:
        self._observadores.append(observador)

    def publicar(self, alerta: AlertaPublicado) -> None:
        for obs in self._observadores:
            try:
                obs.notificar(alerta)
            except Exception:  # noqa: BLE001 — um observador nunca derruba o fluxo principal
                log.exception("observador %s falhou ao notificar alerta %s", type(obs).__name__, alerta.id)

    @property
    def quantidade(self) -> int:
        return len(self._observadores)


class LogObservador:
    """Escreve uma linha estruturada. É a observabilidade mínima da nuvem."""

    def notificar(self, alerta: AlertaPublicado) -> None:
        log.warning(
            "alerta id=%s tipo=%s momento=%s acesso_id=%s detalhe=%r",
            alerta.id, alerta.tipo.value, alerta.momento.isoformat(), alerta.acesso_id, alerta.detalhe,
        )


class WebhookObservador:
    """POST JSON para uma URL. Compatível com Discord (`content`) e webhooks genéricos."""

    def __init__(self, url: str, *, timeout_s: float = 3.0, abrir: Callable = urllib.request.urlopen) -> None:
        self.url = url
        self.timeout_s = timeout_s
        self._abrir = abrir

    def notificar(self, alerta: AlertaPublicado) -> None:
        texto = f"LOCKWISE · {alerta.tipo.value} · {alerta.momento:%d/%m %H:%M:%S} UTC"
        if alerta.detalhe:
            texto += f" · {alerta.detalhe}"
        corpo = json.dumps({
            "content": texto,
            "alerta": {
                "id": alerta.id,
                "tipo": alerta.tipo.value,
                "momento": alerta.momento.isoformat(),
                "detalhe": alerta.detalhe,
                "acesso_id": alerta.acesso_id,
            },
        }).encode("utf-8")
        req = urllib.request.Request(
            self.url, data=corpo, method="POST", headers={"Content-Type": "application/json"}
        )
        with self._abrir(req, timeout=self.timeout_s):
            pass
