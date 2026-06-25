"""Schemas Pydantic para a camada agentic.

Modelos para evento recebido, intenção detectada, ação proposta,
resultado da ação e necessidade de aprovação humana.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from app.types.common import ActionIntent, ActionResultStatus, ChatType, EventType


class ReceivedEvent(BaseModel):
    """Evento recebido do Telegram, normalizado."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: EventType
    chat_id: int
    chat_type: ChatType
    chat_title: str | None = None
    user_id: int
    user_name: str | None = None
    message_id: int | None = None
    text: str | None = None
    is_bot: bool = False
    is_mention: bool = False
    reply_to_message_id: int | None = None
    forward_from_user_id: int | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    raw_data: dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class DetectedIntent(BaseModel):
    """Intenção detectada a partir de um evento."""

    event_id: str
    intent: ActionIntent
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    reasoning: str = ""
    suggested_params: dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class ProposedAction(BaseModel):
    """Ação proposta pelo agente."""

    action_id: str = Field(default_factory=lambda: str(uuid4()))
    event_id: str
    intent: ActionIntent
    target_chat_id: int | None = None
    target_user_id: int | None = None
    text: str | None = None
    params: dict[str, Any] = Field(default_factory=dict)
    requires_approval: bool = False
    approval_reason: str | None = None

    class Config:
        from_attributes = True


class ActionOutcome(BaseModel):
    """Resultado da execução de uma ação."""

    action_id: str
    status: ActionResultStatus
    message_id: int | None = None
    error: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    class Config:
        from_attributes = True


class ApprovalRequest(BaseModel):
    """Solicitação de aprovação humana para uma ação sensível."""

    request_id: str = Field(default_factory=lambda: str(uuid4()))
    action_id: str
    event_id: str
    intent: ActionIntent
    reason: str
    target_chat_id: int | None = None
    target_user_id: int | None = None
    text_preview: str | None = None  # Primeiros N caracteres
    status: Literal["pending", "approved", "denied"] = "pending"

    class Config:
        from_attributes = True