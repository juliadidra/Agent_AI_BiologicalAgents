from typing import Protocol


class Reranker(Protocol):
    def rerank(self, query: str, documents: list[str], top_k: int) -> list[str]: ...
