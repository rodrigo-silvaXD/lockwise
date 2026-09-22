"""Os turnos: cobertura, sobreposição e custo noturno."""

from lockwise_otimizacao.turnos import (
    DURACAO_H,
    TURNOS,
    HORAS_NOTURNAS,
    CUSTO_BASE,
    cobertura,
    turnos_que_cobrem,
)


def test_sao_seis_turnos_de_oito_horas():
    assert len(TURNOS) == 6
    assert all(len(t.horas) == DURACAO_H == 8 for t in TURNOS)


def test_cada_hora_e_coberta_por_exatamente_dois_turnos():
    """E a sobreposicao que torna o problema nao trivial."""
    for h in range(24):
        assert len(turnos_que_cobrem(h)) == 2, f"hora {h}"


def test_todas_as_horas_do_dia_estao_cobertas():
    cobertas = {h for t in TURNOS for h in t.horas}
    assert cobertas == set(range(24))


def test_turno_que_cruza_a_meia_noite():
    t = next(t for t in TURNOS if t.inicio == 20)
    assert t.horas == (20, 21, 22, 23, 0, 1, 2, 3)
    assert t.cobre(23) and t.cobre(0) and not t.cobre(19)


def test_custo_noturno_e_proporcional_as_horas_noturnas():
    diurno = next(t for t in TURNOS if t.inicio == 8)    # 08-16, nenhuma hora noturna
    noturno = next(t for t in TURNOS if t.inicio == 0)   # 00-08, seis horas noturnas

    assert diurno.horas_noturnas == 0
    assert diurno.custo == CUSTO_BASE

    assert noturno.horas_noturnas == 6
    assert noturno.custo > diurno.custo
    assert noturno.custo == round(CUSTO_BASE * (1 + 0.20 * 6 / 8), 2)


def test_o_turno_mais_caro_e_o_que_tem_mais_madrugada():
    mais_caro = max(TURNOS, key=lambda t: t.custo)
    assert mais_caro.horas_noturnas == max(t.horas_noturnas for t in TURNOS)


def test_matriz_de_cobertura():
    t = next(t for t in TURNOS if t.inicio == 8)
    assert cobertura(t, 8) == 1 and cobertura(t, 15) == 1
    assert cobertura(t, 16) == 0 and cobertura(t, 7) == 0


def test_horas_noturnas_cobrem_a_madrugada():
    assert HORAS_NOTURNAS == {22, 23, 0, 1, 2, 3, 4, 5}
