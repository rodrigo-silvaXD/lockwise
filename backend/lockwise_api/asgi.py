"""Ponto de entrada ASGI: `uvicorn lockwise_api.asgi:app`. Tudo vem do ambiente."""

from .main import criar_app

app = criar_app()
