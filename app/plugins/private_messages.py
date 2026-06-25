"""Plugin: mensagens privadas.

Handler para mensagens recebidas em chats privados.
Normaliza o evento, passa pelo router do agente e executa a ação.
"""

from __future__ import annotations

from pyrogram import Client, filters  # type: ignore[import-untyped]
from pyrogram.types import Message  # type: ignore[import-untyped]

from app.agent.decision import get_decision
from app.agent.schemas import ReceivedEvent
from app.bootstrap import get_audit_log
from app.config.settings import settings
from app.tools.messaging import reply
from app.tools.safety import EventDeduplicator, is_allowed_chat, is_owner, sanitize_text_for_log
from app.types.common import ChatType, EventType
from app.utils.logging import get_logger

logger = get_logger(__name__)

# Deduplicador de eventos
_dedup = EventDeduplicator()


@Client.on_message(filters.private & ~filters.me & ~filters.service)  # type: ignore[misc]
async def handle_private_message(client: Client, message: Message) -> None:
    """Handler para mensagens privadas.

    Filtra mensagens próprias e de serviço. Normaliza o evento,
    passa pelo decisor do agente e executa a ação resultante.
    """
    # Deduplicação
    if message.chat and _dedup.is_duplicate(message.chat.id, message.id):
        return

    # Log seguro (sem conteúdo sensível)
    user_id = message.from_user.id if message.from_user else 0
    text_preview = sanitize_text_for_log(message.text or "") if message.text else ""

    logger.info(
        "private_message_received",
        chat_id=message.chat.id if message.chat else None,
        user_id=user_id,
        text_preview=text_preview,
    )

    # Verifica se o chat é permitido
    chat_id = message.chat.id if message.chat else 0
    if not is_allowed_chat(chat_id):
        logger.info("private_message_chat_not_allowed", chat_id=chat_id)
        return

    # Normaliza o evento
    event = ReceivedEvent(
        event_type=EventType.PRIVATE_MESSAGE,
        chat_id=chat_id,
        chat_type=ChatType.PRIVATE,
        chat_title=None,
        user_id=user_id,
        user_name=message.from_user.first_name if message.from_user else None,
        message_id=message.id,
        text=message.text,
        is_bot=message.from_user.is_bot if message.from_user else False,
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
        "private_message_processed",
        {"event_type": event.event_type, "user_id": user_id},
        chat_id=chat_id,
        user_id=user_id,
    )

    # Se é uma ProposedAction, executa
    from app.agent.schemas import ProposedAction
    if isinstance(result, ProposedAction):
        if result.intent.value == "reply" and result.target_chat_id:
            # MVP: resposta automática simples
            # Em versões futuras, a resposta vem do LLM
            if is_owner(user_id):
                # Owner recebe confirmação de recebimento
                await reply(
                    chat_id=chat_id,
                    message_id=message.id,
                    text="Mensagem recebida. Processando...",
                )
            logger.info("private_message_action_reply", chat_id=chat_id, user_id=user_id)