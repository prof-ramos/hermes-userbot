"""Bootstrap — inicializa todos os componentes na ordem correta."""

from __future__ import annotations

import sys
from typing import Any

from app.client import create_client, get_client, set_client
from app.config.settings import settings
from app.services.audit_log import AuditLog
from app.services.rate_limiter import RateLimiter
from app.services.session_manager import SessionManager
from app.utils.logging import get_logger, setup_logging

logger = get_logger(__name__)

# Instâncias singleton dos serviços
rate_limiter: RateLimiter | None = None
audit_log: AuditLog | None = None
session_manager: SessionManager | None = None


async def bootstrap() -> dict[str, Any]:
    """Inicializa todos os componentes do sistema.

    Ordem:
    1. Logging estruturado
    2. Rate limiter
    3. Audit log
    4. Session manager
    5. Cliente MTProto
    6. Login

    Retorna dict com status de cada componente.
    """
    global rate_limiter, audit_log, session_manager

    status: dict[str, Any] = {}

    # 1. Logging
    try:
        setup_logging()
        logger.info("bootstrap_logging_ok")
        status["logging"] = "ok"
    except Exception as e:
        print(f"Falha ao inicializar logging: {e}", file=sys.stderr)
        status["logging"] = f"error: {e}"
        return status

    # 2. Rate limiter
    try:
        rate_limiter = RateLimiter(
            per_second=settings.rate_limit.per_second,
            per_minute=settings.rate_limit.per_minute,
            per_hour=settings.rate_limit.per_hour,
            daily_max=settings.rate_limit.daily_max,
            per_chat_minute=settings.rate_limit.per_chat_minute,
        )
        logger.info("bootstrap_rate_limiter_ok")
        status["rate_limiter"] = "ok"
    except Exception as e:
        logger.error("bootstrap_rate_limiter_error", error=str(e))
        status["rate_limiter"] = f"error: {e}"

    # 3. Audit log
    try:
        audit_log = AuditLog()
        logger.info("bootstrap_audit_log_ok")
        status["audit_log"] = "ok"
    except Exception as e:
        logger.error("bootstrap_audit_log_error", error=str(e))
        status["audit_log"] = f"error: {e}"

    # 4. Session manager
    try:
        session_manager = SessionManager()
        logger.info("bootstrap_session_manager_ok")
        status["session_manager"] = "ok"
    except Exception as e:
        logger.error("bootstrap_session_manager_error", error=str(e))
        status["session_manager"] = f"error: {e}"

    # 5. Cliente MTProto
    try:
        client = create_client()
        set_client(client)
        logger.info("bootstrap_client_created_ok")
        status["client"] = "ok"
    except Exception as e:
        logger.error("bootstrap_client_error", error=str(e))
        status["client"] = f"error: {e}"
        return status

    # 6. Login
    try:
        await client.start()
        me = await client.get_me()
        logger.info(
            "bootstrap_login_ok",
            user_id=me.id,
            username=me.username,
            first_name=me.first_name,
        )
        status["login"] = "ok"
    except Exception as e:
        logger.error("bootstrap_login_error", error=str(e))
        status["login"] = f"error: {e}"

    # Registra modos operacionais
    if settings.operational.dry_run:
        logger.warning("bootstrap_dry_run_mode")
    if settings.operational.read_only:
        logger.warning("bootstrap_read_only_mode")

    return status


def get_rate_limiter() -> RateLimiter:
    """Retorna o rate limiter singleton."""
    if rate_limiter is None:
        raise RuntimeError("Rate limiter não inicializado. Chame bootstrap() primeiro.")
    return rate_limiter


def get_audit_log() -> AuditLog:
    """Retorna o audit log singleton."""
    if audit_log is None:
        raise RuntimeError("Audit log não inicializado. Chame bootstrap() primeiro.")
    return audit_log


def get_session_manager() -> SessionManager:
    """Retorna o session manager singleton."""
    if session_manager is None:
        raise RuntimeError("Session manager não inicializado. Chame bootstrap() primeiro.")
    return session_manager


async def shutdown() -> None:
    """Encerramento gracioso de todos os componentes."""
    logger.info("shutdown_starting")

    try:
        client = get_client()
        await client.stop()
        logger.info("shutdown_client_stopped")
    except Exception as e:
        logger.error("shutdown_client_error", error=str(e))

    logger.info("shutdown_complete")
