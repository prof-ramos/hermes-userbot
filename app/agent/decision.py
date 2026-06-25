"""Decisor do agente — orquestra roteamento, política e execução.

Esta é a camada principal de tomada de decisão. Recebe eventos,
passa pelo router e pela política, e decide a ação final.
"""

from __future__ import annotations

from app.agent.policy import SecurityPolicy
from app.agent.router import EventRouter
from app.agent.schemas import (
    ApprovalRequest,
    DetectedIntent,
    ProposedAction,
    ReceivedEvent,
)
from app.domains.common import ActionIntent
from app.utils.logging import get_logger

logger = get_logger(__name__)


class AgentDecision:
    """Decisor do agente — coordena roteamento, política e execução.

    Fluxo:
    1. Recebe evento normalizado
    2. Passa pelo router para detectar intenção
    3. Passa pela política de segurança
    4. Cria ação proposta
    5. Delega para execução (tools) ou solicita aprovação

    Esta camada NÃO chama LLM diretamente — é mockável para testes.
    A integração futura com LLM substitui o router por um classificador
    mais inteligente, mantendo a mesma interface.
    """

    def __init__(self) -> None:
        self.router = EventRouter()
        self.policy = SecurityPolicy()
        self._pending_approvals: dict[str, ApprovalRequest] = {}
        self._last_bot_response_chat: int | None = None

    async def process_event(self, event: ReceivedEvent) -> ProposedAction | ApprovalRequest | None:
        """Processa um evento do início ao fim.

        Retorna uma ProposedAction, ApprovalRequest ou None (ignorado).
        """
        # 1. Avalia se o evento deve ser processado
        should_process, reason = self.policy.evaluate_event(event)
        if not should_process:
            logger.info("decision_event_blocked", event_id=event.event_id, reason=reason)
            return None

        # 2. Roteia o evento para detectar intenção
        intent: DetectedIntent = self.route(event)

        # 3. Se deve ignorar, retorna None
        if intent.intent == ActionIntent.IGNORE:
            logger.info("decision_event_ignored", event_id=event.event_id)
            return None

        # 4. Verifica proteção contra loops de bots
        if self.policy.check_bot_loop(event, self._last_bot_response_chat):
            logger.warning("decision_bot_loop_blocked", event_id=event.event_id)
            return None

        # 5. Cria ação proposta
        action = ProposedAction(
            event_id=event.event_id,
            intent=intent.intent,
            target_chat_id=event.chat_id,
            target_user_id=event.user_id,
            text=None,  # Será preenchido pela camada de execução
            params=intent.suggested_params,
        )

        # 6. Avalia ação pela política
        can_execute, reason, requires_approval = self.policy.evaluate_action(action)

        if requires_approval:
            # Ação sensível — solicita aprovação humana
            approval = ApprovalRequest(
                action_id=action.action_id,
                event_id=event.event_id,
                intent=action.intent,
                reason=reason,
                target_chat_id=action.target_chat_id,
                target_user_id=action.target_user_id,
            )
            self._pending_approvals[approval.request_id] = approval
            logger.info("decision_needs_approval", action_id=action.action_id, reason=reason)
            return approval

        if not can_execute:
            # Ação bloqueada (dry-run ou read-only)
            if settings.operational.dry_run:
                action.requires_approval = False
                logger.info("decision_dry_run", action_id=action.action_id, reason=reason)
                return action  # Ação será registrada mas não executada
            logger.info("decision_action_blocked", action_id=action.action_id, reason=reason)
            return None

        # 7. Ação aprovada — registra se for resposta a bot
        if event.is_bot and action.target_chat_id:
            self._last_bot_response_chat = action.target_chat_id

        logger.info("decision_action_approved", action_id=action.action_id, intent=action.intent)
        return action

    def route(self, event: ReceivedEvent) -> DetectedIntent:
        """Delega roteamento ao router. Override para testes ou LLM."""
        return self.router.route(event)

    def get_pending_approvals(self) -> list[ApprovalRequest]:
        """Retorna aprovações pendentes."""
        return [a for a in self._pending_approvals.values() if a.status == "pending"]

    def approve_action(self, request_id: str) -> ProposedAction | None:
        """Aprova uma ação pendente."""
        approval = self._pending_approvals.get(request_id)
        if approval and approval.status == "pending":
            approval.status = "approved"
            logger.info("decision_approved", request_id=request_id)
            return ProposedAction(
                event_id=approval.event_id,
                intent=approval.intent,
                target_chat_id=approval.target_chat_id,
                target_user_id=approval.target_user_id,
            )
        return None

    def deny_action(self, request_id: str) -> bool:
        """Nega uma ação pendente."""
        approval = self._pending_approvals.get(request_id)
        if approval and approval.status == "pending":
            approval.status = "denied"
            logger.info("decision_denied", request_id=request_id)
            return True
        return False


# Singleton do decisor
_decision: AgentDecision | None = None


def get_decision() -> AgentDecision:
    """Retorna o decisor singleton."""
    global _decision
    if _decision is None:
        _decision = AgentDecision()
    return _decision


# Import tardio para evitar circular
from app.config.settings import settings  # noqa: E402
