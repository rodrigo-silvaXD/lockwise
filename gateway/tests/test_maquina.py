"""Os eventos nascem nas transições certas, com os valores da física e do banco."""

from dataclasses import replace

from lockwise_gateway.circuito import Pinos
from lockwise_gateway.eventos import (
    ENERGIA_LIBERACAO_MJ,
    USUARIO_MORADOR,
    Alerta,
    EventoAcesso,
    Resultado,
    TipoAlerta,
)
from lockwise_gateway.maquina import MaquinaDeEstados

CERTA = Pinos().com_senha(0b1011)
ERRADA = Pinos().com_senha(0b0000)


def tentar(m: MaquinaDeEstados, pinos: Pinos) -> list:
    """confirma on + clk + confirma off + clk, como no README."""
    eventos = m.pulsar_clock(replace(pinos, confirma=True))
    eventos += m.pulsar_clock(pinos)
    return eventos


def test_liberado_carrega_energia_da_fisica_e_o_morador():
    m = MaquinaDeEstados()
    (ev,) = tentar(m, CERTA)
    assert isinstance(ev, EventoAcesso)
    assert ev.resultado is Resultado.LIBERADO
    assert ev.energia_mj == ENERGIA_LIBERACAO_MJ == 18_200
    assert ev.usuario_id == USUARIO_MORADOR
    assert ev.tentativa == 1
    assert ev.momento.endswith("+00:00")  # UTC explícito


def test_negado_nao_consome_energia_nem_identifica_usuario():
    m = MaquinaDeEstados()
    (ev,) = tentar(m, ERRADA)
    assert ev.resultado is Resultado.NEGADO
    assert ev.energia_mj == 0
    assert ev.usuario_id is None
    assert ev.tentativa == 1
    (ev2,) = tentar(m, ERRADA)
    assert ev2.tentativa == 2


def test_terceiro_erro_gera_bloqueado_e_alerta():
    m = MaquinaDeEstados()
    tentar(m, ERRADA)
    tentar(m, ERRADA)
    eventos = tentar(m, ERRADA)
    assert [type(e) for e in eventos] == [EventoAcesso, Alerta]
    acesso, alerta = eventos
    assert acesso.resultado is Resultado.BLOQUEADO and acesso.tentativa == 3
    assert alerta.tipo is TipoAlerta.BLOQUEIO
    assert m.estado.nome == "BLOQUEADO" and m.contador.valor == 3


def test_bloqueado_ignora_senha_certa_e_so_sai_com_reset():
    m = MaquinaDeEstados()
    for _ in range(3):
        tentar(m, ERRADA)
    assert tentar(m, CERTA) == []
    assert m.estado.nome == "BLOQUEADO"

    (alerta,) = m.pulsar_clock(Pinos(reset=True))
    assert isinstance(alerta, Alerta) and alerta.tipo is TipoAlerta.DESBLOQUEIO_ADMIN
    assert m.estado.nome == "AGUARDANDO" and m.contador.valor == 0


def test_acerto_apos_dois_erros_registra_tentativa_3():
    m = MaquinaDeEstados()
    tentar(m, ERRADA)
    tentar(m, ERRADA)
    (ev,) = tentar(m, CERTA)
    assert ev.resultado is Resultado.LIBERADO and ev.tentativa == 3


def test_permanencia_nao_gera_evento():
    m = MaquinaDeEstados()
    assert m.pulsar_clock(Pinos()) == []  # AGUARDANDO permanece
    tentar(m, CERTA)
    assert m.pulsar_clock(CERTA) == []  # LIBERADO permanece sem timeout
    assert m.pulsar_clock(Pinos(timeout=True)) == []  # LIBERADO -> AGUARDANDO: sem evento


def test_payloads_seguem_o_esquema_do_banco():
    lib = EventoAcesso.liberado(0).payload()
    assert set(lib) == {"momento", "usuario_id", "resultado", "tentativa", "energia_mj"}
    al = Alerta(TipoAlerta.BLOQUEIO).payload()
    assert set(al) == {"tipo", "momento"}
