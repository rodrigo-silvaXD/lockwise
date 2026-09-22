"""Configuração por variáveis de ambiente. Nenhum segredo no código.

| Variável                    | Padrão                      | Uso                                          |
|-----------------------------|-----------------------------|----------------------------------------------|
| DATABASE_URL                | sqlite:///./lockwise.db     | Render fornece postgres://…; é normalizada    |
| LOCKWISE_API_KEY            | (vazio → escrita bloqueada) | exigida em X-API-Key nas rotas de escrita     |
| LOCKWISE_POLITICA           | limite                      | limite | horario | composta | nenhuma        |
| LOCKWISE_LIMITE_TENTATIVAS  | 2                           | política `limite`: avisa nesta tentativa      |
| LOCKWISE_JANELA             | 06:00-23:00                 | política `horario`: janela permitida          |
| LOCKWISE_FUSO               | America/Sao_Paulo           | fuso da janela e da demanda horária           |
| LOCKWISE_WEBHOOK_URL        | (vazio → desligado)         | Observer: POST de cada alerta                 |
| LOCKWISE_CORS_ORIGINS       | *                           | origens permitidas (o front, depois)          |
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import time


def _hora(texto: str) -> time:
    h, m = texto.strip().split(":")
    return time(int(h), int(m))


class UrlDeBancoInvalida(ValueError):
    pass


def normalizar_url_banco(url: str) -> str:
    """Aceita a string de conexao como os paineis a entregam e devolve o que o SQLAlchemy entende.

    Dois ajustes. O primeiro e de formato: Render e Heroku entregam
    `postgres://` e a Neon `postgresql://`, mas o SQLAlchemy 2 quer
    `postgresql+psycopg://`.

    O segundo e de embrulho. O painel da Neon oferece a mesma string em varios
    formatos, e quem copia do formato errado leva junto um `psql ` na frente,
    aspas em volta ou um `DATABASE_URL=` do formato .env. Nada disso e uma URL,
    e o erro que o SQLAlchemy dava era um traceback sem pista do que fazer.
    """
    texto = url.strip()

    # `psql 'postgresql://...'` (formato psql do painel)
    if texto.lower().startswith("psql "):
        texto = texto[5:].strip()

    # `DATABASE_URL=postgresql://...` (formato .env)
    for prefixo in ("DATABASE_URL=", "database_url="):
        if texto.startswith(prefixo):
            texto = texto[len(prefixo):].strip()

    # aspas em volta, de qualquer um dos formatos acima
    for aspa in ("'", '"'):
        if len(texto) >= 2 and texto.startswith(aspa) and texto.endswith(aspa):
            texto = texto[1:-1].strip()

    if "://" not in texto:
        raise UrlDeBancoInvalida(
            "DATABASE_URL nao parece uma string de conexao. Esperado algo como "
            "postgresql://usuario:senha@host/banco?sslmode=require, recebido "
            f"{_mascarar(texto)!r}. No painel da Neon, use o botao de copiar do "
            "formato 'Connection string' — o formato psql e o .env vem com "
            "enfeites, e selecionar com o mouse copia a senha como asteriscos."
        )

    if texto.startswith("postgres://"):
        return "postgresql+psycopg://" + texto[len("postgres://"):]
    if texto.startswith("postgresql://"):
        return "postgresql+psycopg://" + texto[len("postgresql://"):]
    return texto


def _mascarar(texto: str, visivel: int = 12) -> str:
    """Primeiros caracteres, o resto escondido. Para a mensagem de erro nao vazar senha."""
    return texto[:visivel] + ("..." if len(texto) > visivel else "")


@dataclass(frozen=True)
class Configuracao:
    database_url: str = "sqlite:///./lockwise.db"
    api_key: str | None = None
    politica: str = "limite"
    limite_tentativas: int = 2
    janela: tuple[time, time] = (time(6, 0), time(23, 0))
    fuso: str = "America/Sao_Paulo"
    webhook_url: str | None = None
    cors_origins: tuple[str, ...] = field(default=("*",))

    @classmethod
    def do_ambiente(cls, env: dict[str, str] | None = None) -> Configuracao:
        e = os.environ if env is None else env
        janela = e.get("LOCKWISE_JANELA", "06:00-23:00").split("-")
        return cls(
            database_url=normalizar_url_banco(e.get("DATABASE_URL", cls.database_url)),
            api_key=e.get("LOCKWISE_API_KEY") or None,
            politica=e.get("LOCKWISE_POLITICA", cls.politica),
            limite_tentativas=int(e.get("LOCKWISE_LIMITE_TENTATIVAS", cls.limite_tentativas)),
            janela=(_hora(janela[0]), _hora(janela[1])),
            fuso=e.get("LOCKWISE_FUSO", cls.fuso),
            webhook_url=e.get("LOCKWISE_WEBHOOK_URL") or None,
            cors_origins=tuple(o.strip() for o in e.get("LOCKWISE_CORS_ORIGINS", "*").split(",") if o.strip()),
        )
