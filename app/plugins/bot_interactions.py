"""Plugin: interações com bots.

Handler para mensagens vindas de bots do Telegram.
Processa respostas de bots e permite interação controlada.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pyrogram import Client, filters  # type: ignore[import-untyped]

from app.agent.decision import get_decision
from app.agent.schemas import ReceivedEvent
from app.bootstrap import get_audit_log
from app.domains.common import ChatType, EventType
from app.tools.safety import EventDeduplicator, is_allowed_chat, sanitize_text_for_log
from app.utils.logging import get_logger

if TYPE_CHECKING:
    from pyrogram.types import Message

logger = get_logger(__name__)

_dedup = EventDeduplicator()


@Client.on_message(filters.bot & ~filters.service)  # type: ignore[misc]
async def handle_bot_message(client: Client, message: Message) -> None:
    """Handler para mensagens de bots.

    Processa respostas de bots em chats privados e grupos.
    Inclui proteção contra loops de resposta automática.
    """
    if not message.chat:
        return

    # Deduplicação
    if _dedup.is_duplicate(message.chat.id, message.id):
        return

    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else 0
    text_preview = sanitize_text_for_log(message.text or "") if message.text else ""

    logger.info(
        "bot_message_received",
        chat_id=chat_id,
        bot_id=user_id,
        text_preview=text_preview,
    )

    # Verifica se o chat é permitido
    if not is_allowed_chat(chat_id):
        return

    # Determina tipo do chat
    chat_type = ChatType.PRIVATE
    if message.chat.type:
        chat_type_str = str(message.chat.type).lower()
        if "group" in chat_type_str:
            chat_type = ChatType.GROUP
        elif "supergroup" in chat_type_str:
            chat_type = ChatType.SUPERGROUP

    # Normaliza o evento
    event = ReceivedEvent(
        event_type=EventType.BOT_MESSAGE,
        chat_id=chat_id,
        chat_type=chat_type,
        chat_title=message.chat.title,
        user_id=user_id,
        user_name=message.from_user.first_name if message.from_user else None,
        message_id=message.id,
        text=message.text,
        is_bot=True,
        is_mention=False,
        reply_to_message_id=message.reply_to_message_id if message.reply_to_message else None,
    )

    # Processa pelo decisor
    decision = get_decision()
    result = await decision.process_event(event)

    if result is None:
        return

    # Registra no audit log
    get_audit_log().log_action(
        "bot_message_processed",
        {"bot_id": user_id, "chat_id": chat_id},
        chat_id=chat_id,
        user_id=user_id,
    )

    logger.info("bot_message_action_decided", chat_id=chat_id, bot_id=user_id)
