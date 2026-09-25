from src.services.prompt_builder import PromptBuilder


def _build(**overrides):
    builder = PromptBuilder()
    context = {
        "hoje": "2026-05-23",
        "chat_id": "abc@c.us",
        "history_summary": "Paciente falou sobre PEP ontem.",
        "treatment_info": {"has_active_treatment": True, "medicamento": "Truvada"},
        "patient_profile": {"health_state": "estável"},
    }
    context.update(overrides)
    return builder.build("orchestrator.jinja", question=context.pop("question", "oi"), **context)


def test_build_returns_system_and_user_messages():
    messages = _build(question="tudo bem?")

    assert len(messages) == 2
    assert messages[1] == {"role": "user", "content": "tudo bem?"}
    assert messages[0]["role"] == "system"

    system_content = messages[0]["content"]
    assert "Paciente falou sobre PEP ontem." in system_content
    assert "Truvada" in system_content
    # o partial de guardrails é incluído
    assert "GUARDRAILS" in system_content


def test_json_pt_filter_keeps_unicode():
    messages = _build(treatment_info={"tratamento": "profilaxia pós-exposição"})

    # ensure_ascii=False: acentos não viram \uXXXX
    assert "profilaxia pós-exposição" in messages[0]["content"]


def test_orchestrator_template_renders_chat_id():
    messages = _build(chat_id="5511999@c.us")

    # o chat_id é injetado no prompt para a tool de agendamento
    assert "5511999@c.us" in messages[0]["content"]
