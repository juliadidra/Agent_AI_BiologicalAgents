from typing import Any

from src.ports.patient_repository import PatientRepository


class PatientService:
    # Chaves cujo valor é uma lista acumulada (união, sem duplicar).
    LIST_KEYS = ("condicoes", "alergias")
    # Chaves de texto simples (sobrescrevem o valor anterior).
    TEXT_KEYS = ("tipo_exposicao", "notas")

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

    def update_profile(self, chat_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Mescla `updates` (apenas o delta) no perfil atual e persiste.
        Listas são acumuladas (união); textos sobrescrevem. Chaves
        desconhecidas ou valores vazios são ignorados."""
        profile = self._repo.ensure_exists(chat_id)
        health = dict(profile.health_state or {})

        for key in self.LIST_KEYS:
            incoming = updates.get(key)
            if incoming:
                health[key] = self._union(health.get(key), incoming)

        for key in self.TEXT_KEYS:
            incoming = updates.get(key)
            if incoming and str(incoming).strip():
                health[key] = str(incoming).strip()

        saved = self._repo.save_health_state(chat_id, health)
        return saved.health_state

    @staticmethod
    def _union(existing: Any, incoming: Any) -> list[str]:
        """Une duas listas de strings sem duplicar (case-insensitive),
        preservando a ordem. Aceita string solta como item único."""
        def as_list(v: Any) -> list[str]:
            if v is None:
                return []
            return [v] if isinstance(v, str) else list(v)

        result: list[str] = []
        seen: set[str] = set()
        for item in as_list(existing) + as_list(incoming):
            if not isinstance(item, str):
                continue
            clean = item.strip()
            if clean and clean.lower() not in seen:
                result.append(clean)
                seen.add(clean.lower())
        return result
