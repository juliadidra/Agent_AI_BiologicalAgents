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


def test_update_profile_creates_and_stores_delta():
    repo = FakePatientRepository()
    service = PatientService(patient_repository=repo)

    health = service.update_profile("abc@c.us", {"condicoes": ["HIV"], "alergias": ["dipirona"]})

    assert health == {"condicoes": ["HIV"], "alergias": ["dipirona"]}
    assert service.get_profile("abc@c.us")["health_state"] == health


def test_update_profile_accumulates_lists_without_duplicating():
    repo = FakePatientRepository()
    service = PatientService(patient_repository=repo)
    service.update_profile("abc@c.us", {"condicoes": ["HIV"]})

    # nova condição é somada; repetida (case-insensitive) é ignorada
    health = service.update_profile("abc@c.us", {"condicoes": ["sífilis", "hiv"]})

    assert health["condicoes"] == ["HIV", "sífilis"]


def test_update_profile_overwrites_text_and_preserves_untouched_keys():
    repo = FakePatientRepository()
    service = PatientService(patient_repository=repo)
    service.update_profile("abc@c.us", {"condicoes": ["HIV"], "tipo_exposicao": "sexual"})

    health = service.update_profile("abc@c.us", {"tipo_exposicao": "ocupacional"})

    assert health["tipo_exposicao"] == "ocupacional"  # sobrescreveu
    assert health["condicoes"] == ["HIV"]  # preservado


def test_update_profile_accepts_bare_string_for_list_key():
    repo = FakePatientRepository()
    service = PatientService(patient_repository=repo)

    health = service.update_profile("abc@c.us", {"condicoes": "HIV"})

    assert health["condicoes"] == ["HIV"]


def test_update_profile_ignores_empty_and_unknown_keys():
    repo = FakePatientRepository()
    service = PatientService(patient_repository=repo)

    health = service.update_profile(
        "abc@c.us", {"notas": "  ", "condicoes": [], "campo_invalido": "x"}
    )

    assert health == {}
