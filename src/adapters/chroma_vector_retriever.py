import chromadb


class ChromaVectorRetriever:
    def __init__(
        self,
        api_key: str,
        tenant: str,
        database: str,
        collection_name: str,
    ):
        self._client = chromadb.CloudClient(
            api_key=api_key,
            tenant=tenant,
            database=database,
        )
        self._collection_name = collection_name

    def query(self, embedding: list[float], top_k: int) -> list[str]:
        collection = self._client.get_collection(name=self._collection_name)
        result = collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
        )
        docs_list = result.get("documents", [[]])[0]
        return list(docs_list)
