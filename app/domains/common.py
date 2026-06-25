"""Tipos comuns compartilhados entre módulos."""

from __future__ import annotations

from enum import StrEnum


class ActionResultStatus(StrEnum):
    """Status de resultado de uma ação."""

    SUCCESS = "success"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    ERROR = "error"
    DRY_RUN = "dry_run"
    READ_ONLY = "read_only"


class ChatType(StrEnum):
    """Tipos de chat do Telegram."""

    PRIVATE = "private"
    GROUP = "group"
    SUPERGROUP = "supergroup"
    CHANNEL = "channel"


class EventType(StrEnum):
    """Tipos de evento processados pelo agente."""

    PRIVATE_MESSAGE = "private_message"
    GROUP_MESSAGE = "group_message"
    BOT_MESSAGE = "bot_message"
    MENTION = "mention"
    NEW_CHAT = "new_chat"
    MEMBER_JOIN = "member_join"
    MEMBER_LEAVE = "member_leave"
    COMMAND = "command"


class ActionIntent(StrEnum):
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
