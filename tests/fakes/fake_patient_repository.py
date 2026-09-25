from typing import Optional

from src.ports.patient_repository import PatientProfile


class FakePatientRepository:
    def __init__(self):
        self._items: dict[str, PatientProfile] = {}
        self.ensure_calls: list[str] = []

    def get_profile(self, chat_id: str) -> Optional[PatientProfile]:
        return self._items.get(chat_id)

    def ensure_exists(self, chat_id: str) -> PatientProfile:
        self.ensure_calls.append(chat_id)
        if chat_id not in self._items:
            self._items[chat_id] = PatientProfile(
                chat_id=chat_id,
                health_state={},
                created_at="2026-05-23T00:00:00",
                updated_at="2026-05-23T00:00:00",
            )
        return self._items[chat_id]

    def save_health_state(self, chat_id: str, health_state: dict) -> PatientProfile:
        profile = self.ensure_exists(chat_id)
        profile.health_state = dict(health_state)
        profile.updated_at = "2026-05-23T12:00:00"
        return profile
