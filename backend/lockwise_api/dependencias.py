"""Composição: onde as abstrações ganham implementações concretas.

É o único lugar que sabe, ao mesmo tempo, que existe SQLAlchemy e que existe
`ServicoDeAcessos`. As rotas pedem um serviço via `Depends`; este módulo
monta a sessão, os repositórios e entrega o serviço pronto. Trocar o banco
ou a política de supervisão é trocar uma linha aqui, não nas rotas.
"""

from __future__ import annotations

from typing import Iterator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from .repositorios import AcessosSQL, AlertasSQL, UsuariosSQL
from .servicos import ServicoDaFechadura, ServicoDeAcessos, ServicoDeAlertas


class UoWSQL:
    def __init__(self, sessao: Session) -> None:
        self._s = sessao

    def confirmar(self) -> None:
        self._s.commit()


def obter_sessao(request: Request) -> Iterator[Session]:
    fabrica = request.app.state.sessionmaker
    with fabrica() as sessao:
        yield sessao


def obter_servico_de_acessos(request: Request, sessao: Session = Depends(obter_sessao)) -> ServicoDeAcessos:
    estado = request.app.state
    return ServicoDeAcessos(
        acessos=AcessosSQL(sessao),
        alertas=AlertasSQL(sessao),
        usuarios=UsuariosSQL(sessao),
        politica=estado.politica,
        notificador=estado.notificador,
        uow=UoWSQL(sessao),
        fuso=estado.config.fuso,
    )


def obter_servico_de_alertas(request: Request, sessao: Session = Depends(obter_sessao)) -> ServicoDeAlertas:
    return ServicoDeAlertas(alertas=AlertasSQL(sessao), notificador=request.app.state.notificador, uow=UoWSQL(sessao))


def obter_servico_da_fechadura(sessao: Session = Depends(obter_sessao)) -> ServicoDaFechadura:
    return ServicoDaFechadura(acessos=AcessosSQL(sessao), alertas=AlertasSQL(sessao))
