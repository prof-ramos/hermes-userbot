"""Schemas Pydantic para a API interna."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SendMessageRequest(BaseModel):
    """Request para enviar mensagem."""

    chat_id: int = Field(..., description="ID do chat de destino")
    text: str = Field(..., max_length=4096, description="Texto da mensagem")
    parse_mode: str | None = Field(default=None, description="Modo de parsing (Markdown, HTML)")
    reply_to_message_id: int | None = Field(
        default=None, description="ID da mensagem para responder"
    )


class SendMessageResponse(BaseModel):
    """Response de envio de mensagem."""

    status: str
    message_id: int | None = None
    error: str | None = None
    details: dict[str, Any] | None = None


class JoinLeaveChatRequest(BaseModel):
    """Request para entrar/sair de um chat."""

    chat_id: int | str = Field(..., description="ID ou username do chat")


class JoinLeaveChatResponse(BaseModel):
    """Response de entrar/sair de chat."""

    status: str
    error: str | None = None
    details: dict[str, Any] | None = None


class InteractBotRequest(BaseModel):
    """Request para interagir com um bot."""

    bot_chat_id: int = Field(..., description="ID do chat com o bot")
    command: str = Field(..., description="Comando a enviar")
    params: str | None = Field(default=None, description="Parâmetros do comando")
    wait_response: bool = Field(default=True, description="Se deve aguardar resposta")
    wait_timeout: float = Field(default=30.0, description="Timeout para aguardar resposta (s)")


class InteractBotResponse(BaseModel):
    """Response de interação com bot."""

    status: str
    message_id: int | None = None
    bot_response: list[dict[str, Any]] | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    """Response do healthcheck."""

    status: str = "ok"
    version: str = "0.1.0"
    mode: dict[str, bool] | None = None
    uptime_seconds: float | None = None


class StatusResponse(BaseModel):
    """Response do status."""

    status: str
    user_id: int | None = None
    username: str | None = None
    modes: dict[str, bool] | None = None
    rate_limiter: dict[str, Any] | None = None
    pending_approvals: int = 0
