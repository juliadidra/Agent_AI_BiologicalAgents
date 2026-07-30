import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)


class WahaMessaging:
    def __init__(self, base_url: str, api_key: str, session: str = "default"):
        self._base_url = base_url.rstrip("/") if base_url else "http://waha:3000"
        self._headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json",
        }
        self._session = session

    def send(self, chat_id: str, message: str) -> Any:
        if self._is_group(chat_id):
            return None
        url = f"{self._base_url}/api/sendText"
        payload = {"session": self._session, "chatId": chat_id, "text": message}
        return self._post_json(url, payload)

    def start_typing(self, chat_id: str) -> bool:
        if self._is_group(chat_id):
            return False
        url = f"{self._base_url}/api/startTyping"
        payload = {"session": self._session, "chatId": chat_id}
        return self._post_json(url, payload) is not None

    def stop_typing(self, chat_id: str) -> bool:
        url = f"{self._base_url}/api/stopTyping"
        payload = {"session": self._session, "chatId": chat_id}
        return self._post_json(url, payload) is not None

    def get_history(self, chat_id: str, limit: int) -> list[dict[str, Any]]:
        url = (
            f"{self._base_url}/api/{self._session}/chats/{chat_id}/messages"
            f"?limit={limit}&downloadMedia=false"
        )
        try:
            response = requests.get(url=url, headers=self._headers, timeout=10)
            response.raise_for_status()
            return response.json() or []
        except requests.RequestException:
            logger.exception("Failed to get history from %s", url)
            return []

    def _post_json(self, url: str, payload: dict) -> Any:
        try:
            response = requests.post(
                url=url, json=payload, headers=self._headers, timeout=10
            )
            response.raise_for_status()
            if not response.content:
                return True
            try:
                return response.json()
            except ValueError:
                return response.text
        except requests.RequestException:
            logger.exception("Failed POST to %s", url)
            return None

    @staticmethod
    def _is_group(chat_id: str) -> bool:
        return "@g" in (chat_id or "")
