import requests
from config.settings import Settings
from helpers.WahaHelpers import WahaHelpers

class WahaService:
    def __init__(self):
        self.properties = Settings()

    def send_message(self, chat_id, message):
        if(WahaHelpers.block_group_messages(chat_id)):
            return
        
        url = f"{self.properties.API_URL}/api/sendText"
        headers = {
            'Content-Type': 'application/json',
        }
        payload = {
            "session": "default",
            "chatId": chat_id,
            "text": message
        }
        response = requests.post(url=url, json=payload, headers=headers)
    
    def start_typing(self, chat_id):

        if(WahaHelpers.block_group_messages(chat_id)):
            return

        url = f"{self.properties.API_URL}/api/startTyping"
        headers = {
            'Content-Type': 'application/json',
        }

        payload = {
            "session": "default",
            "chatId": chat_id
        }
        response = requests.post(url=url, json=payload, headers=headers)

    def stop_typing(self, chat_id):
        url = f"{self.properties.API_URL}/api/stopTyping"
        headers = {
            'Content-Type': 'application/json',
        }

        payload = {
            "session": "default",
            "chatId": chat_id
        }
        response = requests.post(url=url, json=payload, headers=headers)

    def get_history_messages(self, chat_id, limit):
        url = f'{self.properties.API_URL}/api/default/chats/{chat_id}/messages?limit={limit}&downloadMedia=false'
        headers = {
            'Content-Type': 'application/json',
        }
        response = requests.get(
            url=url,
            headers=headers,
        )
        return response.json()


