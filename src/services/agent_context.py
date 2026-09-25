from dataclasses import dataclass, field
from typing import Any

from src.core.text import strip_reasoning


@dataclass
class AgentContext:
    """Contexto compartilhado, montado uma única vez pelo orquestrador e
    passado ao roteador e aos agentes especialistas."""

    chat_id: str
    question: str
    today: str
    history_summary: str = ""
    last_turn: str = ""
    patient_profile: dict[str, Any] = field(default_factory=dict)
    treatment_info: dict[str, Any] = field(default_factory=dict)

    @property
    def has_active_treatment(self) -> bool:
        return bool(self.treatment_info.get("has_active_treatment", False))


def extract_content(response: Any) -> str:
    """Extrai o texto de uma resposta de LLM de forma defensiva,
    removendo blocos de raciocínio de modelos de reasoning."""
    content = getattr(response, "content", "") or ""
    if not isinstance(content, str):
        content = str(content)
    return strip_reasoning(content)
