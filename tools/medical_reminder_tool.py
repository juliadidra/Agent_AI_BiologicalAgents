from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from langchain_core.tools import tool



class MedicationReminderTool:
    def __init__(self, waha_service):
        self.waha_service = waha_service

        # Inicializa Firebase apenas uma vez
        if not firebase_admin._apps:
            cred = credentials.Certificate("firebase-credentials.json")
            firebase_admin.initialize_app(cred)

        self.db = firestore.client()

    def execute(self, chat_id, medicamento, tratamento, inicio, fim):
        """
        Salva o tratamento no Firebase e agenda lembretes diários.
        """
        
        existing = self.db.collection("tratamentos")\
        .where("chatId", "==", chat_id)\
        .where("medicamento", "==", medicamento)\
        .where("status", "==", "ativo")\
        .stream()
    
        if any(existing):
            print("[INFO] Tratamento já existente, não registrando novamente.")
            return f"Tratamento com {medicamento} já está ativo e não foi duplicado."
        
        else:
            # Salva no banco
            self.db.collection("tratamentos").add({
                "chatId": chat_id,
                "medicamento": medicamento,
                "tratamento": tratamento,
                "inicio": inicio,
                "fim": fim,
                "status": "ativo",
                "createdAt": datetime.now().isoformat()
            })

            # Confirma para o paciente
            self.waha_service.send_message(
                chat_id,
                f"✅ Seu tratamento com {medicamento} ({tratamento}) foi registrado. "
                f"Você receberá lembretes diários até {fim}."
            )


@tool
def schedule_medication_treatment(chat_id: str, medicamento: str, tratamento: str, inicio: str, fim: str) -> str:
    """
    Registers a new medical treatment for a patient and schedules daily reminders. 
    This tool should only be called if the patient does not already have a treatment scheduled. 
    If the patient already has an active treatment, you must continue the conversation normally 
    without offering to schedule another treatment.
    """

    try:
        print("[DEBUG] Tool chamada!")
        from services.waha.waha_service import WahaService
        waha_service = WahaService()
        tool = MedicationReminderTool(waha_service)
        response = tool.execute(chat_id, medicamento, tratamento, inicio, fim)
        return response
    except Exception as e:
        print(f"[ERRO] Falha ao registrar tratamento: {e}")
        return "Ocorreu um erro ao registrar o tratamento. Por favor, tente novamente."