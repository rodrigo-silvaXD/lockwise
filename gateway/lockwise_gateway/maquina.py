"""A máquina de estados semântica: estado + contador de tentativas + eventos.

`MaquinaDeEstados.pulsar_clock()` é o equivalente de uma borda de subida de
CLK no circuito. Ela avança o estado (padrão State), avança o contador com
as mesmas regras do hardware e devolve os eventos que a transição gerou.

Eventos nascem apenas em transições — nunca por leitura periódica do estado.
"""

from __future__ import annotations

from .circuito import Pinos, Registradores
from .estados import AGUARDANDO, BLOQUEADO, LIBERADO, VERIFICANDO, Estado
from .eventos import LIMITE_TENTATIVAS, SENHA, Alerta, Evento, EventoAcesso, TipoAlerta


class Contador:
    """Contador de tentativas de 2 bits com saturação, como os flip-flops FFC1/FFC0.

    Regras extraídas do circuito:
      CLR = LIBERADO + RESET       zera na borda em que qualquer dos dois vale 1
      EN  = ERRO · ¬(C1·C0)        incrementa em erro, mas para em 11
    """

    MAXIMO = LIMITE_TENTATIVAS  # 0b11

    def __init__(self) -> None:
        self.valor = 0

    def avancar(self, erro: bool, limpar: bool) -> None:
        if limpar:
            self.valor = 0
        elif erro and self.valor < self.MAXIMO:
            self.valor += 1

    @property
    def bits(self) -> tuple[bool, bool]:
        return bool(self.valor & 0b10), bool(self.valor & 0b01)


class MaquinaDeEstados:
    def __init__(self) -> None:
        self.estado: Estado = AGUARDANDO
        self.contador = Contador()

    # ------------------------------------------------------------------ clock

    def pulsar_clock(self, pinos: Pinos) -> list[Evento]:
        """Uma borda de subida de CLK. Devolve os eventos gerados pela transição."""
        anterior = self.estado
        tentativas = self.contador.valor

        erro = anterior.erro(pinos)
        limpar = anterior.libera_trava or pinos.reset
        novo = anterior.proximo(pinos, tentativas)

        # Estado e contador são flip-flops que amostram na mesma borda: ambos
        # avançam a partir dos valores *anteriores*, por isso `tentativas` foi
        # lido antes e `avancar` só é chamado depois de `proximo`.
        self.contador.avancar(erro, limpar)
        self.estado = novo

        return self._eventos(anterior, novo, tentativas)

    @staticmethod
    def _eventos(anterior: Estado, novo: Estado, tentativas: int) -> list[Evento]:
        if anterior is VERIFICANDO and novo is LIBERADO:
            return [EventoAcesso.liberado(tentativas_anteriores=tentativas)]
        if anterior is VERIFICANDO and novo is AGUARDANDO:
            return [EventoAcesso.negado(tentativa=tentativas + 1)]
        if anterior is VERIFICANDO and novo is BLOQUEADO:
            return [EventoAcesso.bloqueado(), Alerta(TipoAlerta.BLOQUEIO)]
        if anterior is BLOQUEADO and novo is AGUARDANDO:
            return [Alerta(TipoAlerta.DESBLOQUEIO_ADMIN)]
        return []

    # --------------------------------------------------------------- leitura

    def registradores(self) -> Registradores:
        """Os quatro flip-flops como o circuito os veria. Base do teste de equivalência."""
        q1, q0 = self.estado.codigo
        c1, c0 = self.contador.bits
        return Registradores(q1=q1, q0=q0, c1=c1, c0=c0)

    def saidas(self, pinos: Pinos) -> dict[str, bool]:
        """Os sete pinos de saída do circuito, com os nomes exatos."""
        return {
            "AGUARDANDO": self.estado is AGUARDANDO,
            "VERIFICANDO": self.estado is VERIFICANDO,
            "TRAVA_ABERTA": self.estado is LIBERADO,
            "BLOQUEADO": self.estado is BLOQUEADO,
            "SENHA_OK": pinos.senha == SENHA,
            "ERROS_C1": self.contador.bits[0],
            "ERROS_C0": self.contador.bits[1],
        }

    def carregar(self, reg: Registradores) -> None:
        """Força um estado arbitrário. Usado apenas pela prova exaustiva."""
        from .estados import POR_CODIGO

        self.estado = POR_CODIGO[(reg.q1, reg.q0)]
        self.contador.valor = reg.contador
