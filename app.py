from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from services.groq_ai.agent_ai_service import AIAgentService
from services.waha.waha_service import WahaService


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post('/agent/webhook')
async def agent_webhook(request: Request):
    data = await request.json()
    print("received_data", data)

    # Validação do payload
    payload = data.get("payload")
    if not payload or not isinstance(payload, dict):
        # Acknowledge eventos genéricos (evita retries de webhook)
        return JSONResponse(status_code=200, content={"ignored": "missing or invalid 'payload'"})

    # Extrai chat id de formas possíveis
    chat_id = payload.get("from") or payload.get("chatId") or payload.get("chat_id")

    # Extrai corpo da mensagem (verifica variantes comuns)
    received_message = payload.get("body") or payload.get("message") or payload.get("text")
    if not received_message:
        # Evento não é uma mensagem (ex.: session.status) — apenas confirmar recebimento
        return JSONResponse(status_code=200, content={"ignored": "non-message event"})

    # Processa mensagem normalmente
    waha = WahaService()
    ai_agent = AIAgentService()

    waha.start_typing(chat_id=chat_id)

    history_messages = waha.get_history_messages(chat_id=chat_id, limit=10)

    response_message = ai_agent.create_prompt(history_messages=history_messages, question=received_message, chat_id=chat_id)
    print("response_message: ", response_message)

    waha.send_message(chat_id=chat_id, message=response_message)
    waha.stop_typing(chat_id=chat_id)

    return JSONResponse(status_code=200, content={"message": "Message sent!"})

# class SendMessageBody(BaseModel):
#     question: str

# @app.post('/agent/send_message')
# async def agent_send_message(body: SendMessageBody):
#     # data = await request.json() 
#     # print("received_data", data)

#     # waha = WahaService()
#     ai_agent = AIAgentService()

#     # print("data payload: ", data.get("payload").get("from"))
#     # chat_id = data.get("payload").get("from")

#     # receveid_message = data['payload']['body']

#     # waha.start_typing(chat_id=chat_id)

#     history_messages = ["ola", "tudo bem?", "como posso ajudar?"]
#     chat_id = 123

#     response_message = ai_agent.create_prompt(history_messages=history_messages, question=body.question, chat_id=chat_id)
#     print("response_message: ", response_message)
    
#     # waha.send_message(chat_id=chat_id, message=response_message)

#     # waha.stop_typing(chat_id=chat_id)

#     return JSONResponse(status_code=200, content={"message": {"response": response_message}})

