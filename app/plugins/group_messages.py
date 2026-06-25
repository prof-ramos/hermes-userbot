"""Plugin: mensagens em grupos.

Handler para mensagens em grupos e supergrupos.
Responde apenas quando a conta suporte é mencionada.
"""

from __future__ import annotations

from pyrogram import Client, filters  # type: ignore[import-untyped]
from pyrogram.types import Message  # type: ignore[import-untyped]

from app.agent.decision import get_decision
from app.agent.schemas import ReceivedEvent
from app.bootstrap import get_audit_log
from app.config.settings import settings
from app.tools.safety import EventDeduplicator, is_allowed_chat, sanitize_text_for_log
from app.types.common import ChatType, EventType
from app.utils.logging import get_logger

logger = get_logger(__name__)

_dedup = EventDeduplicator()


@Client.on_message(filters.group & ~filters.me & ~filters.service)  # type: ignore[misc]
async def handle_group_message(client: Client, message: Message) -> None:
    """Handler para mensagens em grupos.

    Processa apenas menções à conta suporte ou respostas a mensagens
    da conta suporte. Ignora mensagens genéricas de grupo.
    """
    if not message.chat:
        return

    # Deduplicação
    if _dedup.is_duplicate(message.chat.id, message.id):
        return

    # Verifica menção
    is_mention = False
    me = await client.get_me()
    if me:
        # Verifica @username mention
        if message.text and me.username and f"@{me.username}" in message.text:
            is_mention = True
        # Verifica reply à mensagem do bot
        if message.reply_to_message and message.reply_to_message.from_user:
            if message.reply_to_message.from_user.id == me.id:
                is_mention = True

    # Se não é menção e não é reply, ignora silenciosamente
    if not is_mention:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id if message.from_user else 0
    text_preview = sanitize_text_for_log(message.text or "") if message.text else ""

    logger.info(
        "group_message_received",
        chat_id=chat_id,
        user_id=user_id,
        is_mention=is_mention,
        text_preview=text_preview,
    )

    # Verifica se o chat é permitido
    if not is_allowed_chat(chat_id):
        return

    # Determina tipo do chat
    chat_type = ChatType.GROUP
    if message.chat.type:
        chat_type_str = str(message.chat.type).lower()
        if "supergroup" in chat_type_str:
            chat_type = ChatType.SUPERGROUP

    # Normaliza o evento
    event = ReceivedEvent(
        event_type=EventType.GROUP_MESSAGE,
        chat_id=chat_id,
        chat_type=chat_type,
        chat_title=message.chat.title,
        user_id=user_id,
        user_name=message.from_user.first_name if message.from_user else None,
        message_id=message.id,
        text=message.text,
        is_bot=message.from_user.is_bot if message.from_user else False,
        is_mention=is_mention,
        reply_to_message_id=message.reply_to_message_id if message.reply_to_message else None,
    )

    # Processa pelo decisor
    decision = get_decision()
    result = await decision.process_event(event)

    if result is None:
        return

    get_audit_log().log_action(
        "group_message_processed",
        {"event_type": event.event_type, "is_mention": is_mention},
        chat_id=chat_id,
        user_id=user_id,
    )