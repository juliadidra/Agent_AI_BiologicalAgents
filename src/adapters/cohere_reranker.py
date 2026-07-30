import logging

import cohere

logger = logging.getLogger(__name__)


class CohereReranker:
    def __init__(
        self,
        api_key: str,
        model: str = "rerank-multilingual-v3.0",
    ):
        self._client = cohere.Client(api_key)
        self._model = model

    def rerank(self, query: str, documents: list[str], top_k: int) -> list[str]:
        if not documents:
            return []
        result = self._client.rerank(
            query=query,
            documents=documents,
            top_n=top_k,
            model=self._model,
            return_documents=True,
        )
        indices = [r.index for r in result.results]
        logger.info("Reranked document order (indices): %s", indices)
        return [documents[i] for i in indices]
