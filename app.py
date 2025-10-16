import base64
import io
import json
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from services.groq_ai.agent_ai_service import AIAgentService
from services.waha.waha_service import WahaService
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


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post('/agent/webhook')
async def agent_webhook(request: Request):
    data = await request.json()
    print("received_data", data)

    # Validação do payload
    payload = data.get("payload")
    if not payload or not isinstance(payload, dict):
        # Acknowledge eventos genéricos (evita retries de webhook)
        return JSONResponse(status_code=200, content={"ignored": "missing or invalid 'payload'"})

    # Extrai chat id de formas possíveis
    chat_id = payload.get("from") or payload.get("chatId") or payload.get("chat_id")

    # Extrai corpo da mensagem (verifica variantes comuns)
    received_message = payload.get("body") or payload.get("message") or payload.get("text")
    if not received_message:
        # Evento não é uma mensagem (ex.: session.status) — apenas confirmar recebimento
        return JSONResponse(status_code=200, content={"ignored": "non-message event"})

    # Processa mensagem normalmente
    waha = WahaService()
    ai_agent = AIAgentService()

    waha.start_typing(chat_id=chat_id)

    history_messages = waha.get_history_messages(chat_id=chat_id, limit=10)

    response_message = ai_agent.create_prompt(history_messages=history_messages, question=received_message, chat_id=chat_id)
    print("response_message: ", response_message)

    waha.send_message(chat_id=chat_id, message=response_message)
    waha.stop_typing(chat_id=chat_id)

    return JSONResponse(status_code=200, content={"message": "Message sent!"})

@app.post('/agent/daily-reminders')
def initialize_firebase():
    try:
        firebase_json = os.getenv("FIREBASE_CREDENTIALS")
        if firebase_json:
            try:
                decoded = base64.b64decode(firebase_json)
                cred_dict = json.loads(decoded.decode("utf-8"))
            except Exception:
                # se não for base64, tenta interpretar como JSON direto
                try:
                    cred_dict = json.loads(firebase_json)
                except Exception:
                    logger.exception("FIREBASE_CREDENTIALS não é um JSON válido nem um base64 de JSON")
                    raise

            # cria Certificate a partir do dict em memória
            cred = credentials.Certificate(cred_dict)
        else:
            cred = credentials.Certificate("firebase-credentials.json")

        firebase_admin.initialize_app(cred)
        db = firestore.client()
        logger.info("✅ Firebase initialized successfully")
        return db
    except Exception:
        logger.exception("❌ Failed to initialize Firebase")
        raise


def send_daily_reminders():
    db = initialize_firebase()
    waha_service = WahaService()

    hoje = date.today()
    logger.info("Running send_daily_reminders for date=%s", hoje.isoformat())

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