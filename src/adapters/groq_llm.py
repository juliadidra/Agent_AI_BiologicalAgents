from typing import Any

from langchain_groq import ChatGroq


class GroqLLM:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        tools: list[Any] | None = None,
    ):
        chat = ChatGroq(model=model, api_key=api_key)
        self._runnable = chat.bind_tools(tools) if tools else chat

    def invoke(self, messages: list[Any]) -> Any:
        return self._runnable.invoke(messages)
