"""O gateway contra o arquivo .circ de verdade.

`circuito.py` é uma transcrição manual da netlist. Este teste elimina a
confiança na transcrição: lê `circuito/lockwise_completo.circ`, simula o
grafo de portas genericamente (sem saber nada sobre o LOCKWISE) e exige que
o próximo estado e as saídas coincidam com `circuito.py` em todos os 2048
casos. Se alguém mover uma porta no Logisim e esquecer o Python, isto quebra.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lockwise_gateway.circuito import GemeoNetlist, Pinos, Registradores, borda

from .logisim import carregar

CIRC = Path(__file__).resolve().parents[2] / "circuito" / "lockwise_completo.circ"

# rótulo do flip-flop no .circ -> campo de Registradores
FLIPFLOPS = {"FF1": "q1", "FF0": "q0", "FFC1": "c1", "FFC0": "c0"}


@pytest.fixture(scope="module")
def netlist():
    if not CIRC.exists():
        pytest.skip(f"arquivo do circuito não encontrado: {CIRC}")
    return carregar(CIRC, circuito="LOCKWISE")


def _entradas(p: Pinos) -> dict[str, bool]:
    return {
        "S3": p.s3, "S2": p.s2, "S1": p.s1, "S0": p.s0,
        "CONFIRMA": p.confirma, "TIMEOUT": p.timeout, "RESET": p.reset,
        "CLK": False,  # a borda é implícita em `proximo_estado`
    }


def _estado_ff(r: Registradores) -> dict[str, bool]:
    return {rotulo: getattr(r, campo) for rotulo, campo in FLIPFLOPS.items()}


def test_o_circ_tem_a_estrutura_documentada(netlist):
    tipos = [p.tipo for p in netlist.portas]
    assert tipos.count("AND Gate") == 20  # 15 de duas entradas + 5 de três
    assert tipos.count("OR Gate") == 5  # 3 de duas entradas + 2 de três
    assert tipos.count("NOT Gate") == 6
    assert tipos.count("XOR Gate") == 2
    assert set(netlist.flipflops) == set(FLIPFLOPS)
    assert set(netlist.pinos_entrada) == {"S3", "S2", "S1", "S0", "CONFIRMA", "TIMEOUT", "RESET", "CLK"}
    assert set(netlist.pinos_saida) == {
        "AGUARDANDO", "VERIFICANDO", "TRAVA_ABERTA", "BLOQUEADO", "SENHA_OK", "ERROS_C1", "ERROS_C0",
    }


@pytest.mark.parametrize("reg", list(Registradores.todos()), ids=lambda r: f"Q{r.estado:02b}_C{r.contador:02b}")
def test_proximo_estado_do_circ_igual_ao_gateway(netlist, reg):
    for pinos in Pinos.todas():
        do_circ = netlist.proximo_estado(_entradas(pinos), _estado_ff(reg))
        do_gateway = borda(pinos, reg)
        assert do_circ == _estado_ff(do_gateway), f"reg={reg} pinos={pinos}"


@pytest.mark.parametrize("reg", list(Registradores.todos()), ids=lambda r: f"Q{r.estado:02b}_C{r.contador:02b}")
def test_saidas_do_circ_iguais_ao_gateway(netlist, reg):
    gemeo = GemeoNetlist()
    gemeo.reg = reg
    for pinos in Pinos.todas():
        assert netlist.saidas(_entradas(pinos), _estado_ff(reg)) == gemeo.saidas(pinos), f"reg={reg} pinos={pinos}"


def test_equacao_do_readme_antigo_estaria_errada(netlist):
    """Documenta a divergência encontrada: com EN = ERRO·Ē, o 3º erro deixaria o contador em 10.

    A netlist real (EN = ERRO·¬(C1·C0)) leva o contador a 11, como a fig. 11 mostra.
    """
    verificando_com_dois_erros = Registradores(q1=False, q0=True, c1=True, c0=False)
    prox = netlist.proximo_estado(_entradas(Pinos().com_senha(0)), _estado_ff(verificando_com_dois_erros))
    assert (prox["FF1"], prox["FF0"]) == (True, True), "deve ir a BLOQUEADO"
    assert (prox["FFC1"], prox["FFC0"]) == (True, True), "contador deve ir a 11, não ficar em 10"
