"""Rotas da API interna FastAPI.

Endpoints para o backend do Hermes enviar comandos ao userbot.
Autenticação via token interno no header X-Internal-Token.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, Request

from app.agent.decision import get_decision
from app.api.schemas import (
    HealthResponse,
    InteractBotRequest,
    InteractBotResponse,
    JoinLeaveChatRequest,
    JoinLeaveChatResponse,
    SendMessageRequest,
    SendMessageResponse,
    StatusResponse,
)
from app.bootstrap import get_rate_limiter
from app.config.settings import settings
from app.tools.bots import interact_with_bot, send_bot_command
from app.tools.chats import join_chat, leave_chat
from app.tools.messaging import reply, send_message
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Timestamp de startup
_startup_time = time.monotonic()


async def verify_token(request: Request) -> bool:
    """Verifica o token de autenticação interna."""
    token = request.headers.get("X-Internal-Token", "")
    if not token or token != settings.api.internal_api_token:
        logger.warning("api_unauthorized_access", path=request.url.path)
        raise HTTPException(status_code=401, detail="Token inválido")
    return True


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Healthcheck — não requer autenticação."""
    return HealthResponse(
        status="ok",
        version="0.1.0",
        mode={
            "dry_run": settings.operational.dry_run,
            "read_only": settings.operational.read_only,
        },
    )


@router.get("/status", response_model=StatusResponse)
async def status(_: bool = Depends(verify_token)) -> StatusResponse:
    """Status detalhado do userbot — requer autenticação."""
    from app.client import get_client

    try:
        client = get_client()
        me = await client.get_me()
        user_id = me.id
        username = me.username
    except Exception:
        user_id = None
        username = None

    rate_limiter = get_rate_limiter()

    return StatusResponse(
        status="ok",
        user_id=user_id,
        username=username,
        modes={
            "dry_run": settings.operational.dry_run,
            "read_only": settings.operational.read_only,
        },
        rate_limiter={
            "daily_count": rate_limiter._daily_count,
            "daily_max": settings.rate_limit.daily_max,
        },
        pending_approvals=len(get_decision().get_pending_approvals()),
    )


@router.post("/commands/send-message", response_model=SendMessageResponse)
async def command_send_message(
    req: SendMessageRequest,
    _: bool = Depends(verify_token),
) -> SendMessageResponse:
    """Envia uma mensagem via API interna."""
    from app.bootstrap import get_audit_log

    get_audit_log().log_command(
        "send_message",
        "api",
        {"chat_id": req.chat_id, "text_len": len(req.text)},
    )

    result = await send_message(
        chat_id=req.chat_id,
        text=req.text,
        parse_mode=req.parse_mode,
        reply_to_message_id=req.reply_to_message_id,
    )

    return SendMessageResponse(
        status=result.status.value,
        message_id=result.message_id,
        error=result.error,
        details=result.details,
    )


@router.post("/commands/reply", response_model=SendMessageResponse)
async def command_reply(
    req: SendMessageRequest,
    _: bool = Depends(verify_token),
) -> SendMessageResponse:
    """Responde a uma mensagem via API interna."""
    if not req.reply_to_message_id:
        raise HTTPException(status_code=400, detail="reply_to_message_id é obrigatório para reply")

    from app.bootstrap import get_audit_log

    get_audit_log().log_command(
        "reply",
        "api",
        {"chat_id": req.chat_id, "message_id": req.reply_to_message_id},
    )

    result = await reply(
        chat_id=req.chat_id,
        message_id=req.reply_to_message_id,
        text=req.text,
        parse_mode=req.parse_mode,
    )

    return SendMessageResponse(
        status=result.status.value,
        message_id=result.message_id,
        error=result.error,
    )


@router.post("/commands/join-chat", response_model=JoinLeaveChatResponse)
async def command_join_chat(
    req: JoinLeaveChatRequest,
    _: bool = Depends(verify_token),
) -> JoinLeaveChatResponse:
    """Entra em um chat via API interna."""
    from app.bootstrap import get_audit_log

    get_audit_log().log_command("join_chat", "api", {"chat_id": str(req.chat_id)})

    result = await join_chat(req.chat_id)

    return JoinLeaveChatResponse(
        status=result.status.value,
        error=result.error,
        details=result.details,
    )


@router.post("/commands/leave-chat", response_model=JoinLeaveChatResponse)
async def command_leave_chat(
    req: JoinLeaveChatRequest,
    _: bool = Depends(verify_token),
) -> JoinLeaveChatResponse:
    """Sai de um chat via API interna."""
    from app.bootstrap import get_audit_log

    get_audit_log().log_command("leave_chat", "api", {"chat_id": str(req.chat_id)})

    result = await leave_chat(req.chat_id)

    return JoinLeaveChatResponse(
        status=result.status.value,
        error=result.error,
        details=result.details,
    )


@router.post("/commands/interact-with-bot", response_model=InteractBotResponse)
async def command_interact_with_bot(
    req: InteractBotRequest,
    _: bool = Depends(verify_token),
) -> InteractBotResponse:
    """Interage com um bot via API interna."""
    from app.bootstrap import get_audit_log

    get_audit_log().log_command(
        "interact_with_bot",
        "api",
        {"bot_chat_id": req.bot_chat_id, "command": req.command},
    )

    if req.wait_response:
        result = await interact_with_bot(
            bot_chat_id=req.bot_chat_id,
            command=req.command,
            params=req.params,
            wait_timeout=req.wait_timeout,
        )
        bot_response = result.details.get("messages") if result.details else None
    else:
        result = await send_bot_command(
            bot_chat_id=req.bot_chat_id,
            command=req.command,
            params=req.params,
        )
        bot_response = None

    return InteractBotResponse(
        status=result.status.value,
        message_id=result.message_id,
        bot_response=bot_response,
        error=result.error,
    )
