"""Padrão State: a projeção reconstrói a fechadura a partir dos eventos."""

from datetime import datetime, timedelta, timezone

from lockwise_api.dominio.estados import Aguardando, Bloqueado, Liberado, Projecao
from lockwise_api.dominio.eventos import (
    TEMPO_TRAVA_ABERTA_S,
    AcessoRegistrado,
    AlertaRegistrado,
    Resultado,
    TipoAlerta,
)

T0 = datetime(2026, 11, 10, 14, 0, 0, tzinfo=timezone.utc)


def em(segundos: float) -> datetime:
    return T0 + timedelta(seconds=segundos)


def acesso(resultado: Resultado, tentativa: int, t: float = 0) -> AcessoRegistrado:
    energia = 18_200 if resultado is Resultado.LIBERADO else 0
    usuario = 1 if resultado is Resultado.LIBERADO else None
    return AcessoRegistrado(em(t), resultado, tentativa, energia, usuario)


def alerta(tipo: TipoAlerta, t: float = 0) -> AlertaRegistrado:
    return AlertaRegistrado(em(t), tipo)


def test_comeca_aguardando_sem_tentativas():
    p = Projecao()
    assert isinstance(p.estado, Aguardando) and p.estado.tentativas == 0
    assert p.ultimo_evento is None and p.avisos == []


def test_negados_acumulam_tentativas_e_permanecem_aguardando():
    p = Projecao.reconstruir([acesso(Resultado.NEGADO, 1, 0), acesso(Resultado.NEGADO, 2, 10)])
    assert isinstance(p.estado, Aguardando) and p.estado.tentativas == 2


def test_liberado_vale_pelo_tempo_do_ne555_e_depois_expira():
    p = Projecao.reconstruir([acesso(Resultado.LIBERADO, 1, 0)])
    assert isinstance(p.estado, Liberado)
    assert p.vigente(em(1)).nome == "LIBERADO"
    assert p.vigente(em(TEMPO_TRAVA_ABERTA_S - 0.01)).nome == "LIBERADO"
    depois = p.vigente(em(TEMPO_TRAVA_ABERTA_S))
    assert isinstance(depois, Aguardando) and depois.tentativas == 0
    assert depois.desde == em(TEMPO_TRAVA_ABERTA_S)  # o instante em que o NE555 fechou a trava


def test_liberado_zera_as_tentativas_anteriores():
    p = Projecao.reconstruir([
        acesso(Resultado.NEGADO, 1, 0), acesso(Resultado.NEGADO, 2, 10), acesso(Resultado.LIBERADO, 3, 20),
    ])
    assert isinstance(p.estado, Liberado) and p.estado.tentativas == 0
    assert p.vigente(em(60)).tentativas == 0


def test_terceiro_erro_bloqueia_e_bloqueio_ignora_acessos():
    p = Projecao.reconstruir([
        acesso(Resultado.NEGADO, 1, 0),
        acesso(Resultado.NEGADO, 2, 10),
        acesso(Resultado.BLOQUEADO, 3, 20),
        alerta(TipoAlerta.BLOQUEIO, 20),
    ])
    assert isinstance(p.estado, Bloqueado) and p.estado.tentativas == 3
    assert p.avisos == []

    # um acesso durante o bloqueio é impossível no hardware: registrado, avisado, estado mantido
    p.aplicar(acesso(Resultado.LIBERADO, 1, 30))
    assert isinstance(p.estado, Bloqueado)
    assert len(p.avisos) == 1 and "BLOQUEADA" in p.avisos[0]


def test_desbloqueio_admin_volta_a_aguardando_zerado():
    p = Projecao.reconstruir([
        acesso(Resultado.BLOQUEADO, 3, 0), alerta(TipoAlerta.BLOQUEIO, 0), alerta(TipoAlerta.DESBLOQUEIO_ADMIN, 100),
    ])
    assert isinstance(p.estado, Aguardando) and p.estado.tentativas == 0
    assert p.estado.desde == em(100)


def test_alertas_da_nuvem_nao_mudam_o_estado():
    p = Projecao.reconstruir([acesso(Resultado.NEGADO, 2, 0), alerta(TipoAlerta.TENTATIVAS_SUSPEITAS, 0)])
    assert isinstance(p.estado, Aguardando) and p.estado.tentativas == 2


def test_reconstruir_ordena_por_momento():
    fora_de_ordem = [acesso(Resultado.LIBERADO, 1, 50), acesso(Resultado.NEGADO, 1, 0), acesso(Resultado.NEGADO, 2, 10)]
    p = Projecao.reconstruir(fora_de_ordem)
    assert isinstance(p.estado, Liberado)
    assert p.ultimo_evento.momento == em(50)


def test_evento_apos_liberado_encontra_a_trava_ja_fechada():
    """O hardware não aceita CONFIRMA em LIBERADO; o próximo acesso veio depois do TIMEOUT."""
    p = Projecao.reconstruir([acesso(Resultado.LIBERADO, 1, 0), acesso(Resultado.NEGADO, 1, 30)])
    assert isinstance(p.estado, Aguardando) and p.estado.tentativas == 1


def test_momento_sem_fuso_e_tratado_como_utc():
    ingenuo = AcessoRegistrado(datetime(2026, 11, 10, 14, 0, 0), Resultado.LIBERADO, 1, 18_200, 1)
    p = Projecao.reconstruir([ingenuo])
    assert p.estado.desde == T0
