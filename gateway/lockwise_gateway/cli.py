"""Interface de linha de comando: o painel de pinos do circuito, em texto.

Cada comando corresponde a um gesto no Logisim com a Poke Tool. `clk` é a
borda de subida. Os macros (`tentar`, `fechar`, `desbloquear`) executam as
sequências do README, para a demo andar no ritmo da conversa.
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
from dataclasses import replace
from pathlib import Path
from typing import Callable

from . import __version__
from .circuito import Pinos
from .eventos import TEMPO_TRAVA_ABERTA_S, Alerta, Evento, EventoAcesso
from .fontes import FonteDeComandos, Roteiro, Teclado
from .maquina import MaquinaDeEstados
from .transporte import Cliente, ClienteAPI, ClienteEco

AJUDA = """\
comandos (cada um e um gesto na Poke Tool do Logisim):
  senha 1011          define S3 S2 S1 S0
  s3|s2|s1|s0 on|off  um bit de cada vez
  confirma [on|off]   pino CONFIRMA (sem argumento: alterna)
  timeout  [on|off]   pino TIMEOUT
  reset    [on|off]   pino RESET
  clk                 borda de subida do clock

macros (as sequencias do README):
  tentar 1011         senha + confirma on + clk + confirma off + clk
  fechar              timeout on + clk + timeout off   (LIBERADO -> AGUARDANDO)
  desbloquear         reset on + clk + reset off       (BLOQUEADO -> AGUARDANDO)

outros:
  estado              pinos, estado, contador e saidas
  fila                reenvia a fila offline
  acordar             chama /health ate a API responder (plano gratuito hiberna)
  ajuda | sair"""


class ErroDeComando(Exception):
    pass


class Interprete:
    def __init__(
        self,
        cliente: Cliente,
        *,
        saida: Callable[[str], None] = print,
        timeout_fisico: bool = False,
        agendar: Callable[[float, Callable[[], None]], None] | None = None,
    ) -> None:
        self.maquina = MaquinaDeEstados()
        self.pinos = Pinos()
        self.cliente = cliente
        self.eventos: list[Evento] = []
        self._saida = saida
        self._timeout_fisico = timeout_fisico
        self._agendar = agendar or _agendar_com_thread
        self._trava = threading.RLock()
        self.encerrado = False

    # ----------------------------------------------------------- execução

    def executar(self, linha: str) -> None:
        with self._trava:
            partes = linha.strip().split()
            if not partes:
                return
            cmd, args = partes[0].lower(), partes[1:]
            metodo = getattr(self, f"_cmd_{cmd}", None)
            if metodo is None:
                raise ErroDeComando(f"comando desconhecido: {cmd!r} (digite 'ajuda')")
            metodo(*args)

    def rodar(self, fonte: FonteDeComandos) -> None:
        for linha in fonte.comandos():
            try:
                self.executar(linha)
            except ErroDeComando as e:
                self._saida(f"   ! {e}")
            except (TypeError, ValueError) as e:
                self._saida(f"   ! argumento invalido: {e}")
            if self.encerrado:
                return

    # -------------------------------------------------------------- pinos

    def _cmd_senha(self, bits: str) -> None:
        if len(bits) != 4 or set(bits) - {"0", "1"}:
            raise ErroDeComando("senha deve ter exatamente 4 bits, ex.: senha 1011")
        self.pinos = self.pinos.com_senha(int(bits, 2))
        self._mostrar_pinos()

    def _bit(self, nome: str, valor: str | None) -> None:
        atual = getattr(self.pinos, nome)
        novo = (not atual) if valor is None else _ligado(valor)
        self.pinos = replace(self.pinos, **{nome: novo})
        self._mostrar_pinos()

    def _cmd_s3(self, valor: str) -> None: self._bit("s3", valor)
    def _cmd_s2(self, valor: str) -> None: self._bit("s2", valor)
    def _cmd_s1(self, valor: str) -> None: self._bit("s1", valor)
    def _cmd_s0(self, valor: str) -> None: self._bit("s0", valor)
    def _cmd_confirma(self, valor: str | None = None) -> None: self._bit("confirma", valor)
    def _cmd_timeout(self, valor: str | None = None) -> None: self._bit("timeout", valor)
    def _cmd_reset(self, valor: str | None = None) -> None: self._bit("reset", valor)

    # -------------------------------------------------------------- clock

    def _cmd_clk(self) -> None:
        anterior = self.maquina.estado
        eventos = self.maquina.pulsar_clock(self.pinos)
        novo = self.maquina.estado

        seta = f"{anterior.nome} -> {novo.nome}" if anterior is not novo else f"{novo.nome} (permanece)"
        self._saida(f"CLK  {seta:32} tentativas={self.maquina.contador.valor}")

        for ev in eventos:
            self.eventos.append(ev)
            self._saida(f"   evento {_descrever(ev)}")
            envio = self.cliente.enviar(ev)
            if envio.situacao == "simulado":
                continue
            codigo = f" HTTP {envio.codigo_http}" if envio.codigo_http else ""
            detalhe = f" ({envio.detalhe})" if envio.detalhe else ""
            self._saida(f"   POST {envio.rota} -> {envio.situacao}{codigo}{detalhe}")

        if self._timeout_fisico and novo.libera_trava and anterior is not novo:
            self._saida(f"   trava aberta: TIMEOUT automatico em {TEMPO_TRAVA_ABERTA_S} s (NE555)")
            self._agendar(TEMPO_TRAVA_ABERTA_S, lambda: self.executar("fechar"))

    # ------------------------------------------------------------- macros

    def _cmd_tentar(self, bits: str) -> None:
        self._cmd_senha(bits)
        self._cmd_confirma("on")
        self._cmd_clk()
        self._cmd_confirma("off")
        self._cmd_clk()

    def _cmd_fechar(self) -> None:
        self._cmd_timeout("on")
        self._cmd_clk()
        self._cmd_timeout("off")

    def _cmd_desbloquear(self) -> None:
        self._cmd_reset("on")
        self._cmd_clk()
        self._cmd_reset("off")

    # ------------------------------------------------------------- outros

    def _cmd_estado(self) -> None:
        self._mostrar_pinos()
        saidas = self.maquina.saidas(self.pinos)
        acesas = " ".join(n for n, v in saidas.items() if v)
        self._saida(f"   estado={self.maquina.estado.nome} contador={self.maquina.contador.valor:02b}")
        self._saida(f"   saidas acesas: {acesas or '(nenhuma)'}")

    def _cmd_fila(self) -> None:
        enviados, restantes = self.cliente.reenviar_fila()
        self._saida(f"   fila: {enviados} reenviado(s), {restantes} pendente(s)")

    def _cmd_acordar(self, espera: str = "60") -> None:
        self._saida(f"   acordando a API (ate {espera}s)...")
        if self.cliente.acordar(float(espera)):
            self._saida("   API respondeu; pode comecar a demo")
        else:
            self._saida("   ! a API nao respondeu a tempo; os eventos irao para a fila")

    def _cmd_ajuda(self) -> None:
        self._saida(AJUDA)

    def _cmd_sair(self) -> None:
        self.encerrado = True

    def _mostrar_pinos(self) -> None:
        p = self.pinos
        self._saida(
            f"   pinos: S={p.senha:04b} CONFIRMA={int(p.confirma)} "
            f"TIMEOUT={int(p.timeout)} RESET={int(p.reset)}"
        )


# --------------------------------------------------------------- auxiliares


def _ligado(valor: str) -> bool:
    v = valor.lower()
    if v in ("on", "1", "true", "liga"):
        return True
    if v in ("off", "0", "false", "desliga"):
        return False
    raise ErroDeComando(f"esperado on|off, recebido {valor!r}")


def _descrever(ev: Evento) -> str:
    if isinstance(ev, EventoAcesso):
        return f"{ev.resultado.value} tentativa={ev.tentativa} energia_mj={ev.energia_mj}"
    if isinstance(ev, Alerta):
        return f"ALERTA {ev.tipo.value}"
    return repr(ev)


def _agendar_com_thread(segundos: float, acao: Callable[[], None]) -> None:
    t = threading.Timer(segundos, acao)
    t.daemon = True
    t.start()


# --------------------------------------------------------------------- main


def montar_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="lockwise-gateway",
        description="Gemeo digital do circuito LOCKWISE e ponte para a API na nuvem.",
    )
    p.add_argument("--api-url", default=os.environ.get("LOCKWISE_API_URL"),
                   help="URL base da API (ou LOCKWISE_API_URL). Sem ela, roda em modo eco.")
    p.add_argument("--api-key", default=os.environ.get("LOCKWISE_API_KEY"),
                   help="chave enviada em X-API-Key (ou LOCKWISE_API_KEY)")
    p.add_argument("--fila", type=Path, default=Path(os.environ.get("LOCKWISE_FILA", "fila_offline.jsonl")),
                   help="arquivo JSON Lines da fila offline")
    p.add_argument("--roteiro", type=Path, help="executa os comandos deste arquivo em vez do teclado")
    p.add_argument("--timeout-fisico", action="store_true",
                   help=f"dispara TIMEOUT sozinho {TEMPO_TRAVA_ABERTA_S} s apos LIBERADO, como o NE555")
    p.add_argument("--espera-acordar", type=float, default=60.0, metavar="SEGUNDOS",
                   help="quanto esperar a API acordar no arranque (0 desliga)")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = montar_parser().parse_args(argv)

    if args.api_url:
        cliente: Cliente = ClienteAPI(args.api_url, args.api_key, fila=args.fila)
        modo = f"API {args.api_url}"
    else:
        cliente = ClienteEco()
        modo = "eco (sem rede; defina --api-url ou LOCKWISE_API_URL)"

    print(f"LOCKWISE gateway {__version__} - modo {modo}")
    print("senha gravada: 1011 - digite 'ajuda' para os comandos")

    if isinstance(cliente, ClienteAPI):
        print("acordando a API...", end=" ", flush=True)
        print("no ar" if cliente.acordar(args.espera_acordar) else "sem resposta (eventos irao para a fila)")
        if cliente.tamanho_fila():
            enviados, restantes = cliente.reenviar_fila()
            print(f"fila offline: {enviados} reenviado(s), {restantes} pendente(s)")

    interprete = Interprete(cliente, timeout_fisico=args.timeout_fisico)
    fonte: FonteDeComandos = Roteiro.do_arquivo(args.roteiro) if args.roteiro else Teclado()
    interprete.rodar(fonte)
    return 0


if __name__ == "__main__":
    sys.exit(main())
