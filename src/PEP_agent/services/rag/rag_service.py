import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from config.settings import Settings
from langchain_community.document_loaders import PyPDFLoader
from langchain_huggingface import HuggingFaceEmbeddings

properties = Settings()

os.environ['GROQ_API_KEY'] = properties.GROQ_API_KEY
os.environ['HUGGINGFACE_API_KEY'] = properties.HUGGINGFACE_API_KEY

if __name__ == '__main__':
    file_path = '/app/services/rag/data/PCDT_Tratado.pdf'
    loader = PyPDFLoader(file_path)
    docs = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    )
    chunks = text_splitter.split_documents(
        documents=docs,
    )

    #TODO: Posteriormente isolar a parte do banco de dados
    persist_directory = '/app/chroma_data'

    embedding = HuggingFaceEmbeddings()
    vector_store = Chroma(
        embedding_function=embedding,
        persist_directory=persist_directory,
    )
    vector_store.add_documents(
        documents=chunks,
    )
