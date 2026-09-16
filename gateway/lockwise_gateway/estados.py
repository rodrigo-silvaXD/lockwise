"""Padrão State: a máquina de estados do circuito, um estado por classe.

O hardware *é* uma máquina de estados finitos — dois flip-flops, quatro
estados. O padrão State é a tradução direta disso para objetos: cada classe
sabe seu código (Q1, Q0), sabe para onde ir na próxima borda de clock e sabe
o que sinaliza enquanto está ativa. Não há `if estado == ...` espalhado pelo
código; a decisão de transição pertence ao estado.

A equivalência entre estas classes e as equações de `circuito.py` é provada
exaustivamente em `tests/test_equivalencia.py`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from .circuito import Pinos
from .eventos import LIMITE_TENTATIVAS, SENHA


class Estado(ABC):
    """Um dos quatro estados da máquina. Instâncias são singletons de módulo."""

    nome: ClassVar[str]
    codigo: ClassVar[tuple[bool, bool]]  # (Q1, Q0), como nos flip-flops

    # Sinal LIB do circuito: verdadeiro apenas em LIBERADO. Alimenta a trava
    # e é um dos dois termos de CLR, que zera o contador de tentativas.
    libera_trava: ClassVar[bool] = False

    @abstractmethod
    def proximo(self, pinos: Pinos, tentativas: int) -> Estado:
        """O estado após a próxima borda de subida de CLK."""

    def erro(self, pinos: Pinos) -> bool:
        """Sinal ERRO = VERIFICANDO · ¬IGUAL. Só o estado VERIFICANDO o produz."""
        return False

    def __repr__(self) -> str:
        return self.nome


class Aguardando(Estado):
    """00 — repouso. Sai quando o operador confirma uma senha."""

    nome = "AGUARDANDO"
    codigo = (False, False)

    def proximo(self, pinos: Pinos, tentativas: int) -> Estado:
        return VERIFICANDO if pinos.confirma else self


class Verificando(Estado):
    """01 — a senha nos pinos é comparada. Três saídas possíveis."""

    nome = "VERIFICANDO"
    codigo = (False, True)

    def erro(self, pinos: Pinos) -> bool:
        return pinos.senha != SENHA

    def proximo(self, pinos: Pinos, tentativas: int) -> Estado:
        if pinos.senha == SENHA:
            return LIBERADO
        # Limiar antecipado: E = C1·(C0 + ERRO). Com ERRO = 1, E vale C1, ou
        # seja, "já houve duas tentativas". A terceira bloqueia nesta mesma
        # borda, sem esperar o contador chegar a 11.
        if tentativas >= LIMITE_TENTATIVAS - 1:
            return BLOQUEADO
        return AGUARDANDO


class Liberado(Estado):
    """10 — trava acionada. Permanece até o temporizador sinalizar TIMEOUT."""

    nome = "LIBERADO"
    codigo = (True, False)
    libera_trava = True

    def proximo(self, pinos: Pinos, tentativas: int) -> Estado:
        return AGUARDANDO if pinos.timeout else self


class Bloqueado(Estado):
    """11 — sistema travado. Só RESET administrativo sai daqui."""

    nome = "BLOQUEADO"
    codigo = (True, True)

    def proximo(self, pinos: Pinos, tentativas: int) -> Estado:
        return AGUARDANDO if pinos.reset else self


AGUARDANDO = Aguardando()
VERIFICANDO = Verificando()
LIBERADO = Liberado()
BLOQUEADO = Bloqueado()

ESTADOS: tuple[Estado, ...] = (AGUARDANDO, VERIFICANDO, LIBERADO, BLOQUEADO)
POR_CODIGO: dict[tuple[bool, bool], Estado] = {e.codigo: e for e in ESTADOS}
