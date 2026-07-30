from src.ports.embedder import Embedder
from src.ports.reranker import Reranker
from src.ports.vector_retriever import VectorRetriever


class RagPipeline:
    def __init__(
        self,
        embedder: Embedder,
        retriever: VectorRetriever,
        reranker: Reranker,
        top_k: int = 8,
    ):
        self._embedder = embedder
        self._retriever = retriever
        self._reranker = reranker
        self._top_k = top_k

    def search(self, query: str) -> list[str]:
        embedding = self._embedder.embed_query(query)
        documents = self._retriever.query(embedding, self._top_k)
        if not documents:
            return []
        return self._reranker.rerank(query, documents, self._top_k)
