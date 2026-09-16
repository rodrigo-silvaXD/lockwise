"""Casos de uso. Orquestram repositórios e domínio; não conhecem HTTP.

Cada serviço tem uma responsabilidade: registrar e consultar acessos,
registrar e resolver alertas, projetar o estado da fechadura. Dependem de
abstrações (Protocols de `repositorios.py`, `PoliticaDeSupervisao`,
`Notificador`) recebidas no construtor — quem monta é `dependencias.py`.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Protocol, Sequence
from zoneinfo import ZoneInfo

from .dominio.estados import Liberado, Projecao
from .dominio.eventos import AcessoRegistrado, AlertaRegistrado, Evento, Resultado, TipoAlerta, utc
from .dominio.notificacao import AlertaPublicado, Notificador
from .dominio.politicas import PoliticaDeSupervisao
from .esquemas import (
    AcessoEntrada,
    AlertaEntrada,
    DemandaHoraria,
    FaixaHoraria,
    FechaduraSaida,
    UltimoEvento,
)
from .modelos import Acesso, Alerta
from .repositorios import RepositorioDeAcessos, RepositorioDeAlertas, RepositorioDeUsuarios

log = logging.getLogger("lockwise.servicos")

# Quantos eventos recentes bastam para projetar o estado atual. A projeção
# converge em poucos eventos (qualquer LIBERADO ou DESBLOQUEIO zera o passado).
JANELA_DE_PROJECAO = 200


class UnidadeDeTrabalho(Protocol):
    def confirmar(self) -> None: ...


class UsuarioDesconhecido(ValueError):
    pass


def _registrado(a: Acesso) -> AcessoRegistrado:
    return AcessoRegistrado(utc(a.momento), Resultado(a.resultado), a.tentativa, a.energia_mj, a.usuario_id)


def _publicado(al: Alerta) -> AlertaPublicado:
    return AlertaPublicado(al.id, TipoAlerta(al.tipo), utc(al.momento), al.detalhe, al.acesso_id)


# ----------------------------------------------------------------- acessos


class ServicoDeAcessos:
    def __init__(
        self,
        acessos: RepositorioDeAcessos,
        alertas: RepositorioDeAlertas,
        usuarios: RepositorioDeUsuarios,
        politica: PoliticaDeSupervisao,
        notificador: Notificador,
        uow: UnidadeDeTrabalho,
        fuso: str,
    ) -> None:
        self._acessos = acessos
        self._alertas = alertas
        self._usuarios = usuarios
        self._politica = politica
        self._notificador = notificador
        self._uow = uow
        self._fuso = fuso

    def registrar(self, entrada: AcessoEntrada) -> tuple[Acesso, list[Alerta]]:
        if entrada.usuario_id is not None and self._usuarios.obter(entrada.usuario_id) is None:
            raise UsuarioDesconhecido(f"usuario_id {entrada.usuario_id} não existe")

        acesso = self._acessos.adicionar(Acesso(**entrada.model_dump()))

        gerados = [
            self._alertas.adicionar(Alerta(
                tipo=g.tipo.value, momento=acesso.momento, detalhe=g.detalhe, acesso_id=acesso.id,
            ))
            for g in self._politica.avaliar(_registrado(acesso))
        ]
        self._uow.confirmar()

        log.info(
            "acesso id=%s resultado=%s tentativa=%s energia_mj=%s usuario=%s alertas=%s",
            acesso.id, acesso.resultado, acesso.tentativa, acesso.energia_mj, acesso.usuario_id,
            [a.tipo for a in gerados],
        )
        for al in gerados:
            self._notificador.publicar(_publicado(al))
        return acesso, gerados

    def listar(self, de: datetime | None, ate: datetime | None, limite: int) -> Sequence[Acesso]:
        return self._acessos.listar(de, ate, limite)

    def demanda_horaria(self, de: datetime | None, ate: datetime | None) -> DemandaHoraria:
        """Agrega por hora **local**. É a demanda d_h do modelo de otimização.

        A agregação é feita aqui, não em SQL, para que o fuso seja respeitado
        igualmente em SQLite (testes) e Postgres (produção).
        """
        fuso = ZoneInfo(self._fuso)
        faixas: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for a in self._acessos.no_periodo(de, ate):
            h = utc(a.momento).astimezone(fuso).hour
            faixas[h]["acessos"] += 1
            faixas[h][a.resultado.lower() + "s"] += 1
            faixas[h]["energia_mj"] += a.energia_mj

        lista = [
            FaixaHoraria(
                hora=h,
                acessos=faixas[h]["acessos"],
                liberados=faixas[h]["liberados"],
                negados=faixas[h]["negados"],
                bloqueados=faixas[h]["bloqueados"],
                energia_mj=faixas[h]["energia_mj"],
            )
            for h in range(24)
        ]
        return DemandaHoraria(
            de=de, ate=ate, fuso=self._fuso,
            total_acessos=sum(f.acessos for f in lista),
            total_energia_mj=sum(f.energia_mj for f in lista),
            faixas=lista,
        )


# ----------------------------------------------------------------- alertas


class ServicoDeAlertas:
    def __init__(self, alertas: RepositorioDeAlertas, notificador: Notificador, uow: UnidadeDeTrabalho) -> None:
        self._alertas = alertas
        self._notificador = notificador
        self._uow = uow

    def registrar(self, entrada: AlertaEntrada) -> Alerta:
        alerta = self._alertas.adicionar(Alerta(tipo=entrada.tipo.value, momento=entrada.momento, detalhe=entrada.detalhe))
        self._uow.confirmar()
        log.info("alerta id=%s tipo=%s origem=gateway", alerta.id, alerta.tipo)
        self._notificador.publicar(_publicado(alerta))
        return alerta

    def listar(self, resolvido: bool | None, limite: int) -> Sequence[Alerta]:
        return self._alertas.listar(resolvido, limite)

    def resolver(self, id: int) -> Alerta | None:
        alerta = self._alertas.obter(id)
        if alerta is None:
            return None
        alerta.resolvido = True
        self._uow.confirmar()
        log.info("alerta id=%s resolvido", id)
        return alerta


# --------------------------------------------------------------- fechadura


class ServicoDaFechadura:
    def __init__(self, acessos: RepositorioDeAcessos, alertas: RepositorioDeAlertas) -> None:
        self._acessos = acessos
        self._alertas = alertas

    def estado(self, agora: datetime | None = None) -> FechaduraSaida:
        agora = utc(agora or datetime.now(timezone.utc))
        eventos: list[Evento] = [_registrado(a) for a in self._acessos.recentes(JANELA_DE_PROJECAO)]
        eventos += [AlertaRegistrado(utc(al.momento), TipoAlerta(al.tipo)) for al in self._alertas.recentes(JANELA_DE_PROJECAO)]

        projecao = Projecao.reconstruir(eventos)
        vigente = projecao.vigente(agora)
        registrado = projecao.estado

        return FechaduraSaida(
            estado=vigente.nome,
            tentativas=vigente.tentativas,
            desde=vigente.desde,
            trava_fecha_em=registrado.ate if isinstance(vigente, Liberado) and isinstance(registrado, Liberado) else None,
            ultimo_evento=_descrever(projecao.ultimo_evento),
            avisos=projecao.avisos,
            consultado_em=agora,
        )


def _descrever(ev: Evento | None) -> UltimoEvento | None:
    if ev is None:
        return None
    if isinstance(ev, AcessoRegistrado):
        return UltimoEvento(
            tipo="acesso", momento=ev.momento,
            descricao=f"{ev.resultado.value} (tentativa {ev.tentativa}, {ev.energia_mj} mJ)",
        )
    return UltimoEvento(tipo="alerta", momento=ev.momento, descricao=ev.tipo.value)
