from typing import Any, Optional

from src.ports.tool_provider import ToolProvider


class ToolRegistry:
    def __init__(
        self,
        local_tools: list[Any],
        providers: Optional[list[ToolProvider]] = None,
    ):
        self._local_tools = list(local_tools)
        self._providers = list(providers or [])
        self._cache: Optional[list[Any]] = None

    def get_tools(self) -> list[Any]:
        if self._cache is None:
            tools = list(self._local_tools)
            for provider in self._providers:
                tools.extend(provider.get_tools())
            self._cache = tools
        return self._cache
