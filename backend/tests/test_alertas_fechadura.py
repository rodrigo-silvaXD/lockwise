"""POST/GET/PATCH /alertas e GET /fechadura (a projeção via HTTP)."""

from datetime import timedelta

from .conftest import T0, acesso, alerta, em


def test_alerta_do_gateway_e_registrado(api, chave):
    r = api.post("/alertas", json=alerta("BLOQUEIO"), headers=chave)
    assert r.status_code == 201, r.text
    corpo = r.json()
    assert corpo["tipo"] == "BLOQUEIO" and corpo["resolvido"] is False and corpo["acesso_id"] is None


def test_payload_exato_do_gateway_e_aceito(api, chave):
    payload = {"tipo": "DESBLOQUEIO_ADMIN", "momento": "2026-09-16T11:48:11.832+00:00"}
    assert api.post("/alertas", json=payload, headers=chave).status_code == 201


def test_tipo_desconhecido_e_422(api, chave):
    assert api.post("/alertas", json=alerta("INVASAO_ALIEN"), headers=chave).status_code == 422


def test_listar_e_filtrar_por_resolvido(api, chave):
    api.post("/alertas", json=alerta("BLOQUEIO", 0), headers=chave)
    api.post("/alertas", json=alerta("DESBLOQUEIO_ADMIN", 10), headers=chave)
    api.patch("/alertas/1/resolver", headers=chave)

    todos = api.get("/alertas").json()
    assert [a["tipo"] for a in todos] == ["DESBLOQUEIO_ADMIN", "BLOQUEIO"]  # mais recente primeiro
    assert [a["id"] for a in api.get("/alertas", params={"resolvido": "false"}).json()] == [2]
    assert [a["id"] for a in api.get("/alertas", params={"resolvido": "true"}).json()] == [1]


def test_resolver_e_idempotente_e_404_se_nao_existe(api, chave):
    api.post("/alertas", json=alerta("BLOQUEIO"), headers=chave)
    assert api.patch("/alertas/1/resolver", headers=chave).json()["resolvido"] is True
    assert api.patch("/alertas/1/resolver", headers=chave).json()["resolvido"] is True
    assert api.patch("/alertas/42/resolver", headers=chave).status_code == 404


# --------------------------------------------------------------- fechadura


def test_fechadura_comeca_aguardando(api):
    corpo = api.get("/fechadura").json()
    assert corpo["estado"] == "AGUARDANDO" and corpo["tentativas"] == 0
    assert corpo["ultimo_evento"] is None and corpo["avisos"] == []


def test_fechadura_liberada_agora_mesmo_mostra_quando_fecha(api, chave):
    from datetime import datetime, timezone

    agora = datetime.now(timezone.utc)
    api.post("/acessos", json={**acesso("LIBERADO"), "momento": agora.isoformat()}, headers=chave)
    corpo = api.get("/fechadura").json()
    assert corpo["estado"] == "LIBERADO"
    fecha_em = datetime.fromisoformat(corpo["trava_fecha_em"])
    assert abs((fecha_em - agora).total_seconds() - 5.16) < 0.01
    assert corpo["ultimo_evento"]["descricao"] == "LIBERADO (tentativa 1, 18200 mJ)"


def test_fechadura_liberada_no_passado_ja_esta_aguardando(api, chave):
    api.post("/acessos", json=acesso("LIBERADO"), headers=chave)  # T0 está no passado
    corpo = api.get("/fechadura").json()
    assert corpo["estado"] == "AGUARDANDO" and corpo["trava_fecha_em"] is None
    # `desde` é o instante em que o NE555 fechou a trava
    assert corpo["desde"] == "2026-01-10T14:00:05.160000Z"


def test_fechadura_bloqueada_e_desbloqueio(api, chave):
    api.post("/acessos", json=acesso("NEGADO", 1, 0), headers=chave)
    api.post("/acessos", json=acesso("NEGADO", 2, 10), headers=chave)
    parcial = api.get("/fechadura").json()
    assert parcial["estado"] == "AGUARDANDO" and parcial["tentativas"] == 2

    api.post("/acessos", json=acesso("BLOQUEADO", 3, 20), headers=chave)
    api.post("/alertas", json=alerta("BLOQUEIO", 20), headers=chave)
    corpo = api.get("/fechadura").json()
    assert corpo["estado"] == "BLOQUEADO" and corpo["tentativas"] == 3
    assert corpo["ultimo_evento"] == {"tipo": "alerta", "momento": "2026-01-10T14:00:20Z", "descricao": "BLOQUEIO"}

    api.post("/alertas", json=alerta("DESBLOQUEIO_ADMIN", 100), headers=chave)
    corpo = api.get("/fechadura").json()
    assert corpo["estado"] == "AGUARDANDO" and corpo["tentativas"] == 0 and corpo["desde"] == "2026-01-10T14:01:40Z"


def test_fechadura_anota_aviso_em_sequencia_impossivel(api, chave):
    api.post("/acessos", json=acesso("BLOQUEADO", 3, 0), headers=chave)
    api.post("/acessos", json=acesso("NEGADO", 1, 10), headers=chave)  # impossível no hardware
    corpo = api.get("/fechadura").json()
    assert corpo["estado"] == "BLOQUEADO"
    assert len(corpo["avisos"]) == 1 and "impossível" in corpo["avisos"][0]
    assert len(api.get("/acessos").json()) == 2  # o evento foi guardado, não rejeitado
