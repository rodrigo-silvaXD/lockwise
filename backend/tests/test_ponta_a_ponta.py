"""A demo, automatizada: gateway real → HTTP real → API real → banco → consultas.

Sobe a API com uvicorn num porto livre (SQLite em arquivo), importa o gateway
de `../gateway`, executa `roteiros/demo.txt` contra a API e verifica, pelas
rotas de leitura, que tudo o que o circuito faria está no banco: 4 acessos,
3 alertas (2 do gateway + 1 da política de supervisão), demanda horária com a
energia da física e a fechadura de volta a AGUARDANDO.

Se este teste passa, a demo ao vivo funciona — só falta o Logisim na tela ao lado.
"""

from __future__ import annotations

import socket
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import pytest
import uvicorn

from lockwise_api.config import Configuracao
from lockwise_api.db import criar_engine
from lockwise_api.main import criar_app

RAIZ = Path(__file__).resolve().parents[2]
GATEWAY = RAIZ / "gateway"
ROTEIRO = GATEWAY / "roteiros" / "demo.txt"
CHAVE = "chave-ponta-a-ponta"


def _porto_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def api_no_ar(tmp_path_factory):
    if not ROTEIRO.exists():
        pytest.skip(f"gateway não encontrado em {GATEWAY}")
    banco = tmp_path_factory.mktemp("e2e") / "lockwise.db"
    config = Configuracao(database_url=f"sqlite:///{banco.as_posix()}", api_key=CHAVE, politica="limite")
    app = criar_app(config, engine=criar_engine(config.database_url))

    porto = _porto_livre()
    servidor = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=porto, log_level="warning"))
    thread = threading.Thread(target=servidor.run, daemon=True)
    thread.start()
    for _ in range(100):
        if servidor.started:
            break
        time.sleep(0.05)
    else:
        raise RuntimeError("uvicorn não subiu")

    yield f"http://127.0.0.1:{porto}"

    servidor.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(scope="module")
def gateway():
    sys.path.insert(0, str(GATEWAY))
    from lockwise_gateway import cli, fontes, transporte  # noqa: E402

    yield cli, fontes, transporte
    sys.path.remove(str(GATEWAY))


@pytest.fixture(scope="module")
def demo_executada(api_no_ar, gateway, tmp_path_factory):
    cli, fontes, transporte = gateway
    linhas: list[str] = []
    cliente = transporte.ClienteAPI(api_no_ar, CHAVE, fila=tmp_path_factory.mktemp("fila") / "fila.jsonl")
    interprete = cli.Interprete(cliente, saida=linhas.append)

    inicio = datetime.now(timezone.utc)
    interprete.rodar(fontes.Roteiro.do_arquivo(ROTEIRO))
    return interprete, linhas, cliente, inicio


def test_todos_os_posts_do_gateway_foram_aceitos(demo_executada):
    interprete, linhas, cliente, _ = demo_executada
    envios = [l for l in linhas if l.strip().startswith("POST ")]
    assert len(envios) == 6, envios  # 4 acessos + 2 alertas
    assert all("-> enviado HTTP 201" in l for l in envios), envios
    assert cliente.tamanho_fila() == 0
    assert interprete.maquina.estado.nome == "AGUARDANDO"


def test_os_acessos_do_circuito_estao_no_banco(demo_executada, api_no_ar):
    acessos = httpx.get(f"{api_no_ar}/acessos").json()
    # do mais recente ao mais antigo
    assert [a["resultado"] for a in acessos] == ["BLOQUEADO", "NEGADO", "NEGADO", "LIBERADO"]
    assert [a["tentativa"] for a in acessos] == [3, 2, 1, 1]
    assert [a["energia_mj"] for a in acessos] == [0, 0, 0, 18_200]
    assert [a["usuario_id"] for a in acessos] == [None, None, None, 1]
    assert all(a["momento"].endswith("Z") for a in acessos)


def test_alertas_do_gateway_e_da_politica(demo_executada, api_no_ar):
    alertas = httpx.get(f"{api_no_ar}/alertas").json()
    tipos = sorted(a["tipo"] for a in alertas)
    assert tipos == ["BLOQUEIO", "DESBLOQUEIO_ADMIN", "TENTATIVAS_SUSPEITAS"]

    suspeita = next(a for a in alertas if a["tipo"] == "TENTATIVAS_SUSPEITAS")
    segundo_negado = next(a for a in httpx.get(f"{api_no_ar}/acessos").json() if a["tentativa"] == 2)
    assert suspeita["acesso_id"] == segundo_negado["id"]  # a nuvem avisou uma tentativa antes do hardware bloquear
    assert all(a["resolvido"] is False for a in alertas)


def test_demanda_horaria_carrega_a_energia_da_fisica(demo_executada, api_no_ar):
    _, _, _, inicio = demo_executada
    demanda = httpx.get(f"{api_no_ar}/acessos/demanda-horaria").json()
    assert demanda["total_acessos"] == 4
    assert demanda["total_energia_mj"] == 18_200  # uma liberação, docs/fisica.md §6

    hora_local = inicio.astimezone(ZoneInfo(demanda["fuso"])).hour
    faixa = demanda["faixas"][hora_local]
    # a demo dura menos de um segundo: tudo cai na hora local em que começou
    assert faixa == {"hora": hora_local, "acessos": 4, "liberados": 1, "negados": 2, "bloqueados": 1, "energia_mj": 18_200}


def test_fechadura_voltou_a_aguardando_apos_desbloqueio(demo_executada, api_no_ar):
    fechadura = httpx.get(f"{api_no_ar}/fechadura").json()
    assert fechadura["estado"] == "AGUARDANDO" and fechadura["tentativas"] == 0
    assert fechadura["ultimo_evento"]["descricao"] == "DESBLOQUEIO_ADMIN"
    assert fechadura["avisos"] == []


def test_health_no_ar(api_no_ar):
    corpo = httpx.get(f"{api_no_ar}/health").json()
    assert corpo["status"] == "ok" and corpo["banco"] == "ok" and corpo["politica"] == "limite"
