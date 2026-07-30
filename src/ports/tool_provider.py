from typing import Any, Protocol


class ToolProvider(Protocol):
    def get_tools(self) -> list[Any]: ...
