"""Leitura do ambiente, com atenção ao que os painéis de nuvem realmente entregam."""

from datetime import time

import pytest

from lockwise_api.config import Configuracao, UrlDeBancoInvalida, normalizar_url_banco

NEON = "postgresql://neondb_owner:npg_S3nh4@ep-nome-123.sa-east-1.aws.neon.tech/neondb?sslmode=require"
ESPERADO = "postgresql+psycopg://neondb_owner:npg_S3nh4@ep-nome-123.sa-east-1.aws.neon.tech/neondb?sslmode=require"


def test_prefixo_vira_psycopg_preservando_a_query():
    assert normalizar_url_banco(NEON) == ESPERADO
    # Render e Heroku entregam postgres://
    assert normalizar_url_banco("postgres://u:p@host/db") == "postgresql+psycopg://u:p@host/db"
    # channel_binding aparece em algumas strings da Neon
    com_cb = NEON + "&channel_binding=require"
    assert normalizar_url_banco(com_cb).endswith("&channel_binding=require")


@pytest.mark.parametrize("embrulho", [
    f"psql '{NEON}'",            # formato psql do painel da Neon
    f"psql {NEON}",
    f"DATABASE_URL={NEON}",      # formato .env
    f"DATABASE_URL='{NEON}'",
    f"'{NEON}'",                 # copiado com aspas
    f'"{NEON}"',
    f"  {NEON}  ",               # espaço sobrando na colagem
    f"\n{NEON}\n",
])
def test_aceita_os_embrulhos_que_os_paineis_entregam(embrulho):
    assert normalizar_url_banco(embrulho) == ESPERADO


@pytest.mark.parametrize("lixo", [
    "********",                  # senha mascarada: selecionou com o mouse em vez de copiar
    "npg_S3nh4",                 # só a senha, do formato "parameters only"
    "ep-nome-123.sa-east-1.aws.neon.tech",  # só o host
    "",
])
def test_erro_util_quando_nao_e_uma_url(lixo):
    with pytest.raises(UrlDeBancoInvalida) as e:
        normalizar_url_banco(lixo)
    assert "DATABASE_URL" in str(e.value) and "Connection string" in str(e.value)


def test_a_mensagem_de_erro_nao_vaza_a_senha_inteira():
    senha = "npg_umaSenhaMuitoLongaQueNaoDeveAparecerInteira"
    with pytest.raises(UrlDeBancoInvalida) as e:
        normalizar_url_banco(senha)
    assert senha not in str(e.value)
    assert senha[:8] in str(e.value)  # o começo aparece, para a pessoa reconhecer o que colou


def test_sqlite_passa_intacto():
    assert normalizar_url_banco("sqlite:///./lockwise.db") == "sqlite:///./lockwise.db"
    assert normalizar_url_banco("sqlite://") == "sqlite://"


# ------------------------------------------------------------- do ambiente


def test_padroes_sem_nenhuma_variavel():
    c = Configuracao.do_ambiente({})
    assert c.database_url == "sqlite:///./lockwise.db"
    assert c.api_key is None and c.politica == "limite"
    assert c.janela == (time(6, 0), time(23, 0)) and c.fuso == "America/Sao_Paulo"
    assert c.webhook_url is None and c.cors_origins == ("*",)


def test_le_o_ambiente_como_o_render_entrega():
    c = Configuracao.do_ambiente({
        "DATABASE_URL": f"psql '{NEON}'",
        "LOCKWISE_API_KEY": "chave",
        "LOCKWISE_POLITICA": "composta",
        "LOCKWISE_LIMITE_TENTATIVAS": "1",
        "LOCKWISE_JANELA": "22:00-06:00",
        "LOCKWISE_FUSO": "UTC",
        "LOCKWISE_WEBHOOK_URL": "https://hooks.exemplo/x",
        "LOCKWISE_CORS_ORIGINS": "https://painel.exemplo, https://outro.exemplo",
    })
    assert c.database_url == ESPERADO
    assert c.api_key == "chave" and c.politica == "composta" and c.limite_tentativas == 1
    assert c.janela == (time(22, 0), time(6, 0)) and c.fuso == "UTC"
    assert c.cors_origins == ("https://painel.exemplo", "https://outro.exemplo")


def test_variaveis_vazias_contam_como_ausentes():
    c = Configuracao.do_ambiente({"LOCKWISE_API_KEY": "", "LOCKWISE_WEBHOOK_URL": ""})
    assert c.api_key is None and c.webhook_url is None
