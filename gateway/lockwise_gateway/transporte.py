"""Entrega dos eventos à API na nuvem, com retry e fila offline.

Só biblioteca padrão. A política de entrega:

- Falha de conexão ou resposta 5xx: tenta de novo com espera crescente
  (0,5 s, 1 s, 2 s). A rede da sala de aula pode oscilar; a API no free tier
  pode estar acordando de hibernação.
- Esgotadas as tentativas: o evento vai para uma fila em disco (JSON Lines) e
  é reenviado na próxima oportunidade. Nenhum acesso se perde por queda de rede.
- Resposta 4xx: não tenta de novo nem enfileira. É um defeito de contrato
  entre gateway e API, e repetir não resolve — o operador precisa ver.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from .eventos import Evento

ESPERAS_S = (0.5, 1.0, 2.0)


@dataclass(frozen=True)
class Envio:
    """O que aconteceu com um evento ao tentar entregá-lo."""

    situacao: str  # "enviado" | "enfileirado" | "rejeitado" | "simulado"
    rota: str
    codigo_http: int | None = None
    tentativas: int = 0
    detalhe: str = ""

    @property
    def ok(self) -> bool:
        return self.situacao in ("enviado", "simulado")


class Cliente(Protocol):
    def enviar(self, evento: Evento) -> Envio: ...
    def reenviar_fila(self) -> tuple[int, int]: ...
    def acordar(self, espera_s: float = ...) -> bool: ...


class ClienteAPI:
    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        *,
        timeout_s: float = 5.0,
        fila: Path | None = None,
        dormir: Callable[[float], None] = time.sleep,
        abrir: Callable = urllib.request.urlopen,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_s = timeout_s
        self.fila = fila
        self._dormir = dormir
        self._abrir = abrir

    # ------------------------------------------------------------- público

    def enviar(self, evento: Evento) -> Envio:
        envio = self._enviar_com_retry(evento.rota, evento.payload())
        if envio.situacao == "enfileirado":
            self._enfileirar(evento.rota, evento.payload())
        return envio

    def reenviar_fila(self) -> tuple[int, int]:
        """Tenta entregar tudo o que está na fila. Devolve (enviados, restantes)."""
        if not self.fila or not self.fila.exists():
            return 0, 0

        pendentes = [json.loads(l) for l in self.fila.read_text(encoding="utf-8").splitlines() if l.strip()]
        restantes: list[dict] = []
        enviados = 0
        for item in pendentes:
            envio = self._enviar_com_retry(item["rota"], item["payload"])
            if envio.situacao == "enviado":
                enviados += 1
            elif envio.situacao == "enfileirado":
                restantes.append(item)
            # "rejeitado" (4xx) é descartado: repetir não vai resolver

        self.fila.write_text(
            "".join(json.dumps(i, ensure_ascii=False) + "\n" for i in restantes),
            encoding="utf-8",
        )
        return enviados, len(restantes)

    def tamanho_fila(self) -> int:
        if not self.fila or not self.fila.exists():
            return 0
        return sum(1 for l in self.fila.read_text(encoding="utf-8").splitlines() if l.strip())

    def acordar(self, espera_s: float = 60.0) -> bool:
        """Chama GET /health ate a API responder, ou ate esgotar `espera_s`.

        Servico em plano gratuito hiberna quando fica sem trafego, e a primeira
        requisicao depois disso pode levar 30 s ou mais — bem mais que o retry
        de um POST. Chamar isto antes da demo evita que o primeiro acesso do
        circuito caia na fila so porque a API estava dormindo.
        """
        limite = time.monotonic() + espera_s
        while True:
            try:
                req = urllib.request.Request(self.base_url + "/health", method="GET")
                with self._abrir(req, timeout=self.timeout_s) as resp:
                    if resp.status == 200:
                        return True
            except Exception:  # noqa: BLE001 — qualquer falha aqui e "ainda dormindo"
                pass
            if time.monotonic() >= limite:
                return False
            self._dormir(2.0)

    # ------------------------------------------------------------- interno

    def _enviar_com_retry(self, rota: str, payload: dict) -> Envio:
        ultimo_erro = ""
        for n, espera in enumerate((*ESPERAS_S, None), start=1):
            try:
                codigo = self._post(rota, payload)
                return Envio("enviado", rota, codigo_http=codigo, tentativas=n)
            except urllib.error.HTTPError as e:
                if 400 <= e.code < 500:
                    return Envio("rejeitado", rota, codigo_http=e.code, tentativas=n, detalhe=_corpo(e))
                ultimo_erro = f"HTTP {e.code}"
            except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
                ultimo_erro = str(getattr(e, "reason", e))

            if espera is not None:
                self._dormir(espera)

        return Envio("enfileirado", rota, tentativas=len(ESPERAS_S) + 1, detalhe=ultimo_erro)

    def _post(self, rota: str, payload: dict) -> int:
        corpo = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        cabecalhos = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            cabecalhos["X-API-Key"] = self.api_key
        req = urllib.request.Request(self.base_url + rota, data=corpo, headers=cabecalhos, method="POST")
        with self._abrir(req, timeout=self.timeout_s) as resp:
            return resp.status

    def _enfileirar(self, rota: str, payload: dict) -> None:
        if not self.fila:
            return
        self.fila.parent.mkdir(parents=True, exist_ok=True)
        with self.fila.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"rota": rota, "payload": payload}, ensure_ascii=False) + "\n")


class ClienteEco:
    """Não fala com rede nenhuma: imprime o que enviaria. Para demo sem backend."""

    def __init__(self, saida: Callable[[str], None] = print) -> None:
        self._saida = saida
        self.enviados: list[tuple[str, dict]] = []

    def enviar(self, evento: Evento) -> Envio:
        payload = evento.payload()
        self.enviados.append((evento.rota, payload))
        self._saida(f"   POST {evento.rota}  {json.dumps(payload, ensure_ascii=False)}")
        return Envio("simulado", evento.rota)

    def reenviar_fila(self) -> tuple[int, int]:
        return 0, 0

    def acordar(self, espera_s: float = 60.0) -> bool:
        return True


def _corpo(e: urllib.error.HTTPError) -> str:
    try:
        return e.read().decode("utf-8", errors="replace")[:200]
    except Exception:  # noqa: BLE001 — corpo é só diagnóstico
        return ""
