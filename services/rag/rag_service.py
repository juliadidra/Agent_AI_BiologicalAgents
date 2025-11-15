from config.settings import Settings
import chromadb
import cohere

from langchain_huggingface import HuggingFaceEmbeddings

properties = Settings()

class VectorStore:
    def __init__(self):
        self.embedding = HuggingFaceEmbeddings()
        self.vector_store = chromadb.CloudClient(
        api_key=properties.CHROMA_API_KEY,
        tenant='61e7981b-97e1-4d61-9631-874e85036da2',
        database='tcc-ai-agent'
        )
        self.co = cohere.Client(properties.COHERE_API_KEY)

    def similarity_search(self, question):
        collection = self.vector_store.get_collection(name='langchain')
        print("Collection retrieved:", collection)
        emb = self.embedding.embed_query(question)
        print("Query embedding:", emb)
        result = collection.query(
            query_embeddings=[emb],
            n_results=8
        )
        print("Raw retrieved result:", result)
        documents = []
        docs_list = result.get('documents', [[]])[0]
        for text in docs_list:
            documents.append(text)

        print("Retrieved docs:", documents)

        rerank_docs = self.co.rerank(
            query=question, documents=documents, top_n=8, model="rerank-multilingual-v3.0"
        )
        
        final_doc_index = rerank_docs.results[0].index
        return documents[final_doc_index]
