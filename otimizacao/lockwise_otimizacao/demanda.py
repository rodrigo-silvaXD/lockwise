"""De acessos por hora para vigilantes por hora.

A demanda do modelo não é inventada: vem de `GET /acessos/demanda-horaria`,
que agrega o histórico que o gateway gravou a partir do circuito. Este módulo
faz a leitura e a conversão.

A conversão precisa de dois cuidados.

O primeiro é dividir pelo número de dias do período. A rota devolve o total
acumulado: se ela soma 28 dias, as 540 passagens das 18h são 19 por dia, não
540 de uma vez. Dimensionar a escala pelo acumulado daria um resultado
absurdo.

O segundo é a capacidade. Cada acesso consome atenção do vigilante — conferir
quem entra, registrar, acompanhar até o elevador. Estimando quinze minutos por
acesso, um vigilante dá conta de quatro por hora. É o K da conversão. Além
disso há uma presença mínima: a portaria não fica vazia nem na madrugada sem
movimento.
"""

from __future__ import annotations

import json
import math
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

# Acessos que um vigilante acompanha por hora: 60 min / 15 min por acesso.
CAPACIDADE_POR_VIGILANTE = 4
MINUTOS_POR_ACESSO = 15

# Ninguém de plantão é risco, não economia.
PRESENCA_MINIMA = 1


@dataclass(frozen=True)
class Demanda:
    """As 24 faixas horárias, em acessos e em vigilantes necessários."""

    acessos: tuple[int, ...]      # acessos por hora, acumulados no período
    energia_mj: tuple[int, ...]   # energia por hora (docs/fisica.md §6)
    fuso: str
    origem: str                   # de onde vieram os dados, para o relatório
    dias: int = 1                 # dias que o período abrange
    capacidade: int = CAPACIDADE_POR_VIGILANTE
    presenca_minima: int = PRESENCA_MINIMA

    def __post_init__(self) -> None:
        if len(self.acessos) != 24 or len(self.energia_mj) != 24:
            raise ValueError("a demanda precisa ter exatamente 24 faixas horárias")
        if self.capacidade < 1:
            raise ValueError("a capacidade por vigilante precisa ser pelo menos 1")
        if self.dias < 1:
            raise ValueError("o período precisa ter pelo menos um dia")

    @property
    def media_diaria(self) -> tuple[float, ...]:
        """Acessos por hora num dia típico."""
        return tuple(a / self.dias for a in self.acessos)

    @property
    def vigilantes(self) -> tuple[int, ...]:
        """d_h da formulação: vigilantes exigidos em cada hora de um dia típico."""
        return tuple(
            max(self.presenca_minima, math.ceil(m / self.capacidade)) for m in self.media_diaria
        )

    @property
    def total_acessos(self) -> int:
        return sum(self.acessos)

    @property
    def total_energia_mj(self) -> int:
        return sum(self.energia_mj)

    @property
    def hora_de_pico(self) -> int:
        return max(range(24), key=lambda h: self.acessos[h])


def da_api(
    base_url: str,
    *,
    de: str | None = None,
    ate: str | None = None,
    timeout_s: float = 60.0,
    abrir: Callable = urllib.request.urlopen,
    **kwargs,
) -> Demanda:
    """Lê a demanda da API. É o caminho normal: o modelo consome o banco real."""
    url = base_url.rstrip("/") + "/acessos/demanda-horaria"
    # urlencode e obrigatorio aqui: o "+00:00" do fuso vira espaco numa query
    # string se for colado cru, e a API devolve 422.
    filtros = urllib.parse.urlencode({k: v for k, v in (("de", de), ("ate", ate)) if v})
    if filtros:
        url += "?" + filtros

    with abrir(urllib.request.Request(url, method="GET"), timeout=timeout_s) as resp:
        corpo = json.loads(resp.read().decode("utf-8"))

    return _do_json(corpo, origem=url, **kwargs)


def do_arquivo(caminho: Path, **kwargs) -> Demanda:
    """Lê de um JSON salvo no formato da rota. Serve para rodar sem rede."""
    corpo = json.loads(caminho.read_text(encoding="utf-8"))
    return _do_json(corpo, origem=str(caminho), **kwargs)


def _do_json(corpo: dict, *, origem: str, **kwargs) -> Demanda:
    faixas = {f["hora"]: f for f in corpo["faixas"]}
    if set(faixas) != set(range(24)):
        raise ValueError(f"esperava as 24 faixas horárias, recebi {sorted(faixas)}")
    return Demanda(
        acessos=tuple(faixas[h]["acessos"] for h in range(24)),
        energia_mj=tuple(faixas[h]["energia_mj"] for h in range(24)),
        fuso=corpo.get("fuso", "?"),
        origem=origem,
        **kwargs,
    )
