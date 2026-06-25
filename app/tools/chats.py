"""Tools de chats — entrar, sair, obter informações."""

from __future__ import annotations

from app.agent.schemas import ActionOutcome
from app.bootstrap import get_audit_log, get_rate_limiter
from app.client import get_client
from app.config.settings import settings
from app.domains.common import ActionResultStatus
from app.utils.errors import handle_telegram_error
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def join_chat(chat_id: int | str) -> ActionOutcome:
    """Entra em um grupo ou canal. Ação sensível — exige aprovação."""
    action_id = f"join_{chat_id}"

    if settings.operational.read_only:
        return ActionOutcome(
            action_id=action_id,
            status=ActionResultStatus.READ_ONLY,
            error="Modo read-only ativo — entrar em chat bloqueado",
        )

    limiter = get_rate_limiter()
    try:
        await limiter.acquire()
    except Exception as e:
        return ActionOutcome(action_id=action_id, status=ActionResultStatus.BLOCKED, error=str(e))

    if settings.operational.dry_run:
        logger.info("join_chat_dry_run", chat_id=chat_id)
        return ActionOutcome(
            action_id=action_id,
            status=ActionResultStatus.DRY_RUN,
            details={"chat_id": chat_id},
        )

    try:
        client = get_client()
        result = await client.join_chat(chat_id)

        get_audit_log().log_action(
            "join_chat",
            {"chat_id": chat_id},
            chat_id=int(chat_id) if isinstance(chat_id, int) else None,
        )

        return ActionOutcome(
            action_id=action_id,
            status=ActionResultStatus.SUCCESS,
            details={"chat_id": chat_id, "result": str(result)},
        )

    except Exception as e:
        error = handle_telegram_error(e)
        logger.error("join_chat_error", chat_id=chat_id, error=str(error))
        return ActionOutcome(action_id=action_id, status=ActionResultStatus.ERROR, error=str(error))


async def leave_chat(chat_id: int | str) -> ActionOutcome:
    """Sai de um grupo ou canal. Ação sensível — exige aprovação."""
    action_id = f"leave_{chat_id}"

    if settings.operational.read_only:
        return ActionOutcome(
            action_id=action_id,
            status=ActionResultStatus.READ_ONLY,
            error="Modo read-only ativo — sair de chat bloqueado",
        )

    if settings.operational.dry_run:
        logger.info("leave_chat_dry_run", chat_id=chat_id)
        return ActionOutcome(
            action_id=action_id,
            status=ActionResultStatus.DRY_RUN,
            details={"chat_id": chat_id},
        )

    try:
        client = get_client()
        await client.leave_chat(chat_id)

        get_audit_log().log_action(
            "leave_chat",
            {"chat_id": chat_id},
            chat_id=int(chat_id) if isinstance(chat_id, int) else None,
        )

        return ActionOutcome(
            action_id=action_id,
            status=ActionResultStatus.SUCCESS,
            details={"chat_id": chat_id},
        )

    except Exception as e:
        error = handle_telegram_error(e)
        logger.error("leave_chat_error", chat_id=chat_id, error=str(error))
        return ActionOutcome(action_id=action_id, status=ActionResultStatus.ERROR, error=str(error))


async def get_chat_info(chat_id: int | str) -> ActionOutcome:
    """Obtém informações sobre um chat. Ação de leitura — sempre permitida."""
    action_id = f"info_{chat_id}"

    try:
        client = get_client()
        chat = await client.get_chat(chat_id)

        info = {
            "id": chat.id,
            "type": str(chat.type) if chat.type else None,
            "title": chat.title,
            "username": chat.username,
            "members_count": getattr(chat, "members_count", None),
        }

        return ActionOutcome(
            action_id=action_id,
            status=ActionResultStatus.SUCCESS,
            details=info,
        )

    except Exception as e:
        error = handle_telegram_error(e)
        logger.error("get_chat_info_error", chat_id=chat_id, error=str(error))
        return ActionOutcome(action_id=action_id, status=ActionResultStatus.ERROR, error=str(error))
