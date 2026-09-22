"""A arquitetura documentada, verificada pelo próprio código.

`docs/arquitetura.md` afirma que as dependências apontam para dentro: o
domínio não conhece HTTP nem banco, e os serviços dependem de abstrações.
Afirmação em documento envelhece em silêncio — alguém importa `sqlalchemy`
dentro de `dominio/` num dia apertado e o diagrama passa a mentir.

Estes testes transformam o desenho em restrição executável. Se a arquitetura
mudar de propósito, é aqui que se muda primeiro.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PACOTE = Path(__file__).resolve().parent.parent / "lockwise_api"
DOMINIO = PACOTE / "dominio"

# O que o domínio não pode conhecer: nem web, nem banco, nem o resto da app.
PROIBIDO_NO_DOMINIO = ("fastapi", "starlette", "sqlalchemy", "pydantic", "uvicorn", "psycopg")


def importes(arquivo: Path) -> set[str]:
    """Os módulos de primeiro nível importados por este arquivo."""
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"), filename=str(arquivo))
    nomes: set[str] = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            nomes.update(a.name.split(".")[0] for a in no.names)
        elif isinstance(no, ast.ImportFrom) and no.level == 0 and no.module:
            nomes.add(no.module.split(".")[0])
    return nomes


def arquivos_do_dominio() -> list[Path]:
    return sorted(p for p in DOMINIO.glob("*.py") if p.name != "__init__.py")


def test_existe_dominio_para_verificar():
    assert arquivos_do_dominio(), "nenhum arquivo em dominio/ — o teste ficaria vazio"


@pytest.mark.parametrize("arquivo", arquivos_do_dominio(), ids=lambda p: p.name)
def test_dominio_nao_conhece_web_nem_banco(arquivo: Path):
    """Nível 3 do C4: nenhuma seta sai do domínio para a infraestrutura."""
    proibidos = importes(arquivo) & set(PROIBIDO_NO_DOMINIO)
    assert not proibidos, (
        f"{arquivo.name} importa {sorted(proibidos)}. O domínio precisa continuar puro — "
        f"veja docs/arquitetura.md, nível 3. Se a dependência for mesmo necessária, "
        f"mova a regra para servicos.py ou esconda a infraestrutura atrás de um Protocol."
    )


@pytest.mark.parametrize("arquivo", arquivos_do_dominio(), ids=lambda p: p.name)
def test_dominio_so_importa_a_si_mesmo_dentro_do_pacote(arquivo: Path):
    """O domínio não pode depender de rotas, serviços nem repositórios."""
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"), filename=str(arquivo))
    for no in ast.walk(arvore):
        # `from ..servicos import X` tem level >= 2: sai de dominio/ para o pacote
        if isinstance(no, ast.ImportFrom) and no.level >= 2:
            pytest.fail(
                f"{arquivo.name} importa de fora do domínio ('{'.' * no.level}{no.module or ''}'). "
                f"As dependências apontam para dentro."
            )


def test_servicos_dependem_de_protocols_e_nao_de_sqlalchemy():
    """Inversão de dependência: quem injeta a implementação é dependencias.py."""
    assert "sqlalchemy" not in importes(PACOTE / "servicos.py"), (
        "servicos.py importa sqlalchemy. Os serviços recebem os Protocols de "
        "repositorios.py; a implementação concreta é montada em dependencias.py."
    )


def test_rotas_nao_falam_com_o_banco_diretamente():
    """A fronteira HTTP chama serviços, não repositórios nem sessões."""
    for rota in sorted((PACOTE / "rotas").glob("*.py")):
        if rota.name == "__init__.py":
            continue
        proibidos = importes(rota) & {"sqlalchemy", "psycopg"}
        # saude.py consulta o banco de propósito, para reportar se ele responde
        if rota.name == "saude.py":
            continue
        assert not proibidos, f"{rota.name} fala com o banco direto; deveria passar por um serviço"


def test_o_documento_de_arquitetura_existe_e_aponta_o_dominio():
    doc = PACOTE.parent.parent / "docs" / "arquitetura.md"
    assert doc.exists(), "docs/arquitetura.md sumiu; os diagramas C4 fazem parte da entrega"
    texto = doc.read_text(encoding="utf-8")
    for marca in ("Nível 1", "Nível 2", "Nível 3", "SOLID", "```mermaid"):
        assert marca in texto, f"docs/arquitetura.md não tem {marca!r}"
