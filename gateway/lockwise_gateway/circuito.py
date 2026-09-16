"""Gêmeo da netlist: as equações booleanas do circuito, porta a porta.

Este módulo reproduz `circuito/lockwise_completo.circ` sem interpretação.
Cada linha de `combinacional()` corresponde a uma porta do arquivo, e o
comentário à direita indica a coordenada `loc` da porta no Logisim, para que
qualquer divergência entre o modelo e o circuito seja localizável.

O módulo não sabe o que é "senha", "tentativa" ou "acesso". Ele conhece
apenas pinos, portas e flip-flops. A camada semântica está em `estados.py`,
e `tests/test_equivalencia.py` prova que as duas descrevem a mesma máquina.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterator


@dataclass(frozen=True)
class Pinos:
    """Os sete pinos de entrada, exceto CLK, que é a chamada a `borda()`."""

    s3: bool = False
    s2: bool = False
    s1: bool = False
    s0: bool = False
    confirma: bool = False
    timeout: bool = False
    reset: bool = False

    @property
    def senha(self) -> int:
        """Os quatro bits S3..S0 lidos como inteiro (S3 é o mais significativo)."""
        return (self.s3 << 3) | (self.s2 << 2) | (self.s1 << 1) | int(self.s0)

    def com_senha(self, valor: int) -> Pinos:
        if not 0 <= valor <= 0b1111:
            raise ValueError(f"senha deve ter 4 bits, recebido {valor!r}")
        return replace(
            self,
            s3=bool(valor & 0b1000),
            s2=bool(valor & 0b0100),
            s1=bool(valor & 0b0010),
            s0=bool(valor & 0b0001),
        )

    @staticmethod
    def todas() -> Iterator[Pinos]:
        """As 128 combinações possíveis de entrada — usado pela prova exaustiva."""
        for n in range(1 << 7):
            yield Pinos(*(bool(n >> i & 1) for i in range(7)))


@dataclass(frozen=True)
class Registradores:
    """Os quatro flip-flops D: dois da máquina de estados, dois do contador."""

    q1: bool = False  # FF1  @(1000,1620)
    q0: bool = False  # FF0  @(1000,1820)
    c1: bool = False  # FFC1 @(1000,2700)
    c0: bool = False  # FFC0 @(1000,2900)

    @property
    def estado(self) -> int:
        return (self.q1 << 1) | int(self.q0)

    @property
    def contador(self) -> int:
        return (self.c1 << 1) | int(self.c0)

    @staticmethod
    def todos() -> Iterator[Registradores]:
        """As 16 combinações possíveis — usado pela prova exaustiva."""
        for n in range(1 << 4):
            yield Registradores(*(bool(n >> i & 1) for i in range(4)))


@dataclass(frozen=True)
class Sinais:
    """Todos os nós internos e as sete saídas, com os nomes dos túneis do .circ."""

    # comparador
    p1: bool
    p2: bool
    igual: bool  # túnel IGUAL / pino SENHA_OK
    # decodificação de estado
    aguardando: bool
    verificando: bool
    liberado: bool  # túnel LIB / pino TRAVA_ABERTA
    bloqueado: bool
    # lógica de bloqueio
    erro: bool
    e: bool
    # próximo estado
    d1: bool
    d0: bool
    # contador
    clr: bool
    en: bool
    dc1: bool
    dc0: bool

    @property
    def saidas(self) -> dict[str, bool]:
        """Os sete pinos de saída, com os nomes exatos do circuito."""
        return {
            "AGUARDANDO": self.aguardando,
            "VERIFICANDO": self.verificando,
            "TRAVA_ABERTA": self.liberado,
            "BLOQUEADO": self.bloqueado,
            "SENHA_OK": self.igual,
        }


def combinacional(p: Pinos, r: Registradores) -> Sinais:
    """Avalia toda a lógica combinacional para os pinos e registradores atuais."""
    # --- comparador de senha (senha gravada: 1011) ---
    s2n = not p.s2                       # NOT  @(300,620)
    p1 = p.s3 and s2n                    # AND  @(300,720)
    p2 = p.s1 and p.s0                   # AND  @(300,820)
    igual = p1 and p2                    # AND  @(700,770)
    ig_n = not igual                     # NOT  @(1000,770)   túnel IN

    # --- decodificação do estado (Q̄ vem direto do flip-flop) ---
    aguardando = (not r.q1) and (not r.q0)   # AND @(300,940)
    verificando = (not r.q1) and r.q0        # AND @(300,1040)
    liberado = r.q1 and (not r.q0)           # AND @(300,1140)
    bloqueado = r.q1 and r.q0                # AND @(300,1240)

    # --- limiar de bloqueio, antecipado ---
    erro = verificando and ig_n          # AND  @(700,940)    túnel ERR
    ce = r.c0 or erro                    # OR   @(700,1040)
    e = r.c1 and ce                      # AND  @(1050,1040)  E = C1·(C0 + ERRO)

    # --- lógica de próximo estado ---
    tn = not p.timeout                   # NOT  @(300,1340)
    rn = not p.reset                     # NOT  @(300,1410)
    ie = igual or e                      # OR   @(700,1360)
    ne = ig_n and e                      # AND  @(700,1460)
    a1 = (not r.q1) and r.q0 and ie      # AND3 @(300,1650)
    a2 = r.q1 and (not r.q0) and tn      # AND3 @(300,1770)
    a3 = r.q1 and r.q0 and rn            # AND3 @(300,1890)
    b1 = (not r.q1) and (not r.q0) and p.confirma  # AND3 @(300,2010)
    b2 = (not r.q1) and r.q0 and ne      # AND3 @(300,2130)
    d1 = a1 or a2 or a3                  # OR3  @(700,1650)
    d0 = b1 or b2 or a3                  # OR3  @(700,2010)

    # --- contador de tentativas com saturação ---
    ecnt = r.c1 and r.c0                 # AND  @(300,2350)   contador cheio
    ebar = not ecnt                      # NOT  @(300,2430)
    clr = liberado or p.reset            # OR   @(300,2510)
    clrn = not clr                       # NOT  @(700,2510)
    en = erro and ebar                   # AND  @(300,2610)   EN = ERRO·¬(C1·C0)
    x0 = r.c0 != en                      # XOR  @(300,2710)
    g = r.c0 and en                      # AND  @(300,2810)
    x1 = r.c1 != g                       # XOR  @(300,2910)
    dc0 = x0 and clrn                    # AND  @(700,2710)
    dc1 = x1 and clrn                    # AND  @(700,2910)

    return Sinais(
        p1=p1, p2=p2, igual=igual,
        aguardando=aguardando, verificando=verificando,
        liberado=liberado, bloqueado=bloqueado,
        erro=erro, e=e, d1=d1, d0=d0,
        clr=clr, en=en, dc1=dc1, dc0=dc0,
    )


def borda(p: Pinos, r: Registradores) -> Registradores:
    """Borda de subida de CLK: cada flip-flop copia sua entrada D."""
    s = combinacional(p, r)
    return Registradores(q1=s.d1, q0=s.d0, c1=s.dc1, c0=s.dc0)


class GemeoNetlist:
    """Interface com estado, para ser usada lado a lado com a máquina semântica."""

    def __init__(self) -> None:
        self.reg = Registradores()

    def pulsar_clock(self, p: Pinos) -> Registradores:
        self.reg = borda(p, self.reg)
        return self.reg

    def sinais(self, p: Pinos) -> Sinais:
        return combinacional(p, self.reg)

    def saidas(self, p: Pinos) -> dict[str, bool]:
        s = combinacional(p, self.reg).saidas
        s["ERROS_C1"] = self.reg.c1
        s["ERROS_C0"] = self.reg.c0
        return s
