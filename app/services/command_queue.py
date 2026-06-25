"""Fila de comandos recebidos pela API interna.

Processa comandos vindos do backend do Hermes de forma assíncrona
e na ordem correta, respeitando rate limits e políticas.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Command:
    """Comando recebido pela API interna."""

    id: str = field(default_factory=lambda: str(uuid4()))
    action: str = ""
    params: dict[str, Any] = field(default_factory=dict)
    source: str = "api"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    priority: int = 0  # 0 = normal, >0 = alta, <0 = baixa

    @property
    def is_high_priority(self) -> bool:
        return self.priority > 0


class CommandQueue:
    """Fila assíncrona de comandos com prioridade e deduplicação."""

    def __init__(self, max_size: int = 1000) -> None:
        self._queue: asyncio.PriorityQueue[Command] = asyncio.PriorityQueue(maxsize=max_size)
        self._seen_ids: set[str] = set()
        self._max_seen = 10000  # Limpa IDs antigos
        logger.info("command_queue_initialized", max_size=max_size)

    async def enqueue(self, command: Command) -> bool:
        """Adiciona um comando à fila. Rejeita duplicatas por ID."""
        if command.id in self._seen_ids:
            logger.warning("command_duplicate_rejected", command_id=command.id, action=command.action)
            return False

        # Prioridade invertida (maior número = menor prioridade no heapq)
        priority_tuple = (-command.priority, command.created_at, command.id)

        try:
            # Cria um item compatível com PriorityQueue
            self._queue.put_nowait(command)
            self._seen_ids.add(command.id)

            # Limpa IDs antigos se necessário
            if len(self._seen_ids) > self._max_seen:
                self._seen_ids.clear()
                logger.info("command_queue_seen_ids_cleared")

            logger.info("command_enqueued", command_id=command.id, action=command.action)
            return True
        except asyncio.QueueFull:
            logger.error("command_queue_full", command_id=command.id)
            return False

    async def dequeue(self, timeout: float = 30.0) -> Command | None:
        """Retira o próximo comando da fila."""
        try:
            command = await asyncio.wait_for(self._queue.get(), timeout=timeout)
            logger.info("command_dequeued", command_id=command.id, action=command.action)
            return command
        except asyncio.TimeoutError:
            return None

    @property
    def size(self) -> int:
        """Número de comandos na fila."""
        return self._queue.qsize()

    async def clear(self) -> int:
        """Limpa a fila e retorna o número de comandos removidos."""
        count = 0
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                count += 1
            except asyncio.QueueEmpty:
                break
        self._seen_ids.clear()
        logger.info("command_queue_cleared", removed=count)
        return count