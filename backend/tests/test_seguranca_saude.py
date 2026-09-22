"""X-API-Key nas escritas, leitura aberta, /health."""

from .conftest import acesso, alerta, montar


def test_escrita_sem_chave_e_401(api):
    assert api.post("/acessos", json=acesso("LIBERADO")).status_code == 401
    assert api.post("/alertas", json=alerta("BLOQUEIO")).status_code == 401
    assert api.patch("/alertas/1/resolver").status_code == 401


def test_escrita_com_chave_errada_e_401(api):
    r = api.post("/acessos", json=acesso("LIBERADO"), headers={"X-API-Key": "errada"})
    assert r.status_code == 401
    assert api.get("/acessos").json() == []


def test_leitura_e_aberta(api):
    for rota in ("/acessos", "/acessos/demanda-horaria", "/alertas", "/fechadura", "/health"):
        assert api.get(rota).status_code == 200, rota


def test_sem_chave_configurada_a_escrita_falha_fechada_com_503():
    """503, não 401: o gateway trata 5xx como temporário e guarda o evento na fila."""
    api = montar(api_key=None)
    r = api.post("/acessos", json=acesso("LIBERADO"), headers={"X-API-Key": "qualquer"})
    assert r.status_code == 503 and "LOCKWISE_API_KEY" in r.json()["detail"]
    assert api.get("/acessos").status_code == 200  # leitura segue aberta


def test_health_reporta_banco_politica_e_observadores():
    api = montar(politica="composta")
    corpo = api.get("/health").json()
    assert corpo == {
        "status": "ok", "banco": "ok", "motor": "sqlite", "persistente": False,
        "versao": "0.1.0", "politica": "composta", "observadores": 1,
    }


def test_health_denuncia_sqlite_como_nao_persistente():
    """Sem DATABASE_URL o codigo cai no SQLite; em producao isso e disco efemero."""
    corpo = montar().get("/health").json()
    assert corpo["motor"] == "sqlite" and corpo["persistente"] is False


def test_health_com_banco_indisponivel_e_503(api):
    api.app.state.engine.dispose()
    api.app.state.engine.url  # ainda existe, mas vamos quebrar a conexão de verdade:
    from sqlalchemy import create_engine
    api.app.state.engine = create_engine("sqlite:////caminho/que/nao/existe/x.db")
    r = api.get("/health")
    assert r.status_code == 503
    assert r.json()["status"] == "degradado" and r.json()["banco"].startswith("erro:")


def test_webhook_configurado_vira_observador():
    api = montar(webhook_url="https://hooks.exemplo/lockwise")
    assert api.get("/health").json()["observadores"] == 2


def test_docs_e_openapi_disponiveis(api):
    assert api.get("/docs").status_code == 200
    esquema = api.get("/openapi.json").json()
    assert esquema["info"]["title"] == "LOCKWISE API"
    assert set(esquema["paths"]) == {
        "/health", "/acessos", "/acessos/demanda-horaria", "/alertas", "/alertas/{id}/resolver", "/fechadura",
    }
