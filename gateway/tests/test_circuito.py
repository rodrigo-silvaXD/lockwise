"""Sanidade das equações: o comparador e as duas decisões de projeto do README."""

from lockwise_gateway.circuito import Pinos, Registradores, borda, combinacional


def test_comparador_reconhece_apenas_1011():
    for senha in range(16):
        s = combinacional(Pinos().com_senha(senha), Registradores())
        assert s.igual == (senha == 0b1011), f"senha {senha:04b}"


def test_bloqueio_antecipado_na_terceira_tentativa():
    """E = C1·(C0 + ERRO): com contador em 10 e erro, bloqueia nesta borda."""
    verificando_com_dois_erros = Registradores(q1=False, q0=True, c1=True, c0=False)
    s = combinacional(Pinos().com_senha(0), verificando_com_dois_erros)
    assert s.e is True
    assert (s.d1, s.d0) == (True, True)  # BLOQUEADO
    assert (s.dc1, s.dc0) == (True, True)  # e o contador vai a 11 na mesma borda


def test_contador_satura_em_11():
    """EN = ERRO·¬(C1·C0): no 11, um novo erro não transborda para 00."""
    verificando_cheio = Registradores(q1=False, q0=True, c1=True, c0=True)
    prox = borda(Pinos().com_senha(0), verificando_cheio)
    assert prox.contador == 0b11


def test_reset_zera_contador_em_qualquer_estado():
    for reg in Registradores.todos():
        prox = borda(Pinos(reset=True), reg)
        assert prox.contador == 0


def test_liberado_zera_contador_na_borda_seguinte():
    liberado_com_dois_erros = Registradores(q1=True, q0=False, c1=True, c0=False)
    prox = borda(Pinos().com_senha(0b1011), liberado_com_dois_erros)
    assert prox.estado == 0b10 and prox.contador == 0


def test_pinos_todas_tem_128_combinacoes_distintas():
    assert len(set(Pinos.todas())) == 128
    assert len(set(Registradores.todos())) == 16
