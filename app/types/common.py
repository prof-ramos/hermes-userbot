"""Tipos comuns compartilhados entre módulos."""

from __future__ import annotations

from enum import Enum
from typing import Any


class ActionResultStatus(str, Enum):
    """Status de resultado de uma ação."""

    SUCCESS = "success"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    ERROR = "error"
    DRY_RUN = "dry_run"
    READ_ONLY = "read_only"


class ChatType(str, Enum):
    """Tipos de chat do Telegram."""

    PRIVATE = "private"
    GROUP = "group"
    SUPERGROUP = "supergroup"
    CHANNEL = "channel"


class EventType(str, Enum):
    """Tipos de evento processados pelo agente."""

    PRIVATE_MESSAGE = "private_message"
    GROUP_MESSAGE = "group_message"
    BOT_MESSAGE = "bot_message"
    MENTION = "mention"
    NEW_CHAT = "new_chat"
    MEMBER_JOIN = "member_join"
    MEMBER_LEAVE = "member_leave"
    COMMAND = "command"


class ActionIntent(str, Enum):
    """Intenções de ação do agente."""

    REPLY = "reply"
    SEND = "send"
    FORWARD = "forward"
    JOIN = "join"
    LEAVE = "leave"
    INTERACT_BOT = "interact_bot"
    READ = "read"
    DELETE = "delete"
    IGNORE = "ignore"
    NEEDS_APPROVAL = "needs_approval"