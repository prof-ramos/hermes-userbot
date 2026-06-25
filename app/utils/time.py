"""Utilitários de tempo — delays, jitter, backoff."""

from __future__ import annotations

import asyncio
import random
from typing import Awaitable, TypeVar

from app.utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


async def delay_jitter(base: float, jitter_range: float = 0.3) -> None:
    """Espera base segundos + jitter aleatório para evitar rajadas artificiais.

    Não é ferramenta de evasão — serve para espaçar requisições de forma
    conservadora e reduzir risco operacional.
    """
    jitter = base * jitter_range * (2 * random.random() - 1)
    wait = max(0.1, base + jitter)
    logger.debug("delay_jitter", base=base, actual=round(wait, 3))
    await asyncio.sleep(wait)


async def backoff_retry(
    coro: Awaitable[T],
    max_retries: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
) -> T:
    """Executa corotina com backoff exponencial em caso de erro transitório."""

    from app.utils.errors import FloodWaitError, HermesUserbotError

    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            return await coro
        except FloodWaitError as e:
            # Flood wait: respeitar o tempo indicado pelo Telegram
            wait = min(e.retry_after, max_delay)
            logger.warning("flood_wait_retry", attempt=attempt, wait=wait)
            await asyncio.sleep(wait)
            last_error = e
        except HermesUserbotError as e:
            if e.code in {"rate_limited", "network_error"}:
                delay = min(base_delay * (2 ** attempt), max_delay)
                logger.warning("backoff_retry", attempt=attempt, delay=delay, error=e.code)
                await asyncio.sleep(delay)
                last_error = e
            else:
                raise
        except Exception as e:
            delay = min(base_delay * (2 ** attempt), max_delay)
            logger.warning("backoff_retry_unknown", attempt=attempt, delay=delay, error=str(e))
            await asyncio.sleep(delay)
            last_error = e

    raise last_error  # type: ignore[misc]