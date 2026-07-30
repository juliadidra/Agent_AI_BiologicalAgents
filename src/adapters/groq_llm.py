from typing import Any

from langchain_groq import ChatGroq


class GroqLLM:
    def __init__(self, api_key: str, model: str, tools: list[Any] | None = None):
        chat = ChatGroq(model=model, api_key=api_key)
        self._chat = chat.bind_tools(tools) if tools else chat

    def invoke(self, messages: list[Any]) -> Any:
        return self._chat.invoke(messages)
