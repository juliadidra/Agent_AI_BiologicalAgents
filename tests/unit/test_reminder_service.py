from datetime import date, timedelta
from unittest.mock import patch

from src.ports.treatment_repository import Treatment
from src.services.reminder_service import ReminderService
from tests.fakes.fake_messaging import FakeMessagingGateway
from tests.fakes.fake_treatment_repository import FakeTreatmentRepository


def _treatment(id_, chat, medicamento, inicio, fim, status="ativo"):
    return Treatment(
        id=id_,
        chat_id=chat,
        medicamento=medicamento,
        tratamento="HIV",
        inicio=inicio,
        fim=fim,
        status=status,
    )


def test_sends_reminders_for_treatments_within_window():
    today = date(2026, 5, 23)
    treatments = [
        _treatment("1", "in@c.us", "Truvada", "2026-05-01", "2026-06-01"),
        _treatment("2", "before@c.us", "Truvada", "2026-06-01", "2026-07-01"),
        _treatment("3", "after@c.us", "Truvada", "2026-04-01", "2026-05-10"),
    ]
    repo = FakeTreatmentRepository(initial=treatments)
    messaging = FakeMessagingGateway()
    service = ReminderService(treatment_repository=repo, messaging=messaging)

    with patch("src.services.reminder_service.date") as date_mock:
        date_mock.today.return_value = today
        sent = service.run_for_today()

    chat_ids_notified = [c for c, _ in messaging.sent]
    assert sent == 1
    assert chat_ids_notified == ["in@c.us"]


def test_marks_expired_treatments_inactive():
    today = date(2026, 5, 23)
    expired = _treatment("99", "old@c.us", "X", "2026-04-01", "2026-05-10")
    repo = FakeTreatmentRepository(initial=[expired])
    messaging = FakeMessagingGateway()
    service = ReminderService(treatment_repository=repo, messaging=messaging)

    with patch("src.services.reminder_service.date") as date_mock:
        date_mock.today.return_value = today
        service.run_for_today()

    assert "99" in repo.marked_inactive


def test_skips_treatments_with_invalid_dates():
    today = date(2026, 5, 23)
    bad = _treatment("1", "bad@c.us", "X", "not-a-date", "also-not")
    good = _treatment("2", "good@c.us", "Y", "2026-05-01", "2026-06-01")
    repo = FakeTreatmentRepository(initial=[bad, good])
    messaging = FakeMessagingGateway()
    service = ReminderService(treatment_repository=repo, messaging=messaging)

    with patch("src.services.reminder_service.date") as date_mock:
        date_mock.today.return_value = today
        sent = service.run_for_today()

    assert sent == 1
    assert messaging.sent[0][0] == "good@c.us"


def test_returns_zero_when_no_active_treatments():
    repo = FakeTreatmentRepository(initial=[])
    messaging = FakeMessagingGateway()
    service = ReminderService(treatment_repository=repo, messaging=messaging)

    assert service.run_for_today() == 0
    assert messaging.sent == []


def test_today_is_inclusive_at_start_and_end_of_window():
    today = date(2026, 5, 23)
    starting_today = _treatment("a", "s@c.us", "X", today.isoformat(), (today + timedelta(days=10)).isoformat())
    ending_today = _treatment("b", "e@c.us", "Y", (today - timedelta(days=10)).isoformat(), today.isoformat())
    repo = FakeTreatmentRepository(initial=[starting_today, ending_today])
    messaging = FakeMessagingGateway()
    service = ReminderService(treatment_repository=repo, messaging=messaging)

    with patch("src.services.reminder_service.date") as date_mock:
        date_mock.today.return_value = today
        sent = service.run_for_today()

    assert sent == 2
