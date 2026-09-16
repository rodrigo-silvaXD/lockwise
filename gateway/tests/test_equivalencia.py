"""Prova de que o gateway é a mesma máquina que o circuito.

Três níveis de evidência, do mais forte ao mais concreto:

1. **Prova exaustiva.** Para cada um dos 16 estados possíveis dos flip-flops e
   cada uma das 128 combinações de pinos, o próximo estado calculado pelas
   equações do circuito (`circuito.py`) é idêntico ao calculado pelo padrão
   State (`estados.py` + `maquina.py`). 2048 casos — todo o espaço.

2. **Saídas.** Para todos os estados alcançáveis e todos os pinos, os sete
   pinos de saída dos dois modelos coincidem.

3. **Sequências da simulação.** As sequências documentadas em
   `referencia/sequencias.json`, extraídas das figuras de evidência, produzem
   nos dois modelos exatamente o estado e o contador que o Logisim mostra.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lockwise_gateway.circuito import GemeoNetlist, Pinos, Registradores, borda
from lockwise_gateway.maquina import MaquinaDeEstados

REFERENCIA = Path(__file__).resolve().parent.parent / "referencia" / "sequencias.json"


# ------------------------------------------------------------ 1. exaustiva


@pytest.mark.parametrize("reg", list(Registradores.todos()), ids=lambda r: f"Q{r.estado:02b}_C{r.contador:02b}")
def test_proximo_estado_identico_em_todo_o_espaco(reg: Registradores) -> None:
    for pinos in Pinos.todas():
        esperado = borda(pinos, reg)

        maquina = MaquinaDeEstados()
        maquina.carregar(reg)
        maquina.pulsar_clock(pinos)

        assert maquina.registradores() == esperado, (
            f"divergência em reg={reg} pinos={pinos}: "
            f"netlist→{esperado}, State→{maquina.registradores()}"
        )


# --------------------------------------------------------------- 2. saídas


@pytest.mark.parametrize("reg", list(Registradores.todos()), ids=lambda r: f"Q{r.estado:02b}_C{r.contador:02b}")
def test_saidas_identicas(reg: Registradores) -> None:
    netlist = GemeoNetlist()
    netlist.reg = reg
    maquina = MaquinaDeEstados()
    maquina.carregar(reg)

    for pinos in Pinos.todas():
        assert maquina.saidas(pinos) == netlist.saidas(pinos)


# ------------------------------------------------- 3. sequências da simulação


def _carregar_sequencias() -> list[dict]:
    return json.loads(REFERENCIA.read_text(encoding="utf-8"))["sequencias"]


def _pinos_de(passo: dict) -> Pinos:
    p = passo["pinos"]
    pinos = Pinos(
        confirma=bool(p.get("confirma", 0)),
        timeout=bool(p.get("timeout", 0)),
        reset=bool(p.get("reset", 0)),
    )
    if "senha" in p:
        pinos = pinos.com_senha(int(p["senha"], 2))
    return pinos


@pytest.mark.parametrize("seq", _carregar_sequencias(), ids=lambda s: s["nome"])
def test_sequencia_da_simulacao(seq: dict) -> None:
    netlist = GemeoNetlist()
    maquina = MaquinaDeEstados()

    for n, passo in enumerate(seq["passos"], start=1):
        pinos = _pinos_de(passo)
        esperado = passo["esperado"]

        reg = netlist.pulsar_clock(pinos)
        maquina.pulsar_clock(pinos)

        # o padrão State reproduz o Logisim
        assert maquina.estado.nome == esperado["estado"], f"passo {n}: estado"
        assert f"{maquina.contador.valor:02b}" == esperado["contador"], f"passo {n}: contador"

        # e as equações também
        assert reg == maquina.registradores(), f"passo {n}: netlist ≠ State"


def test_referencia_cobre_todos_os_estados_e_valores_do_contador() -> None:
    """Garante que as sequências de referência não deixam nenhum estado sem visita."""
    estados_vistos: set[str] = set()
    contadores_vistos: set[str] = set()
    for seq in _carregar_sequencias():
        for passo in seq["passos"]:
            estados_vistos.add(passo["esperado"]["estado"])
            contadores_vistos.add(passo["esperado"]["contador"])

    assert estados_vistos == {"AGUARDANDO", "VERIFICANDO", "LIBERADO", "BLOQUEADO"}
    assert contadores_vistos == {"00", "01", "10", "11"}
