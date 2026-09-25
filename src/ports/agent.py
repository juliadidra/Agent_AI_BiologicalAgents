from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from src.services.agent_context import AgentContext


class Agent(Protocol):
    def handle(self, ctx: "AgentContext") -> str: ...
