import logging
from config.settings import Settings
import chromadb
import cohere

from langchain_huggingface import HuggingFaceEmbeddings
logging.basicConfig(level=logging.DEBUG)

properties = Settings()

class VectorStore:
    def __init__(self):
        self.embedding = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",  # Mais rápido e leve que padrão
        model_kwargs={"device": "cpu"},  # Use "cuda" se houver GPU disponível
        encode_kwargs={"normalize_embeddings": True}  # Melhor para similarity search
    )
        self.vector_store = chromadb.CloudClient(
        api_key=properties.CHROMA_API_KEY,
        tenant=properties.CHROMA_TENANT_ID,
        database=properties.CHROMA_DATABASE
        )
        self.co = cohere.Client(properties.COHERE_API_KEY)

    def similarity_search(self, question):
        collection = self.vector_store.get_collection(name='tcc-grobid-data')
        emb = self.embedding.embed_query(question)
        result = collection.query(
            query_embeddings=[emb],
            n_results=8
        )
        documents = []
        docs_list = result.get('documents', [[]])[0]
        for text in docs_list:
            documents.append(text)

        rerank_docs = self.co.rerank(
            query=question, documents=documents, top_n=8, model="rerank-multilingual-v3.0", return_documents=True
        )
        
        final_doc_indices = [r.index for r in rerank_docs.results]
        final_docs = [documents[i] for i in final_doc_indices]
        logging.info("Reranked documents order (indices): %s", final_doc_indices)
        return final_docs
