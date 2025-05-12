import os
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings

from config.settings import Settings

class AIAgentService:

    def __init__(self):
        properties = Settings()
        os.environ['GROQ_API_KEY'] = properties.GROQ_API_KEY
        self.__chat = ChatGroq(model='llama-3.3-70b-versatile')
        self.__retriever = self.__build_retriever()

    def __build_retriever(self):
        persist_directory = '/app/chroma_data'
        embedding = HuggingFaceEmbeddings()

        vector_store = Chroma(
            persist_directory=persist_directory,
            embedding_function=embedding,
        )
        return vector_store.as_retriever(
            search_kwargs={'k': 30},
        )
    
    def __build_messages(self, history_messages, question):
        messages = []
        for message in history_messages:
            message_class = HumanMessage if message.get('fromMe') else AIMessage
            messages.append(message_class(content=message.get('body')))
        messages.append(HumanMessage(content=question))
        return messages


    def invoke(self, history_messages, question):
        SYSTEM_TEMPLATE = '''
        Responda as perguntas dos usuários com base no contexto abaixo.
        Você é um assistente especializado em tirar dúvidas e prestar auxilio a pacientes de um pronto atendimento que é especializado em exposição a agentes biológicos.
        Você deve tirar dúvidas dos pacientes, prestar apoio emocional (se necessário) e também terá o papel de relembrar aos paciente que tome as medicações indicadas para cada caso.

        Instruções:
        - Inicialmente você deve se apresentar e perguntar como pode ajudar o paciente.
        - Em seguida, você pode fazer perguntas para entender melhor a situação do paciente e oferecer o suporte necessário.    
        - Você deve sempre se lembrar de que o paciente pode estar em um estado emocional delicado e que você deve ser gentil e compreensivo.
        - Suas respostas devem ser claras e objetivas, evitando jargões médicos complexos.
        - importante: Responda de forma curta, para que seja uma conversa fluida e natural.
            - Sua resposta NAO deve ser grande, como um texto longo.

        Responda de forma natural, agradável e respeitosa. Seja objetivo nas respostas, com informações
        claras e diretas. Foque em ser natural e humanizado, como um diálogo comum entre duas pessoas.
        Leve em consideração também o histórico de mensagens da conversa com o usuário.
        Responda sempre em português brasileiro.

        <context>
        {context}
        </context>
        '''

        docs = self.__retriever.invoke(question)
        question_answering_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    'system',
                    SYSTEM_TEMPLATE,
                ),
                MessagesPlaceholder(variable_name='messages'),
            ]
        )
        document_chain = create_stuff_documents_chain(self.__chat, question_answering_prompt)
        response = document_chain.invoke(
            {
                'context': docs,
                'messages': self.__build_messages(history_messages, question),
            }
        )
        return response
