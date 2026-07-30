from src.services.patient_service import PatientService
from tests.fakes.fake_patient_repository import FakePatientRepository


def test_get_profile_returns_empty_dict_when_missing():
    repo = FakePatientRepository()
    service = PatientService(patient_repository=repo)

    assert service.get_profile("abc@c.us") == {}


def test_ensure_profile_exists_is_idempotent():
    repo = FakePatientRepository()
    service = PatientService(patient_repository=repo)

    first = service.ensure_profile_exists("abc@c.us")
    second = service.ensure_profile_exists("abc@c.us")

    assert first == second
    assert repo.ensure_calls == ["abc@c.us", "abc@c.us"]
    assert len(repo._items) == 1


def test_get_profile_returns_stored_data():
    repo = FakePatientRepository()
    service = PatientService(patient_repository=repo)
    service.ensure_profile_exists("abc@c.us")

    profile = service.get_profile("abc@c.us")

    assert profile["chat_id"] == "abc@c.us"
    assert profile["health_state"] == {}
