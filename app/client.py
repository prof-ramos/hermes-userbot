"""Cliente Kurigram — factory e gerenciamento de ciclo de vida.

Usa Kurigram (fork ativo do Pyrogram) como biblioteca MTProto.
Kurigram é drop-in: os imports continuam `from pyrogram import Client`.

Smart Plugins:
- Decorators usam @Client.on_message() (classe, não instância)
- O parâmetro `plugins` no Client aponta para o diretório de plugins
- include/exclude usam notação de ponto relativa ao root
- Exemplo: root="app.plugins", include=["private_messages", "commands"]
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pyrogram import Client  # type: ignore[import-untyped]  # kurigram é drop-in

from app.config.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Diretório de sessões em arquivo
SESSIONS_DIR = Path(__file__).resolve().parent.parent / "sessions"
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def create_client() -> Client:
    """Cria uma instância configurada do cliente MTProto.

    - Com STRING_SESSION: usa sessão em string (preferencial para Docker)
    - Sem STRING_SESSION: usa sessão em arquivo (sessions/hermes_userbot.session)
    """
    # Configuração dos Smart Plugins
    # Kurigram/Pyrogram usa notação de ponto para o root e para include/exclude
    plugins_config: dict[str, Any] = {
        "root": "app.plugins",
    }
    if settings.plugins.include:
        plugins_config["include"] = settings.plugins.include
    if settings.plugins.exclude:
        plugins_config["exclude"] = settings.plugins.exclude

    # Determina sessão
    # Kurigram Client: `name` é o session_name (para arquivo) ou session_string
    # Quando usando string session, name=session_string e workdir é ignorado
    # Quando usando arquivo, name=nome_da_sessao e workdir=diretório
    if settings.telegram.string_session:
        logger.info("client_using_string_session")
        client = Client(
            name=settings.telegram.string_session,
            api_id=settings.telegram.api_id,
            api_hash=settings.telegram.api_hash,
            plugins=plugins_config,
            no_updates=False,
        )
    else:
        session_name = "hermes_userbot"
        logger.info("client_using_file_session", name=session_name)
        client = Client(
            name=session_name,
            api_id=settings.telegram.api_id,
            api_hash=settings.telegram.api_hash,
            plugins=plugins_config,
            workdir=str(SESSIONS_DIR),
            no_updates=False,
        )

    logger.info(
        "client_created",
        session_type="string" if settings.telegram.string_session else "file",
        plugins_root=plugins_config.get("root"),
        plugins_include=plugins_config.get("include", "all"),
        plugins_exclude=plugins_config.get("exclude", "none"),
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
