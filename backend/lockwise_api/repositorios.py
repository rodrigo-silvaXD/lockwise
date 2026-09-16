"""Acesso a dados por trás de interfaces (Protocols).

Os serviços dependem dos Protocols, não das classes SQLAlchemy — inversão de
dependência. Um repositório em memória serviria igualmente para testar o
serviço, e trocar de ORM não tocaria em nenhuma regra de negócio.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from .modelos import Acesso, Alerta, Usuario


class RepositorioDeAcessos(Protocol):
    def adicionar(self, acesso: Acesso) -> Acesso: ...
    def listar(self, de: datetime | None, ate: datetime | None, limite: int) -> Sequence[Acesso]: ...
    def no_periodo(self, de: datetime | None, ate: datetime | None) -> Sequence[Acesso]: ...
    def recentes(self, quantidade: int) -> Sequence[Acesso]: ...


class RepositorioDeAlertas(Protocol):
    def adicionar(self, alerta: Alerta) -> Alerta: ...
    def obter(self, id: int) -> Alerta | None: ...
    def listar(self, resolvido: bool | None, limite: int) -> Sequence[Alerta]: ...
    def recentes(self, quantidade: int) -> Sequence[Alerta]: ...


class RepositorioDeUsuarios(Protocol):
    def obter(self, id: int) -> Usuario | None: ...


# ------------------------------------------------------------- SQLAlchemy


def _periodo(consulta, coluna, de, ate):
    if de is not None:
        consulta = consulta.where(coluna >= de)
    if ate is not None:
        consulta = consulta.where(coluna < ate)
    return consulta


class AcessosSQL:
    def __init__(self, sessao: Session) -> None:
        self._s = sessao

    def adicionar(self, acesso: Acesso) -> Acesso:
        self._s.add(acesso)
        self._s.flush()
        return acesso

    def listar(self, de, ate, limite) -> Sequence[Acesso]:
        q = _periodo(select(Acesso), Acesso.momento, de, ate).order_by(Acesso.momento.desc(), Acesso.id.desc())
        return self._s.scalars(q.limit(limite)).all()

    def no_periodo(self, de, ate) -> Sequence[Acesso]:
        q = _periodo(select(Acesso), Acesso.momento, de, ate).order_by(Acesso.momento)
        return self._s.scalars(q).all()

    def recentes(self, quantidade: int) -> Sequence[Acesso]:
        q = select(Acesso).order_by(Acesso.momento.desc(), Acesso.id.desc()).limit(quantidade)
        return self._s.scalars(q).all()


class AlertasSQL:
    def __init__(self, sessao: Session) -> None:
        self._s = sessao

    def adicionar(self, alerta: Alerta) -> Alerta:
        self._s.add(alerta)
        self._s.flush()
        return alerta

    def obter(self, id: int) -> Alerta | None:
        return self._s.get(Alerta, id)

    def listar(self, resolvido, limite) -> Sequence[Alerta]:
        q = select(Alerta)
        if resolvido is not None:
            q = q.where(Alerta.resolvido == resolvido)
        return self._s.scalars(q.order_by(Alerta.momento.desc(), Alerta.id.desc()).limit(limite)).all()

    def recentes(self, quantidade: int) -> Sequence[Alerta]:
        q = select(Alerta).order_by(Alerta.momento.desc(), Alerta.id.desc()).limit(quantidade)
        return self._s.scalars(q).all()


class UsuariosSQL:
    def __init__(self, sessao: Session) -> None:
        self._s = sessao

    def obter(self, id: int) -> Usuario | None:
        return self._s.get(Usuario, id)
