"""POST /acessos e GET /acessos: o contrato com o gateway e o histórico."""

from .conftest import acesso, em, montar


def test_registra_liberado_e_devolve_201_com_o_acesso(api, chave):
    r = api.post("/acessos", json=acesso("LIBERADO"), headers=chave)
    assert r.status_code == 201, r.text
    corpo = r.json()
    assert corpo["acesso"]["id"] == 1
    assert corpo["acesso"]["resultado"] == "LIBERADO"
    assert corpo["acesso"]["energia_mj"] == 18_200
    assert corpo["acesso"]["usuario_id"] == 1
    assert corpo["acesso"]["momento"] == "2026-01-10T14:00:00Z"  # sempre UTC explícito
    assert corpo["alertas_gerados"] == []


def test_payload_exato_do_gateway_e_aceito(api, chave):
    """Copiado da saída real do gateway. Se este teste quebrar, o contrato quebrou."""
    payload = {
        "momento": "2026-09-16T11:37:23.010+00:00",
        "usuario_id": 1,
        "resultado": "LIBERADO",
        "tentativa": 2,
        "energia_mj": 18200,
    }
    assert api.post("/acessos", json=payload, headers=chave).status_code == 201


def test_negado_sem_usuario_e_aceito(api, chave):
    r = api.post("/acessos", json=acesso("NEGADO", tentativa=2), headers=chave)
    assert r.status_code == 201 and r.json()["acesso"]["usuario_id"] is None


def test_validacoes_do_contrato(api, chave):
    invalidos = [
        {**acesso("LIBERADO"), "resultado": "ABERTO"},  # resultado fora do enum
        acesso("NEGADO", tentativa=0),  # tentativa mínima 1
        acesso("NEGADO", tentativa=4),  # o hardware bloqueia na 3ª
        acesso("LIBERADO", energia_mj=-1),  # energia negativa
        {**acesso("LIBERADO"), "momento": "ontem"},  # data inválida
    ]
    for corpo in invalidos:
        r = api.post("/acessos", json=corpo, headers=chave)
        assert r.status_code == 422, corpo
    assert api.get("/acessos").json() == []  # nada foi gravado


def test_usuario_desconhecido_e_422(api, chave):
    r = api.post("/acessos", json=acesso("LIBERADO", usuario_id=99), headers=chave)
    assert r.status_code == 422 and "99" in r.json()["detail"]


def test_momento_sem_fuso_e_aceito_como_utc(api, chave):
    r = api.post("/acessos", json={**acesso("LIBERADO"), "momento": "2026-01-10T14:00:00"}, headers=chave)
    assert r.status_code == 201
    assert r.json()["acesso"]["momento"] == "2026-01-10T14:00:00Z"


def test_historico_do_mais_recente_ao_mais_antigo(api, chave):
    for t, res in [(0, "NEGADO"), (10, "NEGADO"), (20, "LIBERADO")]:
        api.post("/acessos", json=acesso(res, t=t), headers=chave)
    lista = api.get("/acessos").json()
    assert [a["resultado"] for a in lista] == ["LIBERADO", "NEGADO", "NEGADO"]
    assert [a["id"] for a in lista] == [3, 2, 1]


def test_filtro_por_periodo_inicio_inclusivo_fim_exclusivo(api, chave):
    for t in (0, 60, 120, 180):
        api.post("/acessos", json=acesso("NEGADO", t=t), headers=chave)
    r = api.get("/acessos", params={"de": em(60), "ate": em(180)})
    assert sorted(a["momento"] for a in r.json()) == ["2026-01-10T14:01:00Z", "2026-01-10T14:02:00Z"]


def test_limite_e_respeitado(api, chave):
    for t in range(5):
        api.post("/acessos", json=acesso("NEGADO", t=t), headers=chave)
    assert len(api.get("/acessos", params={"limite": 2}).json()) == 2
    assert api.get("/acessos", params={"limite": 0}).status_code == 422


def test_politica_gera_alerta_ligado_ao_acesso():
    api = montar(politica="limite", limite_tentativas=2)
    chave = {"X-API-Key": "chave-de-teste"}
    api.post("/acessos", json=acesso("NEGADO", tentativa=1), headers=chave)
    r = api.post("/acessos", json=acesso("NEGADO", tentativa=2, t=10), headers=chave)

    (gerado,) = r.json()["alertas_gerados"]
    assert gerado["tipo"] == "TENTATIVAS_SUSPEITAS" and "2ª" in gerado["detalhe"]

    (alerta,) = api.get("/alertas").json()
    assert alerta["id"] == gerado["id"]
    assert alerta["acesso_id"] == r.json()["acesso"]["id"]
    assert alerta["momento"] == r.json()["acesso"]["momento"]  # mesmo instante do acesso
    assert alerta["resolvido"] is False
