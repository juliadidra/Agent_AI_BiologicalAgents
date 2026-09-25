import logging
from typing import Any, Optional

from src.ports.treatment_repository import TreatmentRepository

logger = logging.getLogger(__name__)


class TreatmentService:
    def __init__(
        self,
        treatment_repository: TreatmentRepository,
    ):
        self._repo = treatment_repository

    def schedule(
        self,
        chat_id: str,
        medicamento: str,
        tratamento: str,
        inicio: str,
        fim: str,
    ) -> str:
        existing = self._repo.find_active(chat_id, medicamento)
        if existing:
            return f"Tratamento com {medicamento} já está ativo e não foi duplicado."

        self._repo.add(
            chat_id=chat_id,
            medicamento=medicamento,
            tratamento=tratamento,
            inicio=inicio,
            fim=fim,
        )
        # Resultado factual para a LLM (fonte da verdade): quem redige a
        # mensagem final ao paciente é o turno seguinte do agente. Sem envio
        # direto aqui — evita mensagem duplicada.
        return (
            f"Agendamento concluído. Dados confirmados: medicamento={medicamento}, "
            f"tratamento={tratamento}, inicio={inicio}, fim={fim}. "
            f"Lembretes diários ativos até {fim}."
        )

    def cancel(
        self,
        chat_id: str,
        medicamento: str,
        tratamento: Optional[str] = None,
    ) -> str:
        cancelled = self._repo.cancel(chat_id, medicamento, tratamento)
        if cancelled == 0:
            return f"Não há tratamento ativo com {medicamento} para cancelar."

        return (
            f"Cancelamento concluído. Dados confirmados: medicamento={medicamento}"
            + (f", tratamento={tratamento}" if tratamento else "")
            + ". Lembretes diários encerrados."
        )

    def get_summary(self, chat_id: str) -> dict[str, Any]:
        treatments = self._repo.find_active_by_chat(chat_id)
        if not treatments:
            return {"has_active_treatment": False, "has_daily_reminders": False}

        selected = next(
            (t for t in treatments if t.status == "ativo"),
            treatments[0],
        )
        return {
            "has_active_treatment": True,
            "has_daily_reminders": selected.status == "ativo",
            "medicamento": selected.medicamento,
            "status": selected.status,
            "data_inicial": selected.inicio,
            "data_final": selected.fim,
            "tratamento": selected.tratamento,
        }
