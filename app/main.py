"""Ponto de entrada principal do hermes-userbot.

Inicia o cliente MTProto e a API interna de controle.
Usa asyncio.run() com encerramento gracioso via sinais.
"""

from __future__ import annotations

import asyncio
import contextlib
import signal
import sys

from app.bootstrap import bootstrap, shutdown
from app.config.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def main() -> None:
    """Função principal — orquestra inicialização e execução."""

    logger.info("main_starting", version="0.1.0")

    # Bootstrap de todos os componentes
    status = await bootstrap()

    # Verifica se inicialização crítica falhou
    critical_components = ["logging", "client", "login"]
    for component in critical_components:
        if status.get(component, "").startswith("error"):
            logger.error("main_bootstrap_critical_failure", component=component, status=status)
            sys.exit(1)

    logger.info("main_bootstrap_complete", status=status)

    # Inicia a API interna em paralelo com o cliente MTProto
    from app.api.server import create_api_server

    api_task = asyncio.create_task(
        create_api_server(
            host=settings.api.host,
            port=settings.api.port,
        )
    )

    logger.info("main_api_started", host=settings.api.host, port=settings.api.port)

    # Mantém rodando até receber sinal de encerramento
    stop_event = asyncio.Event()

    def _signal_handler(signum: int, frame: object) -> None:
        logger.info("main_signal_received", signal=signum)
        stop_event.set()

    # Registra handlers de sinal para encerramento gracioso
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            asyncio.get_event_loop().add_signal_handler(sig, lambda s=sig: stop_event.set())
        except NotImplementedError:
            # Windows não suporta add_signal_handler no loop
            signal.signal(sig, _signal_handler)

    logger.info(
        "main_running",
        modes={
            "dry_run": settings.operational.dry_run,
            "read_only": settings.operational.read_only,
        },
    )

    try:
        await stop_event.wait()
    except KeyboardInterrupt:
        logger.info("main_keyboard_interrupt")
    finally:
        logger.info("main_shutting_down")
        api_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await api_task
        await shutdown()


def run() -> None:
    """Entry point para execução via python -m app.main."""
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())


if __name__ == "__main__":
    run()
