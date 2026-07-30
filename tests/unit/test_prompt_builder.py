import json

from src.services.prompt_builder import PromptBuilder


def test_build_renders_all_context_pieces():
    builder = PromptBuilder()

    messages = builder.build(
        question="quais efeitos do Truvada?",
        today="2026-05-23",
        chat_id="abc@c.us",
        context_docs=["doc-protocolo-pep", "doc-truvada"],
        history_summary="Paciente perguntou sobre PEP ontem.",
        treatment_info={"has_active_treatment": True, "medicamento": "Truvada"},
    )

    assert len(messages) == 2
    assert messages[1] == {"role": "user", "content": "quais efeitos do Truvada?"}

    system_content = messages[0]["content"]
    assert messages[0]["role"] == "system"
    assert "2026-05-23" in system_content
    assert "abc@c.us" in system_content
    assert "doc-protocolo-pep" in system_content
    assert "Paciente perguntou sobre PEP ontem." in system_content
    assert "Truvada" in system_content
    # treatment_info é renderizado como JSON dentro de <user_info>
    assert json.dumps({"has_active_treatment": True, "medicamento": "Truvada"}, ensure_ascii=False) in system_content


def test_build_handles_empty_optional_fields():
    builder = PromptBuilder()

    messages = builder.build(
        question="oi",
        today="2026-05-23",
        chat_id="abc@c.us",
        context_docs=[],
        history_summary="",
        treatment_info={},
    )

    assert messages[1]["content"] == "oi"
    assert "abc@c.us" in messages[0]["content"]
