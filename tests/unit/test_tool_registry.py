from src.services.tool_registry import ToolRegistry


class _FakeProvider:
    def __init__(self, tools):
        self._tools = tools

    def get_tools(self):
        return self._tools


def test_returns_local_tools_only_when_no_providers():
    registry = ToolRegistry(local_tools=["a", "b"])
    assert registry.get_tools() == ["a", "b"]


def test_aggregates_local_and_provider_tools():
    registry = ToolRegistry(
        local_tools=["local1"],
        providers=[_FakeProvider(["mcp1", "mcp2"]), _FakeProvider(["mcp3"])],
    )
    assert registry.get_tools() == ["local1", "mcp1", "mcp2", "mcp3"]


def test_caches_result_across_calls():
    provider = _FakeProvider(["x"])
    registry = ToolRegistry(local_tools=[], providers=[provider])
    first = registry.get_tools()
    provider._tools.append("y")
    second = registry.get_tools()
    assert first is second
    assert "y" not in second
