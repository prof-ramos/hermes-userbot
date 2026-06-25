"""Plugin: eventos de ciclo de vida.

Handler para eventos de conexão, desconexão e mudanças de status.
Registra logs e gerencia reconexão.
"""

from __future__ import annotations

from pyrogram import Client  # type: ignore[import-untyped]
from pyrogram.raw.types import UpdateServiceNotification  # type: ignore[import-untyped]

from app.bootstrap import get_audit_log
from app.utils.logging import get_logger

logger = get_logger(__name__)


@Client.on_raw_update()  # type: ignore[misc]
async def on_raw_update(client: Client, update: object, users: dict, chats: dict) -> None:
    """Handler para updates brutos — usado para detectar eventos de serviço.

    Registra notificações de serviço do Telegram (ex: reconexão, atualização).
    Não processa mensagens normais — isso é feito pelos handlers de mensagem.
    """
    # Apenas loga notificações de serviço importantes
    if isinstance(update, UpdateServiceNotification):
        logger.info(
            "service_notification",
            type_=getattr(update, "type_", "unknown"),
            message=getattr(update, "message", "")[:200] if hasattr(update, "message") else "",
        )


async def on_startup(client: Client) -> None:
    """Callback executado quando o cliente MTProto conecta."""
    me = await client.get_me()
    logger.info(
        "userbot_started",
        user_id=me.id,
        username=me.username,
        first_name=me.first_name,
    )
    get_audit_log().log_action(
        "startup",
        {"user_id": me.id, "username": me.username},
    )


async def on_shutdown(client: Client) -> None:
    """Callback executado quando o cliente MTProto desconecta."""
    logger.info("userbot_shutdown")
    get_audit_log().log_action("shutdown", {"status": "graceful"})


# Registra os callbacks de ciclo de vida
# Esses são chamados pelo Pyrogram/Kurigram automaticamente
# quando o cliente conecta/desconecta.
