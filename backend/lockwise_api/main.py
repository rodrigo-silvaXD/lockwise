"""Montagem da aplicação.

`criar_app()` recebe configuração e engine opcionais para que os testes montem
uma instância isolada (SQLite em memória, chave conhecida, política escolhida)
sem variáveis de ambiente. Em produção, `asgi.py` chama `criar_app()` sem
argumentos e tudo vem do ambiente.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Engine

from . import __version__
from .config import Configuracao
from .db import criar_engine, criar_sessionmaker, iniciar
from .dominio.notificacao import LogObservador, Notificador, WebhookObservador
from .dominio.politicas import politica_por_nome
from .rotas import acessos, alertas, fechadura, saude

DESCRICAO = """\
Backend do **LOCKWISE** — sistema de controle de acesso da ExpoTech 2026.2 (UniFECAF).

Recebe os eventos que o gateway produz a partir do circuito, persiste o histórico e expõe
a **demanda horária** (entrada do modelo de otimização) e o **estado atual da fechadura**.

Escrita exige `X-API-Key`. Leitura é aberta.
"""


def configurar_logs(nivel: int = logging.INFO) -> None:
    raiz = logging.getLogger()
    if not raiz.handlers:
        logging.basicConfig(level=nivel, format="%(asctime)s %(levelname)s %(name)s %(message)s")


def criar_app(config: Configuracao | None = None, engine: Engine | None = None) -> FastAPI:
    configurar_logs()
    config = config or Configuracao.do_ambiente()
    engine = engine or criar_engine(config.database_url)
    iniciar(engine)

    notificador = Notificador()
    notificador.assinar(LogObservador())
    if config.webhook_url:
        notificador.assinar(WebhookObservador(config.webhook_url))

    politica = politica_por_nome(
        config.politica, limite=config.limite_tentativas, janela=config.janela, fuso=config.fuso,
    )

    app = FastAPI(title="LOCKWISE API", version=__version__, description=DESCRICAO)
    app.state.config = config
    app.state.engine = engine
    app.state.sessionmaker = criar_sessionmaker(engine)
    app.state.notificador = notificador
    app.state.politica = politica

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(config.cors_origins),
        allow_methods=["GET", "POST", "PATCH"],
        allow_headers=["Content-Type", "X-API-Key"],
    )

    app.include_router(saude.router)
    app.include_router(acessos.router)
    app.include_router(alertas.router)
    app.include_router(fechadura.router)

    logging.getLogger("lockwise").info(
        "app pronta versao=%s politica=%s observadores=%s banco=%s chave=%s",
        __version__, politica.nome, notificador.quantidade,
        engine.url.render_as_string(hide_password=True),
        "configurada" if config.api_key else "AUSENTE (escrita bloqueada)",
    )
    return app
