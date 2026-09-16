"""GET /acessos/demanda-horaria — a entrada d_h do modelo de otimização."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from .conftest import acesso, montar

SP = ZoneInfo("America/Sao_Paulo")


def local(hora: int, minuto: int = 0, dia: int = 10) -> str:
    return datetime(2026, 11, dia, hora, minuto, tzinfo=SP).astimezone(timezone.utc).isoformat()


def test_sempre_24_faixas_mesmo_sem_dados(api):
    corpo = api.get("/acessos/demanda-horaria").json()
    assert [f["hora"] for f in corpo["faixas"]] == list(range(24))
    assert all(f["acessos"] == 0 for f in corpo["faixas"])
    assert corpo["total_acessos"] == 0 and corpo["fuso"] == "America/Sao_Paulo"


def test_agrega_por_hora_local_nao_por_utc(api, chave):
    """22:30 em São Paulo é 01:30 UTC do dia seguinte. A faixa certa é a 22."""
    api.post("/acessos", json={**acesso("LIBERADO"), "momento": local(22, 30)}, headers=chave)
    faixas = api.get("/acessos/demanda-horaria").json()["faixas"]
    assert faixas[22]["acessos"] == 1 and faixas[22]["liberados"] == 1
    assert faixas[1]["acessos"] == 0


def test_soma_energia_e_separa_resultados(api, chave):
    for corpo in [
        {**acesso("LIBERADO"), "momento": local(8, 5)},
        {**acesso("LIBERADO"), "momento": local(8, 40)},
        {**acesso("NEGADO", 1), "momento": local(8, 50)},
        {**acesso("NEGADO", 2), "momento": local(19, 0)},
        {**acesso("BLOQUEADO", 3), "momento": local(19, 1)},
    ]:
        api.post("/acessos", json=corpo, headers=chave)

    r = api.get("/acessos/demanda-horaria").json()
    assert r["faixas"][8] == {"hora": 8, "acessos": 3, "liberados": 2, "negados": 1, "bloqueados": 0, "energia_mj": 36_400}
    assert r["faixas"][19] == {"hora": 19, "acessos": 2, "liberados": 0, "negados": 1, "bloqueados": 1, "energia_mj": 0}
    assert r["total_acessos"] == 5 and r["total_energia_mj"] == 36_400


def test_periodo_filtra_a_demanda(api, chave):
    api.post("/acessos", json={**acesso("LIBERADO"), "momento": local(8, dia=10)}, headers=chave)
    api.post("/acessos", json={**acesso("LIBERADO"), "momento": local(8, dia=11)}, headers=chave)
    de = datetime(2026, 11, 11, tzinfo=SP).isoformat()
    r = api.get("/acessos/demanda-horaria", params={"de": de}).json()
    assert r["total_acessos"] == 1 and r["de"] is not None


def test_fuso_e_configuravel():
    api = montar(fuso="UTC")
    chave = {"X-API-Key": "chave-de-teste"}
    api.post("/acessos", json={**acesso("LIBERADO"), "momento": local(22, 30)}, headers=chave)  # 01:30 UTC
    r = api.get("/acessos/demanda-horaria").json()
    assert r["fuso"] == "UTC" and r["faixas"][1]["acessos"] == 1
