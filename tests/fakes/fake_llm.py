from typing import Any

from src.services.agent_context import AgentContext


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


class FakeSequenceLLM:
    """Retorna respostas em sequência (para testar o loop agêntico).
    A última resposta é repetida caso o loop invoque mais vezes."""

    def __init__(self, responses: list[FakeLLMResponse]):
        self.responses = responses
        self.calls: list[list[Any]] = []

    def invoke(self, messages: list[Any]) -> FakeLLMResponse:
        self.calls.append(list(messages))
        index = min(len(self.calls) - 1, len(self.responses) - 1)
        return self.responses[index]


class FakeAgent:
    def __init__(self, reply: str = "resposta do agente"):
        self.reply = reply
        self.calls: list[AgentContext] = []

    def handle(self, ctx: AgentContext) -> str:
        self.calls.append(ctx)
        return self.reply


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
