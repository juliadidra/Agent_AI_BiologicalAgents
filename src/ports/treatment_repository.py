from dataclasses import dataclass
from typing import Iterator, Optional, Protocol


@dataclass
class Treatment:
    id: str
    chat_id: str
    medicamento: str
    tratamento: str
    inicio: str
    fim: str
    status: str
    created_at: Optional[str] = None


class TreatmentRepository(Protocol):
    def find_active(self, chat_id: str, medicamento: str) -> list[Treatment]: ...
    def find_active_by_chat(self, chat_id: str) -> list[Treatment]: ...
    def add(
        self,
        chat_id: str,
        medicamento: str,
        tratamento: str,
        inicio: str,
        fim: str,
    ) -> Treatment: ...
    def cancel(
        self,
        chat_id: str,
        medicamento: str,
        tratamento: Optional[str] = None,
    ) -> int: ...
    def iter_active(self) -> Iterator[Treatment]: ...
    def mark_inactive(self, treatment_id: str) -> None: ...
