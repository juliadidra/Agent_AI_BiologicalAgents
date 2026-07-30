from langchain.memory import ConversationSummaryMemory
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq


class LangChainSummarizer:
    def __init__(self, api_key: str, model: str):
        chat = ChatGroq(model=model, temperature=0, api_key=api_key)
        self._memory = ConversationSummaryMemory(llm=chat, return_messages=True)

    def summarize(self, messages: list[dict]) -> str:
        if not messages:
            return ""
        objs = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "assistant":
                objs.append(AIMessage(content=content))
            elif role == "system":
                objs.append(SystemMessage(content=content))
            else:
                objs.append(HumanMessage(content=content))
        return self._memory.predict_new_summary(objs, "")
