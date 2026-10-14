"""O modelo de cobertura: quantos vigilantes em cada turno, ao menor custo.

Formulação (programação linear inteira):

    Conjuntos
        H = {0, …, 23}          horas do dia
        T = {0, …, 5}           turnos de 8 h começando a cada 4 h

    Parâmetros
        a(t,h) ∈ {0,1}          1 se o turno t cobre a hora h
        d_h ∈ ℤ⁺                vigilantes exigidos na hora h
        c_t ∈ ℝ⁺                custo de um vigilante no turno t
        N_max ∈ ℤ⁺              vigilantes disponíveis na equipe

    Variável de decisão
        x_t ∈ ℤ⁺                vigilantes escalados no turno t

    minimizar    Σ_t c_t · x_t

    sujeito a    Σ_t a(t,h) · x_t ≥ d_h    ∀h ∈ H      (cobertura)
                 Σ_t x_t ≤ N_max                        (equipe disponível)
                 x_t ≥ 0, inteiro          ∀t ∈ T

Resolvido com CBC (COIN-OR Branch and Cut), o solver de código aberto que
acompanha o PuLP.
"""

from __future__ import annotations

from dataclasses import dataclass

import warnings

import pulp

from .demanda import Demanda
from .turnos import TURNOS, Turno, cobertura, turnos_que_cobrem

# Vigilantes que a equipe tem. Alto o bastante para não ser o gargalo no caso
# normal, mas presente na formulação porque é uma restrição real.
EQUIPE_MAXIMA = 12


class SemSolucao(Exception):
    """A demanda não cabe na equipe disponível."""


def _solver():
    """O CBC, pelo caminho que existir nesta instalação.

    O nome do solver mudou entre versões do PuLP: a 4 removeu `PULP_CBC_CMD`
    em favor de `COIN_CMD`. O `pyproject.toml` fixa a faixa que sabemos boa,
    e esta função procura os dois nomes para o módulo não quebrar se alguém
    instalar fora dela.

    Cada candidato é consultado com `getattr`, nunca por acesso direto: um
    atributo que deixou de existir levanta `AttributeError` em vez de ser
    pulado, e foi exatamente assim que a versão anterior desta função quebrou
    o pipeline quando o PuLP 4 saiu.
    """
    for nome in ("COIN_CMD", "PULP_CBC_CMD"):
        fabrica = getattr(pulp, nome, None)
        if fabrica is None:
            continue
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                candidato = fabrica(msg=False)
            if candidato.available():
                return candidato
        except Exception:  # noqa: BLE001 — binário ausente ou incompatível
            continue

    raise SemSolucao(
        "nenhum solver CBC disponível nesta instalação do PuLP "
        f"({getattr(pulp, '__version__', 'versão desconhecida')}). "
        "Instale a faixa suportada: pip install -e \".[dev]\" na pasta otimizacao."
    )


@dataclass(frozen=True)
class Escala:
    """Uma escala: quantos vigilantes em cada turno, e o que ela custa."""

    por_turno: tuple[int, ...]
    demanda: Demanda
    rotulo: str

    @property
    def total_vigilantes(self) -> int:
        return sum(self.por_turno)

    @property
    def custo(self) -> float:
        return round(sum(t.custo * x for t, x in zip(TURNOS, self.por_turno)), 2)

    def presentes(self, hora: int) -> int:
        """Vigilantes de plantão nesta hora, somando os turnos que a cobrem."""
        return sum(x for t, x in zip(TURNOS, self.por_turno) if t.cobre(hora))

    @property
    def folga(self) -> tuple[int, ...]:
        """Por hora, quantos vigilantes além do exigido. Zero significa restrição justa."""
        return tuple(self.presentes(h) - self.demanda.vigilantes[h] for h in range(24))

    def cobre_tudo(self) -> bool:
        return all(f >= 0 for f in self.folga)

    def __str__(self) -> str:
        return " · ".join(f"{t.rotulo}: {x}" for t, x in zip(TURNOS, self.por_turno))


def otimizar(demanda: Demanda, equipe_maxima: int = EQUIPE_MAXIMA) -> Escala:
    """Resolve o modelo e devolve a escala de menor custo."""
    problema = pulp.LpProblem("escala_de_vigilancia_lockwise", pulp.LpMinimize)

    # add_variable e a forma que o PuLP 4.0 exige; LpVariable direto esta
    # deprecado. Onde o metodo ainda nao existe, caimos no construtor antigo.
    def variavel(nome: str):
        if hasattr(problema, "add_variable"):
            return problema.add_variable(nome, lowBound=0, cat=pulp.LpInteger)
        return pulp.LpVariable(nome, lowBound=0, cat=pulp.LpInteger)

    x = {t.indice: variavel(f"x_{t.indice}") for t in TURNOS}

    # Objetivo: custo total da folha do dia.
    problema += pulp.lpSum(t.custo * x[t.indice] for t in TURNOS), "custo_total"

    # Cobertura: cada hora precisa dos seus d_h vigilantes.
    for h in range(24):
        problema += (
            pulp.lpSum(cobertura(t, h) * x[t.indice] for t in TURNOS) >= demanda.vigilantes[h],
            f"cobertura_hora_{h:02d}",
        )

    # Equipe disponível.
    problema += pulp.lpSum(x.values()) <= equipe_maxima, "equipe_disponivel"

    problema.solve(_solver())

    situacao = pulp.LpStatus[problema.status]
    if situacao != "Optimal":
        raise SemSolucao(
            f"o solver terminou em '{situacao}'. Com {equipe_maxima} vigilantes não há "
            f"escala que cubra a demanda (pico de {max(demanda.vigilantes)} às "
            f"{demanda.vigilantes.index(max(demanda.vigilantes))}h). Aumente a equipe "
            f"ou a capacidade por vigilante."
        )

    return Escala(
        por_turno=tuple(int(round(x[t.indice].value())) for t in TURNOS),
        demanda=demanda,
        rotulo="otimizada",
    )


def escala_ingenua(demanda: Demanda) -> Escala:
    """A escala que sai sem modelo nenhum: o mesmo número de gente em todo turno.

    É o que uma planilha produz. Como cada hora é coberta por dois turnos,
    basta n tal que 2n ≥ pico. O resultado cobre a demanda, mas paga gente
    sobrando na madrugada para dar conta do pico da tarde — e é contra isso
    que a otimização é comparada.
    """
    pico = max(demanda.vigilantes)
    cobertura_por_hora = len(turnos_que_cobrem(0))  # 2, com turnos de 8 h a cada 4 h
    n = -(-pico // cobertura_por_hora)  # divisão para cima
    return Escala(por_turno=tuple(n for _ in TURNOS), demanda=demanda, rotulo="ingênua")


@dataclass(frozen=True)
class Comparacao:
    otimizada: Escala
    ingenua: Escala

    @property
    def economia(self) -> float:
        return round(self.ingenua.custo - self.otimizada.custo, 2)

    @property
    def economia_percentual(self) -> float:
        if self.ingenua.custo == 0:
            return 0.0
        return round(100 * self.economia / self.ingenua.custo, 1)

    @property
    def vigilantes_a_menos(self) -> int:
        return self.ingenua.total_vigilantes - self.otimizada.total_vigilantes

    @property
    def economia_mensal(self) -> float:
        return round(self.economia * 30, 2)


def comparar(demanda: Demanda, equipe_maxima: int = EQUIPE_MAXIMA) -> Comparacao:
    return Comparacao(otimizada=otimizar(demanda, equipe_maxima), ingenua=escala_ingenua(demanda))
