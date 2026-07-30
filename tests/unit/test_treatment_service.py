from src.ports.treatment_repository import Treatment
from src.services.treatment_service import TreatmentService
from tests.fakes.fake_messaging import FakeMessagingGateway
from tests.fakes.fake_treatment_repository import FakeTreatmentRepository


def _build(initial=None):
    repo = FakeTreatmentRepository(initial=initial)
    messaging = FakeMessagingGateway()
    service = TreatmentService(treatment_repository=repo, messaging=messaging)
    return service, repo, messaging


def test_schedule_creates_treatment_and_sends_confirmation():
    service, repo, messaging = _build()

    result = service.schedule(
        chat_id="abc@c.us",
        medicamento="Truvada",
        tratamento="HIV",
        inicio="2026-05-23",
        fim="2026-06-22",
    )

    assert "Truvada" in result and "registrado" in result
    assert len(repo._items) == 1
    assert repo._items[0].medicamento == "Truvada"
    assert messaging.sent == [("abc@c.us", result)]


def test_schedule_does_not_duplicate_active_treatment():
    existing = Treatment(
        id="1",
        chat_id="abc@c.us",
        medicamento="Truvada",
        tratamento="HIV",
        inicio="2026-05-01",
        fim="2026-05-31",
        status="ativo",
    )
    service, repo, messaging = _build(initial=[existing])

    result = service.schedule(
        chat_id="abc@c.us",
        medicamento="Truvada",
        tratamento="HIV",
        inicio="2026-05-23",
        fim="2026-06-22",
    )

    assert "já está ativo" in result
    assert len(repo._items) == 1
    assert messaging.sent == []


def test_cancel_removes_active_treatment_and_notifies():
    existing = Treatment(
        id="1",
        chat_id="abc@c.us",
        medicamento="Truvada",
        tratamento="HIV",
        inicio="2026-05-01",
        fim="2026-05-31",
        status="ativo",
    )
    service, repo, messaging = _build(initial=[existing])

    result = service.cancel(chat_id="abc@c.us", medicamento="Truvada")

    assert "cancelado" in result
    assert repo._items == []
    assert len(messaging.sent) == 1


def test_cancel_when_nothing_active_returns_message_and_does_not_notify():
    service, repo, messaging = _build()

    result = service.cancel(chat_id="abc@c.us", medicamento="Truvada")

    assert "Não há tratamento ativo" in result
    assert messaging.sent == []


def test_get_summary_returns_falsey_dict_when_no_treatment():
    service, _, _ = _build()
    summary = service.get_summary("abc@c.us")
    assert summary == {"has_active_treatment": False, "has_daily_reminders": False}


def test_get_summary_prefers_active_treatment():
    existing = [
        Treatment(id="1", chat_id="abc@c.us", medicamento="X", tratamento="HIV",
                  inicio="2026-01-01", fim="2026-01-31", status="inativo"),
        Treatment(id="2", chat_id="abc@c.us", medicamento="Truvada", tratamento="HIV",
                  inicio="2026-05-01", fim="2026-05-31", status="ativo"),
    ]
    service, _, _ = _build(initial=existing)

    summary = service.get_summary("abc@c.us")

    assert summary["has_active_treatment"] is True
    assert summary["has_daily_reminders"] is True
    assert summary["medicamento"] == "Truvada"
