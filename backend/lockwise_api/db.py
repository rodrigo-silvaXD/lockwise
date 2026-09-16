"""Conexão com o banco, criação das tabelas e semente inicial."""

from __future__ import annotations

import logging

from sqlalchemy import Engine, create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .modelos import Base, Usuario

log = logging.getLogger("lockwise.db")

# O circuito tem uma senha gravada (1011), logo um morador. O gateway envia usuario_id=1.
MORADOR = {"id": 1, "nome": "Morador", "codigo_senha": 0b1011, "ativo": True}


def criar_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        # `check_same_thread`: o TestClient e o uvicorn usam threads diferentes.
        # StaticPool só para banco em memória, para todas as sessões verem o mesmo banco.
        opcoes = {"connect_args": {"check_same_thread": False}}
        if ":memory:" in url or url.endswith("sqlite://"):
            opcoes["poolclass"] = StaticPool
        return create_engine(url, **opcoes)
    return create_engine(url, pool_pre_ping=True)


def criar_sessionmaker(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def iniciar(engine: Engine) -> None:
    """Cria as tabelas que faltam e garante o morador. Idempotente."""
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        if s.scalar(select(Usuario).where(Usuario.id == MORADOR["id"])) is None:
            s.add(Usuario(**MORADOR))
            s.commit()
            log.info("semente: usuario id=%s (%s) criado", MORADOR["id"], MORADOR["nome"])
