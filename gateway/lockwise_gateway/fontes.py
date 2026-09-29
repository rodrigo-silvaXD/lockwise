"""De onde vêm os comandos que acionam os pinos.

Do teclado, na demonstração, ou de um arquivo de roteiro, nos testes e no
ensaio. As duas implementam o mesmo `FonteDeComandos`, então o interpretador
não sabe de qual está lendo.
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
