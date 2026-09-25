import logging
from typing import Annotated, Any, Optional

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


def _container() -> Any:
    from src.api.main import app

    return app.state.container


@tool
def schedule_medication_treatment(
    chat_id: str,
    medicamento: str,
    tratamento: str,
    inicio: Annotated[str, "format: YYYY-MM-DD"],
    fim: Annotated[str, "format: YYYY-MM-DD"],
) -> str:
    """
    Registers a new medical treatment for a patient and schedules daily reminders.
    This tool should only be called if the patient does not already have a treatment scheduled.
    If the patient already has an active treatment, you must continue the conversation normally
    without offering to schedule another treatment.
    """
    try:
        return _container().treatment_service.schedule(
            chat_id=chat_id,
            medicamento=medicamento,
            tratamento=tratamento,
            inicio=inicio,
            fim=fim,
        )
    except Exception:
        logger.exception("schedule_medication_treatment failed")
        return "Ocorreu um erro ao registrar o tratamento. Por favor, tente novamente."


@tool
def cancel_medication_treatment(
    chat_id: str,
    medicamento: str,
    tratamento: Optional[str] = None,
) -> str:
    """
    Cancels an existing medical treatment for a patient.
    This tool should only be called if the patient asks to cancel their treatment.
    """
    try:
        return _container().treatment_service.cancel(
            chat_id=chat_id,
            medicamento=medicamento,
            tratamento=tratamento,
        )
    except Exception:
        logger.exception("cancel_medication_treatment failed")
        return "Ocorreu um erro ao cancelar o tratamento. Por favor, tente novamente."


@tool
def get_user_information(chat_id: str) -> dict:
    """
    Return user information based on chat_id. This tool retrieves details such as
    active treatments, medication status, duration of treatment, if user has daily
    reminders and which treatment the user is undergoing.
    """
    try:
        return _container().treatment_service.get_summary(chat_id)
    except Exception:
        logger.exception("get_user_information failed")
        return {"has_active_treatment": False, "has_daily_reminders": False}


@tool
def update_patient_profile(
    chat_id: str,
    condicoes: Optional[list[str]] = None,
    alergias: Optional[list[str]] = None,
    tipo_exposicao: Optional[str] = None,
    notas: Optional[str] = None,
) -> str:
    """
    Persist NEW health facts the patient stated EXPLICITLY into their long-term
    profile. Pass only the fields that changed; omit the rest. Lists (condicoes,
    alergias) are accumulated, not replaced. Never infer, deduce or diagnose —
    store only what the patient actually said. In doubt, do not call this tool.
    Fields: condicoes (conditions/diagnoses), alergias (drug allergies),
    tipo_exposicao (exposure type), notas (free text for anything else).
    """
    updates = {
        "condicoes": condicoes,
        "alergias": alergias,
        "tipo_exposicao": tipo_exposicao,
        "notas": notas,
    }
    updates = {k: v for k, v in updates.items() if v is not None}
    try:
        health_state = _container().patient_service.update_profile(chat_id, updates)
        return f"Perfil atualizado. Estado atual: {health_state}"
    except Exception:
        logger.exception("update_patient_profile failed")
        return "Não foi possível atualizar o perfil do paciente agora."


@tool
def search_clinical_knowledge(query: str) -> str:
    """
    Search the clinical reference material (treatment protocol / PCDT) for passages
    relevant to a patient's informational question about medication, side effects,
    drug interactions, exams or protocol. Call this before answering clinical or
    informational doubts. Pass the patient's clinical question in `query`.
    """
    try:
        docs = _container().rag_pipeline.search(query)
        if not docs:
            return "Nenhum trecho relevante encontrado no material clínico."
        return "\n\n".join(f"- {d}" for d in docs)
    except Exception:
        logger.exception("search_clinical_knowledge failed")
        return "Não foi possível consultar o material clínico agora."


LOCAL_TOOLS = [
    schedule_medication_treatment,
    cancel_medication_treatment,
    get_user_information,
    update_patient_profile,
    search_clinical_knowledge,
]
