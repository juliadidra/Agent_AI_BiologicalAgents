from typing import Protocol


class Summarizer(Protocol):
    def summarize(self, messages: list[dict]) -> str: ...
