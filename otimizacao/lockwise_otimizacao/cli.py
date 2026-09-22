"""Linha de comando: semear o histórico e resolver a escala.

    python -m lockwise_otimizacao.cli semear --dias 7 --chave ...
    python -m lockwise_otimizacao.cli resolver
    python -m lockwise_otimizacao.cli resolver --arquivo demanda.json
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import __version__
from .demanda import Demanda, da_api, do_arquivo
from .modelo import EQUIPE_MAXIMA, SemSolucao
from .relatorio import completo

API_PADRAO = "https://lockwise-api.onrender.com"


# ------------------------------------------------------------------ semear


def semear(args: argparse.Namespace) -> int:
    """Gera o histórico e envia pela API, usando o cliente do próprio gateway."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "gateway"))
    from lockwise_gateway.transporte import ClienteAPI  # noqa: E402

    from .historico import enviar, gerar  # noqa: E402

    if not args.chave:
        print("Falta a chave da API. Use --chave ou a variável LOCKWISE_API_KEY.", file=sys.stderr)
        return 1

    cliente = ClienteAPI(args.api, args.chave, fila=args.fila)
    print(f"API: {args.api}")
    print("acordando...", end=" ", flush=True)
    print("no ar" if cliente.acordar(90) else "sem resposta (os eventos irão para a fila)")

    eventos = list(gerar(dias=args.dias, semente=args.semente))
    print(f"{len(eventos)} eventos de {args.dias} dia(s) de operação a enviar\n")

    def progresso(n: int, ev, envio) -> None:
        if n % 50 == 0 or not envio.ok:
            marca = "" if envio.ok else f"  ← {envio.situacao}"
            print(f"  {n:>5}/{len(eventos)}{marca}", flush=True)

    entregues, falhas = enviar(iter(eventos), cliente, ao_enviar=progresso)
    print(f"\nentregues: {entregues} · falhas: {falhas}")
    if falhas:
        print(f"os eventos que falharam estão em {args.fila}; rode de novo para reenviar")
    return 0 if falhas == 0 else 1


# ---------------------------------------------------------------- resolver


def resolver(args: argparse.Namespace) -> int:
    opcoes = {"capacidade": args.capacidade, "presenca_minima": args.presenca_minima}
    try:
        if args.arquivo:
            demanda = do_arquivo(args.arquivo, dias=args.dias, **opcoes)
        else:
            de = (datetime.now(timezone.utc) - timedelta(days=args.dias)).isoformat()
            demanda = da_api(args.api, de=de, dias=args.dias, **opcoes)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"não consegui ler a demanda de {args.api}: {e}", file=sys.stderr)
        print("a API do plano gratuito hiberna; tente de novo em alguns segundos", file=sys.stderr)
        return 1

    if demanda.total_acessos == 0:
        print("o período não tem nenhum acesso registrado.", file=sys.stderr)
        print("rode antes:  python -m lockwise_otimizacao.cli semear --chave ...", file=sys.stderr)
        return 1

    try:
        texto = completo(demanda, args.equipe)
    except SemSolucao as e:
        print(f"sem solução: {e}", file=sys.stderr)
        return 1

    print(texto)
    if args.saida:
        args.saida.write_text(texto, encoding="utf-8")
        print(f"relatório salvo em {args.saida}")
    return 0


# -------------------------------------------------------------------- main


def montar_parser() -> argparse.ArgumentParser:
    import os

    p = argparse.ArgumentParser(
        prog="lockwise-otimizar",
        description="Escala de vigilância de menor custo a partir do histórico de acessos.",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="comando", required=True)

    s = sub.add_parser("semear", help="gera histórico sintético e envia pela API")
    s.add_argument("--api", default=os.environ.get("LOCKWISE_API_URL", API_PADRAO))
    s.add_argument("--chave", default=os.environ.get("LOCKWISE_API_KEY"))
    s.add_argument("--dias", type=int, default=7)
    s.add_argument("--semente", type=int, default=20261110)
    s.add_argument("--fila", type=Path, default=Path("fila_semeadura.jsonl"))
    s.set_defaults(func=semear)

    r = sub.add_parser("resolver", help="lê a demanda e resolve o modelo")
    r.add_argument("--api", default=os.environ.get("LOCKWISE_API_URL", API_PADRAO))
    r.add_argument("--arquivo", type=Path, help="lê de um JSON salvo em vez da API")
    r.add_argument("--dias", type=int, default=7, help="dias que o período abrange")
    r.add_argument("--capacidade", type=int, default=4, help="acessos por vigilante por hora (K)")
    r.add_argument("--presenca-minima", type=int, default=1)
    r.add_argument("--equipe", type=int, default=EQUIPE_MAXIMA, help="vigilantes disponíveis")
    r.add_argument("--saida", type=Path, help="salva o relatório neste arquivo")
    r.set_defaults(func=resolver)

    return p


def _console_em_utf8() -> None:
    """O relatório usa ─ █ ∀ Σ ℤ; o console do Windows fala cp1252 por padrão.

    Sem isto, imprimir o relatório levanta UnicodeEncodeError. `errors=replace`
    garante que, num terminal que realmente não desenhe algum caractere, saia
    um sinal no lugar em vez de derrubar o programa.
    """
    for fluxo in (sys.stdout, sys.stderr):
        reconfigurar = getattr(fluxo, "reconfigure", None)
        if reconfigurar is not None:
            try:
                reconfigurar(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def main(argv: list[str] | None = None) -> int:
    _console_em_utf8()
    args = montar_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
