import logging

from langchain.schema import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

logger = logging.getLogger(__name__)


class GroqGuardrail:
    def __init__(self, api_key: str, model: str, policy: str):
        self._chat = ChatGroq(model=model, api_key=api_key)
        self._policy = policy

    def is_safe(self, text: str) -> bool:
        messages = [
            SystemMessage(content=self._policy),
            HumanMessage(content=text),
        ]
        response = self._chat.invoke(messages)
        content = getattr(response, "content", "")
        if not isinstance(content, str):
            logger.warning("Guardrail returned non-string content: %r", content)
            return True
        return "UNSAFE" not in content.strip().upper()
