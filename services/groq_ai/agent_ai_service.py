import os
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings

from config.settings import Settings
from tools.medical_reminder_tool import registrar_tratamento
import logging
logging.basicConfig(level=logging.DEBUG)

class AIAgentService:

    def __init__(self):
        properties = Settings()
        os.environ['GROQ_API_KEY'] = properties.GROQ_API_KEY
        tool = [registrar_tratamento]
        chat = ChatGroq(model=properties.GROQ_AI_MODEL)
        self.__chat = chat.bind_tools(tool, tool_choice="auto")
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
        MAX_HISTORY_MESSAGES = 5
        messages = []
        for message in history_messages[-MAX_HISTORY_MESSAGES:]:
            message_class = HumanMessage if message.get('fromMe') else AIMessage
            messages.append(message_class(content=message.get('body')))
        messages.append(HumanMessage(content=question))
        return messages


    def create_prompt(self, history_messages, question, chat_id):
        SYSTEM_TEMPLATE = '''
        Responda as perguntas dos usuários com base no contexto abaixo.
        Você é um assistente especializado em tirar dúvidas e prestar auxilio á pacientes que foram expostos a agentes biológicos.
        Você deve tirar dúvidas dos pacientes, prestar apoio emocional (se necessário) e também terá o papel de relembrar aos paciente que tome as medicações indicadas para cada caso.

        Instruções:
        1. Apresentação:
            - Inicialmente você deve se apresentar e perguntar como pode ajudar o paciente.
            - Voce deve indicar ao paciente que voce pode agendar lembretes para as medicações que ele estiver tomando.
        2. Comportamento:
            - Em seguida, você pode fazer perguntas para entender melhor a situação do paciente e oferecer o suporte necessário.    
            - Você deve sempre se lembrar de que o paciente pode estar em um estado emocional delicado e que você deve ser gentil e compreensivo.
            - Suas respostas devem ser claras e objetivas, evitando jargões médicos complexos.
            - Responda sempre em português brasileiro.
            - importante: Responda de forma curta, para que seja uma conversa fluida e natural.
        3. Agendar lembretes de medicamentos:
            - voce deve ficar atento para os 2 cenarios abaixo:
                1. O paciente menciona que esta fazendo algum tratamento ou tomando alguma medicação.
                    - Neste caso, você deve perguntar sobre os detalhes do tratamento e oferecer agendar lembretes.
                        - Caso o usuario queira agendar um lembrete, você deve coletar as informações necessárias e chamar a tool que ira agendar os lembretes. Voce devera coletar as seguintes informações:
                          - nome do medicamento, o tratamento (se é para hiv, sifilis ou hepatite), a data inicial e final do tratamento, o chat_id: {chat_id}
                            - IMPORTANTE: Caso o paciente nao saiba mencionar a data final, voce deve usar as informações do seu contexto, identificando a duração do tratamento e calculando a data final baseando-se da na data inicial fornecida. (ex: 30 dias após a data inicial)
                2. O paciente solicita um lembrete para tomar a medicação.
                    - Caso o paciente solicite o serviço de lembretes voce deve pedir as informações necessarias para o agendamento:
                        - nome do medicamento, o tratamento (se é para hiv, sifilis ou hepatite), a data inicial e final do tratamento.
                            - IMPORTANTE: Caso o paciente nao saiba mencionar a data final, voce deve usar as informações do seu contexto, identificando a duração do tratamento e calculando a data final baseando-se da na data inicial fornecida. (ex: 30 dias após a data inicial)


        Responda de forma natural, agradável e respeitosa. Seja objetivo nas respostas, com informações
        claras e diretas. Foque em ser natural e humanizado, como um diálogo comum entre duas pessoas.
        Leve em consideração também o histórico de mensagens da conversa com o usuário.
        

        <context>
        {{context}}
        </context>
        '''.format(chat_id=chat_id)

        docs = self.__retriever.invoke(question)
        MAX_DOCS = 5  # limite de documentos
        docs = docs[:MAX_DOCS]

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
        print("chamada llm: ", self.__chat)

        print("docs: ", docs)

        try:
            response = document_chain.invoke(
                {
                    'context': docs,
                    'messages': self.__build_messages(history_messages, question),
                }
            )

            # print("messages: ", response["messages"])

            print("response: ", response)
            if isinstance(response, dict):
                if "tool_calls" in response:
                    print("[LOG] Tool chamada pela IA:", response["tool_calls"])
                elif "function_call" in response:
                    print("[LOG] Function call detectada:", response["function_call"])
                elif "content" in response:
                    print("[LOG] Conteúdo da resposta:", response["content"])
            return response 
        except Exception as e:
            print(f"Error during response generation: {e}")
