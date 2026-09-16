"""Uma API isolada por teste: SQLite em memória, chave conhecida, política escolhida."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from lockwise_api.config import Configuracao
from lockwise_api.db import criar_engine
from lockwise_api.main import criar_app

CHAVE = "chave-de-teste"
T0 = datetime(2026, 1, 10, 14, 0, 0, tzinfo=timezone.utc)  # 11:00 em São Paulo; no passado em relação a hoje

logging.getLogger("lockwise").setLevel(logging.WARNING)


def montar(politica: str = "nenhuma", api_key: str | None = CHAVE, **extras) -> TestClient:
    config = Configuracao(database_url="sqlite://", api_key=api_key, politica=politica, **extras)
    app = criar_app(config, engine=criar_engine(config.database_url))
    return TestClient(app)


@pytest.fixture
def api() -> TestClient:
    """API com política `nenhuma`: só os alertas do gateway. Testes de política montam a sua."""
    return montar()


@pytest.fixture
def chave() -> dict[str, str]:
    return {"X-API-Key": CHAVE}


def em(segundos: float) -> str:
    return (T0 + timedelta(seconds=segundos)).isoformat()


def acesso(resultado: str, tentativa: int = 1, t: float = 0, **extras) -> dict:
    corpo = {
        "momento": em(t),
        "usuario_id": 1 if resultado == "LIBERADO" else None,
        "resultado": resultado,
        "tentativa": tentativa,
        "energia_mj": 18_200 if resultado == "LIBERADO" else 0,
    }
    corpo.update(extras)
    return corpo


def alerta(tipo: str, t: float = 0) -> dict:
    return {"tipo": tipo, "momento": em(t)}
