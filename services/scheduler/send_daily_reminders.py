import logging
import sys
import traceback
from datetime import date, datetime

import firebase_admin
from firebase_admin import credentials, firestore
from services.waha.waha_service import WahaService


# Configure logging to stdout so cron redirection captures it
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def initialize_firebase():
    try:
        cred = credentials.Certificate("firebase-credentials.json")
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        logger.info("Firebase initialized")
        return db
    except Exception:
        logger.exception("Failed to initialize Firebase (check firebase-credentials.json mount and contents)")
        raise


def send_daily_reminders():
    db = initialize_firebase()
    waha_service = WahaService()

    hoje = date.today()
    logger.info("Running send_daily_reminders for date=%s", hoje.isoformat())

    # Busca todos os tratamentos ativos
    try:
        tratamentos = db.collection("tratamentos").where("status", "==", "ativo").stream()
    except Exception:
        logger.exception("Failed to query tratamentos collection")
        return

    sent = 0
    for t in tratamentos:
        data = t.to_dict()
        try:
            inicio = datetime.fromisoformat(data.get("inicio")).date()
            fim = datetime.fromisoformat(data.get("fim")).date()
        except Exception:
            logger.exception("Invalid date format for tratamento id=%s: %s", getattr(t, 'id', '<unknown>'), data)
            continue

        logger.info("Checking tratamento id=%s medicamento=%s inicio=%s fim=%s", getattr(t, 'id', '<unknown>'), data.get('medicamento'), inicio, fim)

        # Só envia se hoje está dentro do período
        if inicio <= hoje <= fim:
            mensagem = (
                f"💊 Olá! Já tomou sua medicação **{data.get('medicamento')}** hoje?"
                "\nResponda SIM ou NÃO para registrar."
            )
            try:
                logger.info("Sending message to chatId=%s", data.get('chatId'))
                waha_service.send_message(data.get("chatId"), mensagem)
                sent += 1
                logger.info("Message sent to %s", data.get('chatId'))
            except Exception:
                logger.exception("Failed to send message to %s", data.get('chatId'))
        else:
            # Marca como inativo se o período terminou
            if hoje > fim:
                try:
                    db.collection("tratamentos").document(t.id).update({"status": "inativo"})
                    logger.info("Marked tratamento id=%s as inativo", getattr(t, 'id', '<unknown>'))
                except Exception:
                    logger.exception("Failed to mark tratamento id=%s as inativo", getattr(t, 'id', '<unknown>'))

    logger.info("send_daily_reminders finished — messages_sent=%d", sent)


if __name__ == "__main__":
    try:
        send_daily_reminders()
    except Exception:
        logger.exception("Unhandled exception in send_daily_reminders")
        # Exit non-zero so cron/system logs may show the failure (if capturing exit status)
        sys.exit(1)
