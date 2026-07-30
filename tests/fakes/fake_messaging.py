from typing import Any


class FakeMessagingGateway:
    def __init__(self):
        self.sent: list[tuple[str, str]] = []
        self.typing_started: list[str] = []
        self.typing_stopped: list[str] = []
        self.history: dict[str, list[dict]] = {}

    def send(self, chat_id: str, message: str) -> Any:
        self.sent.append((chat_id, message))
        return {"ok": True}

    def start_typing(self, chat_id: str) -> bool:
        self.typing_started.append(chat_id)
        return True

    def stop_typing(self, chat_id: str) -> bool:
        self.typing_stopped.append(chat_id)
        return True

    def get_history(self, chat_id: str, limit: int) -> list[dict]:
        return list(self.history.get(chat_id, []))[-limit:]
