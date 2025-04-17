import random
import time
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from services.waha_service import WahaService
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
    chat_id = data['payload']['from']

    waha.start_typing(chat_id=chat_id)
    time.sleep(random.randint(3,10))
    waha.send_message(chat_id=chat_id, message="Testando meu bot!")
    waha.stop_typing(chat_id=chat_id)

    return JSONResponse(status_code=200, content={"message": "Message sent!"})

