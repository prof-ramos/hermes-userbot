"""Servidor FastAPI — API interna de controle do userbot.

Roda em paralelo com o cliente MTProto, permitindo que o
backend do Hermes envie comandos programaticamente.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.api.routes import router
from app.utils.logging import get_logger

logger = get_logger(__name__)

_startup_time = time.monotonic()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle do FastAPI."""
    logger.info("api_server_starting")
    yield
    logger.info("api_server_stopping")


def create_app() -> FastAPI:
    """Cria a aplicação FastAPI."""
    app = FastAPI(
        title="Hermes Userbot API",
        description="API interna para controle do Hermes Userbot via MTProto",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(router, prefix="/api/v1")

    @app.get("/")
    async def root():
        return {"service": "hermes-userbot", "version": "0.1.0"}

    return app


async def create_api_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Inicia o servidor uvicorn de forma assíncrona."""
    app = create_app()
    config = uvicorn.Config(app, host=host, port=port, log_level="info", access_log=False)
    server = uvicorn.Server(config)
    logger.info("api_server_listening", host=host, port=port)
    await server.serve()
