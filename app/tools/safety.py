"""Tools de segurança — verificações e deduplicação."""

from __future__ import annotations

import hashlib
import time
from collections import OrderedDict
from typing import Any

from app.config.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class EventDeduplicator:
    """Deduplicação básica de eventos para evitar processamento duplicado.

    Usa LRU cache com TTL para rastrear IDs de eventos recentes.
    """

    def __init__(self, max_size: int = 10000, ttl_seconds: int = 300) -> None:
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._seen: OrderedDict[str, float] = OrderedDict()

    def _event_key(self, chat_id: int, message_id: int) -> str:
        """Gera chave única para o evento."""
        raw = f"{chat_id}:{message_id}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def is_duplicate(self, chat_id: int, message_id: int) -> bool:
        """Verifica se o evento já foi processado."""
        key = self._event_key(chat_id, message_id)
        now = time.monotonic()

        # Remove entradas expiradas
        expired = [k for k, t in self._seen.items() if now - t > self._ttl]
        for k in expired:
            del self._seen[k]

        if key in self._seen:
            logger.debug("event_deduplicated", chat_id=chat_id, message_id=message_id)
            return True

        # Registra o evento
        self._seen[key] = now
        if len(self._seen) > self._max_size:
            self._seen.popitem(last=False)  # Remove o mais antigo

        return False


def is_allowed_chat(chat_id: int) -> bool:
    """Verifica se o chat está permitido para interação."""
    if chat_id in settings.security.blocked_chat_ids:
        logger.info("chat_blocked", chat_id=chat_id)
        return False

    if settings.security.allowed_chat_ids:
        if chat_id not in settings.security.allowed_chat_ids:
            logger.info("chat_not_in_allowlist", chat_id=chat_id)
            return False

    return True


def is_owner(user_id: int) -> bool:
    """Verifica se o usuário é o dono (conta de controle)."""
    if settings.security.owner_user_id is None:
        return False
    return user_id == settings.security.owner_user_id


def sanitize_text_for_log(text: str, max_length: int = 100) -> str:
    """Sanitiza texto para logs — trunca e remove dados sensíveis."""
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text