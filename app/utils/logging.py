"""Logging estruturado com structlog.

Configura formatadores, processadores e níveis.
Nunca registra dados sensíveis (API hash, session, tokens, senhas).
"""

from __future__ import annotations

import logging
import sys
from datetime import UTC
from pathlib import Path
from typing import Any

import structlog

from app.config.settings import settings

# Campos sensíveis que devem ser mascarados em logs
SENSITIVE_KEYS = frozenset(
    {
        "api_hash",
        "api_id",
        "string_session",
        "phone_number",
        "two_fa_password",
        "internal_api_token",
        "password",
        "token",
        "secret",
        "authorization",
    }
)


def _mask_sensitive(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Mascara valores sensíveis nos logs."""
    for key in event_dict:
        if key.lower() in SENSITIVE_KEYS and event_dict[key] is not None:
            val = str(event_dict[key])
            if len(val) > 4:
                event_dict[key] = val[:2] + "***" + val[-2:]
            else:
                event_dict[key] = "***"
    return event_dict


def _add_timestamp(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Adiciona timestamp ISO formatado."""
    from datetime import datetime

    event_dict["timestamp"] = datetime.now(UTC).isoformat()
    return event_dict


def setup_logging() -> None:
    """Configura structlog com processadores para logging estruturado."""
    log_level = getattr(logging, settings.log.level.upper(), logging.INFO)

    # Garante diretório de logs
    log_path = Path(settings.log.file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Configura logging padrão do Python para capturar logs de bibliotecas
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # File handler
    file_handler = logging.FileHandler(str(log_path), encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter("%(message)s"))
    logging.getLogger().addHandler(file_handler)

    # Configura structlog
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        _add_timestamp,
        _mask_sensitive,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Retorna um logger estruturado."""
    return structlog.get_logger(name)
