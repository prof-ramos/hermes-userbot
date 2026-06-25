"""Utilitários de tratamento de erros centralizado."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from app.utils.logging import get_logger

logger = get_logger(__name__)


class ErrorCode(StrEnum):
    """Códigos de erro padronizados do userbot."""

    # Erros de autenticação
    AUTH_FAILED = "auth_failed"
    SESSION_EXPIRED = "session_expired"
    TWO_FA_REQUIRED = "2fa_required"

    # Erros de rate limit
    RATE_LIMITED = "rate_limited"
    DAILY_LIMIT_EXCEEDED = "daily_limit_exceeded"
    CHAT_LIMIT_EXCEEDED = "chat_limit_exceeded"

    # Erros de ação
    ACTION_BLOCKED = "action_blocked"
    ACTION_DENIED = "action_denied"
    CHAT_NOT_FOUND = "chat_not_found"
    USER_NOT_FOUND = "user_not_found"
    BOT_NOT_RESPONDING = "bot_not_responding"
    MESSAGE_NOT_FOUND = "message_not_found"

    # Erros de política
    POLICY_VIOLATION = "policy_violation"
    UNAUTHORIZED_CHAT = "unauthorized_chat"
    DRY_RUN_BLOCKED = "dry_run_blocked"
    READ_ONLY_BLOCKED = "read_only_blocked"

    # Erros de sistema
    FLOOD_WAIT = "flood_wait"
    NETWORK_ERROR = "network_error"
    INTERNAL_ERROR = "internal_error"


class HermesUserbotError(Exception):
    """Exceção base do userbot."""

    def __init__(self, code: ErrorCode, message: str, details: dict[str, Any] | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{code.value}] {message}")


class RateLimitError(HermesUserbotError):
    """Erro de rate limit."""

    def __init__(self, message: str, retry_after: int = 0, details: dict[str, Any] | None = None):
        super().__init__(ErrorCode.RATE_LIMITED, message, details)
        self.retry_after = retry_after


class FloodWaitError(HermesUserbotError):
    """Erro de flood wait do Telegram."""

    def __init__(self, retry_after: int):
        super().__init__(
            ErrorCode.FLOOD_WAIT,
            f"Flood wait: aguarde {retry_after} segundos",
            {"retry_after": retry_after},
        )
        self.retry_after = retry_after


class PolicyViolationError(HermesUserbotError):
    """Erro de violação de política de segurança."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(ErrorCode.POLICY_VIOLATION, message, details)


class DryRunBlockedError(HermesUserbotError):
    """Ação bloqueada pelo modo dry-run."""

    def __init__(self, action: str, details: dict[str, Any] | None = None):
        super().__init__(
            ErrorCode.DRY_RUN_BLOCKED,
            f"Ação bloqueada pelo modo dry-run: {action}",
            details,
        )


class ReadOnlyBlockedError(HermesUserbotError):
    """Ação bloqueada pelo modo read-only."""

    def __init__(self, action: str, details: dict[str, Any] | None = None):
        super().__init__(
            ErrorCode.READ_ONLY_BLOCKED,
            f"Ação bloqueada pelo modo read-only: {action}",
            details,
        )


def handle_telegram_error(error: Exception) -> HermesUserbotError:
    """Converte erros do Pyrogram/Kurigram em erros do userbot."""

    error_type = type(error).__name__
    error_str = str(error)

    # Flood wait
    if "FloodWait" in error_type or "Flood" in error_str:
        import re

        match = re.search(r"(\d+)", error_str)
        retry_after = int(match.group(1)) if match else 60
        logger.warning("flood_wait_detected", retry_after=retry_after)
        return FloodWaitError(retry_after=retry_after)

    # Erros de autenticação
    if "AuthKey" in error_type or "Unauthorized" in error_type:
        logger.error("auth_error", error_type=error_type)
        return HermesUserbotError(ErrorCode.AUTH_FAILED, error_str)

    # Erros de chat não encontrado
    if "ChatNotFound" in error_type or "PEER_ID_INVALID" in error_str:
        return HermesUserbotError(ErrorCode.CHAT_NOT_FOUND, error_str)

    # Erros genéricos
    logger.error("telegram_error", error_type=error_type, error=error_str)
    return HermesUserbotError(ErrorCode.INTERNAL_ERROR, error_str)
