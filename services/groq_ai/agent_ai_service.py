import os
from config.settings import Settings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq

class AIAgentService:

    def __init__(self):
        properties = Settings()
        os.environ['GROQ_API_KEY'] = properties.GROQ_API_KEY
        self.__chat = ChatGroq(model='llama-3.3-70b-versatile')

    def invoke(self, user_message):
        prompt = PromptTemplate(
            input_variables=['text'],
            template='''
            Voce deve tirar duvidas sobre a exposição de pessoas a agentes biologicos, como por exemplo: HIV, Hepatites, etc
            <text>
            {text}
            </text>
            '''
        )
        chain = prompt | self.__chat | StrOutputParser()
        response = chain.invoke({
            'text': user_message,
        })
        return response
