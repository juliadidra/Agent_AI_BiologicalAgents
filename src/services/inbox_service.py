import logging
from typing import Any

from src.ports.messaging import MessagingGateway
from src.prompts.default_message import DEFAULT_MESSAGE
from src.services.conversation_service import ConversationService

logger = logging.getLogger(__name__)


class InboxService:
    def __init__(
        self,
        conversation_service: ConversationService,
        messaging: MessagingGateway,
        history_limit: int,
    ):
        self._conversation = conversation_service
        self._messaging = messaging
        self._history_limit = history_limit

    def process_message(self, chat_id: str, body: str) -> dict[str, Any]:
        self._messaging.start_typing(chat_id)
        try:
            history = self._messaging.get_history(chat_id, self._history_limit) or []
            logger.info("History messages: %s", history)

            if self._is_first_interaction(history):
                response = self._messaging.send(chat_id, DEFAULT_MESSAGE)
                return {"message": "Default message sent!", "response": response}

            answer = self._conversation.handle_incoming(chat_id, body, history)
            self._messaging.send(chat_id, answer)
            return {"message": "Message sent!"}
        finally:
            self._messaging.stop_typing(chat_id)

    @staticmethod
    def _is_first_interaction(history: list[dict[str, Any]]) -> bool:
        filtered = [
            m for m in history if m.get("body") and str(m.get("body", "")).strip()
        ]
        assistant_messages = [m for m in filtered if m.get("fromMe") is True]
        return len(assistant_messages) == 0
