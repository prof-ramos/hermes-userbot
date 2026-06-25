"""Cliente Pyrogram/Kurigram — factory e gerenciamento de ciclo de vida.

Usa Kurigram (fork ativo do Pyrogram) como biblioteca MTProto.
A API é idêntica ao Pyrogram — basta trocar o import.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pyrogram import Client  # type: ignore[import-untyped]  # kurigram é drop-in

from app.config.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Diretório de sessões
SESSIONS_DIR = Path(__file__).resolve().parent.parent / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def create_client() -> Client:
    """Cria uma instância configurada do cliente MTProto.

    Suporta string session (preferencial) ou sessão em arquivo.
    """

    # Configuração dos plugins
    plugins_config: dict[str, Any] = {
        "root": "app.plugins",
    }
    if settings.plugins.include:
        plugins_config["include"] = settings.plugins.include
    if settings.plugins.exclude:
        plugins_config["exclude"] = settings.plugins.exclude

    # Determina tipo de sessão
    if settings.telegram.string_session:
        logger.info("client_using_string_session")
        session = settings.telegram.string_session
    else:
        session_name = "hermes_userbot"
        session_path = str(SESSIONS_DIR / session_name)
        logger.info("client_using_file_session", path=session_path)
        session = session_path

    client = Client(
        name=session,
        api_id=settings.telegram.api_id,
        api_hash=settings.telegram.api_hash,
        plugins=plugins_config,
        workdir=str(SESSIONS_DIR) if not settings.telegram.string_session else None,
        no_updates=False,
        workdir_kwargs=None,
    )

    logger.info(
        "client_created",
        session_type="string" if settings.telegram.string_session else "file",
    )
    return client


# Cliente singleton — inicializado pelo bootstrap
_client: Client | None = None


def get_client() -> Client:
    """Retorna o cliente singleton. Levanta erro se não inicializado."""
    if _client is None:
        raise RuntimeError("Cliente não inicializado. Chame bootstrap() primeiro.")
    return _client


def set_client(client: Client) -> None:
    """Define o cliente singleton."""
    global _client
    _client = client