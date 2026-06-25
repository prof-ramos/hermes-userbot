"""Tools de mensagens — enviar, responder e encaminhar."""

from __future__ import annotations

from typing import Any

from app.agent.schemas import ActionOutcome, ProposedAction
from app.bootstrap import get_audit_log, get_rate_limiter
from app.client import get_client
from app.config.settings import settings
from app.types.common import ActionResultStatus
from app.utils.errors import DryRunBlockedError, ReadOnlyBlockedError, handle_telegram_error
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def send_message(
    chat_id: int,
    text: str,
    parse_mode: str | None = None,
    reply_to_message_id: int | None = None,
    disable_notification: bool = False,
) -> ActionOutcome:
    """Envia uma mensagem de texto.

    Respeita rate limiting, modos operacionais e políticas.
    """
    action_id = f"send_{chat_id}"

    # Verifica modo read-only
    if settings.operational.read_only:
        return ActionOutcome(
            action_id=action_id,
            status=ActionResultStatus.READ_ONLY,
            error="Modo read-only ativo — envio bloqueado",
        )

    # Rate limiting
    limiter = get_rate_limiter()
    try:
        await limiter.acquire(chat_id=chat_id)
    except Exception as e:
        return ActionOutcome(
            action_id=action_id,
            status=ActionResultStatus.BLOCKED,
            error=str(e),
        )

    # Verifica modo dry-run
    if settings.operational.dry_run:
        logger.info("send_message_dry_run", chat_id=chat_id, text_len=len(text))
        get_audit_log().log_action("send_message", {"chat_id": chat_id, "dry_run": True}, chat_id=chat_id)
        return ActionOutcome(
            action_id=action_id,
            status=ActionResultStatus.DRY_RUN,
            details={"chat_id": chat_id, "text_preview": text[:50]},
        )

    try:
        client = get_client()
        result = await client.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_to_message_id=reply_to_message_id,
            disable_notification=disable_notification,
        )
        message_id = result.id if result else None

        get_audit_log().log_action(
            "send_message",
            {"chat_id": chat_id, "message_id": message_id},
            chat_id=chat_id,
        )

        return ActionOutcome(
            action_id=action_id,
            status=ActionResultStatus.SUCCESS,
            message_id=message_id,
            details={"chat_id": chat_id},
        )

    except Exception as e:
        error = handle_telegram_error(e)
        logger.error("send_message_error", chat_id=chat_id, error=str(error))
        get_audit_log().log_action("send_message", {"error": str(error)}, chat_id=chat_id, result="error")
        return ActionOutcome(
            action_id=action_id,
            status=ActionResultStatus.ERROR,
            error=str(error),
        )


async def reply(
    chat_id: int,
    message_id: int,
    text: str,
    parse_mode: str | None = None,
) -> ActionOutcome:
    """Responde a uma mensagem específica."""
    return await send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=parse_mode,
        reply_to_message_id=message_id,
    )


async def forward_message(
    chat_id: int,
    from_chat_id: int,
    message_id: int,
    disable_notification: bool = False,
) -> ActionOutcome:
    """Encaminha uma mensagem para outro chat."""
    action_id = f"forward_{from_chat_id}_{message_id}"

    if settings.operational.read_only:
        return ActionOutcome(
            action_id=action_id,
            status=ActionResultStatus.READ_ONLY,
            error="Modo read-only ativo — encaminhamento bloqueado",
        )

    limiter = get_rate_limiter()
    try:
        await limiter.acquire(chat_id=chat_id)
    except Exception as e:
        return ActionOutcome(action_id=action_id, status=ActionResultStatus.BLOCKED, error=str(e))

    if settings.operational.dry_run:
        logger.info("forward_message_dry_run", chat_id=chat_id, from_chat_id=from_chat_id)
        return ActionOutcome(
            action_id=action_id,
            status=ActionResultStatus.DRY_RUN,
            details={"chat_id": chat_id, "from_chat_id": from_chat_id},
        )

    try:
        client = get_client()
        result = await client.forward_messages(
            chat_id=chat_id,
            from_chat_id=from_chat_id,
            message_ids=message_id,
            disable_notification=disable_notification,
        )

        get_audit_log().log_action(
            "forward_message",
            {"chat_id": chat_id, "from_chat_id": from_chat_id},
            chat_id=chat_id,
        )

        return ActionOutcome(
            action_id=action_id,
            status=ActionResultStatus.SUCCESS,
            message_id=message_id,
            details={"chat_id": chat_id, "from_chat_id": from_chat_id},
        )

    except Exception as e:
        error = handle_telegram_error(e)
        logger.error("forward_message_error", error=str(error))
        return ActionOutcome(action_id=action_id, status=ActionResultStatus.ERROR, error=str(error))


async def delete_own_message(chat_id: int, message_id: int) -> ActionOutcome:
    """Deleta uma mensagem própria (não de outros usuários)."""
    action_id = f"delete_{chat_id}_{message_id}"

    if settings.operational.read_only:
        return ActionOutcome(
            action_id=action_id,
            status=ActionResultStatus.READ_ONLY,
            error="Modo read-only ativo — deleção bloqueada",
        )

    if settings.operational.dry_run:
        return ActionOutcome(action_id=action_id, status=ActionResultStatus.DRY_RUN)

    try:
        client = get_client()
        await client.delete_messages(chat_id=chat_id, message_ids=message_id)

        get_audit_log().log_action(
            "delete_message",
            {"chat_id": chat_id, "message_id": message_id},
            chat_id=chat_id,
        )

        return ActionOutcome(
            action_id=action_id,
            status=ActionResultStatus.SUCCESS,
            message_id=message_id,
        )

    except Exception as e:
        error = handle_telegram_error(e)
        logger.error("delete_message_error", error=str(error))
        return ActionOutcome(action_id=action_id, status=ActionResultStatus.ERROR, error=str(error))