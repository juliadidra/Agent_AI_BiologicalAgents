from typing import Any

from src.ports.patient_repository import PatientRepository


class PatientService:
    def __init__(self, patient_repository: PatientRepository):
        self._repo = patient_repository

    def get_profile(self, chat_id: str) -> dict[str, Any]:
        profile = self._repo.get_profile(chat_id)
        if not profile:
            return {}
        return {
            "chat_id": profile.chat_id,
            "health_state": profile.health_state,
        }

    def ensure_profile_exists(self, chat_id: str) -> dict[str, Any]:
        profile = self._repo.ensure_exists(chat_id)
        return {
            "chat_id": profile.chat_id,
            "health_state": profile.health_state,
        }
