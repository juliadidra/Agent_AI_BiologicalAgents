from typing import Iterator, Optional

from src.ports.treatment_repository import Treatment


class FakeTreatmentRepository:
    def __init__(self, initial: Optional[list[Treatment]] = None):
        self._items: list[Treatment] = list(initial or [])
        self._next_id = len(self._items) + 1
        self.marked_inactive: list[str] = []

    def find_active(self, chat_id: str, medicamento: str) -> list[Treatment]:
        return [
            t
            for t in self._items
            if t.chat_id == chat_id
            and t.medicamento == medicamento
            and t.status == "ativo"
        ]

    def find_active_by_chat(self, chat_id: str) -> list[Treatment]:
        items = [t for t in self._items if t.chat_id == chat_id]
        active = [t for t in items if t.status == "ativo"]
        return active if active else items

    def add(
        self,
        chat_id: str,
        medicamento: str,
        tratamento: str,
        inicio: str,
        fim: str,
    ) -> Treatment:
        t = Treatment(
            id=str(self._next_id),
            chat_id=chat_id,
            medicamento=medicamento,
            tratamento=tratamento,
            inicio=inicio,
            fim=fim,
            status="ativo",
            created_at="2026-05-23T00:00:00",
        )
        self._next_id += 1
        self._items.append(t)
        return t

    def cancel(
        self,
        chat_id: str,
        medicamento: str,
        tratamento: Optional[str] = None,
    ) -> int:
        target = [
            t
            for t in self._items
            if t.chat_id == chat_id
            and t.medicamento == medicamento
            and t.status == "ativo"
            and (tratamento is None or t.tratamento == tratamento)
        ]
        for t in target:
            self._items.remove(t)
        return len(target)

    def iter_active(self) -> Iterator[Treatment]:
        for t in list(self._items):
            if t.status == "ativo":
                yield t

    def mark_inactive(self, treatment_id: str) -> None:
        self.marked_inactive.append(treatment_id)
        for t in self._items:
            if t.id == treatment_id:
                t.status = "inativo"
                break
