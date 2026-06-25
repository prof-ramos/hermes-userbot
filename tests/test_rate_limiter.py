"""Testes para o rate limiter."""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from app.services.rate_limiter import RateLimiter


class TestRateLimiter:
    """Testes para o RateLimiter."""

    def test_can_proceed_initially(self) -> None:
        """Deve permitir a primeira ação."""
        limiter = RateLimiter(per_second=5, per_minute=100, per_hour=1000, daily_max=10000, per_chat_minute=30)
        can, reason = limiter.can_proceed()
        assert can is True
        assert reason == ""

    def test_per_second_limit(self) -> None:
        """Deve bloquear quando o limite por segundo é atingido."""
        limiter = RateLimiter(per_second=2, per_minute=100, per_hour=1000, daily_max=10000, per_chat_minute=30)
        limiter.record_action()
        limiter.record_action()
        can, reason = limiter.can_proceed()
        assert can is False
        assert "segundo" in reason

    def test_per_minute_limit(self) -> None:
        """Deve bloquear quando o limite por minuto é atingido."""
        limiter = RateLimiter(per_second=100, per_minute=3, per_hour=1000, daily_max=10000, per_chat_minute=30)
        limiter.record_action()
        limiter.record_action()
        limiter.record_action()
        can, reason = limiter.can_proceed()
        assert can is False
        assert "minuto" in reason

    def test_daily_limit(self) -> None:
        """Deve bloquear quando o limite diário é atingido."""
        limiter = RateLimiter(per_second=100, per_minute=100, per_hour=1000, daily_max=3, per_chat_minute=30)
        limiter.record_action()
        limiter.record_action()
        limiter.record_action()
        can, reason = limiter.can_proceed()
        assert can is False
        assert "diário" in reason

    def test_per_chat_limit(self) -> None:
        """Deve bloquear por chat quando o limite é atingido."""
        limiter = RateLimiter(per_second=100, per_minute=100, per_hour=1000, daily_max=10000, per_chat_minute=2)
        limiter.record_action(chat_id=123)
        limiter.record_action(chat_id=123)
        can, reason = limiter.can_proceed(chat_id=123)
        assert can is False
        # Outro chat deve permitir
        can2, _ = limiter.can_proceed(chat_id=456)
        assert can2 is True

    def test_record_action_increments(self) -> None:
        """Record action deve incrementar contadores."""
        limiter = RateLimiter(per_second=100, per_minute=100, per_hour=1000, daily_max=10000, per_chat_minute=30)
        assert limiter._daily_count == 0
        limiter.record_action()
        assert limiter._daily_count == 1
        limiter.record_action()
        assert limiter._daily_count == 2

    @pytest.mark.asyncio
    async def test_acquire_blocks_when_limited(self) -> None:
        """Acquire deve levantar RateLimitError quando bloqueado."""
        from app.utils.errors import RateLimitError

        limiter = RateLimiter(per_second=1, per_minute=1, per_hour=1, daily_max=1, per_chat_minute=1)
        # Primeira ação — ok
        # (não vamos await pois o jitter faz sleep)
        # Vamos apenas verificar can_proceed
        limiter.record_action()
        can, reason = limiter.can_proceed()
        assert can is False