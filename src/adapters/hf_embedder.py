from langchain_huggingface import HuggingFaceEmbeddings


class HFEmbedder:
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str = "cpu",
        normalize_embeddings: bool = True,
    ):
        self._embeddings = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={"device": device},
            encode_kwargs={"normalize_embeddings": normalize_embeddings},
        )

    def embed_query(self, text: str) -> list[float]:
        return self._embeddings.embed_query(text)
