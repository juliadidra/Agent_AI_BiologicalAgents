from typing import Any, Protocol


class LLMResponse(Protocol):
    content: Any
    tool_calls: list[dict[str, Any]]


class LLMProvider(Protocol):
    def invoke(self, messages: list[Any]) -> LLMResponse: ...


class GuardrailProvider(Protocol):
    def is_safe(self, text: str) -> bool: ...
