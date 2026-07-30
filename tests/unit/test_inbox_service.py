from src.prompts.default_message import DEFAULT_MESSAGE
from src.services.inbox_service import InboxService
from tests.fakes.fake_messaging import FakeMessagingGateway


class _FakeConversation:
    def __init__(self, reply: str = "resposta gerada pela LLM"):
        self.reply = reply
        self.calls: list[tuple[str, str, list]] = []

    def handle_incoming(self, chat_id, question, history):
        self.calls.append((chat_id, question, history))
        return self.reply


def _build(history=None):
    messaging = FakeMessagingGateway()
    if history is not None:
        messaging.history["abc@c.us"] = history
    conversation = _FakeConversation()
    service = InboxService(
        conversation_service=conversation,
        messaging=messaging,
        history_limit=12,
    )
    return service, messaging, conversation


def test_first_interaction_sends_default_message_and_skips_llm():
    service, messaging, conversation = _build(history=[])

    result = service.process_message("abc@c.us", "oi")

    assert result["message"] == "Default message sent!"
    assert messaging.sent == [("abc@c.us", DEFAULT_MESSAGE)]
    assert conversation.calls == []


def test_subsequent_interaction_calls_conversation_and_sends_reply():
    history = [
        {"body": "oi", "fromMe": False},
        {"body": "olá! como posso ajudar?", "fromMe": True},
    ]
    service, messaging, conversation = _build(history=history)

    result = service.process_message("abc@c.us", "tudo bem?")

    assert result == {"message": "Message sent!"}
    assert conversation.calls == [("abc@c.us", "tudo bem?", history)]
    assert messaging.sent == [("abc@c.us", "resposta gerada pela LLM")]


def test_typing_indicator_starts_and_stops_even_on_default_path():
    service, messaging, _ = _build(history=[])

    service.process_message("abc@c.us", "oi")

    assert messaging.typing_started == ["abc@c.us"]
    assert messaging.typing_stopped == ["abc@c.us"]


def test_typing_stops_when_conversation_raises():
    history = [
        {"body": "oi", "fromMe": False},
        {"body": "ola", "fromMe": True},
    ]
    messaging = FakeMessagingGateway()
    messaging.history["abc@c.us"] = history

    class BrokenConversation:
        def handle_incoming(self, *args, **kwargs):
            raise RuntimeError("llm down")

    service = InboxService(
        conversation_service=BrokenConversation(),
        messaging=messaging,
        history_limit=12,
    )

    try:
        service.process_message("abc@c.us", "oi")
    except RuntimeError:
        pass

    assert messaging.typing_stopped == ["abc@c.us"]


def test_history_with_only_user_messages_is_treated_as_first_interaction():
    history = [
        {"body": "oi", "fromMe": False},
        {"body": "alguem ai?", "fromMe": False},
    ]
    service, messaging, conversation = _build(history=history)

    result = service.process_message("abc@c.us", "oi")

    assert result["message"] == "Default message sent!"
    assert conversation.calls == []


def test_assistant_messages_with_only_whitespace_dont_count_as_interaction():
    history = [
        {"body": "oi", "fromMe": False},
        {"body": "   ", "fromMe": True},
    ]
    service, _, conversation = _build(history=history)

    result = service.process_message("abc@c.us", "oi")

    assert result["message"] == "Default message sent!"
    assert conversation.calls == []
