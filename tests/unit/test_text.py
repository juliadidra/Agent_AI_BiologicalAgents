from src.core.text import strip_reasoning


def test_strips_think_block_and_returns_final_answer():
    raw = "\n<think>\nAnalisando o pedido do paciente...\ndecisão: responder com calma\n</think>\n\nOi! Tudo bem por aqui, e você?"
    assert strip_reasoning(raw) == "Oi! Tudo bem por aqui, e você?"


def test_no_think_block_is_unchanged_except_trim():
    assert strip_reasoning("  resposta simples  ") == "resposta simples"


def test_uses_last_closing_tag_when_multiple():
    raw = "<think>a</think>meio<think>b</think>resposta final"
    assert strip_reasoning(raw) == "resposta final"


def test_empty_input():
    assert strip_reasoning("") == ""


def test_router_label_not_polluted_by_reasoning_mentions():
    # o rótulo real vem depois do </think>, mesmo que o raciocínio cite outras rotas
    raw = "<think>poderia ser TREATMENT ou CLINICAL...</think>SUPPORT"
    assert strip_reasoning(raw) == "SUPPORT"
