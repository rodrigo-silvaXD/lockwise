"""Os turnos de vigilância e o custo de cada um.

A escolha que faz este problema valer a pena: turnos de 8 h começando a cada
4 h. Seis turnos, e cada hora do dia coberta por exatamente dois deles.

Se os turnos fossem de 4 h sem sobreposição, cada hora seria coberta por um
único turno e a resposta ótima seria trivial — bastaria olhar a maior demanda
dentro de cada bloco. É a sobreposição que cria a escolha: colocar um
vigilante no turno 08–16 ajuda tanto a manhã quanto a tarde, e decidir onde
concentrar pessoal passa a ser um problema de verdade.

Turno de 8 h também é o que um vigilante faz na prática.
"""

from __future__ import annotations

from dataclasses import dataclass

DURACAO_H = 8
INICIOS = (0, 4, 8, 12, 16, 20)

# Horas consideradas noturnas para o adicional. A CLT conta 22h–05h; usamos
# 22h–06h porque o turno começa de quatro em quatro horas.
HORAS_NOTURNAS = frozenset({22, 23, 0, 1, 2, 3, 4, 5})

# Custo de um vigilante por turno de 8 h, em reais. Ordem de grandeza de um
# posto de vigilância terceirizado; o valor exato não muda a conclusão, porque
# a comparação com a escala ingênua é proporcional.
CUSTO_BASE = 220.0

# Adicional noturno sobre as horas noturnas do turno.
ADICIONAL_NOTURNO = 0.20


@dataclass(frozen=True)
class Turno:
    indice: int
    inicio: int

    @property
    def horas(self) -> tuple[int, ...]:
        """As 8 horas que este turno cobre, com a virada da meia-noite."""
        return tuple((self.inicio + d) % 24 for d in range(DURACAO_H))

    @property
    def horas_noturnas(self) -> int:
        return sum(1 for h in self.horas if h in HORAS_NOTURNAS)

    @property
    def custo(self) -> float:
        """Custo de um vigilante neste turno, com adicional proporcional às horas noturnas.

        Um turno inteiramente noturno custa 20% a mais; um turno com metade
        das horas à noite custa 10% a mais. Proporcional, não tudo ou nada.
        """
        proporcao_noturna = self.horas_noturnas / DURACAO_H
        return round(CUSTO_BASE * (1 + ADICIONAL_NOTURNO * proporcao_noturna), 2)

    def cobre(self, hora: int) -> bool:
        return hora in self.horas

    @property
    def rotulo(self) -> str:
        fim = (self.inicio + DURACAO_H) % 24
        return f"{self.inicio:02d}h–{fim:02d}h"

    def __str__(self) -> str:
        return f"T{self.indice} {self.rotulo}"


TURNOS: tuple[Turno, ...] = tuple(Turno(i, inicio) for i, inicio in enumerate(INICIOS))


def cobertura(turno: Turno, hora: int) -> int:
    """a(t,h) da formulação: 1 se o turno cobre a hora, 0 caso contrário."""
    return 1 if turno.cobre(hora) else 0


def turnos_que_cobrem(hora: int) -> tuple[Turno, ...]:
    return tuple(t for t in TURNOS if t.cobre(hora))
