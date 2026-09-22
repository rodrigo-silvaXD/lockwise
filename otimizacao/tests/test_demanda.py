"""Conversao de acessos para vigilantes, e leitura da API."""

import json

import pytest

from lockwise_otimizacao.demanda import Demanda, da_api, do_arquivo


def faixa(h, acessos=0, energia=0):
    liberados = acessos
    return {"hora": h, "acessos": acessos, "liberados": liberados, "negados": 0,
            "bloqueados": 0, "energia_mj": energia}


def corpo(acessos_por_hora, fuso="America/Sao_Paulo"):
    return {"de": None, "ate": None, "fuso": fuso,
            "total_acessos": sum(acessos_por_hora), "total_energia_mj": 0,
            "faixas": [faixa(h, a, a * 18_200) for h, a in enumerate(acessos_por_hora)]}


def demanda(acessos, **kw):
    return Demanda(acessos=tuple(acessos), energia_mj=tuple(a * 18_200 for a in acessos),
                   fuso="America/Sao_Paulo", origem="teste", **kw)


def test_divide_pelo_numero_de_dias():
    """A rota devolve o acumulado do periodo; a escala e de um dia tipico."""
    d = demanda([56] * 24, dias=28)
    assert d.media_diaria[0] == 2.0
    assert d.vigilantes[0] == 1  # 2 acessos / 4 por vigilante -> 1


def test_arredonda_para_cima():
    d = demanda([5] + [0] * 23, dias=1, capacidade=4)
    assert d.vigilantes[0] == 2  # 5/4 = 1,25 -> 2 vigilantes


def test_presenca_minima_na_madrugada_vazia():
    d = demanda([0] * 24, dias=1)
    assert d.vigilantes == (1,) * 24


def test_presenca_minima_configuravel():
    assert demanda([0] * 24, presenca_minima=2).vigilantes[0] == 2


def test_capacidade_maior_exige_menos_gente():
    acessos = [16] + [0] * 23
    assert demanda(acessos, capacidade=4).vigilantes[0] == 4
    assert demanda(acessos, capacidade=8).vigilantes[0] == 2


def test_hora_de_pico_e_totais():
    acessos = [0] * 24
    acessos[18] = 40
    d = demanda(acessos, dias=2)
    assert d.hora_de_pico == 18
    assert d.total_acessos == 40
    assert d.total_energia_mj == 40 * 18_200


def test_rejeita_periodo_ou_faixas_invalidos():
    with pytest.raises(ValueError, match="24 faixas"):
        Demanda(acessos=(1, 2), energia_mj=(0, 0), fuso="UTC", origem="x")
    with pytest.raises(ValueError, match="pelo menos um dia"):
        demanda([0] * 24, dias=0)
    with pytest.raises(ValueError, match="capacidade"):
        demanda([0] * 24, capacidade=0)


def test_le_do_arquivo(tmp_path):
    p = tmp_path / "demanda.json"
    p.write_text(json.dumps(corpo([2] * 24)), encoding="utf-8")
    d = do_arquivo(p, dias=1)
    assert d.total_acessos == 48 and d.fuso == "America/Sao_Paulo"
    assert str(p) in d.origem


def test_le_da_api_montando_a_url():
    chamadas = []

    class Resp:
        def __init__(self, dados): self._d = json.dumps(dados).encode()
        def read(self): return self._d
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def abrir(req, timeout):
        chamadas.append((req.full_url, req.get_method()))
        return Resp(corpo([3] * 24))

    d = da_api("https://api.exemplo/", de="2026-11-01T00:00:00Z", abrir=abrir, dias=7)
    url, metodo = chamadas[0]
    assert url.startswith("https://api.exemplo/acessos/demanda-horaria?de=") and metodo == "GET"
    assert d.total_acessos == 72 and d.dias == 7


def test_url_codifica_o_fuso_do_momento():
    """Sem urlencode, o +00:00 vira espaco na query e a API devolve 422."""
    vistas = []

    class Resp:
        def read(self): return json.dumps(corpo([1] * 24)).encode()
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def abrir(req, timeout):
        vistas.append(req.full_url)
        return Resp()

    da_api("https://api.exemplo", de="2026-09-15T18:11:21.772172+00:00", abrir=abrir)
    assert "+" not in vistas[0].split("?", 1)[1]
    assert "%2B00%3A00" in vistas[0]


def test_api_com_faixas_faltando_e_erro():
    class Resp:
        def read(self): return json.dumps({"fuso": "UTC", "faixas": [faixa(0, 1)]}).encode()
        def __enter__(self): return self
        def __exit__(self, *a): return False

    with pytest.raises(ValueError, match="24 faixas"):
        da_api("https://api.exemplo", abrir=lambda req, timeout: Resp())
