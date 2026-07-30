from datetime import datetime
from typing import Optional

from google.cloud.firestore_v1.client import Client

from src.ports.patient_repository import PatientProfile


class FirestorePatientRepository:
    def __init__(self, firestore: Client, collection_name: str = "pacientes"):
        self._db = firestore
        self._collection_name = collection_name

    def _collection(self):
        return self._db.collection(self._collection_name)

    def get_profile(self, chat_id: str) -> Optional[PatientProfile]:
        doc = self._collection().document(chat_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict() or {}
        return PatientProfile(
            chat_id=chat_id,
            health_state=data.get("healthState", {}) or {},
            created_at=data.get("createdAt"),
            updated_at=data.get("updatedAt"),
        )

    def ensure_exists(self, chat_id: str) -> PatientProfile:
        existing = self.get_profile(chat_id)
        if existing:
            return existing
        now = datetime.now().isoformat()
        self._collection().document(chat_id).set(
            {
                "chatId": chat_id,
                "healthState": {},
                "createdAt": now,
                "updatedAt": now,
            }
        )
        return PatientProfile(
            chat_id=chat_id,
            health_state={},
            created_at=now,
            updated_at=now,
        )
