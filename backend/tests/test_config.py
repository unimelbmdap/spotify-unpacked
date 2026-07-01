from app.config import Settings


def test_settings_defaults_loadable(monkeypatch):
    monkeypatch.setenv("IP_HASH_SALT", "x" * 64)
    monkeypatch.setenv("ADMIN_PASSWORD", "hunter2hunter")
    # Clear any value a developer's local .env might set so this test
    # actually verifies the in-code defaults, not whatever the dev typed.
    for var in ("MEDIAFLUX_CLIENT", "MEDIAFLUX_NAMESPACE", "MEDIAFLUX_COLLECTION_ID"):
        monkeypatch.delenv(var, raising=False)
    # Tell Settings to ignore the on-disk .env entirely for this test.
    monkeypatch.setenv("PYDANTIC_SETTINGS_ENV_FILE", "")
    s = Settings(_env_file=None)
    assert s.consent_version == "v1.0"
    assert s.max_files_per_request == 10
    assert s.mediaflux_client == "stub"


def test_participant_codes_file_empty_string_becomes_none(monkeypatch):
    monkeypatch.setenv("IP_HASH_SALT", "x" * 64)
    monkeypatch.setenv("ADMIN_PASSWORD", "hunter2hunter")
    monkeypatch.setenv("PARTICIPANT_CODES_FILE", "")
    s = Settings()
    assert s.participant_codes_file is None


def test_settings_rejects_short_salt(monkeypatch):
    monkeypatch.setenv("IP_HASH_SALT", "tooshort")
    monkeypatch.setenv("ADMIN_PASSWORD", "hunter2hunter")
    import pydantic
    import pytest

    with pytest.raises(pydantic.ValidationError):
        Settings()
