"""Tools de interação com bots — enviar comandos e aguardar respostas."""

from __future__ import annotations

import asyncio

from app.agent.schemas import ActionOutcome
from app.bootstrap import get_audit_log, get_rate_limiter
from app.client import get_client
from app.config.settings import settings
from app.types.common import ActionResultStatus
from app.utils.errors import handle_telegram_error
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def send_bot_command(
    bot_chat_id: int | str,
    command: str,
    params: str | None = None,
) -> ActionOutcome:
    """Envia um comando para um bot (/command ou texto).

    Ação sensível — pode exigir aprovação dependendo da política.
    """
    action_id = f"botcmd_{bot_chat_id}_{command}"

    if settings.operational.read_only:
        return ActionOutcome(
            action_id=action_id,
            status=ActionResultStatus.READ_ONLY,
            error="Modo read-only ativo — interação com bot bloqueada",
        )

    limiter = get_rate_limiter()
    try:
        await limiter.acquire(chat_id=int(bot_chat_id) if isinstance(bot_chat_id, int) else None)
    except Exception as e:
        return ActionOutcome(action_id=action_id, status=ActionResultStatus.BLOCKED, error=str(e))

    if settings.operational.dry_run:
        logger.info("send_bot_command_dry_run", bot_chat_id=bot_chat_id, command=command)
        return ActionOutcome(
            action_id=action_id,
            status=ActionResultStatus.DRY_RUN,
            details={"bot_chat_id": bot_chat_id, "command": command},
        )

    try:
        client = get_client()
        # Envia comando — se começa com /, é comando do bot
        text = f"/{command}" if not command.startswith("/") else command
        if params:
            text = f"{text} {params}"

        result = await client.send_message(chat_id=bot_chat_id, text=text)

        get_audit_log().log_action(
            "send_bot_command",
            {"bot_chat_id": bot_chat_id, "command": command},
            chat_id=int(bot_chat_id) if isinstance(bot_chat_id, int) else None,
        )

        return ActionOutcome(
            action_id=action_id,
            status=ActionResultStatus.SUCCESS,
            message_id=result.id if result else None,
            details={"bot_chat_id": bot_chat_id, "command": command},
        )

    except Exception as e:
        error = handle_telegram_error(e)
        logger.error("send_bot_command_error", bot_chat_id=bot_chat_id, error=str(error))
        return ActionOutcome(action_id=action_id, status=ActionResultStatus.ERROR, error=str(error))


async def wait_for_bot_response(
    bot_chat_id: int,
    timeout: float = 30.0,
    max_messages: int = 1,
) -> ActionOutcome:
    """Aguarda resposta de um bot após interação.

    Escuta novas mensagens no chat do bot por um tempo limitado.
    Proteção contra loops: máximo de mensagens e timeout.
    """
    action_id = f"botwait_{bot_chat_id}"
    collected_messages: list[dict] = []

    try:
        client = get_client()

        # Cria um evento para sinalizar quando a resposta chegar
        response_received = asyncio.Event()

        async def on_message(_, message):
            if message.chat and message.chat.id == bot_chat_id:
                collected_messages.append({
                    "id": message.id,
                    "text": message.text,
                    "date": str(message.date) if message.date else None,
                })
                if len(collected_messages) >= max_messages:
                    response_received.set()

        # Registra handler temporário
        client.add_handler(on_message, group=100)  # type: ignore[arg-type]

        try:
            await asyncio.wait_for(response_received.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.info("bot_response_timeout", bot_chat_id=bot_chat_id, timeout=timeout)

        # Remove handler temporário
        client.remove_handler(on_message, group=100)  # type: ignore[arg-type]

        return ActionOutcome(
            action_id=action_id,
            status=ActionResultStatus.SUCCESS if collected_messages else ActionResultStatus.PARTIAL,
            details={
                "bot_chat_id": bot_chat_id,
                "messages": collected_messages,
                "count": len(collected_messages),
            },
        )

    except Exception as e:
        error = handle_telegram_error(e)
        logger.error("wait_for_bot_response_error", bot_chat_id=bot_chat_id, error=str(error))
        return ActionOutcome(action_id=action_id, status=ActionResultStatus.ERROR, error=str(error))


async def interact_with_bot(
    bot_chat_id: int | str,
    command: str,
    params: str | None = None,
    wait_timeout: float = 30.0,
) -> ActionOutcome:
    """Envia comando a um bot e aguarda a resposta completa.

    Combina send_bot_command + wait_for_bot_response.
    """
    # Envia o comando
    send_result = await send_bot_command(bot_chat_id, command, params)
    if send_result.status != ActionResultStatus.SUCCESS:
        return send_result

    # Aguarda a resposta
    return await wait_for_bot_response(
        bot_chat_id=int(bot_chat_id) if isinstance(bot_chat_id, int) else 0,
        timeout=wait_timeout,
    )