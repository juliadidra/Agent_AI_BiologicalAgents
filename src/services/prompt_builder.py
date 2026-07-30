import json
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader


class PromptBuilder:
    def __init__(
        self,
        template_dir: str = "src/prompts",
        template_name: str = "prompt_template.jinja",
    ):
        env = Environment(loader=FileSystemLoader(template_dir))
        self._template = env.get_template(template_name)

    def build(
        self,
        *,
        question: str,
        today: str,
        chat_id: str,
        context_docs: list[str],
        history_summary: str,
        treatment_info: dict[str, Any],
        patient_profile: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, str]]:
        system_content = self._template.render(
            hoje=today,
            chat_id=chat_id,
            context=context_docs,
            history_messages=history_summary,
            user_info=json.dumps(treatment_info, ensure_ascii=False),
            patient_profile=patient_profile or {},
        )
        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": question},
        ]
