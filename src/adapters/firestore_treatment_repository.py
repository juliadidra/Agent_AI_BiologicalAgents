from datetime import datetime
from typing import Iterator, Optional

from google.cloud.firestore_v1.client import Client

from src.ports.treatment_repository import Treatment


class FirestoreTreatmentRepository:
    def __init__(self, firestore: Client, collection_name: str = "tratamentos"):
        self._db = firestore
        self._collection_name = collection_name

    def _collection(self):
        return self._db.collection(self._collection_name)

    def _to_treatment(self, doc) -> Treatment:
        data = doc.to_dict() or {}
        return Treatment(
            id=doc.id,
            chat_id=data.get("chatId", ""),
            medicamento=data.get("medicamento", ""),
            tratamento=data.get("tratamento", ""),
            inicio=data.get("inicio", ""),
            fim=data.get("fim", ""),
            status=data.get("status", ""),
            created_at=data.get("createdAt"),
        )

    def find_active(self, chat_id: str, medicamento: str) -> list[Treatment]:
        docs = (
            self._collection()
            .where("chatId", "==", chat_id)
            .where("medicamento", "==", medicamento)
            .where("status", "==", "ativo")
            .stream()
        )
        return [self._to_treatment(d) for d in docs]

    def find_active_by_chat(self, chat_id: str) -> list[Treatment]:
        docs = (
            self._collection()
            .where("chatId", "==", chat_id)
            .stream()
        )
        treatments = [self._to_treatment(d) for d in docs]
        active = [t for t in treatments if t.status == "ativo"]
        return active if active else treatments

    def add(
        self,
        chat_id: str,
        medicamento: str,
        tratamento: str,
        inicio: str,
        fim: str,
    ) -> Treatment:
        created_at = datetime.now().isoformat()
        payload = {
            "chatId": chat_id,
            "medicamento": medicamento,
            "tratamento": tratamento,
            "inicio": inicio,
            "fim": fim,
            "status": "ativo",
            "createdAt": created_at,
        }
        _, ref = self._collection().add(payload)
        return Treatment(
            id=ref.id,
            chat_id=chat_id,
            medicamento=medicamento,
            tratamento=tratamento,
            inicio=inicio,
            fim=fim,
            status="ativo",
            created_at=created_at,
        )

    def cancel(
        self,
        chat_id: str,
        medicamento: str,
        tratamento: Optional[str] = None,
    ) -> int:
        query = (
            self._collection()
            .where("chatId", "==", chat_id)
            .where("medicamento", "==", medicamento)
            .where("status", "==", "ativo")
        )
        if tratamento:
            query = query.where("tratamento", "==", tratamento)
        docs = list(query.stream())
        for doc in docs:
            self._collection().document(doc.id).delete()
        return len(docs)

    def iter_active(self) -> Iterator[Treatment]:
        docs = self._collection().where("status", "==", "ativo").stream()
        for d in docs:
            yield self._to_treatment(d)

    def mark_inactive(self, treatment_id: str) -> None:
        self._collection().document(treatment_id).update({"status": "inativo"})
