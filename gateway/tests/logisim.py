"""Leitor mínimo de arquivos .circ do Logisim-evolution, para o teste de netlist.

Lê o XML, reconstrói as conexões elétricas (fios, túneis, pinos, portas dos
componentes) e devolve um simulador genérico do grafo de portas. Não sabe
nada sobre o LOCKWISE: só conhece AND, OR, XOR, NOT, pinos e flip-flops D.

Geometria dos componentes (Logisim-evolution 4.1.0, `facing` leste):
  porta de N entradas, size=50 : saída em `loc`, entradas em x−50
  NOT, size=30                 : saída em `loc`, entrada em x−30
  D Flip-Flop                  : D (−10,+10)  CLK (−10,+50)  Q (+50,+10)  Q̄ (+50,+50)
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

Ponto = tuple[int, int]

OPERADORES = {
    "AND Gate": all,
    "OR Gate": any,
    "XOR Gate": lambda vs: sum(vs) % 2 == 1,
    "NOT Gate": lambda vs: not vs[0],
}


@dataclass
class Porta:
    tipo: str
    saida: int  # id do nó
    entradas: list[int]
    loc: Ponto


@dataclass
class FlipFlop:
    rotulo: str
    d: int
    q: int
    q_barra: int


@dataclass
class Netlist:
    portas: list[Porta]
    flipflops: dict[str, FlipFlop]
    pinos_entrada: dict[str, int]
    pinos_saida: dict[str, int]
    nomes: dict[int, set[str]] = field(default_factory=dict)

    # ---------------------------------------------------------- simulação

    def avaliar(self, entradas: dict[str, bool], estado_ff: dict[str, bool]) -> dict[int, bool]:
        """Propaga valores pelo grafo combinacional até o ponto fixo.

        `entradas`: valor de cada pino de entrada, por rótulo.
        `estado_ff`: valor Q de cada flip-flop, por rótulo.
        Devolve o valor de cada nó. Levanta se alguma porta ficar sem valor
        (o que indicaria conexão faltando ou laço combinacional).
        """
        valores: dict[int, bool] = {}
        for rotulo, no in self.pinos_entrada.items():
            if rotulo in entradas:
                valores[no] = entradas[rotulo]
        for rotulo, ff in self.flipflops.items():
            valores[ff.q] = estado_ff[rotulo]
            valores[ff.q_barra] = not estado_ff[rotulo]

        pendentes = list(self.portas)
        while pendentes:
            restantes = []
            for p in pendentes:
                if all(e in valores for e in p.entradas):
                    valores[p.saida] = OPERADORES[p.tipo]([valores[e] for e in p.entradas])
                else:
                    restantes.append(p)
            if len(restantes) == len(pendentes):
                faltando = [(p.tipo, p.loc) for p in restantes]
                raise RuntimeError(f"portas sem valor de entrada (conexão faltando?): {faltando}")
            pendentes = restantes
        return valores

    def proximo_estado(self, entradas: dict[str, bool], estado_ff: dict[str, bool]) -> dict[str, bool]:
        valores = self.avaliar(entradas, estado_ff)
        return {rotulo: valores[ff.d] for rotulo, ff in self.flipflops.items()}

    def saidas(self, entradas: dict[str, bool], estado_ff: dict[str, bool]) -> dict[str, bool]:
        valores = self.avaliar(entradas, estado_ff)
        return {rotulo: valores[no] for rotulo, no in self.pinos_saida.items()}


# ------------------------------------------------------------------ leitura


class _UniaoBusca:
    def __init__(self) -> None:
        self._pai: dict[Ponto, Ponto] = {}

    def raiz(self, p: Ponto) -> Ponto:
        self._pai.setdefault(p, p)
        while self._pai[p] != p:
            self._pai[p] = self._pai[self._pai[p]]
            p = self._pai[p]
        return p

    def unir(self, a: Ponto, b: Ponto) -> None:
        self._pai[self.raiz(a)] = self.raiz(b)

    def pontos(self) -> list[Ponto]:
        return list(self._pai)


def _ponto(texto: str) -> Ponto:
    x, y = texto.strip("()").split(",")
    return int(x), int(y)


def carregar(caminho: Path, circuito: str | None = None) -> Netlist:
    raiz_xml = ET.parse(caminho).getroot()
    circuitos = [c for c in raiz_xml if c.tag == "circuit"]
    if circuito:
        circuitos = [c for c in circuitos if c.get("name") == circuito]
    if not circuitos:
        raise ValueError(f"circuito {circuito!r} não encontrado em {caminho}")
    circ = circuitos[0]

    comps: list[tuple[str, Ponto, dict[str, str]]] = []
    fios: list[tuple[Ponto, Ponto]] = []
    for el in circ:
        if el.tag == "comp":
            attrs = {a.get("name"): a.get("val") for a in el}
            comps.append((el.get("name"), _ponto(el.get("loc")), attrs))
        elif el.tag == "wire":
            fios.append((_ponto(el.get("from")), _ponto(el.get("to"))))

    # 1. fios: cada ponto da grade ao longo do fio pertence ao mesmo nó
    ub = _UniaoBusca()
    for (x1, y1), (x2, y2) in fios:
        if x1 == x2:
            pts = [(x1, y) for y in range(min(y1, y2), max(y1, y2) + 1, 10)]
        else:
            pts = [(x, y1) for x in range(min(x1, x2), max(x1, x2) + 1, 10)]
        for p in pts:
            ub.unir(p, (x1, y1))

    # 2. túneis com o mesmo rótulo são o mesmo nó
    por_rotulo: dict[str, list[Ponto]] = defaultdict(list)
    for nome, loc, attrs in comps:
        if nome == "Tunnel":
            por_rotulo[attrs["label"]].append(loc)
    for pts in por_rotulo.values():
        for p in pts[1:]:
            ub.unir(p, pts[0])

    def no(p: Ponto) -> int:
        return hash(ub.raiz(p))

    ocupados = set(ub.pontos())

    def entradas_de(loc: Ponto, dx: int, dy_max: int) -> list[int]:
        x, y = loc
        pts = sorted(p for p in ocupados if p[0] == x + dx and abs(p[1] - y) <= dy_max)
        return [no(p) for p in pts]

    portas: list[Porta] = []
    flipflops: dict[str, FlipFlop] = {}
    pinos_entrada: dict[str, int] = {}
    pinos_saida: dict[str, int] = {}
    nomes: dict[int, set[str]] = defaultdict(set)

    for nome, loc, attrs in comps:
        if nome in ("AND Gate", "OR Gate", "XOR Gate"):
            n = int(attrs.get("inputs", 2))
            ent = entradas_de(loc, -50, 30)
            if len(ent) != n:
                raise ValueError(f"{nome} em {loc}: esperava {n} entradas conectadas, achei {len(ent)}")
            portas.append(Porta(nome, no(loc), ent, loc))
        elif nome == "NOT Gate":
            ent = entradas_de(loc, -30, 5)
            if len(ent) != 1:
                raise ValueError(f"NOT em {loc}: entrada não conectada")
            portas.append(Porta(nome, no(loc), ent, loc))
        elif nome == "D Flip-Flop":
            x, y = loc
            flipflops[attrs["label"]] = FlipFlop(
                rotulo=attrs["label"],
                d=no((x - 10, y + 10)),
                q=no((x + 50, y + 10)),
                q_barra=no((x + 50, y + 50)),
            )
        elif nome == "Pin":
            rotulo = attrs["label"]
            (pinos_saida if attrs.get("type") == "output" else pinos_entrada)[rotulo] = no(loc)
            nomes[no(loc)].add(rotulo)
        elif nome == "Tunnel":
            nomes[no(loc)].add(attrs["label"])

    return Netlist(portas, flipflops, pinos_entrada, pinos_saida, dict(nomes))
