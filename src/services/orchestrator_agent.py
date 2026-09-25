import json
import logging
from typing import Any

from langchain_core.messages import ToolMessage

from src.ports.llm import LLMProvider
from src.services.agent_context import AgentContext, extract_content
from src.services.prompt_builder import PromptBuilder
from src.services.tool_registry import ToolRegistry

logger = logging.getLogger(__name__)

_TEMPLATE = "orchestrator.jinja"
_ERROR_RESPONSE = "Ocorreu um erro ao processar sua solicitação."


class OrchestratorAgent:
    """Agente único movido a tools. Um LLM raciocina sobre a mensagem do
    paciente, consulta ferramentas que devolvem DADOS (busca clínica via RAG,
    agendamento/cancelamento) e escreve a resposta final. Loop agêntico: o
    resultado de cada tool é realimentado até o LLM produzir texto (ou até
    atingir MAX_TOOL_ITERS).
    """

    MAX_TOOL_ITERS = 4

    _EMPTY_FALLBACK = (
        "Desculpe, tive um problema para montar a resposta agora. "
        "Pode reenviar sua mensagem?"
    )

    def __init__(
        self,
        llm: LLMProvider,
        tool_registry: ToolRegistry,
        prompt_builder: PromptBuilder,
    ):
        self._llm = llm
        self._tool_registry = tool_registry
        self._prompt_builder = prompt_builder

    def handle(self, ctx: AgentContext) -> str:
        messages: list[Any] = self._prompt_builder.build(
            _TEMPLATE,
            question=ctx.question,
            hoje=ctx.today,
            chat_id=ctx.chat_id,
            treatment_info=ctx.treatment_info,
            patient_profile=ctx.patient_profile,
            history_summary=ctx.history_summary,
        )
        logger.info(
            "Orchestrator prompt:\nSYSTEM:\n%s\nUSER:\n%s",
            messages[0]["content"],
            messages[1]["content"],
        )

        response = None
        for _ in range(self.MAX_TOOL_ITERS + 1):
            response = self._llm.invoke(messages)
            tool_calls = getattr(response, "tool_calls", None) or []
            if not tool_calls:
                return self._finalize(response)

            messages.append(response)
            for call in tool_calls:
                result = self._execute_tool(call)
                messages.append(
                    ToolMessage(
                        content=str(result),
                        tool_call_id=call.get("id") or call.get("name", ""),
                    )
                )

        # Excedeu o número de iterações: devolve o que houver (com guard de vazio).
        return self._finalize(response)

    def _finalize(self, response: Any) -> str:
        final = extract_content(response)
        if final:
            return final
        logger.warning("Orchestrator produced empty content; using fallback")
        return self._EMPTY_FALLBACK

    def _execute_tool(self, call: dict[str, Any]) -> Any:
        name = call.get("name")
        tool = self._find_tool(name) if name else None
        if tool is None:
            logger.warning("Tool %r not found in registry", name)
            return f"Ferramenta '{name}' indisponível."

        args = call.get("args", {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                logger.warning("Tool %s args not valid JSON: %r", name, args)
                return "Argumentos inválidos para a ferramenta."

        try:
            result = tool.invoke(args)
            logger.info("Tool %s executed", name)
            return result
        except Exception:
            logger.exception("Tool %s invocation failed", name)
            return _ERROR_RESPONSE

    def _find_tool(self, name: str) -> Any:
        for t in self._tool_registry.get_tools():
            if getattr(t, "name", None) == name:
                return t
        return None
