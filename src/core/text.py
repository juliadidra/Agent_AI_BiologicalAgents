import re

_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_CLOSE_TAG = "</think>"


def strip_reasoning(text: str) -> str:
    """Remove blocos de raciocínio (<think>...</think>) que modelos de
    reasoning (ex.: qwen3, deepseek-r1) emitem dentro do `content`.

    Modelos de reasoning colocam a resposta final após o último </think>,
    então cortamos até lá; em seguida limpamos eventuais pares residuais.
    """
    if not text:
        return text

    lowered = text.lower()
    if _CLOSE_TAG in lowered:
        idx = lowered.rfind(_CLOSE_TAG)
        text = text[idx + len(_CLOSE_TAG):]

    text = _THINK_BLOCK.sub("", text)
    return text.strip()
