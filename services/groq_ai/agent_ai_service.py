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
from langchain.memory import ConversationSummaryMemory
from langchain.schema import SystemMessage, HumanMessage, AIMessage
logging.basicConfig(level=logging.DEBUG)


#TODO: separar as responsabilidades dessa classe em outras menores (ex: classe para gerenciar o chat, classe para gerenciar o retriever, etc)
class AIAgentService:

    def __init__(self):
        properties = Settings()
        os.environ['GROQ_API_KEY'] = properties.GROQ_API_KEY
        tool = [schedule_medication_treatment, get_user_information, cancel_medication_treatment]
        chat = ChatGroq(model=properties.GROQ_AI_MODEL)
        self.__chat = chat.bind_tools(tools=tool)
        logging.info("Chat model initialized with tools: %s", self.__chat)
        summary_chat = ChatGroq(model=properties.GROQ_AI_MODEL, temperature=0)
        self.memory = ConversationSummaryMemory(llm=summary_chat, return_messages=True)

    def create_prompt(self, history_messages, question, chat_id):

        user_info = UserInformationTool().get_user_info(chat_id)
        logging.info("User info retrieved:", user_info)
        hoje = date.today().isoformat()
        docs_content = VectorStore().similarity_search(question)
        logging.info("doc retrieved:  %s", docs_content)

        #TODO:  montar as mensagens usando langchain (usar o history_messages da propria llm?, usar algum metodo do langchain para resgatar os docs)
        

        filtered_history = [m for m in history_messages if m.get('body') and m.get('body').strip()]

        #TODO: aplicar o ConversationSummaryMemory do langchain para resumir o historico de mensagens

        # 2. usar o ConversationSummaryMemory do langchain para resumir o historico (enviar no system prompt) e deixar apenas a ultima mensagem do usuario como mensagem do user.]
        env = Environment(loader=FileSystemLoader("prompts"))
        template = env.get_template("prompt_template.jinja")
       
        history_messages_chat = []
        for message in filtered_history:
            role = "assistant" if message.get('fromMe') else "user"
            history_messages_chat.append({"role": role, "content": message.get('body')})

        #TODO: ajeitar isso aq dps
        history_chat_text = "\n".join(f"{m['role']}: {m['content']}" for m in history_messages_chat) if history_messages_chat else ""
 

        # Converter o histórico para objetos de mensagemdo langchain antes de resumir
        message_objs = []
        for m in history_messages_chat:
            if m['role'] == "assistant":
                message_objs.append(AIMessage(content=m['content']))
            elif m['role'] == "system":
                message_objs.append(SystemMessage(content=m['content']))
            else:
                message_objs.append(HumanMessage(content=m['content']))

        previous_summary = ""
        history_chat_text = self.memory.predict_new_summary(message_objs, previous_summary)
        logging.info("Summary of previous conversation: %s", history_chat_text)   

        messages = [
            {"role": "system", "content": template.render({"hoje": hoje, "chat_id": chat_id, "context": docs_content, "history_messages": history_chat_text, "user_info": json.dumps(user_info)})},
            {"role": "user", "content": question}
        ]


        logging.info("Messages sent to the model: %s", messages)
        try:
            response = self.__chat.invoke(messages)
            logging.info("response: %s", response)

            if hasattr(response, "tool_calls"):
                logging.info("Tool chamada pela IA: %s", response.tool_calls)
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
