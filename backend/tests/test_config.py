from app.config import Settings


def test_settings_defaults_loadable(monkeypatch):
    monkeypatch.setenv("IP_HASH_SALT", "x" * 64)
    monkeypatch.setenv("ADMIN_PASSWORD", "hunter2hunter")
    s = Settings()
    assert s.consent_version == "v1.0"
    assert s.max_files_per_request == 10
    assert s.mediaflux_client == "stub"


def test_settings_rejects_short_salt(monkeypatch):
    monkeypatch.setenv("IP_HASH_SALT", "tooshort")
    monkeypatch.setenv("ADMIN_PASSWORD", "hunter2hunter")
    import pydantic
    import pytest

    with pytest.raises(pydantic.ValidationError):
        Settings()
