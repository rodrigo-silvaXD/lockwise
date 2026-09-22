"""GET / — a porta de entrada.

Sem esta rota, abrir a URL no navegador devolve `{"detail":"Not Found"}`, que
parece servico quebrado para quem nao conhece a API, e e a primeira coisa
que aparece ao clicar no link.

Redireciona para o Swagger, que lista todas as rotas e permite experimenta-las.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter()


@router.get("/", include_in_schema=False, summary="Leva para a documentacao interativa")
def raiz() -> RedirectResponse:
    return RedirectResponse(url="/docs")
