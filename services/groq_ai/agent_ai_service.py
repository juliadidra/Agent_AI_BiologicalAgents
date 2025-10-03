from datetime import date
import json
import os
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.tools import tool


from config.settings import Settings
from tools.medical_reminder_tool import schedule_medication_treatment
import logging
logging.basicConfig(level=logging.DEBUG)

class AIAgentService:

    def __init__(self):
        properties = Settings()
        os.environ['GROQ_API_KEY'] = properties.GROQ_API_KEY
        tool = [schedule_medication_treatment]
        chat = ChatGroq(model=properties.GROQ_AI_MODEL)
        self.__chat = chat.bind_tools(tools=tool)
        print("Chat model initialized with tools:", self.__chat)
        # self.__chat = chat
        self.__retriever = self.__build_retriever()


    def __build_retriever(self):
        persist_directory = '/app/chroma_data'
        embedding = HuggingFaceEmbeddings()

        vector_store = Chroma(
            persist_directory=persist_directory,
            embedding_function=embedding,
        )
        return vector_store.as_retriever(
            search_kwargs={'k': 5},
        )
    
    @tool
    def greet(name: str) -> str:
        """
        recebe o nome do usuario e Saúda o usuário pelo nome.
        """
        return f"Olá, {name}! Como posso ajudar você hoje?"
    
    # def __build_messages(self, history_messages, question):
    #     MAX_HISTORY_MESSAGES = 5
    #     messages = []
    #     filtered_history = [
    #     m for m in history_messages[-MAX_HISTORY_MESSAGES:]
    #     if m.get('body') and m.get('body').strip()
    #     ]
    #     for message in filtered_history[-MAX_HISTORY_MESSAGES:]:
    #         message_class = HumanMessage if message.get('fromMe') else AIMessage
    #         messages.append(message_class(content=message.get('body')))
    #     messages.append(HumanMessage(content=question))
    #     return messages


    def create_prompt(self, history_messages, question, chat_id):
        hoje = date.today().isoformat()
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
            - MUITO IMPORTANTE: Mensagens de lembrete diário (ex: "Já tomou sua medicação hoje?") não significam que um novo tratamento precisa ser registrado. 
            Essas mensagens são apenas lembretes automáticos e não devem levar ao agendamento de novo tratamento.

                
            - para fins de contexto (caso o usuario nao saiba mencionar a data inicial ou ele indique que esta data é hoje) voce deve considerar a data de hoje: {hoje}
            - IMPORTANTE: As datas devem estar no formato ISO (YYYY-MM-DD). Por mais que o usuario mencione a data em outro formato, voce deve sempre converter para o formato YYYY-MM-DD.


        Responda de forma natural, agradável e respeitosa. Seja objetivo nas respostas, com informações
        claras e diretas. Foque em ser natural e humanizado, como um diálogo comum entre duas pessoas.
        Leve em consideração também o histórico de mensagens da conversa com o usuário.
        

        <context>
        {{context}}
        </context>
        '''.format(chat_id=chat_id, hoje=hoje)

        docs = self.__retriever.invoke(question)
        MAX_DOCS = 1
        docs = docs[:MAX_DOCS]

        # Monte as mensagens para o modelo
        messages = [
            {"role": "system", "content": SYSTEM_TEMPLATE.replace("{{context}}", "\n".join([d.page_content for d in docs]))}
        ]
        # Adicione histórico filtrado
        # if (isinstance(history_messages, list)):
        #     messages.append({"role": "user", "content": history_messages[0]})
        #     messages.append({"role": "user", "content": question})
           
        # else:
        filtered_history = [
            m for m in history_messages[-5:]
            if m.get('body') and m.get('body').strip()
        ]
        for message in filtered_history:
            role = "user" if message.get('fromMe') else "assistant"
            messages.append({"role": role, "content": message.get('body')})
        # Adicione a pergunta atual
        messages.append({"role": "user", "content": question})

        try:
            response = self.__chat.invoke(messages)
            print("response:", response)
            # Se houver tool_calls, logue
            if hasattr(response, "tool_calls"):
                print("[LOG] Tool chamada pela IA:", response.tool_calls)
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    args = tool_call["args"]
                    # Se os argumentos vierem como string JSON, faça o parse
                    if isinstance(args, str):
                        args = json.loads(args)
                    # Chame a função Python correspondente
                    if tool_name == "schedule_medication_treatment":
                        result = schedule_medication_treatment.invoke(args)
                        return result
                    # Adicione outros tools aqui conforme necessário
                # return "Tool chamada, mas não implementada."
            # Se não houver tool_calls, retorne o conteúdo normal
            return getattr(response, "content", "")
        except Exception as e:
            print(f"Error during response generation: {e}")
            return "Ocorreu um erro ao processar sua solicitação."
