from typing import Any


class FakeLLMResponse:
    def __init__(self, content: str = "", tool_calls: list[dict] | None = None):
        self.content = content
        self.tool_calls = tool_calls or []


class FakeLLM:
    def __init__(self, response: FakeLLMResponse | None = None):
        self.response = response or FakeLLMResponse(content="resposta fake")
        self.calls: list[list[Any]] = []

    def invoke(self, messages: list[Any]) -> FakeLLMResponse:
        self.calls.append(messages)
        return self.response


class FakeGuardrail:
    def __init__(self, safe: bool = True):
        self.safe = safe
        self.calls: list[str] = []

    def is_safe(self, text: str) -> bool:
        self.calls.append(text)
        return self.safe


class FakeSummarizer:
    def __init__(self, summary: str = "histórico resumido"):
        self.summary = summary
        self.calls: list[list[dict]] = []

    def summarize(self, messages: list[dict]) -> str:
        self.calls.append(messages)
        return self.summary


class FakeRag:
    def __init__(self, docs: list[str] | None = None):
        self.docs = docs or ["doc-1", "doc-2"]
        self.calls: list[str] = []

    def search(self, query: str) -> list[str]:
        self.calls.append(query)
        return self.docs


class FakeTool:
    def __init__(self, name: str, return_value: Any = "tool-ok"):
        self.name = name
        self.return_value = return_value
        self.invoked_with: list[Any] = []

    def invoke(self, args: Any) -> Any:
        self.invoked_with.append(args)
        return self.return_value
