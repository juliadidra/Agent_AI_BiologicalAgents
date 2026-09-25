from src.services.agent_context import AgentContext
from src.services.orchestrator_agent import OrchestratorAgent
from src.services.prompt_builder import PromptBuilder
from src.services.tool_registry import ToolRegistry
from tests.fakes.fake_llm import FakeLLM, FakeLLMResponse, FakeSequenceLLM, FakeTool


def _ctx(question="oi"):
    return AgentContext(
        chat_id="abc@c.us",
        question=question,
        today="2026-05-23",
        history_summary="",
        last_turn="",
        patient_profile={},
        treatment_info={"has_active_treatment": False},
    )


def _agent(llm, tools=None):
    return OrchestratorAgent(
        llm=llm,
        tool_registry=ToolRegistry(local_tools=tools or []),
        prompt_builder=PromptBuilder(),
    )


def test_no_tool_call_returns_content_directly():
    llm = FakeLLM(FakeLLMResponse(content="Oi! Como posso ajudar?"))
    agent = _agent(llm)

    assert agent.handle(_ctx()) == "Oi! Como posso ajudar?"
    assert len(llm.calls) == 1


def test_agentic_loop_executes_tool_and_feeds_result_back():
    tool = FakeTool(name="search_clinical_knowledge", return_value="- trecho relevante")
    llm = FakeSequenceLLM(
        [
            FakeLLMResponse(
                content="",
                tool_calls=[
                    {"id": "c1", "name": "search_clinical_knowledge", "args": {"query": "efeitos?"}}
                ],
            ),
            FakeLLMResponse(content="Segundo o material, o efeito é X."),
        ]
    )
    agent = _agent(llm, tools=[tool])

    result = agent.handle(_ctx("quais os efeitos?"))

    assert result == "Segundo o material, o efeito é X."
    assert tool.invoked_with == [{"query": "efeitos?"}]
    assert len(llm.calls) == 2


def test_empty_final_content_uses_fallback():
    # modelo sempre pede tool e nunca produz texto -> guard de vazio
    always_tool = FakeLLMResponse(
        content="",
        tool_calls=[{"id": "c", "name": "search_clinical_knowledge", "args": {"query": "x"}}],
    )
    tool = FakeTool(name="search_clinical_knowledge", return_value="ok")
    llm = FakeSequenceLLM([always_tool])
    agent = _agent(llm, tools=[tool])

    result = agent.handle(_ctx())

    assert result == OrchestratorAgent._EMPTY_FALLBACK
    assert len(llm.calls) == OrchestratorAgent.MAX_TOOL_ITERS + 1


def test_unknown_tool_is_reported_not_crashing():
    llm = FakeSequenceLLM(
        [
            FakeLLMResponse(
                content="",
                tool_calls=[{"id": "c", "name": "ferramenta_inexistente", "args": {}}],
            ),
            FakeLLMResponse(content="segue a conversa"),
        ]
    )
    agent = _agent(llm, tools=[])

    assert agent.handle(_ctx()) == "segue a conversa"
