from datetime import date
import json
import os
from jinja2 import Environment, FileSystemLoader
from langchain_groq import ChatGroq
from config.settings import Settings
from services.rag.rag_service import VectorStore
from tools.medical_reminder_tool import cancel_medication_treatment, schedule_medication_treatment
import logging
from tools.get_user_information_tool import UserInformationTool, get_user_information
logging.basicConfig(level=logging.DEBUG)


#TODO: separar as responsabilidades dessa classe em outras menores (ex: classe para gerenciar o chat, classe para gerenciar o retriever, etc)
class AIAgentService:

    def __init__(self):
        properties = Settings()
        os.environ['GROQ_API_KEY'] = properties.GROQ_API_KEY
        tool = [schedule_medication_treatment, get_user_information, cancel_medication_treatment]
        chat = ChatGroq(model=properties.GROQ_AI_MODEL) #estudar o chatgroq e o porque o agente age como se nao fosse um chat e sim um prompt normal
        self.__chat = chat.bind_tools(tools=tool)
        print("Chat model initialized with tools:", self.__chat)

    def create_prompt(self, history_messages, question, chat_id):

        user_info = UserInformationTool().get_user_info(chat_id)
        print("User info retrieved:", user_info)
        hoje = date.today().isoformat()

        docs_content = VectorStore().similarity_search(question)
        print("pure docs:", docs_content)

        #TODO:  montar as mensagens usando langchain (usar o history_messages da propria llm?, usar algum metodo do langchain para resgatar os docs)
        
        # Monte as mensagens para o modelo
        print("Retrieved docs for prompt context:", docs_content)
        # messages = [
        #     {"role": "system", "content": SYSTEM_TEMPLATE.replace("{context}", docs_content)}
        # ]

        filtered_history = [m for m in history_messages if m.get('body') and m.get('body').strip()]

        #TODO: aplicar o ConversationSummaryMemory do langchain para resumir o historico de mensagens

        #PROBLEMA: O historico esta indo de forma amontoada, sem diferenciar as mensagens do usuario e do assistente. logo, a ultima mensagem do usuario esta indo no historico sem ser diferenciada (o modelo se perde pois nao sabe qual foi a ultima pergunta do usuario)

        # possiveis solucoes:
        # 1. separar o historico de mensagens (enviando no system prompt) da ultima pergunta ou mensagem do usuario (enviando como mensagem do user)
        # 2. usar o ConversationSummaryMemory do langchain para resumir o historico (enviar no system prompt) e deixar apenas a ultima mensagem do usuario como mensagem do user.]
        env = Environment(loader=FileSystemLoader("prompts"))
        template = env.get_template("prompt_template.jinja")
       
        history_messages_chat = []
        for message in filtered_history:
            role = "assistant" if message.get('fromMe') else "user"
            history_messages_chat.append({"role": role, "content": message.get('body')})
        # messages.append({"role": "user", "content": question})

        #TODO: ajeitar isso aq dps
        history_chat_text = "\n".join(f"{m['role']}: {m['content']}" for m in history_messages_chat) if history_messages_chat else ""

        messages = [
            {"role": "system", "content": template.render({"hoje": hoje, "chat_id": chat_id, "context": docs_content, "history_messages": history_chat_text, "user_info": json.dumps(user_info)})},
            {"role": "user", "content": question}
        ]


        print("Messages sent to the model:", messages)
        # ----------------------------------------------------------------------------------------------------------------------
        try:
            response = self.__chat.invoke(messages)
            print("response:", response)
            #TODO: caso seja necessario criar novas tools, verificar a alternativa de criar um mcp server

            # As tools nao sao chamadas em tempo de execução (ou seja, o modelo nao chama as tools antes de gerar uma resposta e sim depois), isso nao é util para o proposito das tools (que é auxiliar o modelo a gerar respostas com base em dados externos)
            if hasattr(response, "tool_calls"):
                print("[LOG] Tool chamada pela IA:", response.tool_calls) #TODO: remover, criar um servico de log
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    args = tool_call["args"]
                    if isinstance(args, str):
                        args = json.loads(args)
                    if tool_name == "schedule_medication_treatment":
                        result = schedule_medication_treatment.invoke(args)
                        return result
                    if tool_name == "cancel_medication_treatment":
                        result = cancel_medication_treatment.invoke(args)
                        return result
                    if tool_name == "get_user_information":
                        result = get_user_information.invoke(args)
                        return result

            return getattr(response, "content", "")
        except Exception as e:
            logging.error(f"Error during response generation: {e}")
            return "Ocorreu um erro ao processar sua solicitação."
