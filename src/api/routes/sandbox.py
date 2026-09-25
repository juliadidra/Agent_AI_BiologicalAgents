import logging
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field

from src.api.deps import get_conversation_service
from src.services.conversation_service import ConversationService

router = APIRouter()
logger = logging.getLogger(__name__)


class SandboxMessageRequest(BaseModel):
    """Simula uma mensagem chegando, roda o fluxo do agente e devolve a
    resposta no corpo HTTP — sem passar pelo WhatsApp/WAHA."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "chat_id": "5511999999999@c.us",
                "message": "quero agendar lembrete do Tenofovir a partir de hoje",
                "history": [
                    {"fromMe": False, "body": "oi"},
                    {"fromMe": True, "body": "Olá! Como posso te ajudar hoje?"},
                ],
            }
        }
    )

    chat_id: str = Field(
        ...,
        description="Identificador do chat (ex.: '5511999999999@c.us').",
    )
    message: str = Field(
        ...,
        description="Mensagem do paciente a ser processada pelo agente.",
    )
    history: list[dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "Histórico opcional da conversa: lista de {fromMe: bool, body: str}. "
            "Vazio simula uma conversa nova (sem contexto anterior)."
        ),
    )


class SandboxMessageResponse(BaseModel):
    chat_id: str
    message: str
    answer: str


@router.post("/agent/test-message", response_model=SandboxMessageResponse)
async def send_test_message(
    payload: SandboxMessageRequest,
    conversation: ConversationService = Depends(get_conversation_service),
):
    """Endpoint de teste do fluxo do agente.

    Chama `ConversationService.handle_incoming` diretamente e retorna a
    resposta do agente, sem WAHA. Atenção: dispara chamadas reais de
    LLM/RAG (Groq/Chroma/Cohere).
    """
    logger.info("Sandbox message received for chat_id=%s", payload.chat_id)
    answer = await run_in_threadpool(
        conversation.handle_incoming,
        payload.chat_id,
        payload.message,
        payload.history,
    )
    return SandboxMessageResponse(
        chat_id=payload.chat_id,
        message=payload.message,
        answer=answer,
    )
