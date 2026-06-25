"""Log de auditoria para ações sensíveis do userbot.

Registra decisões do agente, ações executadas, comandos da API
e violações de política. Nunca registra dados sensíveis.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AuditLog:
    """Log de auditoria estruturado — escreve em arquivo JSONL e via structlog."""

    def __init__(self) -> None:
        self._log_dir = Path(settings.log.file).parent
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._audit_file = self._log_dir / "audit.jsonl"
        logger.info("audit_log_initialized", path=str(self._audit_file))

    def _write_entry(self, entry: dict[str, Any]) -> None:
        """Escreve uma entrada no arquivo de auditoria."""
        try:
            line = json.dumps(entry, ensure_ascii=False, default=str) + "\n"
            with open(self._audit_file, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception as e:
            logger.error("audit_log_write_error", error=str(e))

    def log_action(
        self,
        action: str,
        details: dict[str, Any] | None = None,
        chat_id: int | None = None,
        user_id: int | None = None,
        result: str = "success",
    ) -> None:
        """Registra uma ação executada pelo userbot."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "action",
            "action": action,
            "result": result,
            "chat_id": chat_id,
            "user_id": user_id,
            "details": details or {},
        }
        self._write_entry(entry)
        logger.info("audit_action", **entry)

    def log_command(
        self,
        command: str,
        source: str,
        details: dict[str, Any] | None = None,
        result: str = "success",
    ) -> None:
        """Registra um comando recebido pela API interna."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "command",
            "command": command,
            "source": source,
            "result": result,
            "details": details or {},
        }
        self._write_entry(entry)
        logger.info("audit_command", **entry)

    def log_policy(
        self,
        action: str,
        policy_result: str,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Registra uma decisão de política de segurança."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "policy",
            "action": action,
            "policy_result": policy_result,
            "reason": reason,
            "details": details or {},
        }
        self._write_entry(entry)
        logger.info("audit_policy", **entry)

    def log_agent_decision(
        self,
        event_type: str,
        intent: str,
        decision: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Registra uma decisão do agente."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "type": "agent_decision",
            "event_type": event_type,
            "intent": intent,
            "decision": decision,
            "details": details or {},
        }
        self._write_entry(entry)
        logger.info("audit_agent_decision", **entry)