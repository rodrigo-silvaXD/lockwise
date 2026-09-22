"""Retry, fila offline e rejeição — sem tocar na rede."""

import io
import json
import urllib.error
from pathlib import Path

from lockwise_gateway.eventos import Alerta, EventoAcesso, TipoAlerta
from lockwise_gateway.transporte import ESPERAS_S, ClienteAPI, ClienteEco


class RespostaFalsa:
    def __init__(self, status: int) -> None:
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class ServidorFalso:
    """Devolve, em ordem, o que estiver em `respostas`: int (status) ou exceção."""

    def __init__(self, *respostas) -> None:
        self.respostas = list(respostas)
        self.requisicoes = []

    def __call__(self, req, timeout):
        corpo = json.loads(req.data) if req.data else None  # GET /health nao tem corpo
        self.requisicoes.append((req.full_url, req.get_method(), dict(req.header_items()), corpo))
        r = self.respostas.pop(0)
        if isinstance(r, Exception):
            raise r
        return RespostaFalsa(r)


def http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("http://x", code, "erro", {}, io.BytesIO(b"{}"))


def fora() -> urllib.error.URLError:
    return urllib.error.URLError("conexao recusada")


def cliente(servidor, tmp_path: Path, esperas: list | None = None) -> ClienteAPI:
    return ClienteAPI(
        "http://api.exemplo/",
        "chave-secreta",
        fila=tmp_path / "fila.jsonl",
        dormir=(esperas.append if esperas is not None else (lambda s: None)),
        abrir=servidor,
    )


def test_envio_bem_sucedido_monta_requisicao_correta(tmp_path):
    srv = ServidorFalso(201)
    envio = cliente(srv, tmp_path).enviar(EventoAcesso.liberado(0))

    assert envio.ok and envio.situacao == "enviado"
    assert envio.codigo_http == 201 and envio.tentativas == 1
    url, metodo, cabecalhos, corpo = srv.requisicoes[0]
    assert url == "http://api.exemplo/acessos" and metodo == "POST"
    assert cabecalhos["X-api-key"] == "chave-secreta"
    assert cabecalhos["Content-type"] == "application/json"
    assert corpo["resultado"] == "LIBERADO" and corpo["energia_mj"] == 18_200


def test_alerta_vai_para_rota_de_alertas(tmp_path):
    srv = ServidorFalso(201)
    cliente(srv, tmp_path).enviar(Alerta(TipoAlerta.BLOQUEIO))
    assert srv.requisicoes[0][0].endswith("/alertas")


def test_retry_em_5xx_e_queda_de_conexao_com_backoff(tmp_path):
    srv = ServidorFalso(http_error(503), fora(), 201)
    esperas: list = []
    envio = cliente(srv, tmp_path, esperas).enviar(EventoAcesso.negado(1))

    assert envio.situacao == "enviado" and envio.tentativas == 3
    assert esperas == list(ESPERAS_S[:2])  # 0,5 s e 1 s


def test_esgotadas_as_tentativas_o_evento_vai_para_a_fila(tmp_path):
    srv = ServidorFalso(fora(), fora(), fora(), fora())
    c = cliente(srv, tmp_path)
    envio = c.enviar(EventoAcesso.bloqueado())

    assert envio.situacao == "enfileirado" and envio.tentativas == 4 and not envio.ok
    assert c.tamanho_fila() == 1
    item = json.loads((tmp_path / "fila.jsonl").read_text(encoding="utf-8"))
    assert item["rota"] == "/acessos" and item["payload"]["resultado"] == "BLOQUEADO"


def test_4xx_nao_repete_nem_enfileira(tmp_path):
    srv = ServidorFalso(http_error(422))
    c = cliente(srv, tmp_path)
    envio = c.enviar(EventoAcesso.negado(1))

    assert envio.situacao == "rejeitado" and envio.codigo_http == 422 and envio.tentativas == 1
    assert len(srv.requisicoes) == 1
    assert c.tamanho_fila() == 0


def test_reenviar_fila_entrega_o_que_der_e_mantem_o_resto(tmp_path):
    # dois eventos caem na fila
    c = cliente(ServidorFalso(*[fora() for _ in range(8)]), tmp_path)
    c.enviar(EventoAcesso.negado(1))
    c.enviar(Alerta(TipoAlerta.BLOQUEIO))
    assert c.tamanho_fila() == 2

    # a API volta, mas so aceita o primeiro
    c2 = cliente(ServidorFalso(201, *[fora() for _ in range(4)]), tmp_path)
    assert c2.reenviar_fila() == (1, 1)
    assert c2.tamanho_fila() == 1
    restante = json.loads((tmp_path / "fila.jsonl").read_text(encoding="utf-8"))
    assert restante["rota"] == "/alertas"

    # tudo volta ao normal
    c3 = cliente(ServidorFalso(201), tmp_path)
    assert c3.reenviar_fila() == (1, 0)
    assert c3.tamanho_fila() == 0


def test_reenviar_fila_descarta_rejeitados(tmp_path):
    c = cliente(ServidorFalso(*[fora() for _ in range(4)]), tmp_path)
    c.enviar(EventoAcesso.negado(1))
    c2 = cliente(ServidorFalso(http_error(400)), tmp_path)
    assert c2.reenviar_fila() == (0, 0)


def test_fila_inexistente_e_tratada_como_vazia(tmp_path):
    c = cliente(ServidorFalso(), tmp_path)
    assert c.reenviar_fila() == (0, 0) and c.tamanho_fila() == 0


def test_cliente_eco_nao_usa_rede_e_registra_payloads():
    linhas: list[str] = []
    eco = ClienteEco(saida=linhas.append)
    envio = eco.enviar(EventoAcesso.liberado(0))
    assert envio.ok and envio.situacao == "simulado"
    assert eco.enviados[0][0] == "/acessos"
    assert "18200" in linhas[0]


# ------------------------------------------------------- acordar a API


def test_acordar_devolve_true_assim_que_a_api_responde(tmp_path):
    srv = ServidorFalso(200)
    esperas: list = []
    c = cliente(srv, tmp_path, esperas)
    assert c.acordar(espera_s=30) is True
    url, metodo, _, _ = srv.requisicoes[0]
    assert url.endswith("/health") and metodo == "GET"
    assert esperas == []  # respondeu de primeira, nao dormiu


def test_acordar_insiste_enquanto_a_api_hiberna(tmp_path):
    # tres falhas (servico dormindo) e entao o 200
    srv = ServidorFalso(fora(), fora(), fora(), 200)
    esperas: list = []
    c = cliente(srv, tmp_path, esperas)
    assert c.acordar(espera_s=30) is True
    assert len(srv.requisicoes) == 4
    assert esperas == [2.0, 2.0, 2.0]


def test_acordar_desiste_quando_o_tempo_acaba(tmp_path):
    srv = ServidorFalso(*[fora() for _ in range(50)])
    c = cliente(srv, tmp_path)  # dormir e no-op, entao o limite e o relogio
    assert c.acordar(espera_s=0) is False
    assert len(srv.requisicoes) == 1  # tenta uma vez antes de olhar o relogio


def test_cliente_eco_nao_precisa_acordar():
    assert ClienteEco(saida=lambda s: None).acordar() is True
