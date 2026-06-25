"""Router de eventos — classifica relevância e encaminha para o agente.

Recebe eventos normalizados dos handlers do Pyrogram e decide
o que fazer com cada um.
"""

from __future__ import annotations

from app.agent.schemas import DetectedIntent, ReceivedEvent
from app.config.settings import settings
from app.types.common import ActionIntent, EventType
from app.utils.logging import get_logger

logger = get_logger(__name__)


class EventRouter:
    """Roteador de eventos — classifica e encaminha.

    Classifica relevância do evento e propõe uma intenção.
    Esta camada NÃO chama LLM — é uma interface limpa para
    futura integração com um modelo de decisão.
    """

    # Palavras-chave que indicam comandos administrativos
    ADMIN_COMMANDS = {"!status", "!health", "!ping", "!mode", "!help"}

    def route(self, event: ReceivedEvent) -> DetectedIntent:
        """Processa um evento e retorna a intenção detectada.

        A lógica atual é baseada em regras. No futuro, pode ser
        substituída por um LLM para classificação mais inteligente.
        """
        # Verifica se é comando administrativo
        if event.text and event.text.strip().lower() in self.ADMIN_COMMANDS:
            return DetectedIntent(
                event_id=event.event_id,
                intent=ActionIntent.COMMAND,
                confidence=0.95,
                reasoning="Comando administrativo detectado",
            )

        # Menção direta — alta prioridade
        if event.is_mention:
            return DetectedIntent(
                event_id=event.event_id,
                intent=ActionIntent.REPLY,
                confidence=0.9,
                reasoning="Menção direta à conta suporte",
                suggested_params={"priority": "high"},
            )

        # Mensagem privada — sempre responder
        if event.event_type == EventType.PRIVATE_MESSAGE:
            # Se é do owner, alta prioridade
            if event.user_id == settings.security.owner_user_id:
                return DetectedIntent(
                    event_id=event.event_id,
                    intent=ActionIntent.REPLY,
                    confidence=0.95,
                    reasoning="Mensagem privada do owner",
                    suggested_params={"priority": "high"},
                )
            return DetectedIntent(
                event_id=event.event_id,
                intent=ActionIntent.REPLY,
                confidence=0.8,
                reasoning="Mensagem privada recebida",
            )

        # Mensagem em grupo — responder apenas se mencionado
        if event.event_type == EventType.GROUP_MESSAGE:
            if event.is_mention:
                return DetectedIntent(
                    event_id=event.event_id,
                    intent=ActionIntent.REPLY,
                    confidence=0.85,
                    reasoning="Menção em grupo",
                )
            return DetectedIntent(
                event_id=event.event_id,
                intent=ActionIntent.IGNORE,
                confidence=0.7,
                reasoning="Mensagem em grupo sem menção — ignorar",
            )

        # Mensagem de bot — pode ser resposta a interação anterior
        if event.event_type == EventType.BOT_MESSAGE:
            return DetectedIntent(
                event_id=event.event_id,
                intent=ActionIntent.INTERACT_BOT,
                confidence=0.7,
                reasoning="Resposta de bot detectada",
            )

        # Novo chat — exigir aprovação
        if event.event_type == EventType.NEW_CHAT:
            return DetectedIntent(
                event_id=event.event_id,
                intent=ActionIntent.NEEDS_APPROVAL,
                confidence=0.9,
                reasoning="Novo chat detectado — requer aprovação",
            )

        # Evento de membro entrando/saindo — ignorar
        if event.event_type in {EventType.MEMBER_JOIN, EventType.MEMBER_LEAVE}:
            return DetectedIntent(
                event_id=event.event_id,
                intent=ActionIntent.IGNORE,
                confidence=0.95,
                reasoning="Evento de membership — não requer ação",
            )

        # Padrão: ignorar
        return DetectedIntent(
            event_id=event.event_id,
            intent=ActionIntent.IGNORE,
            confidence=0.5,
            reasoning="Evento sem regra específica — ignorar por segurança",
        )