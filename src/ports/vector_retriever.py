from typing import Protocol


class VectorRetriever(Protocol):
    def query(self, embedding: list[float], top_k: int) -> list[str]: ...
