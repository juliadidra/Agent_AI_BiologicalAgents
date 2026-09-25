import logging
from datetime import date
from typing import Any

from src.ports.agent import Agent
from src.ports.llm import GuardrailProvider
from src.ports.summarizer import Summarizer
from src.prompts.guardrail_policy import UNSAFE_RESPONSE
from src.services.agent_context import AgentContext
from src.services.patient_service import PatientService
from src.services.treatment_service import TreatmentService

logger = logging.getLogger(__name__)

_ERROR_RESPONSE = "Ocorreu um erro ao processar sua solicitação."


class ConversationService:
    """Orquestrador do fluxo multi-agente.

    Camada 1: guardrail (curto-circuita antes de tudo). Em seguida monta o
    AgentContext uma única vez e delega ao orquestrador, que raciocina com as
    tools (busca clínica, agendamento) e escreve a resposta final.
    """

    def __init__(
        self,
        guardrail: GuardrailProvider,
        orchestrator: Agent,
        patient_service: PatientService,
        treatment_service: TreatmentService,
        summarizer: Summarizer,
    ):
        self._guardrail = guardrail
        self._orchestrator = orchestrator
        self._patient_service = patient_service
        self._treatment_service = treatment_service
        self._summarizer = summarizer

    def handle_incoming(
        self,
        chat_id: str,
        question: str,
        history: list[dict[str, Any]],
    ) -> str:
        # Camada 1: guardrail antes de montar contexto ou chamar o orquestrador.
        if not self._guardrail.is_safe(question):
            return UNSAFE_RESPONSE

        try:
            ctx = self._build_context(chat_id, question, history)
            return self._orchestrator.handle(ctx)
        except Exception:
            logger.exception("Conversation handling failed")
            return _ERROR_RESPONSE

    def _build_context(
        self,
        chat_id: str,
        question: str,
        history: list[dict[str, Any]],
    ) -> AgentContext:
        return AgentContext(
            chat_id=chat_id,
            question=question,
            today=date.today().isoformat(),
            history_summary=self._summarize_history(history),
            last_turn=self._extract_last_turn(history),
            patient_profile=self._patient_service.get_profile(chat_id),
            treatment_info=self._treatment_service.get_summary(chat_id),
        )

    def _summarize_history(self, history: list[dict[str, Any]]) -> str:
        normalized = [
            {
                "role": "assistant" if m.get("fromMe") else "user",
                "content": m.get("body", ""),
            }
            for m in (history or [])
            if m.get("body") and str(m.get("body", "")).strip()
        ]
        try:
            return self._summarizer.summarize(normalized)
        except Exception:
            logger.exception("Summarizer failed; returning empty summary")
            return ""

    @staticmethod
    def _extract_last_turn(history: list[dict[str, Any]]) -> str:
        """Últimas (até 2) mensagens não vazias, para o router resolver
        referências e respostas curtas sem depender do resumo inteiro."""
        filtered = [
            m
            for m in (history or [])
            if m.get("body") and str(m.get("body", "")).strip()
        ]
        lines = [
            f"{'assistente' if m.get('fromMe') else 'paciente'}: {str(m['body']).strip()}"
            for m in filtered[-2:]
        ]
        return "\n".join(lines)
