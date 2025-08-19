from datetime import date
import firebase_admin
from firebase_admin import credentials, firestore
from services.waha.waha_service import WahaService
# Inicializa Firebase
cred = credentials.Certificate("firebase-credentials.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

waha_service = WahaService()

def send_daily_reminders():
    hoje = date.today().isoformat()

    # Busca todos os tratamentos ativos
    tratamentos = db.collection("tratamentos").where("status", "==", "ativo").stream()

    for t in tratamentos:
        data = t.to_dict()

        # Só envia se hoje está dentro do período
        if data["inicio"] <= hoje <= data["fim"]:
            mensagem = (
                f"💊 Olá! Já tomou sua medicação **{data['medicamento']}** hoje?"
                "\nResponda SIM ou NÃO para registrar."
            )
            waha_service.send_message(data["chatId"], mensagem)

if __name__ == "__main__":
    send_daily_reminders()
