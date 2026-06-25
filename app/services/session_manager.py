"""Gerenciamento de sessão do cliente MTProto.

Cuida de login interativo, 2FA, rotação de sessão e revogação.
"""

from __future__ import annotations

from pathlib import Path

from app.utils.logging import get_logger

logger = get_logger(__name__)

SESSIONS_DIR = Path(__file__).resolve().parent.parent / "sessions"


class SessionManager:
    """Gerencia a sessão MTProto — criação, validação e rotação."""

    def __init__(self) -> None:
        self._sessions_dir = SESSIONS_DIR
        self._sessions_dir.mkdir(parents=True, exist_ok=True)
        logger.info("session_manager_initialized", dir=str(self._sessions_dir))

    def list_sessions(self) -> list[str]:
        """Lista sessões existentes no diretório de sessões."""
        sessions = []
        for f in self._sessions_dir.glob("*.session"):
            sessions.append(f.stem)
        logger.info("session_list", count=len(sessions))
        return sessions

    def session_exists(self, name: str) -> bool:
        """Verifica se uma sessão existe."""
        return (self._sessions_dir / f"{name}.session").exists()

    def get_session_path(self, name: str = "hermes_userbot") -> str:
        """Retorna o caminho completo de uma sessão."""
        return str(self._sessions_dir / name)

    async def revoke_session(self, name: str = "hermes_userbot") -> bool:
        """Remove uma sessão do disco (rotação).

        ATENÇÃO: Isso não revoga a sessão no servidor Telegram.
        Para revogar completamente, use a função de terminate sessions
        nas configurações do Telegram.
        """
        session_file = self._sessions_dir / f"{name}.session"
        try:
            if session_file.exists():
                session_file.unlink()
                logger.warning("session_revoked_locally", name=name)
                return True
            logger.info("session_not_found", name=name)
            return False
        except Exception as e:
            logger.error("session_revoke_error", name=name, error=str(e))
            return False

    async def export_session_string(self, client: object) -> str | None:
        """Exporta a string session do cliente para backup.

        NUNCA logar ou expor a string session em logs.
        """
        try:
            # Pyrogram/Kurigram exporta sessão via atributo
            if hasattr(client, "export_session_string"):
                session_string = await client.export_session_string()  # type: ignore[attr-defined]
                logger.info("session_string_exported")
                return session_string
            logger.warning("session_export_not_supported")
            return None
        except Exception as e:
            logger.error("session_export_error", error=str(e))
            return None