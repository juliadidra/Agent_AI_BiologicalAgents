import logging
from config.settings import Settings
import chromadb
import cohere

from langchain_huggingface import HuggingFaceEmbeddings
logging.basicConfig(level=logging.DEBUG)

properties = Settings()

class VectorStore:
    def __init__(self):
        self.embedding = HuggingFaceEmbeddings()
        self.vector_store = chromadb.CloudClient(
        api_key=properties.CHROMA_API_KEY,
        tenant=properties.CHROMA_TENANT_ID,
        database=properties.CHROMA_DATABASE
        )
        self.co = cohere.Client(properties.COHERE_API_KEY)

    def similarity_search(self, question):
        collection = self.vector_store.get_collection(name='langchain')
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
            query=question, documents=documents, top_n=8, model="rerank-multilingual-v3.0"
        )
        
        final_doc_index = rerank_docs.results[0].index
        logging.info("Reranked document: %s", documents[final_doc_index])
        return documents[final_doc_index]
