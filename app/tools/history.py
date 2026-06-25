"""Tools de histórico — consultar mensagens anteriores."""

from __future__ import annotations

from app.agent.schemas import ActionOutcome
from app.client import get_client
from app.domains.common import ActionResultStatus
from app.utils.errors import handle_telegram_error
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def get_chat_history(
    chat_id: int | str,
    limit: int = 20,
    offset: int = 0,
) -> ActionOutcome:
    """Consulta histórico de mensagens de um chat.

    Ação de leitura — sempre permitida, mesmo em modo read-only.
    """
    action_id = f"history_{chat_id}_{offset}_{limit}"

    try:
        client = get_client()
        messages = []

        async for message in client.get_chat_history(chat_id, limit=limit, offset=offset):
            msg_data = {
                "id": message.id,
                "date": str(message.date) if message.date else None,
                "text": message.text[:200] if message.text else None,  # Limita preview
                "from_user": {
                    "id": message.from_user.id if message.from_user else None,
                    "name": message.from_user.first_name if message.from_user else None,
                }
                if message.from_user
                else None,
                "reply_to_message_id": message.reply_to_message_id,
            }
            messages.append(msg_data)

        return ActionOutcome(
            action_id=action_id,
            status=ActionResultStatus.SUCCESS,
            details={
                "chat_id": chat_id,
                "count": len(messages),
                "messages": messages,
            },
        )

    except Exception as e:
        error = handle_telegram_error(e)
        logger.error("get_chat_history_error", chat_id=chat_id, error=str(error))
        return ActionOutcome(action_id=action_id, status=ActionResultStatus.ERROR, error=str(error))


async def mark_read(chat_id: int | str, message_id: int | None = None) -> ActionOutcome:
    """Marca mensagens como lidas. Ação de leitura — sempre permitida."""
    action_id = f"markread_{chat_id}"

    try:
        client = get_client()
        await client.read_chat_history(chat_id, max_id=message_id or 0)

        return ActionOutcome(
            action_id=action_id,
            status=ActionResultStatus.SUCCESS,
            details={"chat_id": chat_id, "message_id": message_id},
        )

    except Exception as e:
        error = handle_telegram_error(e)
        logger.error("mark_read_error", chat_id=chat_id, error=str(error))
        return ActionOutcome(action_id=action_id, status=ActionResultStatus.ERROR, error=str(error))
