"""Rate limiter conservador para ações do Telegram.

Limites conservadores para reduzir risco operacional.
Não é ferramenta de evasão — respeita limites da plataforma.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field

from app.utils.errors import RateLimitError
from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class _Bucket:
    """Bucket de tokens para rate limiting com janela deslizante."""

    timestamps: list[float] = field(default_factory=list)


class RateLimiter:
    """Rate limiter com limites por segundo, minuto, hora, dia e por chat.

    Usa janela deslizante com timestamps para controle granular.
    Todos os limites são conservadores para evitar flood wait.
    """

    def __init__(
        self,
        per_second: int = 1,
        per_minute: int = 20,
        per_hour: int = 300,
        daily_max: int = 5000,
        per_chat_minute: int = 5,
    ):
        self.per_second = per_second
        self.per_minute = per_minute
        self.per_hour = per_hour
        self.daily_max = daily_max
        self.per_chat_minute = per_chat_minute

        # Buckets globais
        self._second_bucket: list[float] = []
        self._minute_bucket: list[float] = []
        self._hour_bucket: list[float] = []
        self._day_bucket: list[float] = []

        # Buckets por chat
        self._chat_buckets: dict[int, list[float]] = defaultdict(list)

        # Contadores diários
        self._daily_count = 0
        self._daily_reset_day: int = 0

    def _now(self) -> float:
        """Timestamp atual (injetável para testes)."""
        return time.monotonic()

    def _prune(self, bucket: list[float], window: float) -> list[float]:
        """Remove timestamps fora da janela."""
        cutoff = self._now() - window
        return [t for t in bucket if t > cutoff]

    def _check_daily_reset(self) -> None:
        """Reseta contador diário se mudou de dia."""
        import datetime
        today = datetime.date.today().toordinal()
        if today != self._daily_reset_day:
            self._daily_count = 0
            self._daily_reset_day = today

    def can_proceed(self, chat_id: int | None = None) -> tuple[bool, str]:
        """Verifica se uma ação pode prosseguir.

        Retorna (pode_proceder, motivo_se_bloqueado).
        """
        now = self._now()

        # Verifica reset diário
        self._check_daily_reset()

        # Limites globais
        self._second_bucket = self._prune(self._second_bucket, 1.0)
        if len(self._second_bucket) >= self.per_second:
            return False, f"Limite por segundo atingido ({self.per_second}/s)"

        self._minute_bucket = self._prune(self._minute_bucket, 60.0)
        if len(self._minute_bucket) >= self.per_minute:
            return False, f"Limite por minuto atingido ({self.per_minute}/min)"

        self._hour_bucket = self._prune(self._hour_bucket, 3600.0)
        if len(self._hour_bucket) >= self.per_hour:
            return False, f"Limite por hora atingido ({self.per_hour}/h)"

        if self._daily_count >= self.daily_max:
            return False, f"Limite diário atingido ({self.daily_max}/dia)"

        # Limite por chat
        if chat_id is not None:
            chat_bucket = self._prune(self._chat_buckets.get(chat_id, []), 60.0)
            if len(chat_bucket) >= self.per_chat_minute:
                return False, f"Limite por chat/minuto atingido ({self.per_chat_minute}/min para chat {chat_id})"

        return True, ""

    def record_action(self, chat_id: int | None = None) -> None:
        """Registra que uma ação foi executada."""
        now = self._now()

        self._second_bucket.append(now)
        self._minute_bucket.append(now)
        self._hour_bucket.append(now)
        self._day_bucket.append(now)
        self._daily_count += 1

        if chat_id is not None:
            self._chat_buckets[chat_id].append(now)

        logger.debug(
            "rate_limiter_action_recorded",
            daily_count=self._daily_count,
            chat_id=chat_id,
        )

    async def acquire(self, chat_id: int | None = None) -> None:
        """Verifica e registra uma ação. Levanta RateLimitError se bloqueado.

        Usa delays pequenos e aleatórios entre verificações para evitar
        rajadas artificiais — isso NÃO é evasão, é boas práticas operacionais.
        """
        import asyncio
        import random

        can, reason = self.can_proceed(chat_id)
        if not can:
            logger.warning("rate_limiter_blocked", reason=reason, chat_id=chat_id)
            raise RateLimitError(reason)

        self.record_action(chat_id)

        # Delay conservador entre ações (0.5-1.5s) — boa prática operacional
        jitter = 0.5 + random.random() * 1.0
        await asyncio.sleep(jitter)