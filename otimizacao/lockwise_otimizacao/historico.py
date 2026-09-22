"""Gera histórico de acessos para o modelo ter demanda nas 24 horas.

Os dados são sintéticos, e isso precisa ser dito em voz alta. O que eles não
são é fabricados por fora: cada evento nasce da **mesma máquina de estados do
gateway**, acionando os mesmos pinos, e é enviado pela **mesma API** com a
mesma chave. O `tentativa`, o `energia_mj` e a sequência de estados saem
corretos porque quem os produz é o circuito replicado, não um gerador de JSON.

O cenário é a **portaria de um condomínio** de cerca de cinquenta unidades,
não uma porta residencial isolada. É o que justifica falar em escala de
vigilância: ninguém escala turnos para uma única porta. O circuito demonstra
o controle de um ponto de acesso com uma senha; a tabela `usuario` do banco já
modela vários moradores, e o cenário de otimização assume esse uso.

O perfil é o de um prédio: pico ao sair de manhã e ao voltar à noite,
movimento moderado no meio do dia, madrugada quase parada. Fins de semana
mais espalhados e com mais movimento à tarde e à noite.

O que muda em relação à operação real é só o relógio: em vez de esperar dias,
os eventos são carimbados com datas passadas.
"""

from __future__ import annotations

import random
import sys
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterator
from zoneinfo import ZoneInfo

# O gateway é o irmão ao lado no repositório; importamos a FSM de lá em vez de
# reimplementar o comportamento do circuito.
_GATEWAY = Path(__file__).resolve().parents[2] / "gateway"
if str(_GATEWAY) not in sys.path:
    sys.path.insert(0, str(_GATEWAY))

from lockwise_gateway.circuito import Pinos  # noqa: E402
from lockwise_gateway.eventos import SENHA, Evento  # noqa: E402
from lockwise_gateway.maquina import MaquinaDeEstados  # noqa: E402

FUSO = ZoneInfo("America/Sao_Paulo")

# Acessos esperados por hora local num dia útil, para a portaria inteira.
# Índice = hora. Saída para o trabalho entre 7h e 8h, almoço, retorno às 18h.
PERFIL_DIA_UTIL = (
    0.4, 0.2, 0.1, 0.1, 0.4, 1.6,        # 00–05 madrugada
    6.4, 17.6, 11.2, 4.0, 3.2, 4.8,      # 06–11 manhã, pico às 7h
    8.8, 7.2, 3.2, 4.0, 7.2, 12.8,       # 12–17 almoço e início do retorno
    19.2, 13.6, 7.2, 4.8, 2.8, 1.2,      # 18–23 pico às 18h, noite calma
)

# Fim de semana: ninguém sai às 7h, mas há movimento à tarde e à noite.
PERFIL_FIM_DE_SEMANA = (
    2.0, 1.2, 0.6, 0.3, 0.2, 0.4,
    0.8, 2.0, 4.8, 7.2, 8.8, 9.6,
    10.4, 8.0, 8.8, 9.6, 10.4, 11.2,
    12.0, 10.4, 8.8, 7.2, 5.6, 3.6,
)

# Chance de o morador errar a senha numa tentativa. Erros acontecem mais no
# escuro: à noite e de madrugada a mão erra mais.
ERRO_BASE = 0.10
ERRO_NOTURNO = 0.22
HORAS_ESCURAS = frozenset({0, 1, 2, 3, 4, 5, 21, 22, 23})


def _perfil(momento: datetime) -> tuple[float, ...]:
    return PERFIL_FIM_DE_SEMANA if momento.weekday() >= 5 else PERFIL_DIA_UTIL


def _chance_de_erro(hora: int) -> float:
    return ERRO_NOTURNO if hora in HORAS_ESCURAS else ERRO_BASE


def gerar(
    dias: int = 28,
    *,
    ate: datetime | None = None,
    semente: int = 20261110,  # data da avaliação, para o resultado ser reprodutível
) -> Iterator[Evento]:
    """Produz os eventos de `dias` de operação, terminando em `ate`.

    Cada tentativa é conduzida pela máquina de estados do gateway: liga
    CONFIRMA, pulsa o clock, desliga, pulsa de novo — exatamente a sequência
    do README. Os eventos saem com o momento sintético no lugar do relógio.
    """
    sorteio = random.Random(semente)
    fim = (ate or datetime.now(timezone.utc)).astimezone(FUSO).replace(minute=0, second=0, microsecond=0)
    maquina = MaquinaDeEstados()

    for dia in range(dias, 0, -1):
        data = fim - timedelta(days=dia)
        perfil = _perfil(data)
        for hora in range(24):
            instante = data.replace(hour=hora)
            for _ in range(_quantas_tentativas(sorteio, perfil[hora])):
                minuto = sorteio.randrange(60)
                momento = instante.replace(minute=minuto, second=sorteio.randrange(60))
                errou = sorteio.random() < _chance_de_erro(hora)
                yield from _tentar(maquina, momento, acerta=not errou, sorteio=sorteio)

            # Depois de bloquear, o administrador destrava em algum momento.
            if maquina.estado.nome == "BLOQUEADO":
                yield from _desbloquear(maquina, instante.replace(minute=59))


def _quantas_tentativas(sorteio: random.Random, media: float) -> int:
    """Amostra de Poisson pela soma de exponenciais: eventos raros e independentes."""
    limite, k, p = pow(2.718281828459045, -media), 0, 1.0
    while True:
        p *= sorteio.random()
        if p <= limite:
            return k
        k += 1


def _tentar(
    maquina: MaquinaDeEstados, momento: datetime, *, acerta: bool, sorteio: random.Random
) -> Iterator[Evento]:
    senha = SENHA if acerta else sorteio.choice([s for s in range(16) if s != SENHA])
    pinos = Pinos().com_senha(senha)

    eventos = maquina.pulsar_clock(replace(pinos, confirma=True))
    eventos += maquina.pulsar_clock(pinos)
    yield from _carimbar(eventos, momento)

    # Acesso liberado: o NE555 devolve a máquina a AGUARDANDO depois de 5,16 s.
    if maquina.estado.nome == "LIBERADO":
        maquina.pulsar_clock(Pinos(timeout=True))


def _desbloquear(maquina: MaquinaDeEstados, momento: datetime) -> Iterator[Evento]:
    yield from _carimbar(maquina.pulsar_clock(Pinos(reset=True)), momento)


def _carimbar(eventos: list[Evento], momento: datetime) -> Iterator[Evento]:
    """Troca o relógio do gateway pelo momento sintético, em UTC."""
    carimbo = momento.astimezone(timezone.utc).isoformat(timespec="milliseconds")
    for ev in eventos:
        yield replace(ev, momento=carimbo)


def enviar(
    eventos: Iterator[Evento],
    cliente,
    *,
    ao_enviar: Callable[[int, Evento, object], None] | None = None,
) -> tuple[int, int]:
    """Entrega os eventos pela API. Devolve (entregues, falhas)."""
    entregues = falhas = 0
    for n, ev in enumerate(eventos, start=1):
        envio = cliente.enviar(ev)
        if envio.ok:
            entregues += 1
        else:
            falhas += 1
        if ao_enviar:
            ao_enviar(n, ev, envio)
    return entregues, falhas
