"""De onde vêm os comandos que acionam os pinos.

Hoje, do teclado (demo) ou de um arquivo de roteiro (testes e ensaio).
Se a equipe montar o estágio de potência de `docs/fisica.md` com um ESP32
lendo os pinos de estado, uma fonte `Serial` entra aqui sem tocar no resto.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable, Iterator, Protocol


class FonteDeComandos(Protocol):
    def comandos(self) -> Iterator[str]: ...


class Teclado:
    def __init__(self, prompt: str = "lockwise> ", ler: Callable[[str], str] = input) -> None:
        self._prompt = prompt
        self._ler = ler

    def comandos(self) -> Iterator[str]:
        while True:
            try:
                yield self._ler(self._prompt)
            except (EOFError, KeyboardInterrupt):
                yield "sair"
                return


class Roteiro:
    """Uma linha por comando. Linhas vazias e iniciadas por `#` são ignoradas."""

    def __init__(self, linhas: Iterable[str]) -> None:
        self._linhas = list(linhas)

    @classmethod
    def do_arquivo(cls, caminho: Path) -> Roteiro:
        return cls(caminho.read_text(encoding="utf-8").splitlines())

    def comandos(self) -> Iterator[str]:
        for linha in self._linhas:
            texto = linha.split("#", 1)[0].strip()
            if texto:
                yield texto
