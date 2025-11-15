from typing import Annotated
from firebase_admin import firestore
from langchain_core.tools import tool
from sympy import Dict
import logging
logging.basicConfig(level=logging.DEBUG)

class UserInformationTool:
    def __init__(self):
        self.db = firestore.client()

    def get_user_info(self, chat_id):
        """
        Recupera informações do usuário do Firestore.
        """
        try:
            query = self.db.collection("tratamentos").where("chatId", "==", chat_id)
            docs = list(query.stream())

            if not docs:
                return {"has_active_treatment": False, "has_daily_reminders": False}

            # Preferir documento com status "ativo"
            selected = None
            for doc in docs:
                data = doc.to_dict() or {}
                if data.get("status") == "ativo":
                    selected = data
                    break

            if selected is None:
                selected = docs[0].to_dict() or {}

            user_info = {
                "has_active_treatment": True,
                "has_daily_reminders": True if selected.get("status") == "ativo" else False,
                "medicamento": selected.get("medicamento"),
                "status": selected.get("status"),
                "data_inicial": selected.get("inicio"),
                "data_final": selected.get("fim"),
                "tratamento": selected.get("tratamento"),
            }
            return user_info
        except Exception as e:
            print(f"[ERRO] get_user_info: {e}")
            return {"has_active_treatment": False, "has_daily_reminders": False}

@tool
def get_user_information(
    chat_id: str, ) -> Dict:
    """
    Return user information based on chat_id. This tool retrieves details such as active treatments, medication status, duration of treatment, if user has daily reminders and which treatment the user is undergoing.
    """

    try:
        # print("[DEBUG] Tool chamada!")
        # from services.waha.waha_service import WahaService
        # waha_service = WahaService()
        logging.debug("[DEBUG] Tool get_user_information chamada!")
        tool = UserInformationTool().get_user_info(chat_id)
        return tool
    except Exception as e:
        logging.error(f"[ERRO] Falha ao retornar informações do paciente: {e}")
        return "Ocorreu um erro ao retornar as informações do paciente. Por favor, tente novamente."