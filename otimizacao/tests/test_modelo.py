"""O modelo de cobertura: cobre a demanda, minimiza o custo, ganha da escala ingênua."""

import pytest

from lockwise_otimizacao.demanda import Demanda
from lockwise_otimizacao.modelo import EQUIPE_MAXIMA, SemSolucao, comparar, escala_ingenua, otimizar
from lockwise_otimizacao.turnos import TURNOS


def demanda(acessos, dias=1, **kw) -> Demanda:
    return Demanda(
        acessos=tuple(acessos),
        energia_mj=tuple(a * 18_200 for a in acessos),
        fuso="America/Sao_Paulo",
        origem="teste",
        dias=dias,
        **kw,
    )


# perfil de portaria: madrugada parada, picos às 7h e às 18h
PERFIL = [1, 0, 0, 0, 1, 2, 6, 18, 11, 4, 3, 5, 10, 7, 3, 4, 7, 13, 19, 14, 7, 5, 3, 1]


def test_a_solucao_cobre_todas_as_horas():
    d = demanda(PERFIL)
    e = otimizar(d)
    assert e.cobre_tudo()
    for h in range(24):
        assert e.presentes(h) >= d.vigilantes[h], f"hora {h} descoberta"


def test_respeita_o_limite_de_equipe():
    e = otimizar(demanda(PERFIL), equipe_maxima=EQUIPE_MAXIMA)
    assert e.total_vigilantes <= EQUIPE_MAXIMA


def test_e_mais_barata_que_a_ingenua():
    c = comparar(demanda(PERFIL))
    assert c.otimizada.custo < c.ingenua.custo
    assert c.economia > 0 and c.economia_percentual > 0
    assert c.ingenua.cobre_tudo()  # a ingênua também cobre; ela só custa mais


def test_nenhuma_escala_alternativa_e_mais_barata():
    """Verificação independente do solver: força bruta no espaço viável."""
    d = demanda(PERFIL)
    otima = otimizar(d)

    limite = max(d.vigilantes) + 1  # nunca precisa de mais que o pico num único turno
    melhor = None
    for combinacao in _todas_as_combinacoes(limite):
        if sum(combinacao) > EQUIPE_MAXIMA:
            continue
        if any(
            sum(x for t, x in zip(TURNOS, combinacao) if t.cobre(h)) < d.vigilantes[h]
            for h in range(24)
        ):
            continue
        custo = sum(t.custo * x for t, x in zip(TURNOS, combinacao))
        if melhor is None or custo < melhor:
            melhor = custo

    assert melhor == pytest.approx(otima.custo), "o solver não achou o ótimo de verdade"


def _todas_as_combinacoes(limite: int):
    from itertools import product

    return product(range(limite + 1), repeat=len(TURNOS))


def test_presenca_minima_impede_portaria_vazia():
    """Mesmo sem nenhum acesso, alguém fica de plantão."""
    e = otimizar(demanda([0] * 24))
    assert all(e.presentes(h) >= 1 for h in range(24))


def test_demanda_maior_exige_mais_gente():
    pouco = otimizar(demanda(PERFIL), equipe_maxima=30)
    muito = otimizar(demanda([a * 2 for a in PERFIL]), equipe_maxima=30)
    assert muito.total_vigilantes > pouco.total_vigilantes
    assert muito.custo > pouco.custo


def test_equipe_pequena_demais_nao_tem_solucao():
    with pytest.raises(SemSolucao, match="pico"):
        otimizar(demanda([a * 4 for a in PERFIL]), equipe_maxima=3)


def test_turno_noturno_custa_mais_e_o_modelo_prefere_o_diurno():
    """Com demanda só de dia, o modelo evita pagar adicional noturno."""
    so_de_dia = [0] * 24
    for h in range(9, 17):
        so_de_dia[h] = 12
    e = otimizar(demanda(so_de_dia))
    diurno = next(t for t in TURNOS if t.inicio == 8)  # 08–16, sem hora noturna
    assert e.por_turno[diurno.indice] >= 1


def test_ingenua_usa_o_mesmo_efetivo_em_todo_turno():
    e = escala_ingenua(demanda(PERFIL))
    assert len(set(e.por_turno)) == 1
    assert e.cobre_tudo()


def test_comparacao_reporta_economia_mensal():
    c = comparar(demanda(PERFIL))
    assert c.economia_mensal == pytest.approx(c.economia * 30)
    assert c.vigilantes_a_menos == c.ingenua.total_vigilantes - c.otimizada.total_vigilantes
