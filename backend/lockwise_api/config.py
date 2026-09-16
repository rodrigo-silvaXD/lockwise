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


def normalizar_url_banco(url: str) -> str:
    """Render e Heroku entregam `postgres://`; SQLAlchemy 2 exige `postgresql+psycopg://`."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


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
