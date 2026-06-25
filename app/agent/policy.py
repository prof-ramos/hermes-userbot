"""Política de segurança — decide se ações são permitidas ou bloqueadas.

Verifica listas de permissão/bloqueio, modos operacionais,
e regras de proteção contra loops e abuso.
"""

from __future__ import annotations

from app.agent.schemas import DetectedIntent, ProposedAction, ReceivedEvent
from app.config.settings import settings
from app.types.common import ActionIntent, ChatType, EventType
from app.utils.logging import get_logger

logger = get_logger(__name__)


class SecurityPolicy:
    """Política de segurança para aprovação/bloqueio de ações.

    Regras:
    - Modo read-only bloqueia todas as ações de escrita
    - Modo dry-run permite tudo mas não executa
    - Lista de bloqueio impede ações em chats bloqueados
    - Lista de permissão (se configurada) restringe a chats permitidos
    - Ações sensíveis (join, leave, interagir com bots) exigem aprovação
    - Proteção contra loops (resposta a bots)
    - Proteção contra resposta automática infinita entre bots
    """

    # Ações que sempre exigem aprovação humana
    SENSITIVE_ACTIONS: set[ActionIntent] = {
        ActionIntent.JOIN,
        ActionIntent.LEAVE,
        ActionIntent.INTERACT_BOT,
        ActionIntent.DELETE,
    }

    # Ações de escrita bloqueadas em modo read-only
    WRITE_ACTIONS: set[ActionIntent] = {
        ActionIntent.REPLY,
        ActionIntent.SEND,
        ActionIntent.FORWARD,
        ActionIntent.JOIN,
        ActionIntent.LEAVE,
        ActionIntent.INTERACT_BOT,
        ActionIntent.DELETE,
    }

    def evaluate_event(self, event: ReceivedEvent) -> tuple[bool, str]:
        """Avalia se um evento deve ser processado.

        Retorna (deve_processar, motivo).
        """
        # Verifica chat bloqueado
        if event.chat_id in settings.security.blocked_chat_ids:
            reason = f"Chat {event.chat_id} está na lista de bloqueio"
            logger.info("policy_event_blocked_chat", chat_id=event.chat_id, reason=reason)
            return False, reason

        # Verifica lista de permissão (se configurada)
        if settings.security.allowed_chat_ids:
            if event.chat_id not in settings.security.allowed_chat_ids:
                reason = f"Chat {event.chat_id} não está na lista de permissão"
                logger.info("policy_event_not_allowed_chat", chat_id=event.chat_id, reason=reason)
                return False, reason

        # Proteção contra resposta a bots (exceto interação explícita com bots)
        if event.is_bot and event.event_type not in {EventType.BOT_MESSAGE, EventType.COMMAND}:
            # Apenas responde a bots se a intenção for interagir com bots
            pass  # Permitido, mas será verificado na avaliação de ação

        return True, ""

    def evaluate_action(self, action: ProposedAction) -> tuple[bool, str, bool]:
        """Avalia se uma ação pode ser executada.

        Retorna (pode_executar, motivo, requer_aprovacao).
        """
        # Modo read-only bloqueia todas as ações de escrita
        if settings.operational.read_only and action.intent in self.WRITE_ACTIONS:
            reason = f"Ação {action.intent.value} bloqueada pelo modo read-only"
            logger.info("policy_action_read_only_blocked", action=action.intent.value)
            return False, reason, False

        # Modo dry-run permite tudo mas marca como não executável
        if settings.operational.dry_run and action.intent in self.WRITE_ACTIONS:
            reason = f"Ação {action.intent.value} registrada mas não executada (dry-run)"
            logger.info("policy_action_dry_run", action=action.intent.value)
            return False, reason, False  # Não executa, mas não é erro

        # Verifica chat bloqueado
        target_chat = action.target_chat_id
        if target_chat and target_chat in settings.security.blocked_chat_ids:
            reason = f"Chat alvo {target_chat} está na lista de bloqueio"
            logger.info("policy_action_blocked_chat", chat_id=target_chat)
            return False, reason, False

        # Verifica lista de permissão
        if target_chat and settings.security.allowed_chat_ids:
            if target_chat not in settings.security.allowed_chat_ids:
                reason = f"Chat alvo {target_chat} não está na lista de permissão"
                logger.info("policy_action_not_allowed_chat", chat_id=target_chat)
                return False, reason, False

        # Ações sensíveis exigem aprovação
        if action.intent in self.SENSITIVE_ACTIONS:
            reason = f"Ação {action.intent.value} exige aprovação humana"
            logger.info("policy_action_needs_approval", action=action.intent.value)
            return True, reason, True

        return True, "", False

    def check_bot_loop(self, event: ReceivedEvent, last_bot_response_chat: int | None = None) -> bool:
        """Verifica se uma resposta a um bot pode criar um loop infinito.

        Retorna True se houver risco de loop (ação deve ser bloqueada).
        """
        # Se o evento é de um bot e o último destinatário de resposta
        # do nosso bot é o mesmo chat, há risco de loop
        if event.is_bot and event.chat_id == last_bot_response_chat:
            logger.warning("policy_bot_loop_detected", chat_id=event.chat_id)
            return True
        return False