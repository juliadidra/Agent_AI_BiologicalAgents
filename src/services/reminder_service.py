import logging
from datetime import date, datetime

from src.ports.messaging import MessagingGateway
from src.ports.treatment_repository import TreatmentRepository

logger = logging.getLogger(__name__)


class ReminderService:
    def __init__(
        self,
        treatment_repository: TreatmentRepository,
        messaging: MessagingGateway,
    ):
        self._repo = treatment_repository
        self._messaging = messaging

    def run_for_today(self) -> int:
        today = date.today()
        logger.info("Running daily reminders for %s", today.isoformat())
        sent = 0
        for treatment in self._repo.iter_active():
            inicio, fim = self._parse_dates(treatment.inicio, treatment.fim, treatment.id)
            if inicio is None or fim is None:
                continue

            if inicio <= today <= fim:
                if self._send_reminder(treatment.chat_id, treatment.medicamento):
                    sent += 1
            elif today > fim:
                self._safe_mark_inactive(treatment.id)

        logger.info("Daily reminders finished — sent=%d", sent)
        return sent

    def _parse_dates(self, inicio: str, fim: str, treatment_id: str):
        try:
            return (
                datetime.fromisoformat(inicio).date(),
                datetime.fromisoformat(fim).date(),
            )
        except (ValueError, TypeError):
            logger.exception("Invalid date format for treatment %s", treatment_id)
            return None, None

    def _send_reminder(self, chat_id: str, medicamento: str) -> bool:
        message = (
            f"💊 Olá! Já tomou sua medicação **{medicamento}** hoje?"
            "\nResponda SIM ou NÃO para registrar."
        )
        try:
            self._messaging.send(chat_id, message)
            return True
        except Exception:
            logger.exception("Failed to send reminder to %s", chat_id)
            return False

    def _safe_mark_inactive(self, treatment_id: str) -> None:
        try:
            self._repo.mark_inactive(treatment_id)
            logger.info("Marked treatment %s as inativo", treatment_id)
        except Exception:
            logger.exception("Failed to mark treatment %s as inativo", treatment_id)
