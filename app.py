import random
import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from services.groq_ai.agent_ai_service import AIAgentService
from services.waha.waha_service import WahaService
from fastapi.middleware.cors import CORSMiddleware

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

    waha = WahaService()
    ai_agent = AIAgentService()

    chat_id = data['payload']['from']
    receveid_message = data['payload']['body']

    waha.start_typing(chat_id=chat_id)

    history_messages = waha.get_history_messages(chat_id=chat_id, limit=10)

    response_message = ai_agent.create_prompt(history_messages=history_messages, question=receveid_message)
    
    waha.send_message(chat_id=chat_id, message=response_message)

    waha.stop_typing(chat_id=chat_id)

    return JSONResponse(status_code=200, content={"message": "Message sent!"})

