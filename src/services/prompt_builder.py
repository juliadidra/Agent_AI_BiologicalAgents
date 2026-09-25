import json
from typing import Any

from jinja2 import Environment, FileSystemLoader


class PromptBuilder:
    def __init__(
        self,
        template_dir: str = "src/prompts",
    ):
        env = Environment(loader=FileSystemLoader(template_dir))
        env.filters["json_pt"] = lambda v: json.dumps(v, ensure_ascii=False)
        self._env = env

    def build(
        self,
        template_name: str,
        question: str,
        **context: Any,
    ) -> list[dict[str, str]]:
        """Renderiza `template_name` com `context` como mensagem de sistema e
        retorna a lista [system, user] pronta para o LLM."""
        template = self._env.get_template(template_name)
        system_content = template.render(**context)
        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": question},
        ]
