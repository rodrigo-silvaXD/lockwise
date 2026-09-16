"""Padrão Observer: quem cria o alerta não sabe quem se interessa por ele."""

import json
import logging
from datetime import datetime, timezone

from lockwise_api.dominio.eventos import TipoAlerta
from lockwise_api.dominio.notificacao import (
    AlertaPublicado,
    LogObservador,
    Notificador,
    WebhookObservador,
)

ALERTA = AlertaPublicado(
    id=7, tipo=TipoAlerta.BLOQUEIO, momento=datetime(2026, 11, 10, 14, 0, tzinfo=timezone.utc),
    detalhe="3 tentativas", acesso_id=42,
)


class Espiao:
    def __init__(self, falha: bool = False) -> None:
        self.recebidos: list[AlertaPublicado] = []
        self.falha = falha

    def notificar(self, alerta: AlertaPublicado) -> None:
        if self.falha:
            raise RuntimeError("observador quebrado")
        self.recebidos.append(alerta)


def test_todos_os_assinantes_recebem():
    n, a, b = Notificador(), Espiao(), Espiao()
    n.assinar(a)
    n.assinar(b)
    n.publicar(ALERTA)
    assert a.recebidos == [ALERTA] and b.recebidos == [ALERTA]
    assert n.quantidade == 2


def test_observador_que_falha_nao_impede_os_outros(caplog):
    n, quebrado, sao = Notificador(), Espiao(falha=True), Espiao()
    n.assinar(quebrado)
    n.assinar(sao)
    with caplog.at_level(logging.ERROR, logger="lockwise.alertas"):
        n.publicar(ALERTA)
    assert sao.recebidos == [ALERTA]
    assert "Espiao falhou" in caplog.text


def test_log_observador_escreve_linha_estruturada(caplog):
    with caplog.at_level(logging.WARNING, logger="lockwise.alertas"):
        LogObservador().notificar(ALERTA)
    assert "tipo=BLOQUEIO" in caplog.text and "id=7" in caplog.text and "acesso_id=42" in caplog.text


def test_webhook_envia_json_com_content_e_alerta():
    chamadas = []

    class Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def abrir(req, timeout):
        chamadas.append((req.full_url, req.get_method(), json.loads(req.data), timeout))
        return Resp()

    WebhookObservador("https://hooks.exemplo/x", timeout_s=1.5, abrir=abrir).notificar(ALERTA)
    url, metodo, corpo, timeout = chamadas[0]
    assert url == "https://hooks.exemplo/x" and metodo == "POST" and timeout == 1.5
    assert "BLOQUEIO" in corpo["content"] and "3 tentativas" in corpo["content"]
    assert corpo["alerta"]["id"] == 7 and corpo["alerta"]["acesso_id"] == 42


def test_webhook_fora_do_ar_e_absorvido_pelo_notificador(caplog):
    def abrir(req, timeout):
        raise OSError("conexão recusada")

    n = Notificador()
    n.assinar(WebhookObservador("https://hooks.exemplo/x", abrir=abrir))
    with caplog.at_level(logging.ERROR, logger="lockwise.alertas"):
        n.publicar(ALERTA)  # não levanta
    assert "WebhookObservador falhou" in caplog.text
