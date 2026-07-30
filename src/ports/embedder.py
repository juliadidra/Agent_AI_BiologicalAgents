from typing import Protocol


class Embedder(Protocol):
    def embed_query(self, text: str) -> list[float]: ...
