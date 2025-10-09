import requests
from config.settings import Settings
from helpers.WahaHelpers import WahaHelpers


class WahaService:
    def __init__(self):
        self.properties = Settings()
        # Ensure base URL has no trailing slash
        if self.properties.WAHA_URL:
            self.base_url = self.properties.WAHA_URL.rstrip('/')
        else:
            self.base_url = 'http://waha:3000'

    def send_message(self, chat_id, message):
        if WahaHelpers.block_group_messages(chat_id):
            return None

        url = f"{self.base_url}/api/sendText"
        headers = {'Content-Type': 'application/json'}
        payload = {"session": "default", "chatId": chat_id, "text": message}
        try:
            response = requests.post(url=url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            if response.content:
                try:
                    return response.json()
                except ValueError:
                    return response.text
            return None
        except requests.RequestException as e:
            print(f"[WahaService] failed to send message to {url}: {e}")
            return None

    def start_typing(self, chat_id):
        if WahaHelpers.block_group_messages(chat_id):
            return None

        url = f"{self.base_url}/api/startTyping"
        headers = {'Content-Type': 'application/json'}
        payload = {"session": "default", "chatId": chat_id}
        try:
            response = requests.post(url=url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"[WahaService] failed to start typing at {url}: {e}")
            return False

    def stop_typing(self, chat_id):
        url = f"{self.base_url}/api/stopTyping"
        headers = {'Content-Type': 'application/json'}
        payload = {"session": "default", "chatId": chat_id}
        try:
            response = requests.post(url=url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"[WahaService] failed to stop typing at {url}: {e}")
            return False

    def get_history_messages(self, chat_id, limit):
        url = f'{self.base_url}/api/default/chats/{chat_id}/messages?limit={limit}&downloadMedia=false'
        headers = {'Content-Type': 'application/json'}
        try:
            response = requests.get(url=url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"[WahaService] failed to get history from {url}: {e}")
            return None


