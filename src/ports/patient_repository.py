from dataclasses import dataclass, field
from typing import Optional, Protocol


@dataclass
class PatientProfile:
    chat_id: str
    health_state: dict = field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PatientRepository(Protocol):
    def get_profile(self, chat_id: str) -> Optional[PatientProfile]: ...
    def ensure_exists(self, chat_id: str) -> PatientProfile: ...
    def save_health_state(self, chat_id: str, health_state: dict) -> PatientProfile: ...
