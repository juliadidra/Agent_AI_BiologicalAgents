import json
import logging
from datetime import date
from typing import Any

from src.ports.llm import GuardrailProvider, LLMProvider
from src.ports.summarizer import Summarizer
from src.prompts.guardrail_policy import UNSAFE_RESPONSE
from src.services.patient_service import PatientService
from src.services.prompt_builder import PromptBuilder
from src.services.rag_pipeline import RagPipeline
from src.services.tool_registry import ToolRegistry
from src.services.treatment_service import TreatmentService

logger = logging.getLogger(__name__)

_ERROR_RESPONSE = "Ocorreu um erro ao processar sua solicitação."


class ConversationService:
    def __init__(
        self,
        guardrail: GuardrailProvider,
        patient_service: PatientService,
        treatment_service: TreatmentService,
        rag_pipeline: RagPipeline,
        summarizer: Summarizer,
        prompt_builder: PromptBuilder,
        llm: LLMProvider,
        tool_registry: ToolRegistry,
    ):
        self._guardrail = guardrail
        self._patient_service = patient_service
        self._treatment_service = treatment_service
        self._rag_pipeline = rag_pipeline
        self._summarizer = summarizer
        self._prompt_builder = prompt_builder
        self._llm = llm
        self._tool_registry = tool_registry

    def handle_incoming(
        self,
        chat_id: str,
        question: str,
        history: list[dict[str, Any]],
    ) -> str:
        if not self._guardrail.is_safe(question):
            return UNSAFE_RESPONSE

        patient_profile = self._patient_service.get_profile(chat_id)
        treatment_info = self._treatment_service.get_summary(chat_id)
        docs = self._rag_pipeline.search(question)
        history_summary = self._summarize_history(history)

        messages = self._prompt_builder.build(
            question=question,
            today=date.today().isoformat(),
            chat_id=chat_id,
            context_docs=docs,
            history_summary=history_summary,
            treatment_info=treatment_info,
            patient_profile=patient_profile,
        )

        try:
            response = self._llm.invoke(messages)
        except Exception:
            logger.exception("LLM invocation failed")
            return _ERROR_RESPONSE

        tool_calls = getattr(response, "tool_calls", None) or []
        if tool_calls:
            dispatched = self._dispatch_first_tool(tool_calls)
            if dispatched is not None:
                return dispatched

        content = getattr(response, "content", "") or ""
        return content if isinstance(content, str) else str(content)

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

    def _dispatch_first_tool(self, tool_calls: list[dict[str, Any]]) -> str | None:
        for call in tool_calls:
            name = call.get("name")
            tool = self._find_tool(name) if name else None
            if tool is None:
                continue
            args = call.get("args", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    logger.warning("Tool %s args not valid JSON: %r", name, args)
                    continue
            try:
                return tool.invoke(args)
            except Exception:
                logger.exception("Tool %s invocation failed", name)
                return _ERROR_RESPONSE
        return None

    def _find_tool(self, name: str) -> Any:
        for t in self._tool_registry.get_tools():
            if getattr(t, "name", None) == name:
                return t
        return None
