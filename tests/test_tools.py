"""Testes para as tools — usando client mockado."""

from __future__ import annotations

from unittest.mock import patch

from app.domains.common import ActionResultStatus


class TestSafetyTools:
    """Testes para as ferramentas de segurança."""

    def test_event_deduplicator_first_event(self) -> None:
        """Primeiro evento nunca é duplicado."""
        from app.tools.safety import EventDeduplicator

        dedup = EventDeduplicator()
        assert dedup.is_duplicate(123, 1) is False

    def test_event_deduplicator_duplicate(self) -> None:
        """Evento repetido deve ser detectado."""
        from app.tools.safety import EventDeduplicator

        dedup = EventDeduplicator()
        dedup.is_duplicate(123, 1)  # Primeira vez — não é duplicado
        assert dedup.is_duplicate(123, 1) is True  # Segunda vez — é duplicado

    def test_event_deduplicator_different_chats(self) -> None:
        """Eventos em chats diferentes não são duplicados."""
        from app.tools.safety import EventDeduplicator

        dedup = EventDeduplicator()
        dedup.is_duplicate(123, 1)
        assert dedup.is_duplicate(456, 1) is False

    def test_sanitize_text_for_log(self) -> None:
        """Texto longo deve ser truncado."""
        from app.tools.safety import sanitize_text_for_log

        long_text = "a" * 200
        result = sanitize_text_for_log(long_text, max_length=50)
        assert len(result) == 53  # 50 + "..."
        assert result.endswith("...")

    def test_sanitize_text_short(self) -> None:
        """Texto curto não deve ser truncado."""
        from app.tools.safety import sanitize_text_for_log

        short_text = "hello"
        result = sanitize_text_for_log(short_text)
        assert result == "hello"


class TestAgentSchemas:
    """Testes para os schemas do agente."""

    def test_received_event_creation(self) -> None:
        """ReceivedEvent deve ser criado com valores padrão."""
        from app.agent.schemas import ReceivedEvent
        from app.domains.common import ChatType, EventType

        event = ReceivedEvent(
            event_type=EventType.PRIVATE_MESSAGE,
            chat_id=123,
            chat_type=ChatType.PRIVATE,
            user_id=456,
        )
        assert event.event_type == EventType.PRIVATE_MESSAGE
        assert event.chat_id == 123
        assert event.event_id  # UUID gerado automaticamente

    def test_proposed_action_defaults(self) -> None:
        """ProposedAction deve ter valores padrão corretos."""
        from app.agent.schemas import ProposedAction
        from app.domains.common import ActionIntent

        action = ProposedAction(
            event_id="test",
            intent=ActionIntent.REPLY,
        )
        assert action.requires_approval is False
        assert action.action_id  # UUID gerado

    def test_action_outcome(self) -> None:
        """ActionOutcome deve ser criado corretamente."""
        from app.agent.schemas import ActionOutcome

        outcome = ActionOutcome(
            action_id="test",
            status=ActionResultStatus.SUCCESS,
            message_id=789,
        )
        assert outcome.status == ActionResultStatus.SUCCESS
        assert outcome.message_id == 789


class TestSecurityPolicy:
    """Testes para a política de segurança."""

    def test_blocked_chat(self) -> None:
        """Chats bloqueados devem ser rejeitados."""
        from app.agent.policy import SecurityPolicy
        from app.agent.schemas import ReceivedEvent
        from app.domains.common import ChatType, EventType

        policy = SecurityPolicy()

        with patch("app.agent.policy.settings") as mock_settings:
            mock_settings.security.blocked_chat_ids = [123]
            mock_settings.security.allowed_chat_ids = []

            event = ReceivedEvent(
                event_type=EventType.PRIVATE_MESSAGE,
                chat_id=123,
                chat_type=ChatType.PRIVATE,
                user_id=456,
            )
            can, reason = policy.evaluate_event(event)
            assert can is False
            assert "bloqueio" in reason.lower()

    def test_read_only_blocks_write(self) -> None:
        """Modo read-only deve bloquear ações de escrita."""
        from app.agent.policy import SecurityPolicy
        from app.agent.schemas import ProposedAction
        from app.domains.common import ActionIntent

        policy = SecurityPolicy()

        with patch("app.agent.policy.settings") as mock_settings:
            mock_settings.operational.read_only = True
            mock_settings.operational.dry_run = False

            action = ProposedAction(
                event_id="test",
                intent=ActionIntent.SEND,
                target_chat_id=123,
            )
            can, reason, needs_approval = policy.evaluate_action(action)
            assert can is False
            assert "read-only" in reason.lower()

    def test_dry_run_blocks_write(self) -> None:
        """Modo dry-run deve bloquear execução de escrita."""
        from app.agent.policy import SecurityPolicy
        from app.agent.schemas import ProposedAction
        from app.domains.common import ActionIntent

        policy = SecurityPolicy()

        with patch("app.agent.policy.settings") as mock_settings:
            mock_settings.operational.read_only = False
            mock_settings.operational.dry_run = True

            action = ProposedAction(
                event_id="test",
                intent=ActionIntent.SEND,
                target_chat_id=123,
            )
            can, reason, needs_approval = policy.evaluate_action(action)
            assert can is False
            assert "dry-run" in reason.lower()

    def test_sensitive_action_needs_approval(self) -> None:
        """Ações sensíveis devem exigir aprovação."""
        from app.agent.policy import SecurityPolicy
        from app.agent.schemas import ProposedAction
        from app.domains.common import ActionIntent

        policy = SecurityPolicy()

        with patch("app.agent.policy.settings") as mock_settings:
            mock_settings.operational.read_only = False
            mock_settings.operational.dry_run = False
            mock_settings.security.blocked_chat_ids = []
            mock_settings.security.allowed_chat_ids = []

            action = ProposedAction(
                event_id="test",
                intent=ActionIntent.JOIN,
                target_chat_id=123,
            )
            can, reason, needs_approval = policy.evaluate_action(action)
            assert can is True
            assert needs_approval is True
