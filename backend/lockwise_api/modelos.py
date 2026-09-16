"""Tabelas do banco. É o esquema de `docs/CONTEXTO_LOCKWISE.md` mais a coluna
`tentativa`, que o gateway envia, e `detalhe`/`acesso_id` em alerta, que as
políticas de supervisão preenchem. DDL equivalente em `schema.sql`.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, SmallInteger, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100))
    # O código de 4 bits do comparador (1011 = 11). São 16 valores possíveis;
    # não é um segredo criptográfico e existe para o painel exibir, não para autenticar.
    codigo_senha: Mapped[int] = mapped_column(SmallInteger)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)


class Acesso(Base):
    """Um evento do circuito. A coluna `energia_mj` liga a física à otimização."""

    __tablename__ = "acesso"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"), nullable=True)
    momento: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resultado: Mapped[str] = mapped_column(String(20))  # LIBERADO | NEGADO | BLOQUEADO
    tentativa: Mapped[int] = mapped_column(SmallInteger)  # 1, 2 ou 3
    energia_mj: Mapped[int] = mapped_column(Integer)

    __table_args__ = (Index("idx_acesso_momento", "momento"),)


class Alerta(Base):
    __tablename__ = "alerta"

    id: Mapped[int] = mapped_column(primary_key=True)
    tipo: Mapped[str] = mapped_column(String(30))
    momento: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolvido: Mapped[bool] = mapped_column(Boolean, default=False)
    detalhe: Mapped[str | None] = mapped_column(String(200), nullable=True)
    acesso_id: Mapped[int | None] = mapped_column(ForeignKey("acesso.id"), nullable=True)

    __table_args__ = (Index("idx_alerta_momento", "momento"),)
