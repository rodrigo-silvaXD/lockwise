"""Padrão Strategy: cada política decide sozinha quando um acesso merece alerta."""

from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

import pytest

from lockwise_api.dominio.eventos import AcessoRegistrado, Resultado, TipoAlerta
from lockwise_api.dominio.politicas import (
    Composta,
    JanelaHoraria,
    LimiteDeTentativas,
    SemSupervisao,
    politica_por_nome,
)

SP = ZoneInfo("America/Sao_Paulo")


def acesso(resultado: Resultado, tentativa: int = 1, hora_local: int = 12) -> AcessoRegistrado:
    momento = datetime(2026, 11, 10, hora_local, 30, tzinfo=SP).astimezone(timezone.utc)
    return AcessoRegistrado(momento, resultado, tentativa, 18_200 if resultado is Resultado.LIBERADO else 0, None)


# ------------------------------------------------------------ limite


def test_limite_avisa_na_segunda_tentativa_por_padrao():
    pol = LimiteDeTentativas()
    assert pol.avaliar(acesso(Resultado.NEGADO, 1)) == []
    (al,) = pol.avaliar(acesso(Resultado.NEGADO, 2))
    assert al.tipo is TipoAlerta.TENTATIVAS_SUSPEITAS and "2ª" in al.detalhe


def test_limite_ignora_liberado_e_bloqueado():
    pol = LimiteDeTentativas(limite=1)
    assert pol.avaliar(acesso(Resultado.LIBERADO, 3)) == []
    # BLOQUEADO já vem com alerta BLOQUEIO do gateway; não duplicar
    assert pol.avaliar(acesso(Resultado.BLOQUEADO, 3)) == []


def test_limite_configuravel():
    assert LimiteDeTentativas(limite=1).avaliar(acesso(Resultado.NEGADO, 1)) != []


# ----------------------------------------------------------- horario


def test_janela_padrao_06_23_em_horario_local():
    pol = JanelaHoraria()
    assert pol.avaliar(acesso(Resultado.LIBERADO, hora_local=12)) == []
    assert pol.avaliar(acesso(Resultado.LIBERADO, hora_local=6)) == []
    (al,) = pol.avaliar(acesso(Resultado.LIBERADO, hora_local=23))
    assert al.tipo is TipoAlerta.ACESSO_FORA_DO_HORARIO and "23:30" in al.detalhe
    assert pol.avaliar(acesso(Resultado.LIBERADO, hora_local=3)) != []


def test_janela_usa_fuso_local_e_nao_utc():
    """03:30 em São Paulo é 06:30 UTC. Uma política ingênua em UTC diria 'dentro'."""
    pol = JanelaHoraria()
    a = acesso(Resultado.LIBERADO, hora_local=3)
    assert a.momento.hour == 6  # UTC
    assert pol.avaliar(a) != []  # mas local é 03:30: fora


def test_janela_que_cruza_a_meia_noite():
    pol = JanelaHoraria(inicio=time(22, 0), fim=time(6, 0))
    assert pol.dentro(time(23, 0)) and pol.dentro(time(2, 0)) and pol.dentro(time(22, 0))
    assert not pol.dentro(time(6, 0)) and not pol.dentro(time(12, 0))


def test_janela_so_olha_liberados():
    pol = JanelaHoraria()
    assert pol.avaliar(acesso(Resultado.NEGADO, hora_local=3)) == []


# ---------------------------------------------------------- composta


def test_composta_reune_alertas_de_todas():
    pol = Composta((LimiteDeTentativas(limite=1), JanelaHoraria()))
    assert [a.tipo for a in pol.avaliar(acesso(Resultado.NEGADO, 1, hora_local=3))] == [
        TipoAlerta.TENTATIVAS_SUSPEITAS,
    ]
    assert [a.tipo for a in pol.avaliar(acesso(Resultado.LIBERADO, 1, hora_local=3))] == [
        TipoAlerta.ACESSO_FORA_DO_HORARIO,
    ]


def test_sem_supervisao_nunca_alerta():
    assert SemSupervisao().avaliar(acesso(Resultado.NEGADO, 3, hora_local=3)) == []


# ------------------------------------------------------------ fabrica


@pytest.mark.parametrize("nome,tipo", [
    ("limite", LimiteDeTentativas), ("horario", JanelaHoraria), ("composta", Composta), ("nenhuma", SemSupervisao),
])
def test_fabrica_por_nome(nome, tipo):
    assert isinstance(politica_por_nome(nome), tipo)


def test_fabrica_repassa_parametros():
    pol = politica_por_nome("composta", limite=1, janela=(time(8), time(18)), fuso="UTC")
    assert pol.politicas[0].limite == 1
    assert pol.politicas[1].inicio == time(8) and pol.politicas[1].fuso == "UTC"


def test_fabrica_rejeita_nome_desconhecido():
    with pytest.raises(ValueError, match="desconhecida"):
        politica_por_nome("aleatoria")
